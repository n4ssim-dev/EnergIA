import csv
import json
import os
import sqlite3
from pathlib import Path

import httpx
import psycopg
from fastapi import APIRouter, Depends, Query

from catalog import ROUTES_CATALOG, TABLES

from .auth import check_password

ECO2MIX_CSV_PATH = Path(__file__).parent.parent / "data" / "eco2mix-regional-tr.csv"
ODRE_CONSOMMATION_BRUTE_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "consommation-quotidienne-brute-regionale/records"
)
ODRE_PAGE_SIZE = 100

# analytics.db est désormais la source lue par ms_dijkstra (graph/datastore.py)
# via un chemin cross-service vers ms_data/data.
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "analytics.db"
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
    """Copie le contenu de analytics.db (déjà ingéré) vers Postgres, table par
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


def ingest_scenarios_phase3(conn):
    raw = _load("energia-scenarios-phase3-exemples.json")

    event_count = 0
    for s in raw.get("scenarios", []):
        conn.execute(
            "INSERT INTO scenario_phase3 (id_scenario_phase3, name) VALUES (?, ?)",
            (s["id"], s.get("name")),
        )
        for i, event in enumerate(s.get("events", [])):
            event_count += 1
            conn.execute(
                """
                INSERT INTO fait_evenement_consommation (
                    id_evenement_consommation, type, delta_mw, delta_percent,
                    debut, fin, id_scenario_phase3, id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{s['id']}#{i}", event.get("type"), event.get("delta_mw"),
                    event.get("delta_percent"), event.get("start"), event.get("end"),
                    s["id"], event["region_id"],
                ),
            )

    return {
        "scenario_phase3": len(raw.get("scenarios", [])),
        "fait_evenement_consommation": event_count,
    }


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
        summary.update(ingest_scenarios_phase3(conn))
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


MESURE_ECO2MIX_COLUMNS = [
    "id_region", "date_heure", "nature", "consommation_mw", "thermique_mw",
    "nucleaire_mw", "eolien_mw", "solaire_mw", "hydraulique_mw", "pompage_mw",
    "bioenergies_mw", "ech_physiques_mw", "stockage_batterie_mw",
    "destockage_batterie_mw", "tco_thermique", "tch_thermique", "tco_nucleaire",
    "tch_nucleaire", "tco_eolien", "tch_eolien", "tco_solaire", "tch_solaire",
    "tco_hydraulique", "tch_hydraulique", "tco_bioenergies", "tch_bioenergies",
]

# Colonnes -> en-têtes du CSV eco2mix-regional-tr.csv (pour les colonnes MW/%,
# id_region/date_heure/nature sont dérivées séparément).
_ECO2MIX_CSV_FIELD_MAP = {
    "consommation_mw": "Consommation (MW)",
    "thermique_mw": "Thermique (MW)",
    "nucleaire_mw": "Nucléaire (MW)",
    "eolien_mw": "Eolien (MW)",
    "solaire_mw": "Solaire (MW)",
    "hydraulique_mw": "Hydraulique (MW)",
    "pompage_mw": "Pompage (MW)",
    "bioenergies_mw": "Bioénergies (MW)",
    "ech_physiques_mw": "Ech. physiques (MW)",
    "stockage_batterie_mw": "Stockage batterie",
    "destockage_batterie_mw": "Déstockage batterie",
    "tco_thermique": "TCO Thermique (%)",
    "tch_thermique": "TCH Thermique (%)",
    "tco_nucleaire": "TCO Nucléaire (%)",
    "tch_nucleaire": "TCH Nucléaire (%)",
    "tco_eolien": "TCO Eolien (%)",
    "tch_eolien": "TCH Eolien (%)",
    "tco_solaire": "TCO Solaire (%)",
    "tch_solaire": "TCH Solaire (%)",
    "tco_hydraulique": "TCO Hydraulique (%)",
    "tch_hydraulique": "TCH Hydraulique (%)",
    "tco_bioenergies": "TCO Bioénergies (%)",
    "tch_bioenergies": "TCH Bioénergies (%)",
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
    aussi bien côté analytics.db que Postgres."""
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


MESURE_CONSOMMATION_BRUTE_COLUMNS = [
    "id_region", "date_heure", "consommation_brute_gaz_grtgaz", "statut_grtgaz",
    "consommation_brute_gaz_terega", "statut_terega", "consommation_brute_gaz_totale",
    "consommation_brute_electricite_rte", "statut_rte", "consommation_brute_totale",
    "flag_ignore",
]


def _fetch_odre_records(date_debut, date_fin):
    """Parcourt l'API paginée (v2.1 /records) du dataset ODRE
    consommation-quotidienne-brute-regionale, par lots de ODRE_PAGE_SIZE
    (pas d'export JSON brut global)."""
    where = f"date in [date'{date_debut}'..date'{date_fin}']"
    offset = 0
    with httpx.Client(timeout=30.0) as client:
        while True:
            response = client.get(
                ODRE_CONSOMMATION_BRUTE_URL,
                params={"where": where, "limit": ODRE_PAGE_SIZE, "offset": offset},
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                return
            yield from results
            if len(results) < ODRE_PAGE_SIZE:
                return
            offset += ODRE_PAGE_SIZE


def ingest_consommation_brute_regionale(conn, date_debut, date_fin):
    """Ingestion manuelle, par plage de dates incluse (YYYY-MM-DD), depuis
    l'API ODRE consommation-quotidienne-brute-regionale. Idempotent : upsert
    sur (id_region, date_heure), aussi bien côté analytics.db que Postgres."""
    region_ids = _region_ids_by_insee(conn)
    rows = []
    for record in _fetch_odre_records(date_debut, date_fin):
        id_region = region_ids.get(record.get("code_insee_region"))
        if id_region is None:
            continue
        rows.append((
            id_region, record.get("date_heure"),
            record.get("consommation_brute_gaz_grtgaz"), record.get("statut_grtgaz"),
            record.get("consommation_brute_gaz_terega"), record.get("statut_terega"),
            record.get("consommation_brute_gaz_totale"),
            record.get("consommation_brute_electricite_rte"), record.get("statut_rte"),
            record.get("consommation_brute_totale"), record.get("flag_ignore"),
        ))

    conn.executemany(
        f"""
        INSERT OR REPLACE INTO mesure_consommation_brute_regionale
        ({", ".join(MESURE_CONSOMMATION_BRUTE_COLUMNS)})
        VALUES ({", ".join(["?"] * len(MESURE_CONSOMMATION_BRUTE_COLUMNS))})
        """,
        rows,
    )
    conn.commit()
    _upsert_postgres(
        "mesure_consommation_brute_regionale", MESURE_CONSOMMATION_BRUTE_COLUMNS,
        ["id_region", "date_heure"], rows,
    )
    return {"mesure_consommation_brute_regionale": len(rows)}


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


@router.post("/ingest-consommation-brute")
def ingest_consommation_brute(
    date_debut: str = Query(..., description="YYYY-MM-DD, incluse"),
    date_fin: str = Query(..., description="YYYY-MM-DD, incluse"),
):
    conn = get_connection()
    try:
        summary = ingest_consommation_brute_regionale(conn, date_debut, date_fin)
    finally:
        conn.close()
    return {"message": "Ingestion consommation brute terminée", "lignes_inserees": summary}
