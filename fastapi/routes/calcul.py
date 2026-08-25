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
                  technical_penalty, plant_id, local_plant_ids, initial_output_mw):
    score_distance = geodesic_distance_km * 1
    score_loss = loss_percent * 45
    load = calcul_taux_saturation(initial_output_mw, soft_upper_bound_mw)
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
def repartir_demande(demande_mw, candidats_tries):
    allocation = []
    demand_left = demande_mw

    for candidats in candidats_tries:
        if demand_left <= 0:
            break

        available_power = calcul_puissanceDispo(
            candidats["soft_upper_bound_mw"],
            candidats["initial_output_mw"]
        )

        if available_power <= 0:
            continue

        allocation_candidat = min(demand_left, available_power)

        allocation.append({
            "plant_id": candidats["plant_id"],
            "allocated_mw": allocation_candidat
        })

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
# 11. Import du JSON
# ---------------------------------------------------------------------------
def charger_journee_reference():
    with open("data/energia-production-non-pilotable.json", "r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    return donnees

# ---------------------------------------------------------------------------
# 12. Récupération des données du solaire
# ---------------------------------------------------------------------------
def recuperer_donnees_solaires(donnees):
    production_solaire = {}

    for region in donnees["regions"]:
        region_id = region ["id"]
        production_solaire[region_id] = region["production_mw"]["solar"]

    return production_solaire

# ---------------------------------------------------------------------------
# 13. Récupération des données de l'héolien
# ---------------------------------------------------------------------------
def recuperer_donnees_eolien(donnees):
    production_eolien = {}

    for region in donnees["regions"]:
        region_id = region ["id"]
        production_eolien[region_id] = region["production_mw"]["wind"]

    return production_eolien

# ---------------------------------------------------------------------------
# 14. Calcul de la production énergétique hors nucléaire
# ---------------------------------------------------------------------------

def production_hors_nucleaire(production_solaire, production_eolien):
    total_production = [0] * 96

    for region_id in production_solaire:
        for index in range(96):
            total_production[index] += (
                production_solaire[region_id][index] + production_eolien[region_id][index]
            )

    return total_production

# ---------------------------------------------------------------------------
# 14. Calcul de la production énergétique hors nucléaire
# ---------------------------------------------------------------------------