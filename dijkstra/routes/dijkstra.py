from fastapi import APIRouter, HTTPException

from graph.datastore import get_store, reload_store
from graph.serializers import serialize_centrale, serialize_liaison, serialize_region
from .calcul import calcul_score,repartir_demande,classer_candidats,du_terroire,trouver_liaison,rechercher_centrales_distantes,calcul_distance_region

router = APIRouter(prefix="/dijkstra")


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
        raise HTTPException(status_code=404, detail=f"Centrale '{centrale_id}' introuvable")
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

@router.get("/calcule")
def get_calcule(region: str, augmentation_mw: float):
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
            initial_output_mw=central.initial_output_mw
        )
        candidats.append({
            "plant_id": central.id,
            "score": result,
            "soft_upper_bound_mw": central.soft_upper_bound_mw,
            "initial_output_mw": central.initial_output_mw,
        })

    # --- Centrales externes 
    if central_locales:
        source_id = central_locales[0].id
        distantes = rechercher_centrales_distantes(
            source_id, region_data.external_entry_plant_ids, store
        )
        for d in distantes:
            if d["plant_id"] in region_data.local_plant_ids: continue
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
                initial_output_mw=central.initial_output_mw
            )
            candidats.append({
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "initial_output_mw": central.initial_output_mw,
            })
    else:
        
        for plant_id in region_data.external_entry_plant_ids:
            central = store.centrales.get(plant_id)
            if central is None:
                continue
            if plant_id in region_data.local_plant_ids :
                continue
            result = calcul_score(
                geodesic_distance_km = calcul_distance_region(region_data,central),
                loss_percent=0,
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                initial_output_mw=central.initial_output_mw
            )
            candidats.append({
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "initial_output_mw": central.initial_output_mw,
            })

    candidats_tries = classer_candidats(candidats)
    resultat = repartir_demande(augmentation_mw, candidats_tries)

    return {
        "region": region,
        "demande_mw": augmentation_mw,
        "repartition": resultat["allocation"],
        "puissance_manquante_mw": resultat["unsatisfied_mw"]
    }