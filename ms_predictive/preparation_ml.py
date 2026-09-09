from pathlib import Path
import sqlite3
import pandas as pd


# ---------------------------------
# Connexion à la base
# ---------------------------------

dossier_script = Path(__file__).resolve().parent
chemin_bdd = dossier_script.parent / "analytique.db"

connexion = sqlite3.connect(chemin_bdd)

# ---------------------------------
# Construction du dataframe
# ---------------------------------

def preparer_dataframe_ml(df):
    df_ml = df.copy()

    # transformations
    # créations de variables retardées
    # encodages éventuels
    # suppression des valeurs manquantes

    return df_ml

df_ml = [
    "id_region",
    "annee",
    "saison",
    "mois",
    "jour_semaine",
    "heure",
    "quart_heure",
    "est_weekend",
    "est_ferie",
    "temperature_min",
    "temperature_max",
    "type_event",
    "impact_attendu",
    "demographie",
    "part_indus_lourde",
    "conso_15min_precedente",
    "conso_30min_precedente",
    "conso_1h_precedente",
    "conso_jour_precedent",
    "conso_semaine_precedente",
    "consumption_mw"
]

# ---------------------------------
# Définir x et y 
# ---------------------------------

y = df_ml["consumption_mw"]
x = 