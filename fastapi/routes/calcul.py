from haversine import haversine
import sqlite3
from .contraintes import (puissance_reelle,calcul_puissance_max)
from .db import DB_PATH
from datetime import datetime


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------------------------
# 1. Puissance disponible d'une centrale
# ---------------------------------------------------------------------------
# def calcul_puissanceDispo(soft_upper_bound_mw, initial_output_mw):
#     maxPower = soft_upper_bound_mw
#     powerOutput = initial_output_mw
#     availablePower = maxPower - powerOutput
#     return max(availablePower, 0)

# Nouvelle fonction calcul_puissanceDispo en ajoutant le calcul de la rampe :
# combien de MW une centrale peut encore augmenter pendant le prochain quart d'heure 

def calcul_puissanceDispo(soft_upper_bound_mw,initial_output_mw,max_ramp_up_mw_per_15_min):
    maxPower = soft_upper_bound_mw   # puissance maximale autorisée
    powerOutput = initial_output_mw 
    rampUp = max_ramp_up_mw_per_15_min  # la vitesse à laquelle la centrale peut augmenter

    # maxReachablePower : Puissance maximale que la centrale peut réellement atteindre au prochain quart d'heure
    maxReachablePower = min(
        maxPower,
        powerOutput + rampUp
    )

    availablePower = maxReachablePower - powerOutput

    return max(availablePower, 0)

# ---------------------------------------------------------------------------
# 2. Taux de saturation d'une centrale (ratio 0-1, pas un pourcentage)
# ---------------------------------------------------------------------------
def calcul_taux_saturation(initial_output_mw, soft_upper_bound_mw):
    powerOutput = initial_output_mw
    maxPower = soft_upper_bound_mw
    if maxPower == 0:
        return 1
    saturationRate = powerOutput / maxPower
    return max(saturationRate, 0)


# ---------------------------------------------------------------------------
# 3. Pertes réseau sur une quantité transférée (en MW)
# ---------------------------------------------------------------------------
def calcul_pertes(transferred_mw, loss_percent):
    energieTransfert = transferred_mw
    pertePourcent = loss_percent
    calcul = energieTransfert * (pertePourcent / 100)
    return calcul


# ---------------------------------------------------------------------------
# 4. Une centrale est-elle locale à une région ?
# ---------------------------------------------------------------------------
def du_terroire(plant_id, local_plant_ids):
    central = plant_id
    region = local_plant_ids
    return central in region


# ---------------------------------------------------------------------------
# 5. Score de sélection d'une centrale candidate
#    (formule fournie dans simulation_parameters du JSON)
# ---------------------------------------------------------------------------
def calcul_score(geodesic_distance_km, loss_percent, soft_upper_bound_mw,
                  technical_penalty, plant_id, local_plant_ids,current_output_mw ): #initial_output_mw
    score_distance = geodesic_distance_km * 1
    score_loss = loss_percent * 45
    load = calcul_taux_saturation(current_output_mw, soft_upper_bound_mw) # initial_output_mw
    score_saturation = (load ** 4) * 900
    score_technical = technical_penalty * 200
    if du_terroire(plant_id, local_plant_ids):
        score_bonus = -250
    else:
        score_bonus = 0
    final_score = score_distance + score_loss + score_saturation + score_technical + score_bonus
    return final_score


# ---------------------------------------------------------------------------
# 6. Classement des candidats par score (meilleur = score le plus bas)
# ---------------------------------------------------------------------------
def classer_candidats(candidats):
    ranked = sorted(candidats, key=lambda x: x["score"])
    return ranked


# ---------------------------------------------------------------------------
# 7. Retrouver une liaison directe entre deux centrales dans store.liaisons
# ---------------------------------------------------------------------------
def trouver_liaison(liaisons, from_id, to_id):
    for liaison in liaisons:
        if (liaison.from_id == from_id and liaison.to_id == to_id) or \
           (liaison.from_id == to_id and liaison.to_id == from_id):
            return liaison
    else:
        return None


