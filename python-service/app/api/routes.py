import json

from fastapi import APIRouter
from fastapi import APIRouter, Depends, Header, HTTPException, status
import httpx


router = APIRouter()


def check_password(x_password: str | None = Header(default=None)):
    if x_password != "5":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect ou absent"
        )

router = APIRouter(
    dependencies=[Depends(check_password)]
)

#-------------------------------------------------------------------------------
# Fonction de chargement des données 
#-------------------------------------------------------------------------------
def load_data():
    with open(
        "app/data/parc_nucleaire_prescriptif_france.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)
    
data = load_data()

#-------------------------------------------------------------------------------
# retourner la liste des centrales nucléaires 
#-------------------------------------------------------------------------------
@router.get("/centrales")
def get_centrales():

    return {
        "centrales": data["plants"]
    }


#-------------------------------------------------------------------------------
# retourner la liste des regions 
#-------------------------------------------------------------------------------
@router.get("/regions")
def get_regions():

    return {
        "regions": data["regions"]
    }


#-------------------------------------------------------------------------------
# retourner la liste des liaisons 
#-------------------------------------------------------------------------------
@router.get("/liaisons")
def get_liaisons():

    return {
        "liaisons": data["plant_edges"]
    }

#----------------------------------------------------------------------------------------
# Fonction de simulation
# Une région a besoin de X MW supplémentaires : quelles centrales doivent augmenter leur 
# production, et de combien ? »
#-----------------------------------------------------------------------------------------

@router.get("/simulation")
async def simulation(region: str, augmentation_mw: float):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:8001/dijkstra/calcule",
            params={
                "region": region,
                "augmentation_mw": augmentation_mw
            }
        )

    response.raise_for_status()

    return {
        "message": "Simulation lancée",
        "resultat": response.json()
    }