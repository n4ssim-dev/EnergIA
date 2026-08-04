

def calcul_puissanceDispo(soft_upper_bound_mw, initial_output_mw):
    maxPower = soft_upper_bound_mw
    powerOutput = initial_output_mw
    availablePower = maxPower - powerOutput
    return max(availablePower, 0)



def calcul_taux_saturation(initial_output_mw, soft_upper_bound_mw):
    powerOutput = initial_output_mw
    maxPower = soft_upper_bound_mw
    if maxPower == 0:
        return 1
    saturationRate = powerOutput / maxPower
    return max(saturationRate, 0)



def calcul_pertes(transferred_mw, loss_percent):
    energieTransfert = transferred_mw
    pertePourcent = loss_percent
    calcul = energieTransfert * (pertePourcent / 100)
    return calcul



def du_terroire(plant_id, local_plant_ids):
    central = plant_id
    region = local_plant_ids
    return central in region


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



def classer_candidats(candidats):
    ranked = sorted(candidats, key=lambda x: x["score"])
    return ranked



def trouver_liaison(plant_edges, from_id, to_id):
    for i in plant_edges:
        if (i["from"] == from_id and i["to"] == to_id) or (i["from"] == to_id and i["to"] == from_id):
            return i
    else:
        return None



def construire_graph_distance(plant_edges):
    graph = {}
    for edge in plant_edges:
        a, b = edge["from"], edge["to"]
        if a not in graph:
            graph[a] = {}
        if b not in graph:
            graph[b] = {}
        graph[a][b] = edge["geodesic_distance_km"]
        if edge["bidirectional"]:
            graph[b][a] = edge["geodesic_distance_km"]
    return graph


def rechercher_centrales_distantes(source_id, cibles_ids, plant_edges, GraphClass):
   
    graph = construire_graph_distance(plant_edges)
    g = GraphClass(graph=graph)
    distances = g.shortest_distance(source_id)

    resultats = []
    for cible in cibles_ids:
        distance = distances.get(cible, float("inf"))
        if distance == float("inf"):
            continue  # aucun chemin trouvé, on exclut ce candidat

        liaison_directe = trouver_liaison(plant_edges, source_id, cible)
        loss_percent = liaison_directe["estimated_loss_percent"] if liaison_directe else None

        resultats.append({
            "plant_id": cible,
            "distance_km": distance,
            "loss_percent": loss_percent
        })

    return resultats


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