# ---------------------------------------------------------------------------
# 8. Recherche des centrales distantes via le Diijkstra 
# ---------------------------------------------------------------------------
def rechercher_centrales_distantes(source_id, cibles_ids, store):
    """
    Pour une centrale source, calcule la distance vers chaque centrale cible
    via store.graph.shortest_path (Dijkstra du projet, qui gère déjà le
    suivi du chemin via 'previous'), et enrichit avec les infos de la
    liaison directe (pertes) si elle existe.
    """
    resultats = []
    for cible in cibles_ids:
        distance, chemin = store.graph.shortest_path(source_id, cible)
        if chemin is None:
            continue  # aucun chemin trouvé, on exclut ce candidat

        liaison_directe = trouver_liaison(store.liaisons, source_id, cible)
        loss_percent = liaison_directe.loss_percent if liaison_directe else 0

        resultats.append({
            "plant_id": cible,
            "distance_km": distance,
            "loss_percent": loss_percent,
            "chemin": chemin
        })

    return resultats


# ---------------------------------------------------------------------------
# 9. Répartition de la demande entre les candidates triés
# ---------------------------------------------------------------------------
def repartir_demande(
    demande_mw,
    candidats_tries,
    etat_centrales
):
    allocation = []
    demand_left = demande_mw

    for candidat in candidats_tries:

        if demand_left <= 0:
            break

        plant_id = candidat["plant_id"]

        # Toujours prendre l'état global actuel
        current_output_mw = etat_centrales.get(
            plant_id,
            candidat["current_output_mw"]
        )
        
        soft_upper_bound_mw = candidat["soft_upper_bound_mw"]
        max_ramp_up_mw_per_15_min = candidat["max_ramp_up_mw_per_15_min"]

        donnees_nucleaires = charger_param_temps_nucleaire()
        puissance_precedente = calcul_puissance_precedente(donnees_nucleaires)
        available_power = calcul_marge_reelle_disponible(puissance_precedente,etat_centrales)
        # available_power = calcul_puissanceDispo(
        #     soft_upper_bound_mw,
        #     current_output_mw,
        #     max_ramp_up_mw_per_15_min

        # )
        # print(
        # "----------------------------CENTRALE----------------------------------",
        # plant_id,
        # "current =", current_output_mw,
        # "max =", candidat["soft_upper_bound_mw"],
        # "disponible =", available_power,
        # "demande restante =", demand_left
        # )
        if available_power <= 0:
            continue

        allocation_candidat = min(
            demand_left,
            available_power
        )

        allocation.append({
            "plant_id": plant_id,
            "allocated_mw": allocation_candidat
        })

        # print(
        # " ************************** ALLOCATION ********************************",
        # plant_id,
        # "+", allocation_candidat,
        # "→", current_output_mw + allocation_candidat
        # )
        
        # Mise à jour de l'état global
        etat_centrales[plant_id] = (
            current_output_mw + allocation_candidat
        )

        # Mise à jour du candidat
        candidat["current_output_mw"] = etat_centrales[plant_id]

        demand_left -= allocation_candidat

    return {
        "allocation": allocation,
        "unsatisfied_mw": demand_left
    }
# ---------------------------------------------------------------------------
# 10. Calcule longitude et latitude
# ---------------------------------------------------------------------------
def calcul_distance_region(region_data, central):
    longitude = region_data.longitude
    latitude = region_data.latitude
    regionPosition=(latitude,longitude)
    centralLongitude = central.longitude
    centralLatitude = central.latitude
    centralPosition=(centralLatitude,centralLongitude)
    result = haversine(regionPosition,centralPosition)
    return (result)

# ---------------------------------------------------------------------------
# 11. Chargement depuis analytics.db (reconstruit la forme des anciens JSON,
#     pour ne rien changer aux fonctions/routes qui consomment ces données)
# ---------------------------------------------------------------------------
def charger_journee_reference_hors_nucleaire():
    conn = _connect()
    try:
        timestamps = [
            row["heure"] for row in conn.execute(
                "SELECT heure FROM dim_temps WHERE jour_relatif = 'reference_day' "
                "ORDER BY step_index"
            )
        ]

        regions_meta = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM region")}

        capacites = {}
        for row in conn.execute(
            "SELECT id_1 AS region_id, code_filiere, capacitee_mw "
            "FROM capacitee_instalee_non_pilotable"
        ):
            capacites.setdefault(row["region_id"], {})[row["code_filiere"]] = row["capacitee_mw"]

        productions = {}
        for row in conn.execute(
            "SELECT fp.id_1 AS region_id, fp.code_filiere, fp.production_mw "
            "FROM fait_production_non_pilotable fp "
            "JOIN dim_temps dt ON dt.id_temps = fp.id_temps "
            "WHERE dt.jour_relatif = 'reference_day' "
            "ORDER BY fp.id_1, fp.code_filiere, dt.step_index"
        ):
            productions.setdefault(row["region_id"], {}).setdefault(
                row["code_filiere"], []
            ).append(row["production_mw"])

        regions = [
            {
                "id": region_id,
                "name": regions_meta.get(region_id, ""),
                "synthetic_installed_capacity_mw": capacites.get(region_id, {}),
                "production_mw": productions.get(region_id, {}),
            }
            for region_id in productions
        ]

        return {"timestamps": timestamps, "regions": regions}
    finally:
        conn.close()


