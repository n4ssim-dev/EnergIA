import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from preparation_ml import preparer_dataframe_ml

# ---------------------------------
# Chargement de la base analytique
# ---------------------------------

def charger_donnees_analytiques():
    connexion = sqlite3.connect("data/analytique.db")

    requete = """
    SELECT
        fc.consumption_mw,

        dr.id_region,
        dr.code_insee,
        dr.nom AS region,
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
        dt.est_ferie,

        dm.temperature_min,
        dm.temperature_max,

        de.type_event,
        de.nom AS evenement,
        de.impact_attendu

    FROM fait_consommation AS fc

    LEFT JOIN dim_regionale AS dr
        ON fc.id_region = dr.id_region

    LEFT JOIN dim_temps AS dt
        ON fc.id_temps = dt.id_temps

    LEFT JOIN dim_meteo AS dm
        ON fc.id_meteo = dm.id_meteo

    LEFT JOIN dim_event AS de
        ON fc.id_event = de.id_event
    """

    df = pd.read_sql_query(requete, connexion)

    connexion.close()

    return df
# ---------------------------------
# Chargement
# ---------------------------------

df = charger_donnees_analytiques()

# ---------------------------------
# Préparation des données ML
# ---------------------------------

df_ml = preparer_dataframe_ml(df)

# ---------------------------------
# Matrice de corrélation
# ---------------------------------

correlation = df_ml.corr(numeric_only=True)

print("Matrice de corrélation :")
print(correlation)

# ---------------------------------
# Corrélation avec la consommation
# ---------------------------------

correlation_consommation = (correlation["consumption_mw"].sort_values(ascending=False))

print("\nCorrélation avec consumption_mw :")
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
