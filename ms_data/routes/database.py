import csv
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import httpx
import psycopg
from fastapi import APIRouter, Depends, Query

from catalog import ROUTES_CATALOG, TABLES

from .auth import check_password

ECO2MIX_CSV_PATH = Path(__file__).parent.parent / "data" / "eco2mix-regional-tr.csv"
# Historique consolidé (2013 -> ~1 mois avant aujourd'hui), même grille que
# eco2mix-regional-tr.csv (12 régions, pas 30 min pour l'historique / 15 min
# pour le temps réel). Prend le relais là où eco2mix-regional-tr.csv (temps
# réel, ~2 derniers mois glissants) s'arrête : les deux alimentent la même
# table mesure_eco2mix_regionale.
ECO2MIX_HISTORIQUE_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "eco2mix-regional-cons-def/records"
)
ODRE_PAGE_SIZE = 100
# L'API v2.1 d'opendatasoft refuse offset + limit > 10 000. Avec 12 régions x
# 48 pas de 30 min/jour (576 lignes/jour), 14 jours reste large sous ce
# plafond (8 064 lignes) : on découpe donc la plage demandée en tranches de
# ODRE_CHUNK_DAYS jours, chacune paginée indépendamment (offset repart à 0).
ODRE_CHUNK_DAYS = 14
# L'API refuse aussi limit > 100 (confirmé : 400 InvalidRESTParameterError au
# delà). Avec ce plafond fixe, la seule façon d'accélérer une plage large
# (une année ~= 2 200 requêtes) est de paralléliser les pages plutôt que de
# les attendre une par une.
ODRE_MAX_CONCURRENCY = 8
# Grille fixe du dataset : régions RTE métropole (hors Corse) x pas de 30 min.
ODRE_REGIONS_COUNT = 12
ODRE_SLOTS_PER_DAY = 48

# relationnal.db est désormais la source lue par ms_dijkstra (graph/datastore.py)
# via un chemin cross-service vers ms_data/data.
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "relationnal.db"
SCHEMA_PATH = DATA_DIR / "mcd_analytique.sql"
# Même fichier que celui monté dans le conteneur Postgres pour le bootstrap
# initial (docker-entrypoint-initdb.d) : voir postgres/docker-compose.yml.
POSTGRES_SCHEMA_PATH = Path(__file__).parent.parent / "postgres" / "init" / "001_schema.sql"

FILIERES = {
    "solar": "Solaire",
    "wind": "Éolien",
}

# Colonnes LOGICAL côté SQLite (stockées en 0/1) qu'il faut recaster en bool
# avant insertion dans les colonnes BOOLEAN de Postgres.
POSTGRES_BOOLEAN_COLUMNS = {
    "region": {"connected_to_continental_grid"},
    "centrale": {
        "available", "values_are_simulated", "minimum_power_fallback_used",
        "values_are_simulated_except_maximum_power",
    },
    "liaison": {"bidirectional", "available", "topology_is_synthetic", "capacity_and_loss_are_simulated"},
    "route": {"authentification_requise"},
    "parametre_route": {"requis"},
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def reset_schema(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("PRAGMA foreign_keys = ON")


def get_postgres_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "energia"),
        password=os.getenv("POSTGRES_PASSWORD", "energia"),
        dbname=os.getenv("POSTGRES_DB", "energia"),
    )


def reset_postgres_schema(pg_conn):
    with pg_conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        for statement in POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8").split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)


def mirror_to_postgres(sqlite_conn):
    """Copie le contenu de relationnal.db (déjà ingéré) vers Postgres, table par
    table, dans l'ordre inverse de TABLES (parents avant enfants) pour
    respecter les contraintes de clé étrangère."""
    pg_conn = get_postgres_connection()
    try:
        reset_postgres_schema(pg_conn)
        for table in reversed(TABLES):
            columns = [row[1] for row in sqlite_conn.execute(f"PRAGMA table_info({table})")]
            rows = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            if not rows:
                continue
            boolean_columns = POSTGRES_BOOLEAN_COLUMNS.get(table, set())
            typed_rows = [
                tuple(
                    bool(value) if col in boolean_columns and value is not None else value
                    for col, value in zip(columns, row)
                )
                for row in rows
            ]
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            with pg_conn.cursor() as cur:
                cur.executemany(insert_sql, typed_rows)
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()


