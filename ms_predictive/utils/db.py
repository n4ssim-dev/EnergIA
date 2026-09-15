import os

import psycopg


def connect_bdd():
    connexion = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5435"),
        user=os.getenv("POSTGRES_USER", "energia"),
        password=os.getenv("POSTGRES_PASSWORD", "energia"),
        dbname=os.getenv("POSTGRES_DB", "energia_predictive"),
    )

    return connexion


def disconnect_bdd(connexion):
    if connexion is not None:
        connexion.close()