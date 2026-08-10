

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
# 10. Orchestration complète : répartition d'une augmentation de demande
#     (MW) sur les centrales candidates d'une région (locales, puis
#     distantes via Dijkstra), triées par score et servies dans l'ordre.
#     Partagée par /dijkstra/calcule et /simulation (dijkstra.py, gateway.py)
#     pour éviter que /simulation ne fasse un aller-retour HTTP séparé.
# ---------------------------------------------------------------------------
def executer_simulation(store, region, augmentation_mw):
    region_data = store.regions.get(region)
    if region_data is None:
        raise ValueError(f"Région '{region}' introuvable")

    candidats = []

    # --- Centrales locales (distance = 0, pertes = 0) ---
    central_locales = []
    for plant_id in region_data.local_plant_ids:
        centrale_obj = store.centrales.get(plant_id)
        if centrale_obj:
            central_locales.append(centrale_obj)

    for central in central_locales:
        result = calcul_score(
            geodesic_distance_km=0,
            loss_percent=0,
            soft_upper_bound_mw=central.soft_upper_bound_mw,
            technical_penalty=central.technical_penalty,
            plant_id=central.id,
            local_plant_ids=region_data.local_plant_ids,
            initial_output_mw=central.initial_output_mw
        )
        candidats.append({
            "plant_id": central.id,
            "score": result,
            "soft_upper_bound_mw": central.soft_upper_bound_mw,
            "initial_output_mw": central.initial_output_mw,
        })

    # --- Centrales externes
    if central_locales:
        source_id = central_locales[0].id
        distantes = rechercher_centrales_distantes(
            source_id, region_data.external_entry_plant_ids, store
        )
        for d in distantes:
            central = store.centrales.get(d["plant_id"])
            if central is None:
                continue
            result = calcul_score(
                geodesic_distance_km=d["distance_km"],
                loss_percent=d["loss_percent"],
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                initial_output_mw=central.initial_output_mw
            )
            candidats.append({
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "initial_output_mw": central.initial_output_mw,
            })
    else:
        for plant_id in region_data.external_entry_plant_ids:
            central = store.centrales.get(plant_id)
            if central is None:
                continue
            result = calcul_score(
                geodesic_distance_km=0,
                loss_percent=0,
                soft_upper_bound_mw=central.soft_upper_bound_mw,
                technical_penalty=central.technical_penalty,
                plant_id=central.id,
                local_plant_ids=region_data.local_plant_ids,
                initial_output_mw=central.initial_output_mw
            )
            candidats.append({
                "plant_id": central.id,
                "score": result,
                "soft_upper_bound_mw": central.soft_upper_bound_mw,
                "initial_output_mw": central.initial_output_mw,
            })

    candidats_tries = classer_candidats(candidats)
    resultat = repartir_demande(augmentation_mw, candidats_tries)

    return {
        "region": region,
        "demande_mw": augmentation_mw,
        "repartition": resultat["allocation"],
        "puissance_manquante_mw": resultat["unsatisfied_mw"]
    }
