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
    calcul_besoins_residuels,
    charger_production_nucleaire,
    charger_param_temps_nucleaire,
    calcul_marge_reelle_disponible
)

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

@router.get("/simulation-complete")
def simulation_complete():

        # ---------------------------------------------------------
        # 1. CHARGEMENT DES DONNÉES
        # ---------------------------------------------------------

        donnees_consommation = charger_journee_reference()

        donnees_non_pilotables = (
            charger_journee_reference_hors_nucleaire()
        )

        # data.json
        production_nucleaire = charger_production_nucleaire()

        # energia_parametres_temporels_nucleaire.json
        donnees_nucleaires_temporelles = (
            charger_param_temps_nucleaire()
        )


        # ---------------------------------------------------------
        # 2. CALCUL DU BESOIN RÉSIDUEL
        # consommation - solaire - éolien
        # ---------------------------------------------------------

        journee = parcourir_journee(
            donnees_consommation
        )

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


        # ---------------------------------------------------------
        # 3. TEST OCCITANIE À 00:00
        # ---------------------------------------------------------

        region_id = "occitanie"
        index = 0

        demande_mw = besoins_residuels[region_id][index]


        # ---------------------------------------------------------
        # 4. RÉCUPÉRATION DE LA RÉGION
        # ---------------------------------------------------------

        region = next(
            r
            for r in production_nucleaire["regions"]
            if r["id"] == region_id
        )


        # ---------------------------------------------------------
        # 5. CENTRALES CANDIDATES
        # ---------------------------------------------------------

        candidats_ids = (
            region["local_plant_ids"]
            + region["external_entry_plant_ids"]
        )

        candidats = []

        etat_centrales = {}


        # ---------------------------------------------------------
        # 6. CONSTRUCTION DES CANDIDATS
        # ---------------------------------------------------------

        for plant_id in candidats_ids:

            # Données du premier brief
            centrale_reseau = next(
                plant
                for plant in production_nucleaire["plants"]
                if plant["id"] == plant_id
            )

            # Données temporelles
            centrale_temporelle = next(
                plant
                for plant in donnees_nucleaires_temporelles["plants"]
                if plant["plant_id"] == plant_id
            )

            # Etat t-1
            puissance_precedente = (
                centrale_temporelle[
                    "initial_output_mw_at_23_45_previous_day"
                ]
            )

            etat_centrales[plant_id] = puissance_precedente

            candidats.append({
                "plant_id": plant_id,

                "current_output_mw":
                    puissance_precedente,

                "soft_upper_bound_mw":
                    centrale_reseau["simulation"]["soft_upper_bound_mw"]
            })


        # ---------------------------------------------------------
        # 7. RÉPARTITION SOUHAITÉE DU BESOIN
        # Fonction du collègue n°1
        # ---------------------------------------------------------

        resultat_repartition = repartir_demande(
            demande_mw,
            candidats,
            etat_centrales.copy()
        )


        # ---------------------------------------------------------
        # 8. APPLICATION DES CONTRAINTES RÉELLES
        # Fonction du collègue n°2
        # ---------------------------------------------------------

        allocations_reelles = []

        total_nucleaire_reellement_fourni = 0

        for allocation in resultat_repartition["allocation"]:

            plant_id = allocation["plant_id"]

            allocation_souhaitee = allocation["allocated_mw"]

            centrale_temporelle = next(
                plant
                for plant in donnees_nucleaires_temporelles["plants"]
                if plant["plant_id"] == plant_id
            )

            # Etat réel avant le calcul
            puissance_precedente = etat_centrales[plant_id]

            # Ce que l'on souhaiterait atteindre
            puissance_souhaitee = (
                puissance_precedente
                + allocation_souhaitee
            )

            # ---------------------------------------------
            # Fonction de contraintes du collègue
            # ---------------------------------------------

            nouvelle_puissance_reelle = puissance_reelle(
                puissance_precedente,
                puissance_souhaitee,
                centrale_temporelle
            )

            # Ce que la centrale a réellement pu ajouter
            production_reelle_fournie = (
                nouvelle_puissance_reelle
                - puissance_precedente
            )

            production_reelle_fournie = max(
                production_reelle_fournie,
                0
            )

            # Mise à jour de l'état
            etat_centrales[plant_id] = (
                nouvelle_puissance_reelle
            )

            total_nucleaire_reellement_fourni += (
                production_reelle_fournie
            )

            allocations_reelles.append({
                "plant_id": plant_id,

                "puissance_precedente_mw":
                    puissance_precedente,

                "allocation_souhaitee_mw":
                    allocation_souhaitee,

                "puissance_souhaitee_mw":
                    puissance_souhaitee,

                "puissance_reelle_mw":
                    nouvelle_puissance_reelle,

                "production_reelle_fournie_mw":
                    production_reelle_fournie
            })


        # ---------------------------------------------------------
        # 9. BESOIN QUI RESTE RÉELLEMENT NON COUVERT
        # ---------------------------------------------------------

        besoin_non_couvert = max(
            demande_mw
            - total_nucleaire_reellement_fourni,
            0
        )


        # ---------------------------------------------------------
        # 10. RÉSULTAT
        # ---------------------------------------------------------

        return {

            "region": region_id,

            "index": index,

            "heure": donnees_consommation[
                "timestamps"
            ][index],

            "besoin_residuel_mw":
                demande_mw,

            "repartition_souhaitee":
                resultat_repartition,

            "allocations_apres_contraintes":
                allocations_reelles,

            "production_nucleaire_reellement_fournie_mw":
                total_nucleaire_reellement_fourni,

            "besoin_non_couvert_mw":
                besoin_non_couvert,

            "etat_centrales_apres_calcul":
                etat_centrales
        }