from fastapi import APIRouter

router = APIRouter(prefix="/dijkstra")

@router.get("/load-datastore")
def load_datastore():
    ...

@router.get("/rapport")
def generer_rapport():
    ...

@router.get("/shortest-path")
def shortest_path(to_node: str, from_node: str):
    ...

@router.get("/centrales")
def liste_centrales():
    ...

@router.get("/centrales/{centrale_id}")
def get_centrale(centrale_id: str):
    ...

@router.get("/regions")
def liste_regions():
    ...

@router.get("/regions/{region_id}")
def get_region(region_id: str):
    ...

@router.get("/liaisons")
def liste_liaisons():
    ...

@router.get("/anomalies")
def get_anomalies():
    ...