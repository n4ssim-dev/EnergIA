from pathlib import Path

import joblib
import pandas as pd

from utils.db import connect_bdd, disconnect_bdd


# ---------------------------------
# Chargement du modèle
# ---------------------------------

DOSSIER_SCRIPT = Path(__file__).resolve().parent

CHEMIN_MODELE = DOSSIER_SCRIPT / "conso_predictor.pkl"
CHEMIN_PREPROCESSEUR = DOSSIER_SCRIPT / "preprocesseur.pkl"

model = joblib.load(CHEMIN_MODELE)
preprocesseur = joblib.load(CHEMIN_PREPROCESSEUR)


# ---------------------------------
# Récupération des informations régionales
# ---------------------------------

def recuperer_infos_region(id_region):
    connexion = connect_bdd()

    requete = """
    SELECT
        id_region,
        demographie
    FROM dim_regionale
    WHERE id_region = %s
    """

    try:
        with connexion.cursor() as cursor:
            cursor.execute(
                requete,
                (id_region,)
            )

            resultat = cursor.fetchone()

    finally:
        disconnect_bdd(connexion)

    if resultat is None:
        raise ValueError(
            f"Région inconnue : {id_region}"
        )

    return {
        "id_region": resultat[0],
        "demographie": resultat[1],
    }


# ---------------------------------
# Récupération de la météo
# ---------------------------------

def recuperer_meteo(id_region, date_heure):
    connexion = connect_bdd()

    requete = """
    SELECT
        temperature_min,
        temperature_max,
        temperature_moy
    FROM dim_meteo
    WHERE id_region = %s
      AND date_meteo = %s
    """

    date_meteo = pd.to_datetime(date_heure).date()

    try:
        with connexion.cursor() as cursor:
            cursor.execute(
                requete,
                (
                    id_region,
                    date_meteo,
                )
            )

            resultat = cursor.fetchone()

    finally:
        disconnect_bdd(connexion)

    if resultat is None:
        raise ValueError(
            f"Météo introuvable pour "
            f"{id_region} le {date_meteo}"
        )

    return {
        "temperature_min": float(resultat[0]),
        "temperature_max": float(resultat[1]),
        "temperature_moy": float(resultat[2]),
    }


# ---------------------------------
# Détermination de la saison
# ---------------------------------

def determiner_saison(mois):
    if mois in [12, 1, 2]:
        return "hiver"

    if mois in [3, 4, 5]:
        return "printemps"

    if mois in [6, 7, 8]:
        return "ete"

    return "automne"


# ---------------------------------
# Jours de la semaine
# ---------------------------------

JOURS_SEMAINE = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
]


# ---------------------------------
# Prédiction d'une consommation
# ---------------------------------

def predire_consommation(donnees):
    df_prediction = pd.DataFrame([donnees])

    X_prediction = preprocesseur.transform(df_prediction)

    prediction = model.predict(X_prediction)

    return float(prediction[0])


# ---------------------------------
# Génération des créneaux
# ---------------------------------

def generer_creneaux(date_debut, date_fin):
    date_debut = pd.to_datetime(date_debut)

    date_fin = pd.to_datetime(date_fin)

    return pd.date_range(
        start=date_debut,
        end=date_fin,
        freq="30min"
    )


# ---------------------------------
# Prédictions
# ---------------------------------

def predire_periode(date_debut, date_fin, regions):
    creneaux = generer_creneaux(date_debut, date_fin)

    resultats = []

    for region in regions:

        infos_region = recuperer_infos_region(region)

        for date_heure in creneaux:

            infos_meteo = recuperer_meteo(region, date_heure)

            jour_semaine = JOURS_SEMAINE[
                date_heure.weekday()
            ]

            donnees = {
                "id_region": infos_region["id_region"],
                "annee": date_heure.year,
                "saison": determiner_saison(
                    date_heure.month
                ),
                "mois": date_heure.month,
                "jour_semaine": jour_semaine,
                "heure": (
                    date_heure.hour
                    + date_heure.minute / 60
                ),
                "quart_heure": (
                    date_heure.minute // 15
                ),
                "est_weekend": (
                    jour_semaine
                    in ["samedi", "dimanche"]
                ),
                "est_ferie": False,
                "temperature_min": infos_meteo["temperature_min"],
                "temperature_max": infos_meteo["temperature_max"],
                "temperature_moy": infos_meteo["temperature_moy"],
                "taux_impact_attendu": 0.0,
                "demographie": infos_region["demographie"],
                "presence_evenement": 0,
            }

            prediction = predire_consommation(donnees)

            resultats.append(
                {
                    "id_region": region,
                    "date_heure": date_heure.isoformat(),
                    "consommation_predite_mw": round(
                        prediction,
                        2
                    ),
                }
            )

    return resultats

resultats = predire_periode(
    "2026-08-30 08:00:00",
    "2026-08-30 12:00:00",
    [
        "occitanie",
        "nouvelle_aquitaine",
        "ile_de_france",
    ]
)

print(resultats)