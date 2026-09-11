import os
import pandas as pd
import joblib
import sqlite3


from fastapi import APIRouter, Depends, HTTPException, Query

API_PASSWORD = os.getenv("API_PASSWORD", "5")

router = APIRouter(prefix="/predictions")


def creer_X_prediction(id_region, date, heure):
    conn = sqlite3.connect("data/analytique.db")
    
    # --------------------------------
    # 1. Récupérer la ligne cible
    # --------------------------------

    requete = """
        SELECT
            dr.id_region,
            dr.demographie,
            dr.part_indus_lourde,

            dt.annee,
            dt.saison,
            dt.mois,
            dt.date_,
            dt.jour_semaine,
            dt.heure,
            dt.quart_heure,
            dt.est_weekend,
            dt.est_ferie

        FROM dim_temps AS dt
        CROSS JOIN dim_regionale AS dr

        WHERE dr.id_region = ?
          AND dt.date_ = ?
          AND dt.heure = ?
    """

    ligne = pd.read_sql_query(
        requete,
        conn,
        params=(id_region, date, heure)
    )

    if ligne.empty:
        raise ValueError(
            f"Date/heure introuvable : {date} {heure}"
        )

    ligne = ligne.iloc[0]

    # --------------------------------
    # 2. Variables temporelles
    # --------------------------------

    annee = ligne["annee"]
    saison = ligne["saison"]
    mois = ligne["mois"]
    jour_semaine = ligne["jour_semaine"]
    quart_heure = ligne["quart_heure"]
    est_weekend = ligne["est_weekend"]
    est_ferie = ligne["est_ferie"]

    heure_prediction = ligne["heure"]

    # --------------------------------
    # 3. Informations région
    # --------------------------------

    demographie = ligne["demographie"]
    part_indus_lourde = ligne["part_indus_lourde"]

    # --------------------------------
    # 4. Consommations précédentes
    # --------------------------------

    # À compléter avec la requête historique

    conso_15min_precedente = ...
    conso_30min_precedente = ...
    conso_1h_precedente = ...
    conso_jour_precedent = ...
    conso_semaine_precedent = ...

    # --------------------------------
    # 5. Construction de X
    # --------------------------------

    X = pd.DataFrame([{
        "id_region": id_region,
        "annee": annee,
        "saison": saison,
        "mois": mois,
        "jour_semaine": jour_semaine,
        "heure": heure_prediction,
        "quart_heure": quart_heure,
        "est_weekend": est_weekend,
        "est_ferie": est_ferie,

        "temperature_min": temperature_min,
        "temperature_max": temperature_max,

        "type_event": type_event,
        "impact_attendu": impact_attendu,

        "demographie": demographie,
        "part_indus_lourde": part_indus_lourde,

        "conso_15min_precedente": conso_15min_precedente,
        "conso_30min_precedente": conso_30min_precedente,
        "conso_1h_precedente": conso_1h_precedente,
        "conso_jour_precedent": conso_jour_precedent,
        "conso_semaine_precedent": conso_semaine_precedent
    }])

    return X

    

@router.get("/consommation/{region_id}/{date}/{heure}")
def consommation_region(
    region_id: str = Query(..., description="Region"),
    date: str = Query(..., description="Date au format YYYY-MM-DD"),
    heure: str = Query(..., description="Heure au format HH:MM"),
):
    """ Prédiction de la consommation d'une région à une date et un quart d'heure."""
    
    model = joblib.load("model_random_forest/conso_predictor.pkl")
    preprocesseur = joblib.load("preprocesseur/preprocesseur.pkl")

    X_prepare = preprocesseur.transform(creer_X_prediction(region_id, date, heure))

    prediction = model.predict(X_prepare)

    return {
          "prediction": prediction[0]
        }
   
   

