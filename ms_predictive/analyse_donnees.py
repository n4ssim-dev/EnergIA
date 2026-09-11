import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from utils.db import connect_bdd, disconnect_bdd

from preparation_ml import preparer_dataframe_ml

# ---------------------------------
# Chargement de la base analytique
# ---------------------------------

def charger_donnees_analytiques():
    connexion = connect_bdd()

    requete = """
    SELECT
        fc.consommation_mw,
        fc.date_heure,

        dr.id_region,
        dr.code_insee,
        dr.nom AS region,
        dr.demographie,
        dr.part_indus_lourde,

        dt.annee,
        dt.saison,
        dt.mois,
        dt.jour_semaine,
        dt.quart_heure,
        dt.est_weekend,
        dt.est_ferie,

        dm.temperature_min,
        dm.temperature_max,
        dm.temperature_moy,

        de.taux_impact_attendu

    FROM fait_consommation AS fc

    LEFT JOIN dim_regionale AS dr
        ON fc.id_region = dr.id_region

    LEFT JOIN dim_temps AS dt
        ON fc.date_heure = dt.date_heure

    LEFT JOIN dim_meteo AS dm
        ON fc.id_region = dm.id_region
        AND DATE(fc.date_heure) = dm.date_meteo

    LEFT JOIN dim_event AS de
        ON fc.id_region = de.id_region
        AND DATE(fc.date_heure) = de.date_event
    """

    df = pd.read_sql_query(requete, connexion)

    disconnect_bdd(connexion)

    return df

if __name__ == "__main__":
    # ---------------------------------
    # Chargement
    # ---------------------------------
    df = charger_donnees_analytiques()

    # ---------------------------------
    # Préparation des données ML
    # ---------------------------------
    df_ml = preparer_dataframe_ml(df)

    df_correlation = pd.get_dummies(
        df_ml,
        columns=[
            "saison",
        ],
        drop_first=False
    )


    # ---------------------------------
    # Matrice de corrélation
    # ---------------------------------
    correlation = df_correlation.corr(numeric_only=True)

    print("Matrice de corrélation :")
    print(correlation)

    # ---------------------------------
    # Corrélation avec la consommation
    # ---------------------------------
    correlation_consommation = (correlation["consommation_mw"].sort_values(ascending=False))

    print("\nCorrélation avec consommation_mw :")
    print(correlation_consommation)

    # ---------------------------------
    # Heatmap de corrélation
    # ---------------------------------
    plt.figure(figsize=(12, 8))

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0
    )

    plt.title("Matrice de corrélation des variables")
    plt.tight_layout()
    plt.show()

