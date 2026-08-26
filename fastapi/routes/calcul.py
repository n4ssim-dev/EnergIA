from haversine import haversine
import json


# ---------------------------------------------------------------------------
# 1. Puissance disponible d'une centrale
# ---------------------------------------------------------------------------
def calcul_puissanceDispo(soft_upper_bound_mw, initial_output_mw):
    maxPower = soft_upper_bound_mw
    powerOutput = initial_output_mw
    availablePower = maxPower - powerOutput
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

        available_power = calcul_puissanceDispo(
            candidat["soft_upper_bound_mw"],
            current_output_mw
        )

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
# 11. Import des JSON
# ---------------------------------------------------------------------------
def charger_journee_reference_hors_nucleaire():
    with open("data/energia-production-non-pilotable.json", "r", encoding="utf-8") as fichier:
        donnees_hors_nucleaire = json.load(fichier)

    return donnees_hors_nucleaire

def charger_journee_reference():
    with open("data/energia-journee-reference-avec-t-moins-1.json", "r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    return donnees

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
def calcul_production_restante_a_fournir(parcourir_journee,production_hors_nucleaire):
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
# 20. Calcul des besoins résiduels après monopolisation du nucléaire
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

        available_power = calcul_puissanceDispo(
            candidat["soft_upper_bound_mw"],
            current_output_mw
        )

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






# production_nucleaire_reelle_par_region
# ---------------------------------------------------------------------------
# 20. Calcul des besoins résiduels après monopolisation du nucléaire
# ---------------------------------------------------------------------------

# def calul_besoins_residuels(calcul_production_restante_a_fournir, )
#     besoins_residuels = {}

#     for region_id in calcul_production_restante_a_fournir :
#         besoins_residuels[region_id] = []

#         for index in range(96):
#             total = (calcul_production_restante_a_fournir[index][region_id] - 

#             )