def charger_journee_reference():
    conn = _connect()
    try:
        timestamps = [
            row["heure"] for row in conn.execute(
                "SELECT heure FROM dim_temps WHERE jour_relatif = 'reference_day' "
                "ORDER BY step_index"
            )
        ]

        regions_meta = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM region")}

        consommations = {}
        for row in conn.execute(
            "SELECT fc.id_1 AS region_id, fc.consommation_mw "
            "FROM fait_consommation fc "
            "JOIN dim_temps dt ON dt.id_temps = fc.id_temps "
            "WHERE fc.type_mesure = 'reference' AND dt.jour_relatif = 'reference_day' "
            "ORDER BY fc.id_1, dt.step_index"
        ):
            consommations.setdefault(row["region_id"], []).append(row["consommation_mw"])

        regions = [
            {
                "id": region_id,
                "name": regions_meta.get(region_id, ""),
                "consumption_mw": valeurs,
            }
            for region_id, valeurs in consommations.items()
        ]

        etat_t_moins_1 = {}
        horodatage = None
        jour_relatif = None
        for row in conn.execute(
            "SELECT fc.id_1 AS region_id, fc.consommation_mw, dt.heure, dt.jour_relatif "
            "FROM fait_consommation fc "
            "JOIN dim_temps dt ON dt.id_temps = fc.id_temps "
            "WHERE fc.type_mesure = 'initial_t_moins_1'"
        ):
            horodatage = row["heure"]
            jour_relatif = row["jour_relatif"]
            etat_t_moins_1[row["region_id"]] = {
                "name": regions_meta.get(row["region_id"], ""),
                "consumption_mw": row["consommation_mw"],
            }

        return {
            "timestamps": timestamps,
            "regions": regions,
            "initial_state_t_minus_1": {
                "timestamp": horodatage,
                "relative_day": jour_relatif,
                "regions": etat_t_moins_1,
            },
        }
    finally:
        conn.close()


def charger_param_temps_nucleaire():
    conn = _connect()
    try:
        plants = [
            {
                "plant_id": row["id"],
                "plant_name": row["name"],
                "initial_output_mw_at_23_45_previous_day": row["initial_output_mw_at_23_45_previous_day"],
                "minimum_operating_power_mw": row["minimum_operating_power_mw"],
                "maximum_power_mw": row["installed_power_mw"],
                "max_ramp_up_mw_per_15_min": row["max_ramp_up_mw_15_min"],
                "max_ramp_down_mw_per_15_min": row["max_ramp_down_mw_per_15min"],
                "available": bool(row["available"]),
                "minimum_power_fallback_used": bool(row["minimum_power_fallback_used"]),
                "values_are_simulated_except_maximum_power": bool(
                    row["values_are_simulated_except_maximum_power"]
                ),
            }
            for row in conn.execute("SELECT * FROM centrale ORDER BY id")
        ]

        return {"plants": plants}
    finally:
        conn.close()


