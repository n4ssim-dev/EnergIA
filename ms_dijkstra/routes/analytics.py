import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import check_password
from graph.datastore import DB_PATH

router = APIRouter(prefix="/analytics", dependencies=[Depends(check_password)])


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def normalize_heure(heure: str) -> str:
    """Normalise "19h", "19h00", "19", "19:00" -> "19:00"."""
    brut = heure.strip().lower().replace("h", ":")
    if brut.endswith(":"):
        brut += "00"
    if ":" not in brut:
        brut += ":00"
    heures, minutes = brut.split(":", 1)
    try:
        return f"{int(heures):02d}:{int(minutes):02d}"
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Format d'heure invalide : {heure!r}"
        )


def find_centrale(conn, centrale_id: str):
    row = conn.execute(
        "SELECT * FROM centrale WHERE id = ?", (centrale_id,)
    ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT * FROM centrale WHERE lower(name) = lower(?)", (centrale_id,)
        ).fetchone()
    return row


def find_region(conn, region_id: str):
    return conn.execute(
        "SELECT * FROM region WHERE id = ?", (region_id,)
    ).fetchone()


@router.get("/centrales/{centrale_id}/etat") 
def etat_centrale(centrale_id: str):
    """État d'une centrale : disponibilité, puissance installée/actuelle,
    marge de manœuvre, réacteurs. La puissance maximale (installed_power_mw)
    fait partie de cette réponse."""
    conn = get_connection()
    try:
        centrale = find_centrale(conn, centrale_id)
        if centrale is None:
            raise HTTPException(
                status_code=404, detail=f"Centrale inconnue : {centrale_id!r}"
            )

        reacteurs = conn.execute(
            """
            SELECT id_reacteur, name, installed_power_mw, minimum_design_power_mw,
                   status, industrial_commisionning_date
            FROM reacteur WHERE id = ?
            """,
            (centrale["id"],),
        ).fetchall()

        return {
            "id": centrale["id"],
            "name": centrale["name"],
            "region_id": centrale["id_1"],
            "commune": centrale["commune"],
            "departement": centrale["departement"],
            "available": bool(centrale["available"]),
            "installed_power_mw": centrale["installed_power_mw"],
            "initial_output_mw": centrale["initial_output_mw"],
            "initial_load_ratio": centrale["initial_load_ratio"],
            "soft_upper_bound_mw": centrale["soft_upper_bound_mw"],
            "initial_dispatchable_margin_mw": centrale["initial_dispatchable_margin_mw"],
            "minimum_operating_power_mw": centrale["minimum_operating_power_mw"],
            "reactor_count": centrale["reactor_count"],
            "reacteurs": [dict(r) for r in reacteurs],
        }
    finally:
        conn.close()


