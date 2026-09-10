import pandas as pd


# ---------------------------------
# Enregistrement des prédictions pécédentes
# ---------------------------------

def preparer_dataframe_ml(df):
    df_ml = df.copy()

    # Tri chronologique
    df_ml = df_ml.sort_values(by=["id_region", "date_", "heure"])

    # Consommation 15 minutes avant
    df_ml["conso_15min_precedente"] = (
        df_ml.groupby("id_region")["consumption_mw"].shift(1)
    )

    # Consommation 30 minutes avant
    df_ml["conso_30min_precedente"] = (
        df_ml.groupby("id_region")["consumption_mw"].shift(2)
    )
    
    # Consommation 1 heure avant
    df_ml["conso_1h_precedente"] = (
        df_ml.groupby("id_region")["consumption_mw"].shift(4)
    )
    
    # Consommation du jour précédent
    df_ml["conso_jour_precedent"] = (df_ml.groupby("id_region")["consumption_mw"].shift(96)
    )

    # Consommation du jour précédent
    df_ml["conso_semaine_precedent"] = (df_ml.groupby("id_region")["consumption_mw"].shift(672)
    )
    
    # Suppression des lignes incomplètes
    colonnes_retardees = [
        "conso_15min_precedente",
        "conso_30min_precedente",
        "conso_1h_precedente",
        "conso_jour_precedent",
        "conso_semaine_precedente",
    ]
    df_ml = df_ml.dropna(subset=colonnes_retardees)

    return df_ml

