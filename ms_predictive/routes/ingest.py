import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import httpx
import psycopg
from fastapi import APIRouter, Query

ODRE_TEMPERATURE_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
    "temperature-quotidienne-regionale/records"
)
ODRE_PAGE_SIZE = 100
# Grain journalier (pas 15/30 min comme les autres sources ODRE) : une
# fenêtre de 200 jours x 13 régions = 2 600 lignes, largement sous le
# plafond offset+limit <= 10 000 de l'API.
ODRE_CHUNK_DAYS = 200
ODRE_MAX_CONCURRENCY = 8
# Ce dataset météo couvre la Corse (contrairement aux données RTE
# eco2mix/ODRE électricité, qui n'en ont que 12) : 13 régions, pas 12.
TEMPERATURE_REGIONS_COUNT = 13


def get_target_connection():
    """Base ms_predictive (dim_*/fait_consommation)."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5435"),
        user=os.getenv("POSTGRES_USER", "energia"),
        password=os.getenv("POSTGRES_PASSWORD", "energia"),
        dbname=os.getenv("POSTGRES_DB", "energia_predictive"),
    )


def get_source_connection():
    """Base ms_data (relationnelle) : source de region/mesure_eco2mix_regionale."""
    return psycopg.connect(
        host=os.getenv("SOURCE_POSTGRES_HOST", "localhost"),
        port=os.getenv("SOURCE_POSTGRES_PORT", "5434"),
        user=os.getenv("SOURCE_POSTGRES_USER", "energia"),
        password=os.getenv("SOURCE_POSTGRES_PASSWORD", "energia"),
        dbname=os.getenv("SOURCE_POSTGRES_DB", "energia"),
    )


def _upsert(conn, table, columns, key_columns, rows):
    if not rows:
        return
    update_columns = [c for c in columns if c not in key_columns]
    placeholders = ", ".join(["%s"] * len(columns))
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({', '.join(key_columns)}) DO UPDATE SET {set_clause}"
    )
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()


# ---------------------------------------------------------------------------
# dim_regionale : depuis ms_data.region (démographie = population_2023).
# part_indus_lourde n'a pas de source branchée pour l'instant (laissée NULL) :
# https://opendata.agenceore.fr/.../consommation-annuelle-d-electricite-et-gaz-par-region
# reste à intégrer.
# ---------------------------------------------------------------------------

DIM_REGIONALE_COLUMNS = ["id_region", "code_insee", "nom", "demographie", "part_indus_lourde"]


def ingest_dim_regionale(target_conn, source_conn):
    with source_conn.cursor() as cur:
        cur.execute("SELECT id, insee_code, name, population_2023 FROM region")
        rows = [
            (id_region, int(insee_code), nom, population_2023, None)
            for id_region, insee_code, nom, population_2023 in cur.fetchall()
        ]
    _upsert(target_conn, "dim_regionale", DIM_REGIONALE_COLUMNS, ["id_region"], rows)
    return {"dim_regionale": len(rows)}


# ---------------------------------------------------------------------------
# dim_temps : calculée localement (pas de source externe), à partir des
# date_heure réellement rencontrées dans les données ingérées.
# ---------------------------------------------------------------------------

JOURS_SEMAINE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
DIM_TEMPS_COLUMNS = [
    "date_heure", "annee", "saison", "mois", "jour_semaine",
    "quart_heure", "est_weekend", "est_ferie",
]


def _saison(mois):
    if mois in (12, 1, 2):
        return "hiver"
    if mois in (3, 4, 5):
        return "printemps"
    if mois in (6, 7, 8):
        return "ete"
    return "automne"


def _paques(annee):
    """Dimanche de Pâques (algorithme de Meeus/Jones/Butcher, calendrier grégorien)."""
    a = annee % 19
    b = annee // 100
    c = annee % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = (h + l - 7 * m + 114) % 31 + 1
    return date(annee, mois, jour)


def _jours_feries(annee):
    """Jours fériés français fixes + mobiles (calculés localement, sans appel
    externe : cf. https://www.data.gouv.fr/dataservices/jours-feries pour une
    source API si on veut remplacer ce calcul plus tard)."""
    paques = _paques(annee)
    return {
        date(annee, 1, 1), date(annee, 5, 1), date(annee, 5, 8),
        date(annee, 7, 14), date(annee, 8, 15), date(annee, 11, 1),
        date(annee, 11, 11), date(annee, 12, 25),
        paques + timedelta(days=1),   # lundi de Pâques
        paques + timedelta(days=39),  # Ascension
        paques + timedelta(days=50),  # lundi de Pentecôte
    }


def _derive_temps(dt):
    jour_semaine = JOURS_SEMAINE[dt.weekday()]
    return (
        dt, dt.year, _saison(dt.month), dt.month, jour_semaine,
        dt.minute // 15, jour_semaine in ("samedi", "dimanche"),
        dt.date() in _jours_feries(dt.year),
    )


def _ensure_dim_temps(conn, timestamps):
    distincts = sorted({ts for ts in timestamps})
    rows = [_derive_temps(ts) for ts in distincts]
    _upsert(conn, "dim_temps", DIM_TEMPS_COLUMNS, ["date_heure"], rows)
    return len(rows)


# ---------------------------------------------------------------------------
# fait_consommation : depuis ms_data.mesure_eco2mix_regionale (relationnal.db
# mirroré vers le Postgres de ms_data). id_conso déterministe (id_region +
# date_heure) pour que l'ingestion soit idempotente sur une plage qui recouvre
# une ingestion précédente.
# ---------------------------------------------------------------------------

FAIT_CONSOMMATION_COLUMNS = ["id_conso", "consommation_mw", "date_heure", "id_region"]


def ingest_fait_consommation(target_conn, source_conn, date_debut, date_fin):
    with source_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id_region, date_heure, consommation_mw
            FROM mesure_eco2mix_regionale
            WHERE date_heure >= %s AND date_heure < %s
            """,
            (date_debut, date_fin),
        )
        source_rows = cur.fetchall()

    _ensure_dim_temps(target_conn, (date_heure for _, date_heure, _ in source_rows))

    # consommation_mw manquante à la source (trou réel du flux RTE, ex.
    # 2026-09-04T10:00 bourgogne_franche_comte) : rien à enregistrer, on saute
    # la ligne plutôt que de violer le NOT NULL de fait_consommation.
    rows = [
        (f"{id_region}_{date_heure.isoformat()}", consommation_mw, date_heure, id_region)
        for id_region, date_heure, consommation_mw in source_rows
        if consommation_mw is not None
    ]
    ignorees = len(source_rows) - len(rows)
    _upsert(target_conn, "fait_consommation", FAIT_CONSOMMATION_COLUMNS, ["id_conso"], rows)
    return {"fait_consommation": len(rows), "consommation_manquante_ignoree": ignorees}


