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

def constraint (puissance_precedente, puissance_souhaitee, centrale) :
    if puissance_souhaitee > puissance_precedente :
        
    else 