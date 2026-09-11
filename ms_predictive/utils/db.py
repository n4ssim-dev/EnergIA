import psycopg


def connect_bdd():
    connexion = psycopg.connect(
        host="localhost",
        port=5435,
        user="energia",
        password="energia",
        dbname="energia_predictive",
    )

    return connexion


def disconnect_bdd(connexion):
    if connexion is not None:
        connexion.close()