def charger_production_nucleaire():
    conn = _connect()
    try:
        region_rows = {r["id"]: r for r in conn.execute("SELECT * FROM region")}

        local_plant_ids = {}
        for row in conn.execute("SELECT id, id_1 FROM centrale"):
            local_plant_ids.setdefault(row["id_1"], []).append(row["id"])

        external_entry_plant_ids = {}
        for row in conn.execute("SELECT id, id_1 FROM accessible_via"):
            external_entry_plant_ids.setdefault(row["id_1"], []).append(row["id"])

        reactors_by_centrale = {}
        for row in conn.execute("SELECT * FROM reacteur"):
            reactors_by_centrale.setdefault(row["id"], []).append({
                "id": row["id_reacteur"],
                "name": row["name"],
                "installed_power_mw": row["installed_power_mw"],
                "minimum_design_power_mw": row["minimum_design_power_mw"],
                "industrial_commissioning_date": row["industrial_commisionning_date"],
                "status": row["status"],
                "data_kind": row["data_kind"],
            })

        plants = []
        for row in conn.execute("SELECT * FROM centrale ORDER BY id"):
            region = region_rows.get(row["id_1"], {})
            plants.append({
                "id": row["id"],
                "name": row["name"],
                "location": {
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "commune": row["commune"],
                    "department": row["departement"],
                    "region_id": row["id_1"],
                    "region_name": region["name"] if region else "",
                },
                "reactor_count": row["reactor_count"],
                "installed_power_mw": row["installed_power_mw"],
                "reactors": reactors_by_centrale.get(row["id"], []),
                "simulation": {
                    "available": bool(row["available"]),
                    "initial_output_mw": row["initial_output_mw"],
                    "initial_load_ratio": row["initial_load_ratio"],
                    "soft_upper_bound_mw": row["soft_upper_bound_mw"],
                    "soft_upper_bound_ratio": row["soft_upper_bound_ratio"],
                    "initial_dispatchable_margin_mw": row["initial_dispatchable_margin_mw"],
                    "max_ramp_up_mw_per_15_min": row["max_ramp_up_mw_15_min"],
                    "technical_penalty": row["technical_penalty"],
                    "values_are_simulated": bool(row["values_are_simulated"]),
                },
            })

        regions = [
            {
                "id": row["id"],
                "insee_code": row["insee_code"],
                "name": row["name"],
                "centroid": {"latitude": row["latitude"], "longitude": row["longitude"]},
                "population_2023": row["population_2023"],
                "annual_consumption_twh_2024": row["annual_consumption_twh2024"],
                "average_consumption_mw_2024": row["annual_consumption_mw_2024"],
                "illustrative_peak_consumption_mw": row["illustrative_peak_consumption_mw"],
                "connected_to_continental_grid": bool(row["connected_to_continental_grid"]),
                "local_plant_ids": local_plant_ids.get(row["id"], []),
                "external_entry_plant_ids": external_entry_plant_ids.get(row["id"], []),
                "data_notes": {
                    "population": row["data_notes_population"],
                    "consumption": row["data_notes_consumption"],
                    "illustrative_peak": row["data_notes_illustrative_peak"],
                },
            }
            for row in region_rows.values()
        ]

        plant_edges = [
            {
                "id": row["id"],
                "from": row["id_1"],
                "to": row["id_2"],
                "bidirectional": bool(row["bidirectional"]),
                "geodesic_distance_km": row["distance_km"],
                "estimated_loss_percent": row["loss_percent"],
                "max_transfer_mw": row["max_transfer_mw"],
                "available": bool(row["available"]),
                "topology_is_synthetic": bool(row["topology_is_synthetic"]),
                "capacity_and_loss_are_simulated": bool(row["capacity_and_loss_are_simulated"]),
            }
            for row in conn.execute("SELECT * FROM liaison")
        ]

        overrides_by_scenario = {}
        for row in conn.execute("SELECT * FROM scenario_override"):
            overrides_by_scenario.setdefault(row["id_2"], {})[row["id_1"]] = {
                "initial_output_mw": row["initial_output_mw"],
                "soft_upper_bound_mw": row["soft_upper_bound_mw"],
            }

        example_scenarios = [
            {
                "id": row["id"],
                "description": row["description"],
                "expected_result": row["expected_result"],
                "region_id": row["id_1"],
                "additional_demand_mw": row["additionnal_demand_mw"],
                "plant_overrides": overrides_by_scenario.get(row["id"], {}),
            }
            for row in conn.execute("SELECT * FROM scenario")
        ]

        # metadata / simulation_parameters : réglages statiques du JSON
        # d'origine, non repris dans le schéma relationnel (mcd_analytique.sql
        # ne prévoit pas de table pour ces clés).
        return {
            "metadata": {},
            "simulation_parameters": {},
            "plants": plants,
            "regions": regions,
            "plant_edges": plant_edges,
            "example_scenarios": example_scenarios,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 12. Récupération des données du solaire en /4 d'heure
# ---------------------------------------------------------------------------
def recuperer_donnees_solaires(donnees_hors_nucleaire):
    production_solaire = {}

    for region in donnees_hors_nucleaire["regions"]:
        region_id = region ["id"]
        production_solaire[region_id] = region["production_mw"]["solar"]

    return production_solaire

def parcourir_journee_solaire(donnees_hors_nucleaire):
    resultats = []

    for index in range(len(donnees_hors_nucleaire["timestamps"])):
        heure = donnees_hors_nucleaire["timestamps"][index]

        production = recuperer_donnees_solaires( donnees_hors_nucleaire, index)

        resultats.append({
            "heure": heure,
            "consommations": production,
        })
    return resultats


# ---------------------------------------------------------------------------
# 13. Récupération des données de l'héolien en /4 d'heure
# ---------------------------------------------------------------------------
def recuperer_donnees_eolien(donnees_hors_nucleaire):
    production_eolien = {}

    for region in donnees_hors_nucleaire["regions"]:
        region_id = region ["id"]
        production_eolien[region_id] = region["production_mw"]["wind"]

    return production_eolien

def parcourir_journee_eolien(donnees_hors_nucleaire):
    resultats = []

    for index in range(len(donnees_hors_nucleaire["timestamps"])):
        heure = donnees_hors_nucleaire["timestamps"][index]

        production = recuperer_donnees_eolien( donnees_hors_nucleaire, index)

        resultats.append({
            "heure": heure,
            "consommations": production,
        })
    return resultats

# ---------------------------------------------------------------------------
# 14. Calcul de la production énergétique hors nucléaire
# ---------------------------------------------------------------------------

def production_hors_nucleaire(production_solaire, production_eolien):
    total_production = {}

    for region_id in production_solaire:
        total_production[region_id] = []

        for index in range(96):
            total = (
                production_solaire[region_id][index]
                + production_eolien[region_id][index]
            )

            total_production[region_id].append(total)

    return total_production

# ---------------------------------------------------------------------------
# 15. Récupération de la consommation initiales pour chaque région
# ---------------------------------------------------------------------------
def recuperer_consommations_initiales(donnees):
    consommations_initiales = {}

    for region_id, region in donnees["initial_state_t_minus_1"]["regions"].items():
        consommations_initiales[region_id] = region["consumption_mw"]

    return consommations_initiales

# ---------------------------------------------------------------------------
# 16. Récupération du la consommation par région en /4 d'heure
# ---------------------------------------------------------------------------
def recuperer_consommations_par_temps(donnees, index):
    consommations = {}

    for region in donnees["regions"]:
        consommations[region["id"]] = region["consumption_mw"][index]
    return consommations

# ---------------------------------------------------------------------------
# 17. Evolution de la consommation des régions sur une journée
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 18. Calcul du delta de la consommation par région en /4 d'heure
# ---------------------------------------------------------------------------
def calculer_evolution_consommation(consommation_precedente, consommation_actuelle):
    return consommation_actuelle - consommation_precedente

def calculer_evolutions_regions(consommations_precedentes,consommations_actuelles):
    evolutions = {}

    for region_id in consommations_actuelles:
        evolution = calculer_evolution_consommation(consommations_precedentes[region_id], consommations_actuelles[region_id])

        evolutions[region_id] = evolution

    return evolutions

# ---------------------------------------------------------------------------
# 19. Calcul du besoin en nucléaire par région
# ---------------------------------------------------------------------------
def calcul_besoins_residuels(parcourir_journee,production_hors_nucleaire):
    total_production_restante = {}

    for region_id in production_hors_nucleaire:
        total_production_restante[region_id] = []

        for index in range(96):
            total = (
                parcourir_journee[index]["consommations"][region_id]
                - production_hors_nucleaire[region_id][index]
            )

            total_production_restante[region_id].append(total)

    return total_production_restante

# ---------------------------------------------------------------------------
# 20. Calcul de la puissance nucléaire initiale
# ---------------------------------------------------------------------------
def calcul_puissance_precedente(donnees_nucleaires):
    puissance_precedente = {}

    for centrale in donnees_nucleaires["plants"]:
        puissance_precedente[centrale["plant_id"]] = (
            centrale["initial_output_mw_at_23_45_previous_day"]
        )

    return puissance_precedente

# ---------------------------------------------------------------------------
# 20. Récupération de l'historique de la production nucléaire
# ---------------------------------------------------------------------------
def initialiser_historique_production(donnees_nucleaires):
    historique = {}

    for centrale in donnees_nucleaires["plants"]:
        historique[centrale["plant_id"]] = []

    return historique

# ---------------------------------------------------------------------------
# 21. Calcul de la production nucléaire réelle
# ---------------------------------------------------------------------------
def calcul_production_reelle_nucleaire(puissance_reelle, puissance_precedente):
    production_nucleaire_reelle_fournie = (puissance_reelle - puissance_precedente)

    return production_nucleaire_reelle_fournie

# ---------------------------------------------------------------------------
# 22. Calcul un pas pour chacune des centrales
# ---------------------------------------------------------------------------
def calculer_un_pas_temps(
    donnees_nucleaires,
    puissance_precedente,
    puissances_souhaitees,
    historique
):
    for centrale in donnees_nucleaires["plants"]:
        plant_id = centrale["plant_id"]

        puissance_souhaitee = puissances_souhaitees[plant_id]

        nouvelle_puissance = puissance_reelle(
            puissance_precedente[plant_id],
            puissance_souhaitee,
            centrale
        )

        historique[plant_id].append(nouvelle_puissance)

        puissance_precedente[plant_id] = nouvelle_puissance

    return puissance_precedente, historique

# ---------------------------------------------------------------------------
# 22. Calcul de l'énergie disponible dans les centrtales après contraintes
# ---------------------------------------------------------------------------
def calcul_marge_reelle_disponible(puissance_precedente,centrale):
    puissance_souhaitee = calcul_puissance_max(centrale)

    puissance_atteignable = puissance_reelle(puissance_precedente,puissance_souhaitee,centrale)

    marge_reelle = ( puissance_atteignable - puissance_precedente)
    
    return max(marge_reelle, 0)

# ---------------------------------------------------------------------------
# 23. Fonction qui vérifie si la perturbation est en cours à l'heure donnée.
# ---------------------------------------------------------------------------

def perturbation_active(perturbation, heure):
    """
   Fonction qui vérifie si la perturbation est en cours à l'heure donnée.
   retourne True or false
    """

    start = datetime.strptime(perturbation.start, "%H:%M").time()
    end = datetime.strptime(perturbation.end, "%H:%M").time()
    current = datetime.strptime(heure, "%H:%M").time()

    return start <= current < end

# ---------------------------------------------------------------------------
# 24. Appliquer les perturbations actives à une région et une heure donnée.
# ---------------------------------------------------------------------------
def appliquer_perturbation(region_id, heure, demande_mw, perturbations):
    """
    Applique les perturbations actives à une région et une heure donnée.
    """

    demande_perturbee = demande_mw

    for perturbation in perturbations:

        if perturbation.regionId != region_id:
            continue

        if perturbation_active(perturbation, heure):
            demande_perturbee += perturbation.deltaMw

    return demande_perturbee

# ------------------------------------------------------------------------------
# 26. Fonction qui retourne les besoins résiduels par région et par /4 d'heure
# ------------------------------------------------------------------------------

def get_besoins_solaires_eoliens():

    donnees_non_pilotables = charger_journee_reference_hors_nucleaire()

    production_solaire = recuperer_donnees_solaires(
        donnees_non_pilotables
    )

    production_eolien = recuperer_donnees_eolien(
        donnees_non_pilotables
    )
    
    return {
        "solaires": production_solaire,
        "eoliens" : production_eolien
    }

# -------------------------------------------------------------------------
# 27. Fonction pour calculer la réserve minimale 
#--------------------------------------------------------------------------
def calculer_reserve(etat_centrales, store):
    capacite_max_totale = 0
    production_actuelle_totale = 0

    for plant_id, current_output in etat_centrales.items():
        central = store.centrales.get(plant_id)

        if central is None:
            continue

        capacite_max_totale += central.soft_upper_bound_mw
        production_actuelle_totale += current_output

    reserve_disponible = (
        capacite_max_totale - production_actuelle_totale
    )

    return max(reserve_disponible,0)