@router.get("/centrales/disponibles")
def centrales_disponibles():
    """Combien de centrales sont disponibles ?"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, installed_power_mw FROM centrale WHERE available = 1"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM centrale").fetchone()[0]

        return {
            "disponibles": len(rows),
            "total": total,
            "centrales": [dict(r) for r in rows],
        }
    finally:
        conn.close()


# Colonnes de mesure_eco2mix_regionale portant la production "non pilotable"
# (même périmètre que l'ancien fait_production_non_pilotable : solaire + éolien).
FILIERE_NON_PILOTABLE_COLONNES = {"solar": "solaire_mw", "wind": "eolien_mw"}


def _find_mesure_eco2mix(conn, region_id, date_: str, heure_normalisee: str):
    """mesure_eco2mix_regionale.date_heure est un ISO datetime avec offset
    (ex: 2026-07-01T00:00:00+02:00) : on matche sur le préfixe date+heure,
    l'offset et les secondes n'ont pas besoin d'être connus de l'appelant."""
    return conn.execute(
        """
        SELECT * FROM mesure_eco2mix_regionale
        WHERE id_region = ? AND date_heure LIKE ?
        """,
        (region_id, f"{date_}T{heure_normalisee}:%"),
    ).fetchone()


@router.get("/regions/{region_id}/consommation")
def consommation_region(
    region_id: str,
    heure: str = Query(..., description="Heure au format HH:MM ou '19h'"),
    date: str = Query(..., description="Date ingérée au format YYYY-MM-DD"),
):
    """Consommation d'une région à un instant donné (mesure_eco2mix_regionale,
    ingérée manuellement par plage de dates via POST /database/ingest-eco2mix)."""
    conn = get_connection()
    try:
        if find_region(conn, region_id) is None:
            raise HTTPException(
                status_code=404, detail=f"Région inconnue : {region_id!r}"
            )

        heure_normalisee = normalize_heure(heure)
        row = _find_mesure_eco2mix(conn, region_id, date, heure_normalisee)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée de consommation pour {region_id!r} à {heure_normalisee} ({date})",
            )

        return {
            "region_id": region_id,
            "date": date,
            "heure": heure_normalisee,
            "consommation_mw": row["consommation_mw"],
            "nature": row["nature"],
        }
    finally:
        conn.close()


@router.get("/regions/consommation/max")
def region_consommation_max(
    heure: str = Query(..., description="Heure au format HH:MM ou '19h'"),
    date: str = Query(..., description="Date ingérée au format YYYY-MM-DD"),
):
    """Quelle région consomme le plus à une heure donnée ?"""
    conn = get_connection()
    try:
        heure_normalisee = normalize_heure(heure)
        rows = conn.execute(
            """
            SELECT me.id_region AS region_id, r.name AS region_name, me.consommation_mw
            FROM mesure_eco2mix_regionale me
            JOIN region r ON r.id = me.id_region
            WHERE me.date_heure LIKE ?
            ORDER BY me.consommation_mw DESC
            """,
            (f"{date}T{heure_normalisee}:%",),
        ).fetchall()
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée de consommation à {heure_normalisee} ({date})",
            )

        top = rows[0]
        return {
            "date": date,
            "heure": heure_normalisee,
            "region_id": top["region_id"],
            "region_name": top["region_name"],
            "consommation_mw": top["consommation_mw"],
            "classement": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/regions/{region_id}/situation")
def situation_region(
    region_id: str,
    heure: str = Query(..., description="Heure au format HH:MM ou '18h'"),
    date: str = Query(..., description="Date ingérée au format YYYY-MM-DD"),
):
    """Situation énergétique d'une région à un instant donné : consommation,
    production non pilotable (solaire/éolien) et capacité installée associée."""
    conn = get_connection()
    try:
        region = find_region(conn, region_id)
        if region is None:
            raise HTTPException(
                status_code=404, detail=f"Région inconnue : {region_id!r}"
            )

        heure_normalisee = normalize_heure(heure)
        mesure = _find_mesure_eco2mix(conn, region_id, date, heure_normalisee)

        capacite_rows = conn.execute(
            """
            SELECT c.code_filiere, f.libelle_filiere, c.capacitee_mw
            FROM capacitee_instalee_non_pilotable c
            JOIN filiere f ON f.code_filiere = c.code_filiere
            WHERE c.id_1 = ?
            """,
            (region_id,),
        ).fetchall()

        if mesure is None:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée pour {region_id!r} à {heure_normalisee} ({date})",
            )

        libelles = dict(
            conn.execute("SELECT code_filiere, libelle_filiere FROM filiere").fetchall()
        )
        production_par_filiere = [
            {
                "code_filiere": code_filiere,
                "libelle_filiere": libelles.get(code_filiere),
                "production_mw": mesure[colonne],
            }
            for code_filiere, colonne in FILIERE_NON_PILOTABLE_COLONNES.items()
        ]
        production_totale = sum(r["production_mw"] or 0 for r in production_par_filiere)
        consommation_mw = mesure["consommation_mw"]

        return {
            "region_id": region_id,
            "region_name": region["name"],
            "date": date,
            "heure": heure_normalisee,
            "consommation_mw": consommation_mw,
            "production_non_pilotable_mw": production_totale,
            "production_par_filiere": production_par_filiere,
            "capacite_installee_non_pilotable": [dict(r) for r in capacite_rows],
            "solde_mw": (
                production_totale - consommation_mw
                if consommation_mw is not None
                else None
            ),
        }
    finally:
        conn.close()
