import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

# EnergIA/mcp_fastapi/routes/routes.py -> EnergIA/fastapi/data/analytics.db
DB_PATH = Path(__file__).resolve().parents[2] / "fastapi" / "data" / "analytics.db"

router = APIRouter(prefix="/routes")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def serialize_route(row):
    return {
        "id": row["id"],
        "chemin": row["chemin"],
        "methode": row["methode"],
        "fichier_source": row["fichier_source"],
        "description": row["description"],
        "authentification_requise": bool(row["authentification_requise"]),
    }


def serialize_parametre(row):
    return {
        "id": row["id"],
        "nom": row["nom"],
        "emplacement": row["emplacement"],
        "type": row["type"],
        "requis": bool(row["requis"]),
        "valeur_defaut": row["valeur_defaut"],
    }


@router.get("/health")
def routes_health():
    return {'status': 'healthy'}


@router.get("")
def liste_routes(
    methode: str | None = Query(None, description="Filtrer par méthode HTTP (GET, POST...)"),
    fichier_source: str | None = Query(None, description="Filtrer par fichier source (api.py, dijkstra.py...)"),
):
    """Catalogue des routes de l'API EnergIA (table `route` d'analytics.db)."""
    conn = get_connection()
    try:
        sql = "SELECT * FROM route WHERE 1=1"
        params = []
        if methode:
            sql += " AND methode = ?"
            params.append(methode.upper())
        if fichier_source:
            sql += " AND fichier_source = ?"
            params.append(fichier_source)
        sql += " ORDER BY id"

        rows = conn.execute(sql, params).fetchall()
        return {"count": len(rows), "routes": [serialize_route(r) for r in rows]}
    finally:
        conn.close()


@router.get("/search")
def rechercher_routes(
    chemin: str = Query(..., description="sous texte à rechercher dans le chemin de la route"),
):
    """Recherche des routes dont le chemin contient le texte  donnée."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM route WHERE chemin LIKE ? ORDER BY id",
            (f"%{chemin}%",),
        ).fetchall()
        return {"count": len(rows), "routes": [serialize_route(r) for r in rows]}
    finally:
        conn.close()


@router.get("/{route_id}")
def get_route(route_id: int):
    """Détail d'une route et de ses paramètres (jointure route/parametre_route)."""
    conn = get_connection()
    try:
        route = conn.execute("SELECT * FROM route WHERE id = ?", (route_id,)).fetchone()
        if route is None:
            raise HTTPException(status_code=404, detail=f"Route inconnue : id={route_id}")

        parametres = conn.execute(
            "SELECT * FROM parametre_route WHERE id_route = ? ORDER BY id",
            (route_id,),
        ).fetchall()

        return {
            **serialize_route(route),
            "parametres": [serialize_parametre(p) for p in parametres],
        }
    finally:
        conn.close()


@router.get("/{route_id}/parametres")
def get_parametres_route(route_id: int):
    """Paramètres d'une route donnée."""
    conn = get_connection()
    try:
        route = conn.execute("SELECT id FROM route WHERE id = ?", (route_id,)).fetchone()
        if route is None:
            raise HTTPException(status_code=404, detail=f"Route inconnue : id={route_id}")

        parametres = conn.execute(
            "SELECT * FROM parametre_route WHERE id_route = ? ORDER BY id",
            (route_id,),
        ).fetchall()
        return {
            "count": len(parametres),
            "parametres": [serialize_parametre(p) for p in parametres],
        }
    finally:
        conn.close()
