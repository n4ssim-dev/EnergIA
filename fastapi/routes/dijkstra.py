import json 
from fastapi import APIRouter, HTTPException
from pathlib import Path

from graph.datastore import get_store, reload_store, load_datastore
from graph.serializers import serialize_centrale, serialize_liaison, serialize_region
from .calcul import (
    calcul_score,
    repartir_demande,
    classer_candidats,
    du_terroire,
    trouver_liaison,
    rechercher_centrales_distantes,
    calcul_distance_region,
)
from pathlib import Path

router = APIRouter(prefix="/dijkstra")

def charger_journee_reference():
    with open(
        "data/energia-journee-reference-consommation.json","r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    return donnees


def recuperer_consommations_par_temps(donnees, index):
    consommations = {}

    for region in donnees["regions"]:
        consommations[region["id"]] = region["consumption_mw"][index]
    return consommations


def parcourir_journee(donnees):
    resultats = []

    for index in range(len(donnees["timestamps"])):
        heure = donnees["timestamps"][index]

        consommations = recuperer_consommations_par_temps( donnees, index)

        resultats.append({
            "heure": heure,
            "consommations": consommations,
        })
    return resultats

@router.get("/consommation-journee")
def consommation_journee():
    donnees = charger_journee_reference()

    resultats = parcourir_journee(donnees)

    return {
        "nombre_etape": len(resultats),
        "journee": resultats
    }
    

@router.get("/load-datastore")
def load_datastore_route():
    store = reload_store()
    return {
        "message": "Données chargées avec succès",
        "centrales": len(store.centrales),
        "regions": len(store.regions),
        "liaisons": len(store.liaisons),
    }


@router.get("/rapport")
def generer_rapport():
    store = get_store()
    return {
        "metadata": store.metadata,
        "centrales_count": len(store.centrales),
        "regions_count": len(store.regions),
        "liaisons_count": len(store.liaisons),
        "puissance_installee_totale_mw": sum(
            c.installed_power_mw for c in store.centrales.values()
        ),
        "graphe": repr(store.graph),
        "anomalies_count": len(store.verify()),
    }


@router.get("/shortest-path")
def shortest_path(from_node: str, to_node: str):
    store = get_store()
    if from_node not in store.centrales or to_node not in store.centrales:
        raise HTTPException(status_code=404, detail="Centrale source ou cible inconnue")

    distance, chemin = store.graph.shortest_path(from_node, to_node)
    if chemin is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun chemin trouvé entre '{from_node}' et '{to_node}'",
        )

    return {"from": from_node, "to": to_node, "distance_km": distance, "chemin": chemin}


@router.get("/centrales")
def liste_centrales():
    store = get_store()
    return {"centrales": [serialize_centrale(c) for c in store.centrales.values()]}


@router.get("/centrales/{centrale_id}")
def get_centrale(centrale_id: str):
    store = get_store()
    centrale = store.centrales.get(centrale_id)
    if centrale is None:
        raise HTTPException(
            status_code=404, detail=f"Centrale '{centrale_id}' introuvable"
        )
    return serialize_centrale(centrale)


@router.get("/regions")
def liste_regions():
    store = get_store()
    return {"regions": [serialize_region(r) for r in store.regions.values()]}


@router.get("/regions/{region_id}")
def get_region(region_id: str):
    store = get_store()
    region = store.regions.get(region_id)
    if region is None:
        raise HTTPException(status_code=404, detail=f"Région '{region_id}' introuvable")
    return serialize_region(region)


@router.get("/liaisons")
def liste_liaisons():
    store = get_store()
    return {"liaisons": [serialize_liaison(l) for l in store.liaisons]}


@router.get("/anomalies")
def get_anomalies():
    store = get_store()
    anomalies = store.verify()
    return {"count": len(anomalies), "anomalies": anomalies}


def run_simulation(region: str, augmentation_mw: float):
    """Calcule la répartition d'une demande supplémentaire (MW) sur une région.

    Factorisée pour être appelable à la fois par `/dijkstra/calcule` et par
    `/simulation` (routes/api.py, héritées de python-service).
    """
    store = get_store()
    region_data = store.regions.get(region)
    if region_data is None:
        raise HTTPException(status_code=404, detail=f"Région '{region}' introuvable")

    candidats = []

    # --- Centrales locales (distance = 0, pertes = 0) ---
    central_locales = []
    for plant_id in region_data.local_plant_ids:
        centrale_obj = store.centrales.get(plant_id)
        if centrale_obj:
            central_locales.append(centrale_obj)

    for central in central_locales:
        result = calcul_score(
            geodesic_distance_km=0,
            loss_percent=0,
            soft_upper_bound_mw=central.soft_upper_bound_mw,
            technical_penalty=central.technical_penalty,
            plant_id=central.id,
            local_plant_ids=region_data.local_plant_ids,
            initial_output_mw=central.initial_output_mw,
        )
        candidats.append(
            {
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "initial_output_mw": central.initial_output_mw,
            }
        )

    # --- Centrales externes
    if central_locales:
        source_id = central_locales[0].id
        distantes = rechercher_centrales_distantes(
            source_id, region_data.external_entry_plant_ids, store
        )
        for d in distantes:
            if d["plant_id"] in region_data.local_plant_ids:
                continue
            central = store.centrales.get(d["plant_id"])
            if central is None:
                continue

            result = calcul_score(
                geodesic_distance_km=d["distance_km"],
                loss_percent=d["loss_percent"],
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                initial_output_mw=central.initial_output_mw,
            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    "initial_output_mw": central.initial_output_mw,
                }
            )
    else:
        note = (
            "Aucune centrale locale dans cette région : la distance vers les "
            "centrales externes est estimée via la formule de Haversine "
            "(région -> centrale, à vol d'oiseau), et les pertes réseau sont "
            "fixées à 0% par défaut (non calculables sans liaison directe connue)."
        )
        for plant_id in region_data.external_entry_plant_ids:
            central = store.centrales.get(plant_id)
            if central is None:
                continue
            if plant_id in region_data.local_plant_ids:
                continue
            result = calcul_score(
                geodesic_distance_km=calcul_distance_region(region_data, central),
                loss_percent=0,
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                initial_output_mw=central.initial_output_mw,
            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    "initial_output_mw": central.initial_output_mw,
                }
            )

    candidats_tries = classer_candidats(candidats)
    resultat = repartir_demande(augmentation_mw, candidats_tries)

    reponse = {
        "region": region,
        "demande_mw": augmentation_mw,
        "repartition": resultat["allocation"],
        "puissance_manquante_mw": resultat["unsatisfied_mw"],
    }
    if note:
        reponse["note"] = note

    return reponse

@router.get("/calcule")
def get_calcule(region: str, augmentation_mw: float):
    return run_simulation(region, augmentation_mw)