def _load(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_data_json(conn):
    raw = _load("data.json")

    for r in raw.get("regions", []):
        centroid = r.get("centroid", {})
        notes = r.get("data_notes", {})
        conn.execute(
            """
            INSERT INTO region (
                id, insee_code, name, latitude, longitude,
                population_2023, annual_consumption_twh2024,
                annual_consumption_mw_2024, illustrative_peak_consumption_mw,
                connected_to_continental_grid, data_notes_population,
                data_notes_illustrative_peak, data_notes_consumption
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["id"], r.get("insee_code", ""), r["name"],
                centroid.get("latitude", 0.0), centroid.get("longitude", 0.0),
                r.get("population_2023", 0), r.get("annual_consumption_twh_2024", 0.0),
                r.get("average_consumption_mw_2024", 0.0),
                r.get("illustrative_peak_consumption_mw", 0.0),
                r.get("connected_to_continental_grid", True),
                notes.get("population"), notes.get("illustrative_peak"),
                notes.get("consumption"),
            ),
        )

    for p in raw.get("plants", []):
        location = p["location"]
        sim = p.get("simulation", {})
        conn.execute(
            """
            INSERT INTO centrale (
                id, name, latitude, longitude, commune, departement,
                reactor_count, installed_power_mw, available, initial_output_mw,
                initial_load_ratio, soft_upper_bound_mw, soft_upper_bound_ratio,
                initial_dispatchable_margin_mw, max_ramp_up_mw_15_min,
                technical_penalty, values_are_simulated, id_1
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"], p["name"], location["latitude"], location["longitude"],
                location.get("commune", ""), location.get("department", ""),
                p.get("reactor_count", len(p.get("reactors", []))),
                p["installed_power_mw"], sim.get("available", True),
                sim.get("initial_output_mw", 0.0), sim.get("initial_load_ratio", 0.0),
                sim.get("soft_upper_bound_mw", p["installed_power_mw"]),
                sim.get("soft_upper_bound_ratio", 0.95),
                sim.get("initial_dispatchable_margin_mw", 0.0),
                sim.get("max_ramp_up_mw_per_15_min", 0.0),
                sim.get("technical_penalty", 1.0),
                sim.get("values_are_simulated", True),
                location["region_id"],
            ),
        )

        for reactor in p.get("reactors", []):
            conn.execute(
                """
                INSERT INTO reacteur (
                    id_reacteur, name, installed_power_mw, minimum_design_power_mw,
                    status, industrial_commisionning_date, data_kind, id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reactor["id"], reactor["name"], reactor["installed_power_mw"],
                    reactor.get("minimum_design_power_mw", 0),
                    reactor.get("status", "unknown"),
                    reactor.get("industrial_commissioning_date"),
                    reactor.get("data_kind"),
                    p["id"],
                ),
            )

    for edge in raw.get("plant_edges", []):
        conn.execute(
            """
            INSERT INTO liaison (
                id, bidirectional, distance_km, loss_percent, max_transfer_mw,
                available, topology_is_synthetic, capacity_and_loss_are_simulated,
                id_1, id_2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge["id"], edge.get("bidirectional", True), edge["geodesic_distance_km"],
                edge["estimated_loss_percent"], edge["max_transfer_mw"],
                edge.get("available", True), edge.get("topology_is_synthetic", False),
                edge.get("capacity_and_loss_are_simulated", False),
                edge["from"], edge["to"],
            ),
        )

    for r in raw.get("regions", []):
        for plant_id in r.get("external_entry_plant_ids", []):
            conn.execute(
                "INSERT OR IGNORE INTO accessible_via (id, id_1) VALUES (?, ?)",
                (plant_id, r["id"]),
            )

    scenario_id = 0
    override_id = 0
    for s in raw.get("example_scenarios", []):
        scenario_id += 1
        conn.execute(
            """
            INSERT INTO scenario (id, description, expected_result, additionnal_demand_mw, id_1)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                scenario_id, s.get("description"), s.get("expected_result"),
                s.get("additional_demand_mw", 0.0), s["region_id"],
            ),
        )
        for plant_id, override in s.get("plant_overrides", {}).items():
            override_id += 1
            conn.execute(
                """
                INSERT INTO scenario_override (id, initial_output_mw, soft_upper_bound_mw, id_1, id_2)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    override_id, override.get("initial_output_mw"),
                    override.get("soft_upper_bound_mw"), plant_id, scenario_id,
                ),
            )

    return {
        "region": len(raw.get("regions", [])),
        "centrale": len(raw.get("plants", [])),
        "liaison": len(raw.get("plant_edges", [])),
        "scenario": scenario_id,
        "scenario_override": override_id,
    }


