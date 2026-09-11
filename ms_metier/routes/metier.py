from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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
    region_id, index, store, donnees_consommation, besoins_residuels, production_nucleaire
):
    """Calcule la répartition nucléaire réelle pour une région et un quart d'heure donnés."""

    demande_mw = besoins_residuels[region_id][index]

    region = next(
        r
        for r in production_nucleaire["regions"]
        if r["id"] == region_id
    )

    candidats_ids = (
        region["local_plant_ids"]
        + region["external_entry_plant_ids"]
    )

    candidats = []
    etat_centrales = {}

    for plant_id in candidats_ids:

        centrale_reseau = next(
            plant
            for plant in production_nucleaire["plants"]
            if plant["id"] == plant_id
        )

        centrale_temporelle = store.centrales.get(plant_id)

        puissance_precedente = centrale_temporelle.initial_output_mw_at_23_45_previous_day
        rampUp = centrale_temporelle.max_ramp_up_mw_per_15_min

        etat_centrales[plant_id] = puissance_precedente

        candidats.append({
            "plant_id": plant_id,
            "current_output_mw": puissance_precedente,
            "soft_upper_bound_mw": centrale_reseau["simulation"]["soft_upper_bound_mw"],
            "max_ramp_up_mw_per_15_min": rampUp,
            "centrale": centrale_temporelle,
        })

    resultat_repartition = repartir_demande(demande_mw, candidats, etat_centrales.copy())

    allocations_reelles = []
    total_nucleaire_reellement_fourni = 0

    for allocation in resultat_repartition["allocation"]:

        plant_id = allocation["plant_id"]
        allocation_souhaitee = allocation["allocated_mw"]

        centrale_temporelle = store.centrales.get(plant_id)
        puissance_precedente = etat_centrales[plant_id]

        puissance_souhaitee = (puissance_precedente + allocation_souhaitee)

        nouvelle_puissance_reelle = puissance_reelle(
            puissance_precedente,
            puissance_souhaitee,
            centrale_temporelle
        )

        production_reelle_fournie = max(
            nouvelle_puissance_reelle - puissance_precedente,
            0
        )

        etat_centrales[plant_id] = nouvelle_puissance_reelle
        total_nucleaire_reellement_fourni += production_reelle_fournie

        allocations_reelles.append({
            "plant_id": plant_id,
            "puissance_precedente_mw": puissance_precedente,
            "allocation_souhaitee_mw": allocation_souhaitee,
            "puissance_souhaitee_mw": puissance_souhaitee,
            "puissance_reelle_mw": nouvelle_puissance_reelle,
            "production_reelle_fournie_mw": production_reelle_fournie,
        })

    besoin_non_couvert = max(demande_mw - total_nucleaire_reellement_fourni, 0)

    return {
        "region": region_id,
        "index": index,
        "heure": donnees_consommation["timestamps"][index],
        "besoin_residuel_mw": demande_mw,
        "repartition_souhaitee": resultat_repartition,
        "allocations_apres_contraintes": allocations_reelles,
        "production_nucleaire_reellement_fournie_mw": total_nucleaire_reellement_fourni,
        "besoin_non_couvert_mw": besoin_non_couvert,
        "etat_centrales_apres_calcul": etat_centrales,
    }


@router.post("/simulation-complete")
def simulation_complete(
    date: str = Query(..., description="Jour ingéré (YYYY-MM-DD) via POST /database/ingest-eco2mix"),
    filtre: Optional[SimulationCompleteFiltre] = None,
):
    store = get_store()
    donnees_consommation = charger_journee_reference(date)
    donnees_non_pilotables = charger_journee_reference_hors_nucleaire(date)

    production_nucleaire = charger_production_nucleaire()

    journee = parcourir_journee(donnees_consommation)
    production_solaire = recuperer_donnees_solaires(donnees_non_pilotables)
    production_eolien = recuperer_donnees_eolien(donnees_non_pilotables)
    production_non_pilotable = production_hors_nucleaire(production_solaire, production_eolien)
    besoins_residuels = calcul_besoins_residuels(journee, production_non_pilotable)

    regions_disponibles = list(besoins_residuels.keys())
    timestamps = donnees_consommation["timestamps"]

    region_filtre = filtre.region if filtre else None
    heure_filtre = filtre.heure if filtre else None

    if region_filtre is not None:
        if region_filtre not in regions_disponibles:
            raise HTTPException(
                status_code=404, detail=f"Région '{region_filtre}' introuvable"
            )
        regions_a_traiter = [region_filtre]
    else:
        regions_a_traiter = regions_disponibles

    if heure_filtre is not None:
        if heure_filtre not in timestamps:
            raise HTTPException(
                status_code=404, detail=f"Heure '{heure_filtre}' introuvable"
            )
        indices_a_traiter = [timestamps.index(heure_filtre)]
    else:
        indices_a_traiter = list(range(len(timestamps)))

    resultats = {
        region_id: [
            _simulation_complete_region_heure(
                region_id,
                index,
                store,
                donnees_consommation,
                besoins_residuels,
                production_nucleaire,
            )
            for index in indices_a_traiter
        ]
        for region_id in regions_a_traiter
    }

    return {
        "regions": regions_a_traiter,
        "heures": [timestamps[index] for index in indices_a_traiter],
        "resultats": resultats,
    }