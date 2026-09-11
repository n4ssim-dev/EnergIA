from fastapi import APIRouter, Query

from routes.ingest import get_target_connection

router = APIRouter(prefix="/diagnostics")


# ---------------------------------------------------------------------------
# dates-manquantes : compare les (id_region, jour) de fait_consommation à
# leur présence dans dim_meteo et dim_event, qui se joignent dynamiquement
# (sans FK, contrairement à dim_temps -> fait_consommation a une FK sur
# dim_temps(date_heure), donc une ligne dim_temps manquante y est
# structurellement impossible et n'a pas besoin d'être vérifiée).
#
# dim_event est sparse par construction (une ligne = anomalie détectée,
# cf. ingest_dim_event) : son "manquant" est la normale, pas un défaut de
# données comme pour dim_meteo. On ne liste donc pas ses jours manquants en
# détail (des centaines de milliers de lignes sans intérêt), seulement le
# total et le chevauchement avec dim_meteo.
# ---------------------------------------------------------------------------

JOURS_REGION_CTE = """
    WITH jours AS (
        SELECT DISTINCT id_region, DATE(date_heure) AS jour
        FROM fait_consommation
    )
"""


@router.get("/dates-manquantes")
def dates_manquantes(limite: int = Query(200, ge=1, le=5000)):
    conn = get_target_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                JOURS_REGION_CTE
                + """
                , diag AS (
                    SELECT
                        j.id_region,
                        j.jour,
                        (dm.id_region IS NULL) AS sans_meteo,
                        (de.id_region IS NULL) AS sans_event
                    FROM jours j
                    LEFT JOIN dim_meteo dm
                        ON dm.id_region = j.id_region AND dm.date_meteo = j.jour
                    LEFT JOIN dim_event de
                        ON de.id_region = j.id_region AND de.date_event = j.jour
                )
                SELECT
                    COUNT(*) AS total_jours_region,
                    COUNT(*) FILTER (WHERE sans_meteo) AS total_sans_meteo,
                    COUNT(*) FILTER (WHERE sans_event) AS total_sans_event,
                    COUNT(*) FILTER (WHERE sans_meteo AND sans_event) AS total_chevauchement
                FROM diag
                """
            )
            total_jours_region, total_sans_meteo, total_sans_event, total_chevauchement = cur.fetchone()

            cur.execute(
                JOURS_REGION_CTE
                + """
                SELECT j.jour, COUNT(*) AS nb_regions
                FROM jours j
                LEFT JOIN dim_meteo dm
                    ON dm.id_region = j.id_region AND dm.date_meteo = j.jour
                WHERE dm.id_region IS NULL
                GROUP BY j.jour
                ORDER BY j.jour
                LIMIT %(limite)s
                """,
                {"limite": limite},
            )
            jours_sans_meteo = [
                {"date": jour.isoformat(), "regions_manquantes": nb}
                for jour, nb in cur.fetchall()
            ]

            cur.execute(
                JOURS_REGION_CTE
                + """
                SELECT j.id_region, j.jour
                FROM jours j
                LEFT JOIN dim_meteo dm
                    ON dm.id_region = j.id_region AND dm.date_meteo = j.jour
                LEFT JOIN dim_event de
                    ON de.id_region = j.id_region AND de.date_event = j.jour
                WHERE dm.id_region IS NULL AND de.id_region IS NULL
                ORDER BY j.jour, j.id_region
                LIMIT %(limite)s
                """,
                {"limite": limite},
            )
            chevauchement = [
                {"id_region": id_region, "date": jour.isoformat()}
                for id_region, jour in cur.fetchall()
            ]
    finally:
        conn.close()

    return {
        "total_jours_region": total_jours_region,
        "limite_listes": limite,
        "dim_meteo": {
            "manquants": total_sans_meteo,
            "jours": jours_sans_meteo,
        },
        "dim_event": {
            "manquants": total_sans_event,
            "note": (
                "absence attendue par design : dim_event ne stocke une ligne "
                "que si une anomalie est détectée (cf. ingest_dim_event), donc "
                "la grande majorité des jours n'ont pas de ligne sans que ce "
                "soit un défaut de données."
            ),
        },
        "chevauchement_meteo_et_event": {
            "total": total_chevauchement,
            "jours_region": chevauchement,
        },
        "dim_temps": {
            "note": (
                "non vérifiée : fait_consommation a une contrainte FK sur "
                "dim_temps(date_heure), une ligne manquante y est donc "
                "structurellement impossible."
            ),
        },
    }