# ---------------------------------------------------------------------------
# dim_event : pas de source externe. Détection statistique d'anomalies de
# consommation par région : z-score de la moyenne journalière par rapport à
# une moyenne glissante sur EVENT_WINDOW_DAYS jours précédents (le jour
# courant est exclu de sa propre baseline). |z| >= EVENT_Z_THRESHOLD -> une
# ligne est créée ; sinon "neutre" = simplement pas de ligne (cohérent avec
# le fait que id_region+date_event, comme dim_meteo, se joint dynamiquement
# depuis fait_consommation sans FK stockée). Le signe de taux_impact_attendu
# donne positif/négatif ; tanh(z / EVENT_TANH_SCALE) écrase la magnitude
# proprement dans [-1, 1].
# ---------------------------------------------------------------------------

EVENT_WINDOW_DAYS = 14
EVENT_MIN_HISTORY_DAYS = 7
EVENT_Z_THRESHOLD = 2.0
EVENT_TANH_SCALE = 3.0

DIM_EVENT_COLUMNS = ["id_region", "date_event", "taux_impact_attendu"]


def ingest_dim_event(target_conn):
    with target_conn.cursor() as cur:
        cur.execute(
            """
            WITH quotidien AS (
                SELECT id_region, DATE(date_heure) AS jour, AVG(consommation_mw) AS moyenne_jour
                FROM fait_consommation
                GROUP BY id_region, DATE(date_heure)
            ),
            avec_bandes AS (
                SELECT
                    id_region, jour, moyenne_jour,
                    AVG(moyenne_jour) OVER w AS rolling_mean,
                    STDDEV_SAMP(moyenne_jour) OVER w AS rolling_std,
                    COUNT(*) OVER w AS n_historique
                FROM quotidien
                WINDOW w AS (
                    PARTITION BY id_region ORDER BY jour
                    ROWS BETWEEN %(window)s PRECEDING AND 1 PRECEDING
                )
            )
            SELECT
                id_region, jour,
                TANH((moyenne_jour - rolling_mean) / rolling_std / %(scale)s) AS taux
            FROM avec_bandes
            WHERE n_historique >= %(min_history)s
              AND rolling_std > 0
              AND ABS((moyenne_jour - rolling_mean) / rolling_std) >= %(threshold)s
            """,
            {
                "window": EVENT_WINDOW_DAYS, "min_history": EVENT_MIN_HISTORY_DAYS,
                "threshold": EVENT_Z_THRESHOLD, "scale": EVENT_TANH_SCALE,
            },
        )
        rows = cur.fetchall()

    with target_conn.cursor() as cur:
        cur.execute("DELETE FROM dim_event")
    _upsert(target_conn, "dim_event", DIM_EVENT_COLUMNS, ["date_event", "id_region"], rows)
    return {"dim_event": len(rows)}


