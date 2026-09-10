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
        df_ml
        .groupby("id_region")["consumption_mw"]
        .shift(1)
    )

    # Consommation 30 minutes avant
    df_ml["conso_30min_precedente"] = (
        df_ml
        .groupby("id_region")["consumption_mw"]
        .shift(2)
    )
    return df_ml