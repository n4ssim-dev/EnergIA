from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import os
import httpx
PREDICTIVE_URL = os.getenv(
    "PREDICTIVE_URL",
    "http://ms-predictive:8005"
)
from .predictive_client import recuperer_predictions
from graph.datastore import get_store
from .contraintes import puissance_reelle
from .calcul import (
    calcul_score,
    repartir_demande,
    classer_candidats,
    du_terroire,
    trouver_liaison,
    rechercher_centrales_distantes,
    calcul_distance_region,
    charger_journee_reference,
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
    appliquer_perturbation,
    calcul_puissanceDispo,
    charger_production_nucleaire,
    charger_param_temps_nucleaire,
    calcul_marge_reelle_disponible,
    get_besoins_solaires_eoliens,
    calculer_reserve,
    repartir_besoin_supplementaire,
)


class Perturbation(BaseModel):
    regionId: str
    start: str
    end: str
    deltaMw: float


class SimulationCompleteFiltre(BaseModel):
    region: Optional[str] = None
    heure: Optional[str] = None


router = APIRouter(prefix="/metier")


def run_simulation(region: str, augmentation_mw: float, etat_centrales: dict[str, float]):
    """Calcule la répartition d'une demande supplémentaire (MW) sur une région.

    Factorisée pour être appelable à la fois par `/metier/calcule` et par
    `/simulation` (routes/api.py, héritées de python-service).

    Ajout etat_centrales pour contenir la puissance actuelle de chaque centrale.
    Il est fourni par la simulation globale et doit etre conservé d'un
    quart d'heure au suivant.
    """
    store = get_store()
    region_data = store.regions.get(region)
    if region_data is None:
        raise HTTPException(status_code=404, detail=f"Région '{region}' introuvable")

    candidats = []
    note = None
    # --- Centrales locales (distance = 0, pertes = 0) ---
    central_locales = []
    for plant_id in region_data.local_plant_ids:
        centrale_obj = store.centrales.get(plant_id)
        if centrale_obj:
            central_locales.append(centrale_obj)

    for central in central_locales:
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
            current_output_mw=current_output_mw,
        )
        candidats.append(
            {
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "current_output_mw": current_output_mw,
                "max_ramp_up_mw_per_15_min": central.max_ramp_up_mw_per_15_min,
                "centrale": central,
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

            current_output_mw = etat_centrales.get(central.id, central.initial_output_mw)

            result = calcul_score(
                geodesic_distance_km=d["distance_km"],
                loss_percent=d["loss_percent"],
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                current_output_mw=current_output_mw,
            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    "current_output_mw": current_output_mw,
                    "max_ramp_up_mw_per_15_min": central.max_ramp_up_mw_per_15_min,
                    "centrale": central,
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
                current_output_mw=current_output_mw,
            )
            candidats.append(
                {
                    "plant_id": central.id,
                    "score": result,
                    "soft_upper_bound_mw": central.soft_upper_bound_mw,
                    "current_output_mw": current_output_mw,
                    "max_ramp_up_mw_per_15_min": central.max_ramp_up_mw_per_15_min,
                    "centrale": central,
                }
            )

    candidats_tries = classer_candidats(candidats)
    resultat = repartir_demande(augmentation_mw, candidats_tries, etat_centrales)

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
    store = get_store()
    etat_centrales = {
        plant_id: central.initial_output_mw
        for plant_id, central in store.centrales.items()
    }
    return run_simulation(region, augmentation_mw, etat_centrales)


# ----------------------------------------------------------------------------------------------------------------------
# Automatiser la simulation pour qu'il fasse l'ensemble des régions (13)
# au meme moment pour une meme quart d'heure
# Intégration demande résiduelle
# ----------------------------------------------------------------------------------------------------------------------
@router.post("/simulation-regions")
def calculer_regions(
    date: str = Query(..., description="Jour ingéré (YYYY-MM-DD) via POST /database/ingest-eco2mix"),
    perturbations: Optional[list[Perturbation]] = None
):
    if perturbations is None:
        perturbations = []
    reserve_minimale_mw = 2000
    donnees = charger_journee_reference(date)
    journee = parcourir_journee(donnees)
    indice_heure = 0
    resultats = []

    store = get_store()

    etat_centrales = {
        plant_id: central.initial_output_mw
        for plant_id, central in store.centrales.items()
    }
    besoins_solaires_eoliens = get_besoins_solaires_eoliens(date)

    for etape in journee:

        heure = etape["heure"]
        demandes = etape["consommations"]

        resultats_heure = {}

        for region_id, demande in demandes.items():
            if region_id in ["occitanie", "grand_est"]:  # Test pour deux regions.

                demande_perturbee = appliquer_perturbation(
                    region_id,
                    heure,
                    demande,
                    perturbations
                )
                demande_residuelle = (
                    demande_perturbee
                    - besoins_solaires_eoliens["solaires"][region_id][indice_heure]
                    - besoins_solaires_eoliens["eoliens"][region_id][indice_heure]
                )

                resultats_heure[region_id] = run_simulation(
                    region_id,
                    demande_residuelle,
                    etat_centrales
                )

        etat_centrales_timestamp = {
            plant_id: puissance
            for plant_id, puissance in etat_centrales.items()
        }

        reserve_disponible = calculer_reserve(etat_centrales, store)

        if reserve_disponible < reserve_minimale_mw:
            statut = "degrade"
        else:
            statut = "normal"

        resultats.append({
            "heure": heure,
            "regions": resultats_heure,
            "consommation_mw": demande_residuelle,
            "solaire_mw": besoins_solaires_eoliens["solaires"][region_id][indice_heure],
            "eolien_mw": besoins_solaires_eoliens["eoliens"][region_id][indice_heure],
            "etat_centrales": etat_centrales_timestamp,
            "reserve_disponible_mw": reserve_disponible,
            "reserve_minimale_mw": reserve_minimale_mw,
            "statut": statut
        })
        indice_heure += 1

    return {
        "nombre_etapes": len(resultats),
        "journee": resultats[:10]
    }


# ---------------------------------------------------------------------------
# Exposition des besoins résiduels par région et par /4 d'heure
# ---------------------------------------------------------------------------
@router.get("/besoins-residuels")
def get_besoins_residuels(
    date: str = Query(..., description="Jour ingéré (YYYY-MM-DD) via POST /database/ingest-eco2mix"),
):
    donnees_consommation = charger_journee_reference(date)
    donnees_non_pilotables = charger_journee_reference_hors_nucleaire(date)

    journee = parcourir_journee(donnees_consommation)

    production_solaire = recuperer_donnees_solaires(donnees_non_pilotables)
    production_eolien = recuperer_donnees_eolien(donnees_non_pilotables)

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


def _simulation_complete_region_heure(
    region_id,
    index,
    store,
    donnees_consommation,
    besoins_residuels,
    production_nucleaire,
    etat_centrales,
):
    """
    Calcule la répartition nucléaire pour une région
    et un quart d'heure donné.

    etat_centrales est partagé entre les différents
    quarts d'heure afin de conserver l'état réel
    des centrales au fil de la journée.
    """

    # ---------------------------------------------------------
    # 1. Besoin nucléaire actuel
    # ---------------------------------------------------------

    demande_mw = besoins_residuels[region_id][index]
    besoin_actuel = demande_mw

    # ---------------------------------------------------------
    # 2. Besoin précédent / variation du besoin
    # ---------------------------------------------------------

    if index > 0:
        besoin_precedent = besoins_residuels[region_id][index - 1]

        variation_besoin = (
            besoin_actuel
            - besoin_precedent
        )

    else:
        besoin_precedent = None
        variation_besoin = None

    # La variation sert uniquement à comprendre
    # l'évolution du besoin.
    # Elle ne pilote PAS directement les centrales.

    if variation_besoin is not None:

        if variation_besoin > 0:
            print(
                "Le besoin augmente de",
                variation_besoin,
                "MW"
            )

        elif variation_besoin < 0:
            print(
                "Le besoin diminue de",
                abs(variation_besoin),
                "MW"
            )

        else:
            print(
                "Le besoin nucléaire est stable"
            )

    # ---------------------------------------------------------
    # 3. Configuration de la région
    # ---------------------------------------------------------

    region = next(
        r
        for r in production_nucleaire["regions"]
        if r["id"] == region_id
    )

    # ---------------------------------------------------------
    # 4. Centrales locales
    # ---------------------------------------------------------

    candidats_ids = region["local_plant_ids"]

    candidats = []

    for plant_id in candidats_ids:

        centrale_reseau = next(
            plant
            for plant in production_nucleaire["plants"]
            if plant["id"] == plant_id
        )

        centrale_temporelle = store.centrales.get(
            plant_id
        )

        if centrale_temporelle is None:
            continue

        # Initialisation une seule fois.
        # Ensuite la valeur est conservée d'un quart
        # d'heure au suivant.
        if plant_id not in etat_centrales:

            etat_centrales[plant_id] = (
                centrale_temporelle
                .initial_output_mw_at_23_45_previous_day
            )

        puissance_precedente = (
            etat_centrales[plant_id]
        )

        rampUp = (
            centrale_temporelle
            .max_ramp_up_mw_per_15_min
        )

        # -----------------------------------------------------
        # Contrôle besoin / production actuelle
        # -----------------------------------------------------

        ecart_besoin_production = (
            besoin_actuel
            - puissance_precedente
        )

        if (
            region_id == "occitanie"
            and donnees_consommation["timestamps"][index]
            == "15:00"
            and plant_id == "golfech"
        ):
            print(
                "----- CONTROLE 15:00 OCCITANIE -----"
            )

            print(
                "Besoin précédent :",
                besoin_precedent
            )

            print(
                "Besoin actuel :",
                besoin_actuel
            )

            print(
                "Variation du besoin :",
                variation_besoin
            )

            print(
                "Puissance actuelle Golfech :",
                puissance_precedente
            )

            print(
                "Écart besoin / production :",
                ecart_besoin_production
            )

            print(
                "------------------------------------"
            )

        candidats.append({
            "plant_id": plant_id,

            "current_output_mw":
                puissance_precedente,

            "soft_upper_bound_mw":
                centrale_reseau[
                    "simulation"
                ][
                    "soft_upper_bound_mw"
                ],

            "max_ramp_up_mw_per_15_min":
                rampUp,

            "centrale":
                centrale_temporelle,
        })

    # ---------------------------------------------------------
    # 5. Production nucléaire locale actuellement disponible
    # ---------------------------------------------------------

    production_nucleaire_locale_actuelle = sum(
        etat_centrales.get(plant_id, 0)
        for plant_id
        in region["local_plant_ids"]
    )

    ecart_local = (
        besoin_actuel
        - production_nucleaire_locale_actuelle
    )

    print(
        "Besoin nucléaire actuel :",
        besoin_actuel
    )

    print(
        "Production nucléaire locale actuelle :",
        production_nucleaire_locale_actuelle
    )

    print(
        "Écart besoin / production locale :",
        ecart_local
    )

    # ---------------------------------------------------------
    # 6. Répartition locale
    # ---------------------------------------------------------
    #
    # ATTENTION :
    #
    # C'est précisément cette partie que nous allons
    # corriger ensuite.
    #
    # repartir_demande() attend une puissance
    # SUPPLEMENTAIRE à mobiliser.
    #
    # Pour l'instant on ne lui transmet donc que
    # le manque par rapport à la production locale.
    # Si la production locale est déjà suffisante,
    # il n'y a rien à augmenter.
    # ---------------------------------------------------------

    demande_a_repartir = max(
        ecart_local,
        0
    )

    resultat_repartition = repartir_besoin_supplementaire(
        demande_a_repartir,
        candidats,
        etat_centrales.copy()
    )

    besoin_restant = (
        resultat_repartition["unsatisfied_mw"]
    )

    # ---------------------------------------------------------
    # 7. Centrales extérieures via Dijkstra
    # ---------------------------------------------------------

    if besoin_restant > 0:

        print(
            "Besoin non couvert localement, "
            "recherche de centrales extérieures"
        )

        source_id = (
            region["local_plant_ids"][0]
        )

        centrales_distantes = (
            rechercher_centrales_distantes(
                source_id,
                region[
                    "external_entry_plant_ids"
                ],
                store
            )
        )

        candidats_externes = []

        for distante in centrales_distantes:

            plant_id = distante["plant_id"]

            centrale_temporelle = (
                store.centrales.get(plant_id)
            )

            if centrale_temporelle is None:
                continue

            if plant_id not in etat_centrales:

                etat_centrales[plant_id] = (
                    centrale_temporelle
                    .initial_output_mw_at_23_45_previous_day
                )

            puissance_precedente = (
                etat_centrales[plant_id]
            )

            score = calcul_score(
                geodesic_distance_km=(
                    distante["distance_km"]
                ),
                loss_percent=(
                    distante["loss_percent"]
                ),
                soft_upper_bound_mw=(
                    centrale_temporelle
                    .soft_upper_bound_mw
                ),
                technical_penalty=(
                    centrale_temporelle
                    .technical_penalty
                ),
                plant_id=plant_id,
                local_plant_ids=(
                    region["local_plant_ids"]
                ),
                current_output_mw=(
                    puissance_precedente
                ),
            )

            candidats_externes.append({
                "plant_id":
                    plant_id,

                "score":
                    score,

                "current_output_mw":
                    puissance_precedente,

                "soft_upper_bound_mw":
                    centrale_temporelle
                    .soft_upper_bound_mw,

                "max_ramp_up_mw_per_15_min":
                    centrale_temporelle
                    .max_ramp_up_mw_per_15_min,

                "centrale":
                    centrale_temporelle,
            })

        candidats_externes = classer_candidats(
            candidats_externes
        )

        print(
            "Candidats extérieurs classés :",
            [
                c["plant_id"]
                for c in candidats_externes
            ]
        )

        resultat_repartition_externe = repartir_besoin_supplementaire(
            besoin_restant,
            candidats_externes,
            etat_centrales.copy()
        )

        print(
            "Répartition extérieure :",
            resultat_repartition_externe
        )

        # On fusionne les allocations locales
        # et extérieures.
        resultat_repartition[
            "allocation"
        ].extend(
            resultat_repartition_externe[
                "allocation"
            ]
        )

        resultat_repartition[
            "unsatisfied_mw"
        ] = (
            resultat_repartition_externe[
                "unsatisfied_mw"
            ]
        )

    # ---------------------------------------------------------
    # 8. Application réelle des contraintes
    # ---------------------------------------------------------

    allocations_reelles = []

    total_augmentation_nucleaire = 0

    for allocation in (
        resultat_repartition["allocation"]
    ):

        plant_id = allocation["plant_id"]

        allocation_souhaitee = (
            allocation["allocated_mw"]
        )

        centrale_temporelle = (
            store.centrales.get(plant_id)
        )

        puissance_precedente = (
            etat_centrales[plant_id]
        )

        puissance_souhaitee = (
            puissance_precedente
            + allocation_souhaitee
        )

        nouvelle_puissance_reelle = (
            puissance_reelle(
                puissance_precedente,
                puissance_souhaitee,
                centrale_temporelle
            )
        )

        augmentation_reelle = max(
            nouvelle_puissance_reelle
            - puissance_precedente,
            0
        )

        # Mise à jour de l'état partagé.
        etat_centrales[plant_id] = (
            nouvelle_puissance_reelle
        )

        total_augmentation_nucleaire += (
            augmentation_reelle
        )

        allocations_reelles.append({
            "plant_id":
                plant_id,

            "puissance_precedente_mw":
                puissance_precedente,

            "allocation_souhaitee_mw":
                allocation_souhaitee,

            "puissance_souhaitee_mw":
                puissance_souhaitee,

            "puissance_reelle_mw":
                nouvelle_puissance_reelle,

            "production_reelle_fournie_mw":
                augmentation_reelle,
        })

    # ---------------------------------------------------------
    # 9. Production nucléaire actuelle après calcul
    # ---------------------------------------------------------

    production_nucleaire_locale_actuelle = sum(
        etat_centrales.get(plant_id, 0)
        for plant_id
        in region["local_plant_ids"]
    )

    # Pour le moment, on calcule le besoin non couvert
    # par rapport à la production locale actuelle.
    #
    # On affinera ensuite cette partie pour intégrer
    # correctement les centrales extérieures mobilisées.
    besoin_non_couvert = round(
        max(
            besoin_actuel
            - production_nucleaire_locale_actuelle,
            0
        ),
        2
    )

    print(
        "Production nucléaire locale après calcul :",
        production_nucleaire_locale_actuelle
    )

    print(
        "Besoin non couvert :",
        besoin_non_couvert
    )

    # ---------------------------------------------------------
    # 10. Résultat
    # ---------------------------------------------------------

    return {
        "region":
            region_id,

        "index":
            index,

        "heure":
            donnees_consommation[
                "timestamps"
            ][index],

        "besoin_residuel_mw":
            besoin_actuel,

        "repartition_souhaitee":
            resultat_repartition,

        "allocations_apres_contraintes":
            allocations_reelles,

        # ATTENTION :
        # ce champ représente encore l'AUGMENTATION
        # effectuée pendant ce quart d'heure,
        # pas la production nucléaire totale.
        "production_nucleaire_reellement_fournie_mw":
            total_augmentation_nucleaire,

        "besoin_non_couvert_mw":
            besoin_non_couvert,

        "etat_centrales_apres_calcul":
            dict(etat_centrales),
    }

def construire_besoins_residuels_predits(
    predictions,
    timestamps,
    production_non_pilotable,
    regions,
    perturbations
):
    """
    Construit les besoins résiduels prédits
    pour toutes les régions et tous les créneaux de 15 min.
    """

    # ---------------------------------
    # Ranger les prédictions par région
    # et par heure
    # ---------------------------------

    predictions_par_region = {}

    for prediction in predictions:

        region_id = prediction["id_region"]

        heure = prediction["date_heure"][11:16]

        consommation = prediction["consommation_predite_mw"]

        if region_id not in predictions_par_region:
            predictions_par_region[region_id] = {}

        predictions_par_region[region_id][heure] = consommation

    # ---------------------------------
    # Calcul des besoins résiduels
    # ---------------------------------

    besoins_residuels_predits = {}

    for region_id in regions:

        besoins_residuels_predits[region_id] = []

        predictions_region = (
            predictions_par_region.get(
                region_id,
                {}
            )
        )

        for index, heure in enumerate(timestamps):

            # -------------------------
            # Cas 00 et 30 : prédiction disponible
            # -------------------------

            if heure in predictions_region:

                consommation_predite = (
                    predictions_region[heure]
                )

            # -------------------------
            # Cas 15 et 45 : interpolation
            # -------------------------

            else:

                heure_precedente = (
                    timestamps[index - 1]
                )

                consommation_precedente = (
                    predictions_region[
                        heure_precedente
                    ]
                )

                if index + 1 >= len(timestamps):

                    consommation_predite = (
                        consommation_precedente
                    )

                else:

                    heure_suivante = (
                        timestamps[index + 1]
                    )

                    consommation_suivante = (
                        predictions_region[
                            heure_suivante
                        ]
                    )

                    consommation_predite = (
                        consommation_precedente
                        + consommation_suivante
                    ) / 2

            # -------------------------
            # Application perturbation
            # -------------------------

            consommation_perturbee = (
                appliquer_perturbation(
                    region_id,
                    heure,
                    consommation_predite,
                    perturbations
                )
            )


            # -------------------------
            # Production solaire + éolien
            # -------------------------

            production_non_pilotable_heure = (
                production_non_pilotable[
                    region_id
                ][index]
            )

            # -------------------------
            # Besoin résiduel prédit
            # -------------------------

            besoin_residuel = round(
                consommation_perturbee - production_non_pilotable_heure,
                2
            )

            besoins_residuels_predits[region_id].append(
                besoin_residuel
            )

    return besoins_residuels_predits

@router.post("/simulation-complete")
def simulation_complete(
    date: str = Query(
        ...,
        description="Jour ingéré (YYYY-MM-DD) via POST /database/ingest-eco2mix"
    ),
    filtre: Optional[SimulationCompleteFiltre] = None,
    perturbations: Optional[list[Perturbation]] = None,
):
    store = get_store()

    if perturbations is None:
        perturbations = []

    # ---------------------------------
    # Chargement des données
    # ---------------------------------

    donnees_consommation = charger_journee_reference(date)
    donnees_non_pilotables = (charger_journee_reference_hors_nucleaire(date))
    production_nucleaire = (charger_production_nucleaire())

    # ---------------------------------
    # Préparation des données métier
    # ---------------------------------

    journee = parcourir_journee(donnees_consommation)

    production_solaire = (
        recuperer_donnees_solaires(donnees_non_pilotables)
    )

    production_eolien = (
        recuperer_donnees_eolien(donnees_non_pilotables)
    )

    production_non_pilotable = (
        production_hors_nucleaire(production_solaire, production_eolien)
    )

    besoins_residuels = (
        calcul_besoins_residuels(journee, production_non_pilotable)
    )

    # ---------------------------------
    # Régions et timestamps disponibles
    # ---------------------------------

    regions_disponibles = list(besoins_residuels.keys())

    timestamps = donnees_consommation["timestamps"]

    # ---------------------------------
    # Appel au microservice prédictif
    # ---------------------------------

    predictions = recuperer_predictions(date, regions_disponibles)

    # ---------------------------------
    # Calcul des besoins résiduels prédits
    # ---------------------------------

    besoins_residuels_predits = (
        construire_besoins_residuels_predits(
            predictions,
            timestamps,
            production_non_pilotable,
            regions_disponibles,
            perturbations
        )
    )

    # ---------------------------------
    # Récupération des filtres
    # ---------------------------------

    region_filtre = (
        filtre.region
        if filtre
        else None
    )

    heure_filtre = (
        filtre.heure
        if filtre
        else None
    )

    # ---------------------------------
    # Vérification de la région
    # ---------------------------------

    if region_filtre is not None:

        if region_filtre not in regions_disponibles:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Région "
                    f"'{region_filtre}' introuvable"
                )
            )

        regions_a_traiter = [region_filtre]

    else:

        regions_a_traiter = (regions_disponibles)

    # ---------------------------------
    # Vérification de l'heure
    # ---------------------------------

    if heure_filtre is not None:

        if heure_filtre not in timestamps:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Heure "
                    f"'{heure_filtre}' introuvable"
                )
            )

        indices_a_traiter = [
            timestamps.index(heure_filtre)
        ]

    else:

        indices_a_traiter = list(
            range(len(timestamps))
        )

    # ---------------------------------
    # Recherche de la prédiction filtrée
    # ---------------------------------

    prediction_filtree = None

    if (
        region_filtre is not None
        and heure_filtre is not None
    ):

        for prediction in predictions:

            heure_prediction = (
                prediction["date_heure"][11:16]
            )

            if (
                prediction["id_region"]
                == region_filtre
                and heure_prediction
                == heure_filtre
            ):
                prediction_filtree = prediction
                break

        print("Prédiction filtrée :", prediction_filtree)

    # ---------------------------------
    # Calcul du besoin résiduel prédit
    # ---------------------------------

    besoin_residuel_predit = None

    if prediction_filtree is not None:

        index_heure = timestamps.index(
            heure_filtre
        )

        production_non_pilotable_heure = (
            production_non_pilotable[
                region_filtre
            ][index_heure]
        )

        besoin_residuel_predit = round(
            prediction_filtree[
                "consommation_predite_mw"
            ]
            - production_non_pilotable_heure,
            2
        )

        print(
            "Besoin résiduel prédit :",
            besoin_residuel_predit,
            type(besoin_residuel_predit)
        )


    if (
        besoin_residuel_predit is not None
        and region_filtre is not None
        and heure_filtre is not None
    ):

        index_heure = timestamps.index(
            heure_filtre
        )

        besoins_residuels[
            region_filtre
        ][index_heure] = besoin_residuel_predit
    # ---------------------------------
    # Simulation métier actuelle
    # ---------------------------------

    # Correction : on simule TOUJOURS depuis l'index 0 jusqu'au dernier index
    # demandé, dans l'ordre, pour que etat_centrales reflète la vraie
    # trajectoire de la journée à chaque pas. Filtrer directement sur
    # indices_a_traiter sans rejouer les pas précédents donnait un résultat
    # faux pour toute heure != 00:00 (chaque centrale repartait de
    # initial_output_mw_at_23_45_previous_day au lieu de son état réel).
    dernier_index_necessaire = max(indices_a_traiter)
    indices_a_simuler = set(indices_a_traiter)

    resultats = {}
    for region_id in regions_a_traiter:
        etat_centrales = {}
        resultats_region = []
        for index in range(dernier_index_necessaire + 1):
            resultat_pas = _simulation_complete_region_heure(
                region_id,
                index,
                store,
                donnees_consommation,
                besoins_residuels_predits,
                production_nucleaire,
                etat_centrales,
            )
            if index in indices_a_simuler:
                resultats_region.append(resultat_pas)
        resultats[region_id] = resultats_region

    # ---------------------------------
    # Réponse
    # ---------------------------------

    return {
        "regions": regions_a_traiter,

        "heures": [
            timestamps[index]
            for index in indices_a_traiter
        ],

        "prediction_filtree": (prediction_filtree),

        "besoin_residuel_predit_mw": (besoin_residuel_predit),

        "resultats": resultats,
    }