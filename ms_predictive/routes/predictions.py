import os
import pandas as pd
import joblib
import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path,Header

router = APIRouter()


from preparation_ml import preparer_dataframe_ml
from analyse_donnees import charger_donnees_analytiques

API_PASSWORD = os.getenv("API_PASSWORD", "5")

router = APIRouter(prefix="/predictions")


def creer_X_prediction(id_region,date,heure):
    try:
        # ---------------------------------
        # Chargement des données
        # ---------------------------------
        df = charger_donnees_analytiques()

        if df is None or df.empty:
            raise ValueError("Aucune donnée chargée.")

        df_ml = preparer_dataframe_ml(df)

        if df_ml is None or df_ml.empty:
            raise ValueError("Le DataFrame ML est vide.")

        colonnes = [
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
        ]

        # Vérification des colonnes
        colonnes_manquantes = [
            col for col in colonnes if col not in df_ml.columns
        ]
        if colonnes_manquantes:
            raise KeyError(
                f"Colonnes manquantes : {colonnes_manquantes}"
            )
        # Conversion avant filtre
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")
            
        # Filtrage
        filtre = (
            (df_ml["id_region"] == id_region)
            & (df_ml["annee"] == date.year)
            & (df_ml["heure"] == heure)
        )

        X = df_ml.loc[filtre, colonnes]

        if X.empty:
            raise ValueError(
                f"Date/heure introuvable : {date} {heure}"
            )

        return X

    except KeyError as e:
        print(f"Erreur de colonnes : {e}")
        raise

    except ValueError as e:
        print(f"Erreur de données : {e}")
        raise

    except Exception as e:
        print(f"Erreur inattendue dans creer_X_prediction : {e}")
        raise


@router.get("/consommation/{region_id}/{date}/{heure}")
def consommation_region(
    region_id: str = Path(..., description="Région"),
    date: str = Path(..., description="Date au format YYYY-MM-DD"),
    heure: str = Path(..., description="Heure"),
    x_api_key: str = Header(...)
):
    """Prédiction de la consommation d'une région à une date et un quart heure."""
    
    if x_api_key != API_PASSWORD:
        raise HTTPException(
        status_code=401,
        detail="API key invalide"
    )
    try:
        # Validation de la date
        date_obj = datetime.strptime(date, "%Y-%m-%d")

        # Chargement des modéles
        model = joblib.load(
            "model_random_forest/conso_predictor.pkl"
        )
        preprocesseur = joblib.load(
            "preprocesseur/preprocesseur.pkl"
        )

        # Construction des données d'entrée
        X = creer_X_prediction(
            region_id,
            date_obj,
            heure,
        )

        # Prétraitement
        X_prepare = preprocesseur.transform(X)

        # Prédiction
        prediction = model.predict(X_prepare)

        return {
            "region_id": region_id,
            "date": date,
            "heure": heure,
            "prediction": float(prediction[0])
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fichier introuvable : {e}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne : {e}"
        )
   

