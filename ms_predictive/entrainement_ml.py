from preparation_ml import preparer_dataframe_ml
from analyse_donnees import charger_donnees_analytiques

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
# Définition des variables explicatives
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

print(X.head())
print(y.head())

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

X_train = X[df_ml["annee"] < 2024]
X_test = X[df_ml["annee"] == 2024]

y_train = y[df_ml["annee"] < 2024]
y_test = y[df_ml["annee"] == 2024]