def ingest_nuclear_temporal_params(conn):
    raw = _load("energia_parametres_temporels_nucleaire.json")

    count = 0
    for p in raw.get("plants", []):
        conn.execute(
            """
            UPDATE centrale SET
                initial_output_mw_at_23_45_previous_day = ?,
                minimum_operating_power_mw = ?,
                max_ramp_down_mw_per_15min = ?,
                minimum_power_fallback_used = ?,
                values_are_simulated_except_maximum_power = ?
            WHERE id = ?
            """,
            (
                p.get("initial_output_mw_at_23_45_previous_day"),
                p.get("minimum_operating_power_mw"),
                p.get("max_ramp_down_mw_per_15_min"),
                p.get("minimum_power_fallback_used", False),
                p.get("values_are_simulated_except_maximum_power", True),
                p["plant_id"],
            ),
        )
        count += 1

    return {"centrale_enrichie": count}


def ingest_capacite_installee_non_pilotable(conn):
    raw = _load("energia-production-non-pilotable.json")

    for code, libelle in FILIERES.items():
        conn.execute(
            "INSERT OR IGNORE INTO filiere (code_filiere, libelle_filiere) VALUES (?, ?)",
            (code, libelle),
        )

    capacite_id = 0
    for r in raw.get("regions", []):
        for code_filiere, capacite_mw in r.get("synthetic_installed_capacity_mw", {}).items():
            capacite_id += 1
            conn.execute(
                """
                INSERT INTO capacitee_instalee_non_pilotable (id, capacitee_mw, id_1, code_filiere)
                VALUES (?, ?, ?, ?)
                """,
                (capacite_id, capacite_mw, r["id"], code_filiere),
            )

    return {"capacitee_instalee_non_pilotable": capacite_id}


def ingest_routes(conn):
    """Peuple route/parametre_route depuis ROUTES_CATALOG."""
    route_id = 0
    param_id = 0
    for r in ROUTES_CATALOG:
        route_id += 1
        conn.execute(
            """
            INSERT INTO route (id, chemin, methode, fichier_source, description, authentification_requise)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (route_id, r["chemin"], r["methode"], r["fichier_source"], r["description"], r["auth"]),
        )
        for p in r["parametres"]:
            param_id += 1
            conn.execute(
                """
                INSERT INTO parametre_route (id, nom, emplacement, type, requis, valeur_defaut, id_route)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    param_id, p["nom"], p["emplacement"], p["type"], p["requis"],
                    p.get("defaut"), route_id,
                ),
            )

    return {"route": route_id, "parametre_route": param_id}


def run_ingestion():
    """Recrée le schéma depuis mcd_analytique.sql puis recharge tous les JSON
    de ms_dijkstra/data dans SQLite, puis mirroir le résultat vers Postgres
    (ms_database). Idempotent : rejouable sans accumulation de doublons."""
    conn = get_connection()
    try:
        reset_schema(conn)
        summary = {}
        summary.update(ingest_data_json(conn))
        summary.update(ingest_nuclear_temporal_params(conn))
        summary.update(ingest_capacite_installee_non_pilotable(conn))
        summary.update(ingest_routes(conn))
        conn.commit()
        mirror_to_postgres(conn)
        return summary
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _region_ids_by_insee(conn):
    return dict(conn.execute("SELECT insee_code, id FROM region"))


def _upsert_postgres(table, columns, key_columns, rows):
    if not rows:
        return
    update_columns = [c for c in columns if c not in key_columns]
    placeholders = ", ".join(["%s"] * len(columns))
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({', '.join(key_columns)}) DO UPDATE SET {set_clause}"
    )
    pg_conn = get_postgres_connection()
    try:
        with pg_conn.cursor() as cur:
            cur.executemany(sql, rows)
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()


