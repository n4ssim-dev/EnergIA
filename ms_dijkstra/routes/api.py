from fastapi import APIRouter, Depends

from graph.datastore import get_store
from graph.serializers import serialize_centrale, serialize_liaison, serialize_region
from .auth import check_password
from .dijkstra import run_simulation

# Routes héritées de python-service : exposées sans préfixe (contrairement à
# /dijkstra/...) car c'est ce que gateway/ appelle directement, et protégées
# par le même en-tête x-password que le microservice d'origine.

router = APIRouter(dependencies=[Depends(check_password)])


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
    resultat = run_simulation(region, augmentation_mw)
    return {
        "message": "Simulation lancée",
        "resultat": resultat,
    }
