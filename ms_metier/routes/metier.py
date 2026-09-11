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