# Colonnes retenues côté eco2mix : consommation électrique + solaire/éolien
# (seule production "non pilotable" utilisée par le calcul du besoin résiduel).
# Thermique/nucléaire/hydraulique/pompage/bioénergies/échanges physiques/
# stockage batterie et les taux TCO/TCH sont hors périmètre et non consommés
# par aucun endpoint : volontairement pas ingérés.
MESURE_ECO2MIX_COLUMNS = ["id_region", "date_heure", "nature", "consommation_mw", "eolien_mw", "solaire_mw"]

# Colonnes -> en-têtes du CSV eco2mix-regional-tr.csv (pour les colonnes MW,
# id_region/date_heure/nature sont dérivées séparément).
_ECO2MIX_CSV_FIELD_MAP = {
    "consommation_mw": "Consommation (MW)",
    "eolien_mw": "Eolien (MW)",
    "solaire_mw": "Solaire (MW)",
}


def _to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def _read_eco2mix_rows(region_ids, date_debut, date_fin):
    with open(ECO2MIX_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if not (date_debut <= row["Date"] <= date_fin):
                continue
            id_region = region_ids.get(row["Code INSEE région"])
            if id_region is None:
                continue
            yield (
                id_region, row["Date - Heure"], row["Nature"],
                *(
                    _to_float(row[_ECO2MIX_CSV_FIELD_MAP[c]])
                    for c in MESURE_ECO2MIX_COLUMNS[3:]
                ),
            )


def ingest_eco2mix_regionale(conn, date_debut, date_fin):
    """Ingestion manuelle, par plage de dates incluse (YYYY-MM-DD), depuis
    eco2mix-regional-tr.csv (RTE). Idempotent : upsert sur (id_region, date_heure),
    aussi bien côté relationnal.db que Postgres."""
    region_ids = _region_ids_by_insee(conn)
    rows = list(_read_eco2mix_rows(region_ids, date_debut, date_fin))

    conn.executemany(
        f"""
        INSERT OR REPLACE INTO mesure_eco2mix_regionale ({", ".join(MESURE_ECO2MIX_COLUMNS)})
        VALUES ({", ".join(["?"] * len(MESURE_ECO2MIX_COLUMNS))})
        """,
        rows,
    )
    conn.commit()
    _upsert_postgres(
        "mesure_eco2mix_regionale", MESURE_ECO2MIX_COLUMNS,
        ["id_region", "date_heure"], rows,
    )
    return {"mesure_eco2mix_regionale": len(rows)}


def _date_chunks(date_debut, date_fin, chunk_days=ODRE_CHUNK_DAYS):
    """Découpe [date_debut, date_fin] (YYYY-MM-DD, incluses) en tranches
    contiguës d'au plus chunk_days jours."""
    debut = date.fromisoformat(date_debut)
    fin = date.fromisoformat(date_fin)
    while debut <= fin:
        chunk_fin = min(debut + timedelta(days=chunk_days - 1), fin)
        yield debut.isoformat(), chunk_fin.isoformat()
        debut = chunk_fin + timedelta(days=1)


def _expected_page_count(chunk_debut, chunk_fin):
    """Nombre de pages à interroger pour couvrir une tranche, en se basant sur
    la grille fixe du dataset (régions x pas de 30 min/jour). +2 pages de
    marge pour absorber un léger écart (ex: un pas manquant) sans tronquer."""
    jours = (date.fromisoformat(chunk_fin) - date.fromisoformat(chunk_debut)).days + 1
    lignes_attendues = jours * ODRE_REGIONS_COUNT * ODRE_SLOTS_PER_DAY
    return lignes_attendues // ODRE_PAGE_SIZE + 2


def _fetch_odre_page(client, url, where, offset):
    # order_by explicite : sans lui, le tri par défaut n'est pas garanti
    # stable entre deux appels offset différents faits en parallèle, ce qui
    # peut faire apparaître la même ligne sur deux pages (constaté : quelques
    # doublons sur une plage d'un an sans order_by). INSERT OR REPLACE
    # dédoublonne de toute façon sur (id_region, date_heure), mais autant
    # avoir une pagination correcte à la source.
    response = client.get(
        url,
        params={
            "where": where, "limit": ODRE_PAGE_SIZE, "offset": offset,
            "order_by": "date_heure,code_insee_region",
        },
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _fetch_odre_records(url, date_debut, date_fin):
    """Parcourt l'API paginée (v2.1 /records) d'un dataset ODRE sur la grille
    (12 régions x pas 30 min) d'eco2mix-regional-cons-def, en découpant la
    plage en tranches de ODRE_CHUNK_DAYS jours (l'API refuse offset+limit
    > 10 000) et en
    interrogeant les pages de chaque tranche EN PARALLÈLE (ODRE_MAX_CONCURRENCY
    requêtes à la fois) plutôt qu'une par une : le nombre de pages par tranche
    est déductible à l'avance de la grille fixe du dataset, donc pas besoin
    d'attendre une page pour savoir combien en demander ensuite. Pas d'export
    JSON brut global : uniquement l'API paginée."""
    with httpx.Client(timeout=30.0) as client, ThreadPoolExecutor(max_workers=ODRE_MAX_CONCURRENCY) as pool:
        futures = []
        for chunk_debut, chunk_fin in _date_chunks(date_debut, date_fin):
            # Filtre sur date_heure, pas date : sur eco2mix-regional-cons-def,
            # la colonne "date" est typée text côté ODS (l'API refuse toute
            # comparaison dessus, même via IN [date'...'..date'...']), alors
            # que date_heure est un vrai datetime sur les deux datasets.
            where = f"date_heure in [date'{chunk_debut}'..date'{chunk_fin}']"
            for offset in range(0, _expected_page_count(chunk_debut, chunk_fin) * ODRE_PAGE_SIZE, ODRE_PAGE_SIZE):
                futures.append(pool.submit(_fetch_odre_page, client, url, where, offset))
        for future in futures:
            yield from future.result()


def ingest_eco2mix_historique_regionale(conn, date_debut, date_fin):
    """Ingestion manuelle, par plage de dates incluse (YYYY-MM-DD), depuis
    l'API ODRE eco2mix-regional-cons-def (données consolidées, 2013 ->
    ~1 mois avant aujourd'hui). Alimente la MÊME table que
    ingest_eco2mix_regionale (le CSV temps réel) : idempotent, upsert sur
    (id_region, date_heure), aussi bien côté relationnal.db que Postgres."""
    region_ids = _region_ids_by_insee(conn)
    rows = []
    for record in _fetch_odre_records(ECO2MIX_HISTORIQUE_URL, date_debut, date_fin):
        id_region = region_ids.get(record.get("code_insee_region"))
        if id_region is None:
            continue
        rows.append((
            id_region, record.get("date_heure"), record.get("nature"),
            _to_float(record.get("consommation")),
            _to_float(record.get("eolien")), _to_float(record.get("solaire")),
        ))

    conn.executemany(
        f"""
        INSERT OR REPLACE INTO mesure_eco2mix_regionale ({", ".join(MESURE_ECO2MIX_COLUMNS)})
        VALUES ({", ".join(["?"] * len(MESURE_ECO2MIX_COLUMNS))})
        """,
        rows,
    )
    conn.commit()
    _upsert_postgres(
        "mesure_eco2mix_regionale", MESURE_ECO2MIX_COLUMNS,
        ["id_region", "date_heure"], rows,
    )
    return {"mesure_eco2mix_regionale": len(rows)}


router = APIRouter(prefix="/database", dependencies=[Depends(check_password)])


@router.post("/ingest")
def ingest():
    summary = run_ingestion()
    return {"message": "Ingestion terminée", "lignes_inserees": summary}


@router.post("/ingest-eco2mix")
def ingest_eco2mix(
    date_debut: str = Query(..., description="YYYY-MM-DD, incluse"),
    date_fin: str = Query(..., description="YYYY-MM-DD, incluse"),
):
    conn = get_connection()
    try:
        summary = ingest_eco2mix_regionale(conn, date_debut, date_fin)
    finally:
        conn.close()
    return {"message": "Ingestion eco2mix terminée", "lignes_inserees": summary}


@router.post("/ingest-eco2mix-historique")
def ingest_eco2mix_historique(
    date_debut: str = Query(..., description="YYYY-MM-DD, incluse"),
    date_fin: str = Query(..., description="YYYY-MM-DD, incluse"),
):
    conn = get_connection()
    try:
        summary = ingest_eco2mix_historique_regionale(conn, date_debut, date_fin)
    finally:
        conn.close()
    return {"message": "Ingestion eco2mix historique terminée", "lignes_inserees": summary}
