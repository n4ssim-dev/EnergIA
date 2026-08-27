from fastapi import APIRouter, HTTPException

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
    charger_journee_reference,
    recuperer_consommations_initiales,
    calculer_evolution_consommation,
    calculer_evolutions_regions,
    recuperer_consommations_par_temps,
    parcourir_journee,
    parcourir_journee_solaire,
    parcourir_journee_eolien,
    production_hors_nucleaire,
    recuperer_donnees_solaires,
    recuperer_donnees_eolien,
    charger_journee_reference_hors_nucleaire,
    calcul_besoins_residuels
)

router = APIRouter(prefix="/dijkstra")

@router.get("/production-restante")
def get_production_restante():

    donnees_consommation = charger_journee_reference()
    donnees_non_pilotables = charger_journee_reference_hors_nucleaire()

    consommations = parcourir_journee(donnees_consommation)

    production_solaire = recuperer_donnees_solaires(
        donnees_non_pilotables
    )

    production_eolien = recuperer_donnees_eolien(
        donnees_non_pilotables
    )

    production_non_pilotable = production_hors_nucleaire(
        production_solaire,
        production_eolien
    )

    production_restante = calcul_production_restante_a_fournir(
        consommations,
        production_non_pilotable
    )

    return {
        "production_restante_a_fournir": production_restante
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


def run_simulation(region: str, augmentation_mw: float, etat_centrales: dict[str, float]):
    """Calcule la répartition d'une demande supplémentaire (MW) sur une région.

    Factorisée pour être appelable à la fois par `/dijkstra/calcule` et par
    `/simulation` (routes/api.py, héritées de python-service).
    """
    """ 
    Ajout etat_centrales pour  contenir  la puissance actuelle de chaque centrale.
    Il est fourni par la simulation globale et doit etre conservé d'un
    quart d'heure au suivant.

    """
    store = get_store()
    region_data = store.regions.get(region)
    if region_data is None:
        raise HTTPException(status_code=404, detail=f"Région '{region}' introuvable")

    candidats = []
    #  initialiser note
    note = None
    # --- Centrales locales (distance = 0, pertes = 0) ---
    central_locales = []
    for plant_id in region_data.local_plant_ids:
        centrale_obj = store.centrales.get(plant_id)
        if centrale_obj:
            central_locales.append(centrale_obj)

    for central in central_locales:
        # Puissance actuelle de la centrale
        current_output_mw = etat_centrales.get(
            central.id,
            central.initial_output_mw
        )

        result = calcul_score(
            geodesic_distance_km=0,
            loss_percent=0,
            soft_upper_bound_mw=central.soft_upper_bound_mw,
            technical_penalty=central.technical_penalty,
            plant_id=central.id,
            local_plant_ids=region_data.local_plant_ids,
            #initial_output_mw=central.initial_output_mw,
            current_output_mw=current_output_mw,
        )
        candidats.append(
            {
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                #"initial_output_mw": central.initial_output_mw,
                "current_output_mw": current_output_mw,

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
            
            current_output_mw = etat_centrales.get(central.id,central.initial_output_mw)

            result = calcul_score(
                geodesic_distance_km=d["distance_km"],
                loss_percent=d["loss_percent"],
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                #initial_output_mw=central.initial_output_mw,
                current_output_mw=current_output_mw,

            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    #"initial_output_mw": central.initial_output_mw,
                    "current_output_mw": current_output_mw,

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
            
            current_output_mw = etat_centrales.get(
                central.id,
                central.initial_output_mw
            )

            result = calcul_score(
                geodesic_distance_km=calcul_distance_region(region_data, central),
                loss_percent=0,
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                #initial_output_mw=central.initial_output_mw,
                current_output_mw=current_output_mw,

            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    #"initial_output_mw": central.initial_output_mw,
                    "current_output_mw": current_output_mw,

                }
            )

    candidats_tries = classer_candidats(candidats)
    resultat = repartir_demande(augmentation_mw, candidats_tries,etat_centrales)

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

# ----------------------------------------------------------------------------------------------------------------------
# Automatiser la simulation  pour qu'il fasse l'ensemble des régions (13)
# au meme moment pour une meme quart d'heure
#-----------------------------------------------------------------------------------------------------------------------
@router.get("/simulation-regions")
def calculer_regions():
    donnees = charger_journee_reference()
    journee = parcourir_journee(donnees)

    resultats = []

    store = get_store()

    # État initial des centrales
    etat_centrales = {
        plant_id: central.initial_output_mw
        for plant_id, central in store.centrales.items()
    }

    for etape in journee:

        heure = etape["heure"]
        demandes = etape["consommations"]

        resultats_heure = {}

        # Calcul des 13 régions
        for region_id, demande in demandes.items():

            resultats_heure[region_id] = run_simulation(
                region_id,
                demande,
                etat_centrales
            )

        # Sauvegarde de l'état des centrales à ce timestamp
        etat_centrales_timestamp = {
            plant_id: puissance
            for plant_id, puissance in etat_centrales.items()
        }

        resultats.append({
            "heure": heure,
            "regions": resultats_heure,
            "etat_centrales": etat_centrales_timestamp
        })

    return {
        "nombre_etapes": len(resultats),
        "journee": resultats
    }

# ---------------------------------------------------------------------------
# Exposition des besoins résiduels par région et par /4 d'heure dernière version
# ---------------------------------------------------------------------------
@router.get("/besoins-residuels")
def get_besoins_residuels():

    donnees_consommation = charger_journee_reference()
    donnees_non_pilotables = charger_journee_reference_hors_nucleaire()

    journee = parcourir_journee(donnees_consommation)

    production_solaire = recuperer_donnees_solaires(
        donnees_non_pilotables
    )

    production_eolien = recuperer_donnees_eolien(
        donnees_non_pilotables
    )

    production_non_pilotable = production_hors_nucleaire(
        production_solaire,
        production_eolien
    )

    besoins_residuels = calcul_besoins_residuels(
        journee,
        production_non_pilotable
    )

    return {
        "besoins_residuels": besoins_residuels
    }
