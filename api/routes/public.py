from fastapi import APIRouter, HTTPException

from graph.datastore import get_store
from graph.serializers import serialize_centrale, serialize_liaison, serialize_region
from .calcul import executer_simulation

# Routes à plat (sans préfixe) exposées publiquement : c'est la surface
# HTTP consommée par le gateway Express (lola/gateway/index.js), pas une
# réimplémentation de celui-ci. Hérité de python-service/app/api/routes.py.
router = APIRouter()


@router.get("/centrales")
def get_centrales():
    store = get_store()
    return {"centrales": [serialize_centrale(c) for c in store.centrales.values()]}


@router.get("/regions")
def get_regions():
    store = get_store()
    return {"regions": [serialize_region(r) for r in store.regions.values()]}


@router.get("/liaisons")
def get_liaisons():
    store = get_store()
    return {"liaisons": [serialize_liaison(l) for l in store.liaisons]}


@router.get("/simulation")
def simulation(region: str, augmentation_mw: float):
    store = get_store()
    try:
        resultat = executer_simulation(store, region, augmentation_mw)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "message": "Simulation lancée",
        "resultat": resultat,
    }
