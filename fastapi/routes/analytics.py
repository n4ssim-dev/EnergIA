import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import check_password
from .db import DB_PATH

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


@router.get("/regions/{region_id}/consommation")
def consommation_region(
    region_id: str,
    heure: str = Query(..., description="Heure au format HH:MM ou '19h'"),
    jour_relatif: str = Query("reference_day"),
):
    """Consommation d'une région à un instant donné."""
    conn = get_connection()
    try:
        if find_region(conn, region_id) is None:
            raise HTTPException(
                status_code=404, detail=f"Région inconnue : {region_id!r}"
            )

        heure_normalisee = normalize_heure(heure)
        id_temps = f"{jour_relatif}#{heure_normalisee}"

        row = conn.execute(
            """
            SELECT consommation_mw, type_mesure
            FROM fait_consommation
            WHERE id_1 = ? AND id_temps = ?
            """,
            (region_id, id_temps),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée de consommation pour {region_id!r} à {heure_normalisee} ({jour_relatif})",
            )

        return {
            "region_id": region_id,
            "jour_relatif": jour_relatif,
            "heure": heure_normalisee,
            "consommation_mw": row["consommation_mw"],
            "type_mesure": row["type_mesure"],
        }
    finally:
        conn.close()


@router.get("/regions/consommation/max")
def region_consommation_max(
    heure: str = Query(..., description="Heure au format HH:MM ou '19h'"),
    jour_relatif: str = Query("reference_day"),
):
    """Quelle région consomme le plus à une heure donnée ?"""
    conn = get_connection()
    try:
        heure_normalisee = normalize_heure(heure)
        id_temps = f"{jour_relatif}#{heure_normalisee}"

        rows = conn.execute(
            """
            SELECT fc.id_1 AS region_id, r.name AS region_name, fc.consommation_mw
            FROM fait_consommation fc
            JOIN region r ON r.id = fc.id_1
            WHERE fc.id_temps = ?
            ORDER BY fc.consommation_mw DESC
            """,
            (id_temps,),
        ).fetchall()
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée de consommation à {heure_normalisee} ({jour_relatif})",
            )

        top = rows[0]
        return {
            "jour_relatif": jour_relatif,
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
    jour_relatif: str = Query("reference_day"),
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
        id_temps = f"{jour_relatif}#{heure_normalisee}"

        consommation = conn.execute(
            """
            SELECT consommation_mw, type_mesure
            FROM fait_consommation
            WHERE id_1 = ? AND id_temps = ?
            """,
            (region_id, id_temps),
        ).fetchone()

        production_rows = conn.execute(
            """
            SELECT fp.code_filiere, f.libelle_filiere, fp.production_mw
            FROM fait_production_non_pilotable fp
            JOIN filiere f ON f.code_filiere = fp.code_filiere
            WHERE fp.id_1 = ? AND fp.id_temps = ?
            """,
            (region_id, id_temps),
        ).fetchall()

        capacite_rows = conn.execute(
            """
            SELECT c.code_filiere, f.libelle_filiere, c.capacitee_mw
            FROM capacitee_instalee_non_pilotable c
            JOIN filiere f ON f.code_filiere = c.code_filiere
            WHERE c.id_1 = ?
            """,
            (region_id,),
        ).fetchall()

        if consommation is None and not production_rows:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée pour {region_id!r} à {heure_normalisee} ({jour_relatif})",
            )

        production_totale = sum(r["production_mw"] for r in production_rows)
        consommation_mw = consommation["consommation_mw"] if consommation else None

        return {
            "region_id": region_id,
            "region_name": region["name"],
            "jour_relatif": jour_relatif,
            "heure": heure_normalisee,
            "consommation_mw": consommation_mw,
            "production_non_pilotable_mw": production_totale,
            "production_par_filiere": [dict(r) for r in production_rows],
            "capacite_installee_non_pilotable": [dict(r) for r in capacite_rows],
            "solde_mw": (
                production_totale - consommation_mw
                if consommation_mw is not None
                else None
            ),
        }
    finally:
        conn.close()
