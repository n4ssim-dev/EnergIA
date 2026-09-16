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
    affectations_exterieures,
    informations_dijkstra_exterieures,
):
    """
    Simule la couverture du besoin résiduel d'une région
    pour un quart d'heure donné.

    Logique métier :
    1. récupérer le besoin résiduel ;
    2. regarder ce que produisent déjà les centrales locales ;
    3. ajuster la production locale sous contraintes ;
    4. calculer ce qu'il reste à couvrir ;
    5. si nécessaire, chercher des centrales extérieures via Dijkstra ;
    6. mobiliser ces centrales sous contraintes ;
    7. conserver les états pour le quart d'heure suivant.
    """

    heure = donnees_consommation["timestamps"][index]

    # =========================================================
    # 1. BESOIN RESIDUEL DE LA REGION
    # =========================================================

    besoin_residuel_mw = (
        besoins_residuels[region_id][index]
    )

    # =========================================================
    # 2. CONFIGURATION DE LA REGION
    # =========================================================

    region = next(
        r
        for r in production_nucleaire["regions"]
        if r["id"] == region_id
    )

    centrales_locales_ids = (
        region["local_plant_ids"]
    )

    centrales_exterieures_ids = (
        region["external_entry_plant_ids"]
    )

    # =========================================================
    # 3. INITIALISATION DES CENTRALES LOCALES
    # =========================================================

    etat_local_avant = {}

    for plant_id in centrales_locales_ids:

        centrale = store.centrales.get(
            plant_id
        )

        if centrale is None:
            continue

        # Initialisation uniquement au premier passage.
        # Ensuite l'état vient du quart d'heure précédent.
        if plant_id not in etat_centrales:

            etat_centrales[plant_id] = (
                centrale
                .initial_output_mw_at_23_45_previous_day
            )

        puissance_actuelle_mw = (
            etat_centrales[plant_id]
        )

        marge_mobilisable_mw = (
            calcul_marge_reelle_disponible(
                puissance_actuelle_mw,
                centrale
            )
        )

        etat_local_avant[plant_id] = {
            "puissance_avant_calcul_mw":
                puissance_actuelle_mw,

            "marge_mobilisable_mw":
                marge_mobilisable_mw,
        }

    # =========================================================
    # 4. PRODUCTION DEJA DISPONIBLE POUR LA REGION
    # =========================================================

    production_locale_avant_mw = sum(
        etat_centrales.get(
            plant_id,
            0
        )
        for plant_id in centrales_locales_ids
    )

    # Une centrale extérieure ne fournit à la région
    # que les MW explicitement affectés à cette région.
    production_exterieure_avant_mw = sum(
        affectations_exterieures.values()
    )

    production_totale_avant_mw = (
        production_locale_avant_mw
        + production_exterieure_avant_mw
    )

    # =========================================================
    # 5. CAS OU LA PRODUCTION EST TROP ELEVEE
    # =========================================================

    excedent_mw = max(
        production_totale_avant_mw
        - besoin_residuel_mw,
        0
    )

    # ---------------------------------------------------------
    # On réduit d'abord les apports extérieurs.
    # ---------------------------------------------------------

    if excedent_mw > 0:

        for plant_id in list(
            affectations_exterieures.keys()
        ):

            if excedent_mw <= 0:
                break

            allocation_actuelle_mw = (
                affectations_exterieures[
                    plant_id
                ]
            )

            if allocation_actuelle_mw <= 0:
                continue

            centrale = store.centrales.get(
                plant_id
            )

            if centrale is None:
                continue

            puissance_avant_mw = (
                etat_centrales[plant_id]
            )

            reduction_souhaitee_mw = min(
                excedent_mw,
                allocation_actuelle_mw
            )

            puissance_souhaitee_mw = (
                puissance_avant_mw
                - reduction_souhaitee_mw
            )

            # Contraintes de descente appliquées ici.
            puissance_apres_mw = puissance_reelle(
                puissance_avant_mw,
                puissance_souhaitee_mw,
                centrale
            )

            reduction_reelle_mw = max(
                puissance_avant_mw
                - puissance_apres_mw,
                0
            )

            etat_centrales[plant_id] = (
                puissance_apres_mw
            )

            affectations_exterieures[
                plant_id
            ] = max(
                allocation_actuelle_mw
                - reduction_reelle_mw,
                0
            )

            excedent_mw -= (
                reduction_reelle_mw
            )

    # ---------------------------------------------------------
    # S'il reste un excédent, on réduit les centrales locales.
    # ---------------------------------------------------------

    if excedent_mw > 0:

        for plant_id in centrales_locales_ids:

            if excedent_mw <= 0:
                break

            centrale = store.centrales.get(
                plant_id
            )

            if centrale is None:
                continue

            puissance_avant_mw = (
                etat_centrales[plant_id]
            )

            puissance_souhaitee_mw = max(
                puissance_avant_mw
                - excedent_mw,
                0
            )

            # Contraintes de descente appliquées.
            puissance_apres_mw = puissance_reelle(
                puissance_avant_mw,
                puissance_souhaitee_mw,
                centrale
            )

            reduction_reelle_mw = max(
                puissance_avant_mw
                - puissance_apres_mw,
                0
            )

            etat_centrales[plant_id] = (
                puissance_apres_mw
            )

            excedent_mw -= (
                reduction_reelle_mw
            )

    # =========================================================
    # 6. PRODUCTION DISPONIBLE APRES EVENTUELLE BAISSE
    # =========================================================

    production_locale_mw = sum(
        etat_centrales.get(
            plant_id,
            0
        )
        for plant_id in centrales_locales_ids
    )

    production_exterieure_mw = sum(
        affectations_exterieures.values()
    )

    production_nucleaire_totale_mw = (
        production_locale_mw
        + production_exterieure_mw
    )

    reste_a_couvrir_mw = max(
        besoin_residuel_mw
        - production_nucleaire_totale_mw,
        0
    )

    # =========================================================
    # 7. COMPLEMENT AVEC LES CENTRALES LOCALES
    # =========================================================

    candidats_locaux = []

    if reste_a_couvrir_mw > 0:

        for plant_id in centrales_locales_ids:

            centrale = store.centrales.get(
                plant_id
            )

            if centrale is None:
                continue

            puissance_actuelle_mw = (
                etat_centrales[plant_id]
            )

            score = calcul_score(
                geodesic_distance_km=0,
                loss_percent=0,
                soft_upper_bound_mw=(
                    centrale.soft_upper_bound_mw
                ),
                technical_penalty=(
                    centrale.technical_penalty
                ),
                plant_id=plant_id,
                local_plant_ids=(
                    centrales_locales_ids
                ),
                current_output_mw=(
                    puissance_actuelle_mw
                ),
            )

            candidats_locaux.append({
                "plant_id":
                    plant_id,

                "score":
                    score,

                "current_output_mw":
                    puissance_actuelle_mw,

                "soft_upper_bound_mw":
                    centrale.soft_upper_bound_mw,

                "max_ramp_up_mw_per_15_min":
                    centrale
                    .max_ramp_up_mw_per_15_min,

                "centrale":
                    centrale,
            })

        candidats_locaux = classer_candidats(
            candidats_locaux
        )

        repartition_locale = (
            repartir_besoin_supplementaire(
                reste_a_couvrir_mw,
                candidats_locaux,
                etat_centrales.copy()
            )
        )

        # -----------------------------------------------------
        # Application réelle des contraintes
        # -----------------------------------------------------

        for allocation in (
            repartition_locale["allocation"]
        ):

            plant_id = (
                allocation["plant_id"]
            )

            allocation_souhaitee_mw = (
                allocation["allocated_mw"]
            )

            centrale = store.centrales.get(
                plant_id
            )

            puissance_avant_mw = (
                etat_centrales[plant_id]
            )

            puissance_souhaitee_mw = (
                puissance_avant_mw
                + allocation_souhaitee_mw
            )

            puissance_apres_mw = puissance_reelle(
                puissance_avant_mw,
                puissance_souhaitee_mw,
                centrale
            )

            etat_centrales[plant_id] = (
                puissance_apres_mw
            )

    # =========================================================
    # 8. RECALCUL APRES PRODUCTION LOCALE
    # =========================================================

    production_locale_mw = sum(
        etat_centrales.get(
            plant_id,
            0
        )
        for plant_id in centrales_locales_ids
    )

    production_exterieure_mw = sum(
        affectations_exterieures.values()
    )

    production_nucleaire_totale_mw = (
        production_locale_mw
        + production_exterieure_mw
    )

    reste_a_couvrir_mw = max(
        besoin_residuel_mw
        - production_nucleaire_totale_mw,
        0
    )

    # =========================================================
    # 9. DIJKSTRA SI LE LOCAL NE SUFFIT PAS
    # =========================================================

    if (
        reste_a_couvrir_mw > 0
        and centrales_locales_ids
    ):

        source_id = (
            centrales_locales_ids[0]
        )

        centrales_distantes = (
            rechercher_centrales_distantes(
                source_id,
                centrales_exterieures_ids,
                store
            )
        )

        # Mémorisation des informations Dijkstra
        # pour les conserver entre les quarts d'heure
        for centrale_distante in centrales_distantes:

            plant_id = centrale_distante["plant_id"]

            informations_dijkstra_exterieures[
                plant_id
            ] = {
                "distance_km": centrale_distante.get(
                    "distance_km"
                ),
                "loss_percent": centrale_distante.get(
                    "loss_percent"
                ),
                "chemin": centrale_distante.get(
                    "chemin"
                ),
            }

        candidats_externes = []

        for distante in centrales_distantes:

            plant_id = (
                distante["plant_id"]
            )

            centrale = store.centrales.get(
                plant_id
            )

            if centrale is None:
                continue

            if plant_id not in etat_centrales:

                etat_centrales[plant_id] = (
                    centrale
                    .initial_output_mw_at_23_45_previous_day
                )

            puissance_actuelle_mw = (
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
                    centrale.soft_upper_bound_mw
                ),
                technical_penalty=(
                    centrale.technical_penalty
                ),
                plant_id=plant_id,
                local_plant_ids=(
                    centrales_locales_ids
                ),
                current_output_mw=(
                    puissance_actuelle_mw
                ),
            )

            candidats_externes.append({
                "plant_id":
                    plant_id,

                "score":
                    score,

                "current_output_mw":
                    puissance_actuelle_mw,

                "soft_upper_bound_mw":
                    centrale.soft_upper_bound_mw,

                "max_ramp_up_mw_per_15_min":
                    centrale
                    .max_ramp_up_mw_per_15_min,

                "centrale":
                    centrale,
            })

            informations_dijkstra_exterieures[
                plant_id
            ] = {
                "distance_km":
                    distante["distance_km"],

                "loss_percent":
                    distante["loss_percent"],

                "chemin":
                    distante["chemin"],
            }

        candidats_externes = classer_candidats(
            candidats_externes
        )

        repartition_exterieure = (
            repartir_besoin_supplementaire(
                reste_a_couvrir_mw,
                candidats_externes,
                etat_centrales.copy()
            )
        )

        # -----------------------------------------------------
        # Application réelle des contraintes aux centrales
        # extérieures
        # -----------------------------------------------------

        for allocation in (
            repartition_exterieure["allocation"]
        ):

            plant_id = (
                allocation["plant_id"]
            )

            allocation_souhaitee_mw = (
                allocation["allocated_mw"]
            )

            centrale = store.centrales.get(
                plant_id
            )

            puissance_avant_mw = (
                etat_centrales[plant_id]
            )

            puissance_souhaitee_mw = (
                puissance_avant_mw
                + allocation_souhaitee_mw
            )

            puissance_apres_mw = puissance_reelle(
                puissance_avant_mw,
                puissance_souhaitee_mw,
                centrale
            )

            augmentation_reelle_mw = max(
                puissance_apres_mw
                - puissance_avant_mw,
                0
            )

            etat_centrales[plant_id] = (
                puissance_apres_mw
            )

            # On mémorise uniquement la puissance
            # réellement affectée à cette région.
            affectations_exterieures[
                plant_id
            ] = (
                affectations_exterieures.get(
                    plant_id,
                    0
                )
                + augmentation_reelle_mw
            )

    # =========================================================
    # 10. RESULTAT FINAL DU QUART D'HEURE
    # =========================================================

    production_locale_mw = sum(
        etat_centrales.get(
            plant_id,
            0
        )
        for plant_id in centrales_locales_ids
    )

    production_exterieure_mw = sum(
        affectations_exterieures.values()
    )

    production_nucleaire_totale_mw = round(
        production_locale_mw
        + production_exterieure_mw,
        2
    )

    besoin_non_couvert_mw = round(
        max(
            besoin_residuel_mw
            - production_nucleaire_totale_mw,
            0
        ),
        2
    )

    excedent_production_mw = round(
        max(
            production_nucleaire_totale_mw
            - besoin_residuel_mw,
            0
        ),
        2
    )

    # =========================================================
    # 11. DETAIL DES CENTRALES LOCALES
    # =========================================================

    production_locale = []

    for plant_id in centrales_locales_ids:

        centrale = store.centrales.get(
            plant_id
        )

        if centrale is None:
            continue

        puissance_apres_mw = (
            etat_centrales.get(
                plant_id,
                0
            )
        )

        avant = etat_local_avant.get(
            plant_id,
            {}
        )

        production_locale.append({
            "plant_id":
                plant_id,

            "puissance_avant_calcul_mw":
                round(
                    avant.get(
                        "puissance_avant_calcul_mw",
                        puissance_apres_mw
                    ),
                    2
                ),

            "marge_mobilisable_avant_calcul_mw":
                round(
                    avant.get(
                        "marge_mobilisable_mw",
                        0
                    ),
                    2
                ),

            "puissance_apres_calcul_mw":
                round(
                    puissance_apres_mw,
                    2
                ),
        })

    # =========================================================
    # 12. DETAIL DES CENTRALES EXTERIEURES
    # =========================================================

    production_exterieure = []

    for (
        plant_id,
        puissance_affectee_mw
    ) in affectations_exterieures.items():

        if puissance_affectee_mw <= 0:
            continue

        infos_reseau = (
            informations_dijkstra_exterieures.get(
                plant_id,
                {}
            )
        )

        production_exterieure.append({
            "plant_id":
                plant_id,

            "puissance_affectee_region_mw":
                round(
                    puissance_affectee_mw,
                    2
                ),

            "puissance_centrale_mw":
                round(
                    etat_centrales.get(
                        plant_id,
                        0
                    ),
                    2
                ),

            "distance_km":
                infos_reseau.get(
                    "distance_km"
                ),

            "loss_percent":
                infos_reseau.get(
                    "loss_percent"
                ),

            "chemin":
                infos_reseau.get(
                    "chemin"
                ),
        })

    # =========================================================
    # 13. RETOUR
    # =========================================================

    return {
        "region":
            region_id,

        "heure":
            heure,

        "besoin_residuel_mw":
            round(
                besoin_residuel_mw,
                2
            ),

        "production_locale": {
            "centrales":
                production_locale,

            "production_locale_totale_mw":
                round(
                    production_locale_mw,
                    2
                ),
        },

        "production_exterieure": {
            "centrales":
                production_exterieure,

            "production_exterieure_totale_mw":
                round(
                    production_exterieure_mw,
                    2
                ),
        },

        "production_nucleaire_totale_mw":
            production_nucleaire_totale_mw,

        "besoin_non_couvert_mw":
            besoin_non_couvert_mw,

        "excedent_production_mw":
            excedent_production_mw,

        "etat_centrales": {
            plant_id: round(puissance, 2)
            for plant_id, puissance in etat_centrales.items()
        },
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
        description=(
            "Jour ingéré (YYYY-MM-DD) "
            "via POST /database/ingest-eco2mix"
        )
    ),
    filtre: Optional[SimulationCompleteFiltre] = None,
    perturbations: Optional[list[Perturbation]] = None,
):
    # =========================================================
    # 1. INITIALISATION
    # =========================================================

    store = get_store()

    if perturbations is None:
        perturbations = []

    # =========================================================
    # 2. CHARGEMENT DES DONNEES
    # =========================================================

    donnees_consommation = (
        charger_journee_reference(date)
    )

    donnees_non_pilotables = (
        charger_journee_reference_hors_nucleaire(
            date
        )
    )

    production_nucleaire = (
        charger_production_nucleaire()
    )

    # =========================================================
    # 3. PREPARATION SOLAIRE / EOLIEN
    # =========================================================

    journee = parcourir_journee(
        donnees_consommation
    )

    production_solaire = (
        recuperer_donnees_solaires(
            donnees_non_pilotables
        )
    )

    production_eolien = (
        recuperer_donnees_eolien(
            donnees_non_pilotables
        )
    )

    production_non_pilotable = (
        production_hors_nucleaire(
            production_solaire,
            production_eolien
        )
    )

    # =========================================================
    # 4. REGIONS ET TIMESTAMPS DISPONIBLES
    # =========================================================

    # On utilise les données historiques uniquement
    # pour récupérer la liste des régions disponibles.
    besoins_residuels_reference = (
        calcul_besoins_residuels(
            journee,
            production_non_pilotable
        )
    )

    regions_disponibles = list(
        besoins_residuels_reference.keys()
    )

    timestamps = (
        donnees_consommation["timestamps"]
    )

    # =========================================================
    # 5. PREDICTIONS DE CONSOMMATION
    # =========================================================

    predictions = recuperer_predictions(
        date,
        regions_disponibles
    )

    # =========================================================
    # 6. BESOINS RESIDUELS PREDITS
    # =========================================================
    #
    # Cette fonction réalise :
    #
    # consommation prédite
    # + perturbation éventuelle
    # - solaire
    # - éolien
    #
    # C'est désormais LA source unique utilisée
    # par simulation-complete.
    # =========================================================

    besoins_residuels_predits = (
        construire_besoins_residuels_predits(
            predictions,
            timestamps,
            production_non_pilotable,
            regions_disponibles,
            perturbations
        )
    )

    # =========================================================
    # 7. RECUPERATION DES FILTRES
    # =========================================================

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

    # =========================================================
    # 8. VERIFICATION DE LA REGION
    # =========================================================

    if region_filtre is not None:

        if region_filtre not in regions_disponibles:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Région "
                    f"'{region_filtre}' introuvable"
                )
            )

        regions_a_traiter = [
            region_filtre
        ]

    else:

        regions_a_traiter = (
            regions_disponibles
        )

    # =========================================================
    # 9. VERIFICATION DE L'HEURE
    # =========================================================

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
            timestamps.index(
                heure_filtre
            )
        ]

    else:

        indices_a_traiter = list(
            range(
                len(timestamps)
            )
        )

    # =========================================================
    # 10. PREDICTION FILTREE
    # =========================================================

    prediction_filtree = None

    if (
        region_filtre is not None
        and heure_filtre is not None
    ):

        for prediction in predictions:

            heure_prediction = (
                prediction[
                    "date_heure"
                ][11:16]
            )

            if (
                prediction["id_region"]
                == region_filtre
                and heure_prediction
                == heure_filtre
            ):

                prediction_filtree = (
                    prediction
                )

                break

    # =========================================================
    # 11. BESOIN RESIDUEL FILTRE
    # =========================================================
    #
    # On ne recalcule PAS le besoin ici.
    #
    # On récupère directement la valeur
    # déjà calculée dans besoins_residuels_predits.
    # Elle contient donc aussi la perturbation.
    # =========================================================

    besoin_residuel_filtre_mw = None

    if (
        region_filtre is not None
        and heure_filtre is not None
    ):

        index_heure = timestamps.index(
            heure_filtre
        )

        besoin_residuel_filtre_mw = (
            besoins_residuels_predits[
                region_filtre
            ][index_heure]
        )

    # =========================================================
    # 12. SIMULATION METIER
    # =========================================================
    #
    # Même si on demande uniquement 15:00,
    # on rejoue :
    #
    # 00:00
    # 00:15
    # ...
    # 14:45
    # 15:00
    #
    # Cela permet de conserver l'état réel
    # des centrales au fil de la journée.
    # =========================================================

    dernier_index_necessaire = max(
        indices_a_traiter
    )

    indices_a_simuler = set(
        indices_a_traiter
    )

    resultats = {}

    for region_id in regions_a_traiter:

        # Etat physique des centrales
        # conservé entre les quarts d'heure.
        etat_centrales = {}

        # Puissance des centrales extérieures
        # affectée à cette région.
        affectations_exterieures = {}

        informations_dijkstra_exterieures = {}

        resultats_region = []

        for index in range(
            dernier_index_necessaire + 1
        ):

            resultat_pas = (
                _simulation_complete_region_heure(
                    region_id,
                    index,
                    store,
                    donnees_consommation,
                    besoins_residuels_predits,
                    production_nucleaire,
                    etat_centrales,
                    affectations_exterieures,
                    informations_dijkstra_exterieures,
                )
            )

            # On simule toutes les heures précédentes,
            # mais on ne retourne que celles demandées.
            if index in indices_a_simuler:

                resultats_region.append(
                    resultat_pas
                )

        resultats[
            region_id
        ] = resultats_region

    # =========================================================
    # 13. REPONSE
    # =========================================================

    return {
        "regions":
            regions_a_traiter,

        "heures": [
            timestamps[index]
            for index in indices_a_traiter
        ],

        "prediction_filtree":
            prediction_filtree,

        "besoin_residuel_mw":
            besoin_residuel_filtre_mw,

        "resultats":
            resultats,
    }