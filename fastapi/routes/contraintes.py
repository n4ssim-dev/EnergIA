import json

def charger_param_temps_nucleaire():
    with open("data/energia_parametres_temporels_nucleaire.json", "r", encoding="utf-8") as fichier:
        donnees_nucleaire = json.load(fichier)

    return donnees_nucleaire

# ---------------------------------------------------------------------------
# 1. Puissance maximale
# ---------------------------------------------------------------------------

def calcul_puissance_max(centrale):
    maxPower = centrale.installed_power_mw
    return(maxPower)

# ---------------------------------------------------------------------------
# 2. Puissance minimale
# ---------------------------------------------------------------------------

def calcul_puissance_min(centrale):
    minPower = sum(r.minimum_design_power_mw for r in centrale.reactors)
    return(minPower)

# ---------------------------------------------------------------------------
# 3. Vitesse de montée
# ---------------------------------------------------------------------------

def calcul_vitesse_montee(centrale) :
    rampUp = centrale.max_ramp_up_mw_per_15_min
    return(rampUp)

# ---------------------------------------------------------------------------
# 4. Vitesse de descente
# ---------------------------------------------------------------------------

def calcul_vitesse_descente(centrale) :
    rampDown = calcul_vitesse_montee(centrale)
    return(rampDown)


# ---------------------------------------------------------------------------
# 5. Calcule contrainte en fonction de la demande
# ---------------------------------------------------------------------------

def constraint (puissance_precedente, puissance_souhaitee, centrale) :
    if puissance_souhaitee > puissance_precedente :
       contrainte = calcul_vitesse_montee(centrale) + puissance_precedente
       return min(contrainte,puissance_souhaitee)
    elif puissance_souhaitee < puissance_precedente :
        contrainte =  puissance_precedente - calcul_vitesse_descente(centrale)
        return max (contrainte,puissance_souhaitee)
    else :
        return(puissance_souhaitee)
# ---------------------------------------------------------------------------
#6. On s'assure ici que la puissance reste entre le min et max absolus
# ---------------------------------------------------------------------------

def appliquer_bornes (puissance,centrale):
    return max(calcul_puissance_min(centrale), min(puissance, calcul_puissance_max(centrale)))

# ------------------------------------------------------------------------------------------------------------------
#7. Calcule de la puissance reelle en utilisant les contraintes de la centrale et les bornes de puissance max et min
# ------------------------------------------------------------------------------------------------------------------

def puissance_reelle(puissance_precedente, puissance_souhaitee, centrale):
    contrainte = constraint(puissance_precedente, puissance_souhaitee, centrale)
    limite = appliquer_bornes(contrainte,centrale)
    return (limite)