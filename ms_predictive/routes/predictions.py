import os
import pandas as pd
import joblib
import sqlite3
from datetime import datetime, time

from fastapi import APIRouter, HTTPException, Path,Header

from .preparation_ml import preparer_dataframe_ml
from .analyse_donnees import charger_donnees_analytiques

from pydantic import BaseModel

from .prediction_ml import predire_periode


router = APIRouter(
    prefix="/predictions",
    tags=["prediction"]
)


API_PASSWORD = os.getenv("API_PASSWORD", "5")


def creer_X_prediction(id_region, date, heure):
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
            "temperature_moy",
            "taux_impact_attendu",
            "demographie",
            "presence_evenement",
        ]

        # Vérification des colonnes
        colonnes_manquantes = [
            col for col in colonnes
            if col not in df_ml.columns
        ]

        if colonnes_manquantes:
            raise KeyError(
                f"Colonnes manquantes : {colonnes_manquantes}"
            )

        # Construction du datetime exact recherché
        date_heure_recherchee = pd.Timestamp.combine(
            date.date(),
            heure
        )

        # Filtrage exact
        filtre = (
            (df_ml["id_region"] == id_region)
            & (
                df_ml["date_heure"]
                == date_heure_recherchee
            )
        )

        X = df_ml.loc[filtre, colonnes]

        if X.empty:
            raise ValueError(
                f"Date/heure introuvable : "
                f"{date_heure_recherchee}"
            )

        return X

    except KeyError as e:
        print(f"Erreur de colonnes : {e}")
        raise

    except ValueError as e:
        print(f"Erreur de données : {e}")
        raise

    except Exception as e:
        print(
            "Erreur inattendue dans "
            f"creer_X_prediction : {e}"
        )
        raise

@router.get("/consommation/{region_id}/{date}/{heure}")
def consommation_region(
    region_id: str = Path(..., description="Région"),
    date: str = Path(..., description="Date au format YYYY-MM-DD"),
    heure: time = Path(..., description="Heure au format HH:MM:SS"),
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
            "model_random_forest/preprocesseur.pkl"
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
            "heure": heure.isoformat(),
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

    
# ---------------------------------
# Route de prédiction complète
# ---------------------------------   

class PredictionPeriodeRequest(BaseModel):
    date_debut: datetime
    date_fin: datetime
    regions: list[str]


@router.post("/periode")
def prediction_periode(
    requete: PredictionPeriodeRequest
):
    try:
        resultats = predire_periode(
            date_debut=requete.date_debut,
            date_fin=requete.date_fin,
            regions=requete.regions
        )

        return {
            "date_debut": requete.date_debut,
            "date_fin": requete.date_fin,
            "regions": requete.regions,
            "predictions": resultats
        }

    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur)
        )