# ---------------------------------------------------------------------------
# dim_meteo : depuis l'API ODRE temperature-quotidienne-regionale (Rapport.md).
# ---------------------------------------------------------------------------

DIM_METEO_COLUMNS = ["id_region", "date_meteo", "temperature_min", "temperature_max", "temperature_moy"]


def _date_chunks(date_debut, date_fin, chunk_days=ODRE_CHUNK_DAYS):
    debut = date.fromisoformat(date_debut)
    fin = date.fromisoformat(date_fin)
    while debut <= fin:
        chunk_fin = min(debut + timedelta(days=chunk_days - 1), fin)
        yield debut.isoformat(), chunk_fin.isoformat()
        debut = chunk_fin + timedelta(days=1)


def _expected_page_count(chunk_debut, chunk_fin):
    jours = (date.fromisoformat(chunk_fin) - date.fromisoformat(chunk_debut)).days + 1
    return jours * TEMPERATURE_REGIONS_COUNT // ODRE_PAGE_SIZE + 3


def _fetch_temperature_page(client, where, offset):
    response = client.get(
        ODRE_TEMPERATURE_URL,
        params={
            "where": where, "limit": ODRE_PAGE_SIZE, "offset": offset,
            "order_by": "date,code_insee_region",
        },
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _fetch_temperature_records(date_debut, date_fin):
    with httpx.Client(timeout=30.0) as client, ThreadPoolExecutor(max_workers=ODRE_MAX_CONCURRENCY) as pool:
        futures = []
        for chunk_debut, chunk_fin in _date_chunks(date_debut, date_fin):
            where = f"date in [date'{chunk_debut}'..date'{chunk_fin}']"
            for offset in range(0, _expected_page_count(chunk_debut, chunk_fin) * ODRE_PAGE_SIZE, ODRE_PAGE_SIZE):
                futures.append(pool.submit(_fetch_temperature_page, client, where, offset))
        for future in futures:
            yield from future.result()


def ingest_dim_meteo(target_conn, date_debut, date_fin):
    with target_conn.cursor() as cur:
        cur.execute("SELECT code_insee, id_region FROM dim_regionale")
        region_ids = {str(code_insee): id_region for code_insee, id_region in cur.fetchall()}

        cur.execute(
            "SELECT id_region, date_meteo FROM dim_meteo WHERE date_meteo BETWEEN %s AND %s",
            (date_debut, date_fin),
        )
        deja_presents = set(cur.fetchall())

    rows = []
    for record in _fetch_temperature_records(date_debut, date_fin):
        id_region = region_ids.get(str(record.get("code_insee_region")))
        if id_region is None:
            continue
        date_meteo = date.fromisoformat(record.get("date"))
        if (id_region, date_meteo) in deja_presents:
            continue
        rows.append((
            id_region, record.get("date"),
            record.get("tmin"), record.get("tmax"), record.get("tmoy"),
        ))

    _upsert(target_conn, "dim_meteo", DIM_METEO_COLUMNS, ["date_meteo", "id_region"], rows)

    with target_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM dim_meteo")
        total = cur.fetchone()[0]

    return {"dim_meteo_ingerees": len(rows), "dim_meteo_total": total}


router = APIRouter(prefix="/ingest")


@router.post("/dim-regionale")
def ingest_dim_regionale_route():
    target_conn = get_target_connection()
    source_conn = get_source_connection()
    try:
        return ingest_dim_regionale(target_conn, source_conn)
    finally:
        target_conn.close()
        source_conn.close()


@router.post("/fait-consommation")
def ingest_fait_consommation_route(
    date_debut: str = Query(..., description="YYYY-MM-DD, incluse"),
    date_fin: str = Query(..., description="YYYY-MM-DD, exclue"),
):
    target_conn = get_target_connection()
    source_conn = get_source_connection()
    try:
        return ingest_fait_consommation(target_conn, source_conn, date_debut, date_fin)
    finally:
        target_conn.close()
        source_conn.close()


@router.post("/dim-meteo")
def ingest_dim_meteo_route(
    date_debut: str = Query(..., description="YYYY-MM-DD, incluse"),
    date_fin: str = Query(..., description="YYYY-MM-DD, incluse"),
):
    target_conn = get_target_connection()
    try:
        return ingest_dim_meteo(target_conn, date_debut, date_fin)
    finally:
        target_conn.close()


@router.post("/dim-event")
def ingest_dim_event_route():
    """Recalcule dim_event sur tout l'historique de fait_consommation déjà
    ingéré (pas de plage de dates : la baseline glissante a besoin de
    l'historique complet par région)."""
    target_conn = get_target_connection()
    try:
        return ingest_dim_event(target_conn)
    finally:
        target_conn.close()
