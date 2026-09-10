import joblib
import pandas as pd

from preparation_ml import preparer_dataframe_ml
from analyse_donnees import charger_donnees_analytiques

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# ---------------------------------
# Chargement des données
# ---------------------------------
df = charger_donnees_analytiques()
df_ml = preparer_dataframe_ml(df)

# ---------------------------------
# Définition de la cible
# ---------------------------------
y = df_ml["consommation_mw"]

# ---------------------------------
# Définition des features
# ---------------------------------
X = df_ml[
    [
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
        "taux_impact_attendu",
        "demographie",
        "part_indus_lourde",

        "conso_15min_precedente",
        "conso_30min_precedente",
        "conso_1h_precedente",
        "conso_jour_precedent",
        "conso_semaine_precedente",
    ]
]

# ---------------------------------
# Séparation temporelle
# ---------------------------------
X_train = X[df_ml["annee"] < 2025]
X_test = X[df_ml["annee"] == 2025]

y_train = y[df_ml["annee"] < 2025]
y_test = y[df_ml["annee"] == 2025]

# ---------------------------------
# Séparation des types de variables
# ---------------------------------
variables_categorielles = [
    "id_region",
    "saison",
    "jour_semaine",
    "type_event",
    "impact_attendu",
]

variables_numeriques = [
    "annee",
    "mois",
    "heure",
    "quart_heure",
    "est_weekend",
    "est_ferie",
    "temperature_min",
    "temperature_max",
    "demographie",
    "part_indus_lourde",

    "conso_15min_precedente",
    "conso_30min_precedente",
    "conso_1h_precedente",
    "conso_jour_precedent",
    "conso_semaine_precedente",
]

# ---------------------------------
# Préparation de l'encodage
# ---------------------------------
preprocesseur = ColumnTransformer(
    transformers=[
        ("categoriel",OneHotEncoder(handle_unknown="ignore"),variables_categorielles)
    ],
    remainder="passthrough")

#------------------------------------------------------------------
# 1. Création de la régréssion linéaire
#------------------------------------------------------------------
X_train_prepare = preprocesseur.fit_transform(X_train)
X_test_prepare = preprocesseur.transform(X_test)

print(X_train_prepare.shape)
print(type(X_train_prepare))
print(X_test_prepare.shape)

model_lineaire = LinearRegression()

# Entrainement du modèle
model_lineaire.fit(X_train_prepare, y_train)
print("Entraînement terminé")

# Prédiction du modèle
prediction = model_lineaire.predict(X_test_prepare)

print(prediction[:10])
print(y_test.head(10))

# Utilisation du MAE
mae_lineaire = mean_absolute_error(y_test, prediction)
mape_lineaire = mean_absolute_percentage_error(y_test, prediction)
print(f"MAE régression linéaire : {mae_lineaire:.0f} MW")
print(f"MAPE régression linéaire : {mape_lineaire * 100:.2f} %")

#------------------------------------------------------------------
# 2. Baseline naïve : préparation 2024 et 2025
#------------------------------------------------------------------

df_2024 = df_ml[df_ml["annee"] == 2024].copy()
df_2025 = df_ml[df_ml["annee"] == 2025].copy()

#création de clés pour la baseline pour éviter qu'elle lise ligne par ligne (ce qui poserait problème sur une année bisextile)
df_2024["cle_baseline"] = (
    df_2024["id_region"].astype(str)
    + "_"
    + df_2024["mois"].astype(str)
    + "_"
    + df_2024["jour_mois"].astype(str)
    + "_"
    + df_2024["heure"].astype(str)
)

df_2025["cle_baseline"] = (
    df_2025["id_region"].astype(str)
    + "_"
    + df_2025["mois"].astype(str)
    + "_"
    + df_2025["jour_mois"].astype(str)
    + "_"
    + df_2025["heure"].astype(str)
)

print("2024 :", df_2024.shape)
print("2025 :", df_2025.shape)


# Préparation de la consommation 2024
df_2024_baseline = df_2024[["cle_baseline","consommation_mw",]].copy()
df_2024_baseline = df_2024_baseline.rename(columns={"consommation_mw": "prediction_naive"})

# Correspondance 2025 avec 2024
df_baseline = df_2025.merge(df_2024_baseline, on="cle_baseline", how="inner")

# Valeurs réelles et prédictions naïves
y_baseline = df_baseline["consommation_mw"]
prediction_baseline = df_baseline["prediction_naive"]

# Évaluation de la baseline naïve
mae_baseline = mean_absolute_error(y_baseline, prediction_baseline)
mape_baseline = mean_absolute_percentage_error(y_baseline, prediction_baseline)

print(f"MAE baseline naïve : {mae_baseline:.0f} MW")
print(f"MAPE baseline naïve : {mape_baseline * 100:.2f} %")

#------------------------------------------------------------------
# 2. Random Forest
#------------------------------------------------------------------

model_random_forest = RandomForestRegressor(random_state=42)

# Entraînement
model_random_forest.fit(X_train_prepare,y_train)

# Prédiction sur 2025
prediction_random_forest = model_random_forest.predict(X_test_prepare)

# Évaluation
mae_random_forest = mean_absolute_error(y_test, prediction_random_forest)
mape_random_forest = mean_absolute_percentage_error(y_test, prediction_random_forest)

print(f"MAE Random Forest : {mae_random_forest:.0f} MW")
print(f"MAPE Random Forest : {mape_random_forest * 100:.2f} %")

# Enregistrement du model pour ne pas avoir à le réentréner à chaque fois
joblib.dump(model_random_forest,"conso_predictor.pkl")
joblib.dump(preprocesseur,"preprocesseur.pkl")

# ---------------------------------
# 4. Comparaison des modèles
# ---------------------------------
resultats = pd.DataFrame(
    {
        "Modele": ["Régression linéaire", "Baseline naïve", "Random Forest",],
        "MAE_MW": [mae_lineaire, mae_baseline, mae_random_forest,],
        "MAPE_%": [mape_lineaire * 100, mape_baseline * 100, mape_random_forest * 100,],
    }
)

print(resultats)

# Intégrer les % de sureté de la prédiction de Ramdom Forest et l'alerte automatique :
# Score
        # acc = model.score(X_test, y_test)
        # st.metric("Accuracy du modèle", f"{acc*100:.1f}%")

        # # Probabilités
        # df_cpap["prob"] = model.predict_proba(X)[:, 1]
 # ALERTE AUTOMATIQUE
        # if len(df_risque) > 0:
        #     st.error(f" {len(df_risque)} patient(s) risquent une alerte CPAP dans les prochains jours.")
        # else:
        #     st.success("Aucun patient à risque détecté.")

        # # Tableau des patients à risque
        # if len(df_risque) > 0:
        #     st.dataframe(
        #         df_risque[["id_patient", "date_complete", "prob"]]
        #         .sort_values("prob", ascending=False)
        #         .rename(columns={"prob": "probabilité"})
        #     )