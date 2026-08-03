
import json

from fastapi import APIRouter

router = APIRouter()


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
# retourner la liste des centrales solaires 
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

#-------------------------------------------------------------------------------
# Fonction de simulation
#-------------------------------------------------------------------------------
@router.post("/simulation")
def simulation():
    
    return {
        "message": "Simulation lancée",
    }