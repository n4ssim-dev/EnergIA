from preparation_ml import preparer_dataframe_ml
from analyse_donnees import charger_donnees_analytiques

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error


# ---------------------------------
# Chargement des données
# ---------------------------------
df = charger_donnees_analytiques()

df_ml = preparer_dataframe_ml(df)

# ---------------------------------
# Définition de la cible
# ---------------------------------
y = df_ml["consumption_mw"]

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
        "type_event",
        "impact_attendu",
        "demographie",
        "part_indus_lourde",
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
]

# ---------------------------------
# Préparation de l'encodage
# ---------------------------------
preprocesseur = ColumnTransformer(
    transformers=[
        ("categoriel",OneHotEncoder(handle_unknown="ignore"),variables_categorielles)
    ],
    remainder="passthrough")

# # ---------------------------------
# # Apprentissage sur X_train
# # ---------------------------------
# X_train_encode = preprocesseur.fit_transform(X_train)

# # ---------------------------------
# # Application sur X_test
# # ---------------------------------
# X_test_encode = preprocesseur.transform(X_test)

# # ---------------------------------
# # Vérifications
# # ---------------------------------
# print("X_train avant encodage :", X_train.shape)
# print("X_train après encodage :", X_train_encode.shape)

# print("X_test avant encodage :", X_test.shape)
# print("X_test après encodage :", X_test_encode.shape)

# print("y_train :", y_train.shape)
# print("y_test :", y_test.shape)

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

#------------------------------------------------------------------
# Utilisation du MAE
#------------------------------------------------------------------
mae_lineaire = mean_absolute_error(y_test, prediction)
mape_lineaire = mean_absolute_percentage_error(y_test, prediction)
print(f"MAE régression linéaire : {mae_lineaire:.0f} MW")
print(f"MAPE régression linéaire : {mape_lineaire * 100:.2f} %")

#------------------------------------------------------------------
# 2. Baseline naïve : préparation 2024 et 2025
#------------------------------------------------------------------

df_2024 = df_ml[df_ml["annee"] == 2024].copy()
df_2025 = df_ml[df_ml["annee"] == 2025].copy()

print("2024 :", df_2024.shape)
print("2025 :", df_2025.shape)

