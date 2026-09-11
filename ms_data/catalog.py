# Catalogue statique des routes exposées par l'API ms_dijkstra (méthode,
# fichier source, description, paramètres). Entretenu à la main : à mettre à
# jour en cas d'ajout/suppression/modification de route dans ms_dijkstra/routes/*.py.
ROUTES_CATALOG = [
    {
        "chemin": "/centrales", "methode": "GET", "fichier_source": "api.py",
        "description": "Liste des centrales (datastore, chargé depuis relationnal.db)",
        "auth": True, "parametres": [],
    },
    {
        "chemin": "/regions", "methode": "GET", "fichier_source": "api.py",
        "description": "Liste des régions", "auth": True, "parametres": [],
    },
    {
        "chemin": "/liaisons", "methode": "GET", "fichier_source": "api.py",
        "description": "Liste des liaisons inter-centrales", "auth": True, "parametres": [],
    },
    {
        "chemin": "/simulation", "methode": "GET", "fichier_source": "api.py",
        "description": "Répartition d'une demande supplémentaire sur une région",
        "auth": True,
        "parametres": [
            {"nom": "region", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "augmentation_mw", "emplacement": "query", "type": "float", "requis": True},
        ],
    },
    {
        "chemin": "/database/ingest", "methode": "POST", "fichier_source": "ms_data/routes/database.py",
        "description": "Recrée le schéma et réingère tous les JSON de ms_dijkstra/data "
        "(et le catalogue de routes) dans relationnal.db et Postgres",
        "auth": True, "parametres": [],
    },
    {
        "chemin": "/database/ingest-eco2mix", "methode": "POST", "fichier_source": "ms_data/routes/database.py",
        "description": "Ingestion manuelle, par plage de dates, de eco2mix-regional-tr.csv (RTE) "
        "dans mesure_eco2mix_regionale (relationnal.db et Postgres)",
        "auth": True,
        "parametres": [
            {"nom": "date_debut", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "date_fin", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/database/ingest-eco2mix-historique", "methode": "POST", "fichier_source": "ms_data/routes/database.py",
        "description": "Ingestion manuelle, par plage de dates, du dataset ODRE "
        "eco2mix-regional-cons-def (API paginée, 2013 -> ~1 mois avant aujourd'hui) "
        "dans mesure_eco2mix_regionale (même table que /ingest-eco2mix), "
        "relationnal.db et Postgres",
        "auth": True,
        "parametres": [
            {"nom": "date_debut", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "date_fin", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/load-datastore", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Recharge le datastore mémoire depuis relationnal.db", "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/rapport", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Rapport global : comptages, puissance installée totale, anomalies",
        "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/shortest-path", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Plus court chemin (Dijkstra) entre deux centrales",
        "auth": True,
        "parametres": [
            {"nom": "from_node", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "to_node", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/centrales", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Liste des centrales (datastore)", "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/centrales/{centrale_id}", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Détail d'une centrale",
        "auth": True,
        "parametres": [
            {"nom": "centrale_id", "emplacement": "path", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/regions", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Liste des régions (datastore)", "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/regions/{region_id}", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Détail d'une région",
        "auth": True,
        "parametres": [
            {"nom": "region_id", "emplacement": "path", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/liaisons", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Liste des liaisons (datastore)", "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/anomalies", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Anomalies détectées dans le graphe/datastore", "auth": True, "parametres": [],
    },
    {
        "chemin": "/dijkstra/calcule", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Répartition d'une demande sur une région",
        "auth": True,
        "parametres": [
            {"nom": "region", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "augmentation_mw", "emplacement": "query", "type": "float", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/simulation-regions", "methode": "POST", "fichier_source": "dijkstra.py",
        "description": "Simulation multi-régions sur 96 pas de 15 min, avec perturbations optionnelles",
        "auth": True,
        "parametres": [
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
            {
                "nom": "perturbations", "emplacement": "body", "type": "list[Perturbation]",
                "requis": False, "defaut": "null",
            },
        ],
    },
    {
        "chemin": "/dijkstra/besoins-residuels", "methode": "GET", "fichier_source": "dijkstra.py",
        "description": "Besoin résiduel (conso - solaire - éolien) par région et par quart d'heure",
        "auth": True,
        "parametres": [
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/dijkstra/simulation-complete", "methode": "POST", "fichier_source": "dijkstra.py",
        "description": "Simulation complète avec contraintes réelles sur l'ensemble des faits de consommation "
        "(toutes régions, tous quarts d'heure), avec filtre facultatif par région et/ou heure",
        "auth": True, "parametres": [
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
            {
                "nom": "region", "type": "string", "emplacement": "body",
                "requis": False, "defaut": "null",
            },
            {
                "nom": "heure", "type": "string", "emplacement": "body",
                "requis": False, "defaut": "null",
            },
        ],
    },
    {
        "chemin": "/analytics/centrales/{centrale_id}/etat", "methode": "GET", "fichier_source": "analytics.py",
        "description": "État complet d'une centrale (dispo, puissance max/actuelle, marge, réacteurs)",
        "auth": True,
        "parametres": [
            {"nom": "centrale_id", "emplacement": "path", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/analytics/centrales/disponibles", "methode": "GET", "fichier_source": "analytics.py",
        "description": "Nombre de centrales disponibles", "auth": True, "parametres": [],
    },
    {
        "chemin": "/analytics/regions/{region_id}/consommation", "methode": "GET", "fichier_source": "analytics.py",
        "description": "Consommation d'une région à un instant donné",
        "auth": True,
        "parametres": [
            {"nom": "region_id", "emplacement": "path", "type": "str", "requis": True},
            {"nom": "heure", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/analytics/regions/consommation/max", "methode": "GET", "fichier_source": "analytics.py",
        "description": "Région qui consomme le plus à une heure donnée",
        "auth": True,
        "parametres": [
            {"nom": "heure", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
    {
        "chemin": "/analytics/regions/{region_id}/situation", "methode": "GET", "fichier_source": "analytics.py",
        "description": "Situation énergétique d'une région (conso + prod solaire/éolien + capacité + solde)",
        "auth": True,
        "parametres": [
            {"nom": "region_id", "emplacement": "path", "type": "str", "requis": True},
            {"nom": "heure", "emplacement": "query", "type": "str", "requis": True},
            {"nom": "date", "emplacement": "query", "type": "str", "requis": True},
        ],
    },
]

# Ordre sans contrainte particulière : PRAGMA foreign_keys est désactivé le
# temps du drop, pour ne pas avoir à respecter l'ordre des FK.
TABLES = [
    "parametre_route",
    "route",
    "scenario_override",
    "scenario",
    "accessible_via",
    "reacteur",
    "liaison",
    "centrale",
    "capacitee_instalee_non_pilotable",
    "filiere",
    "region",
]

# mesure_eco2mix_regionale est ingérée à part (POST /database/ingest-eco2mix
# et /ingest-eco2mix-historique, manuellement, par plage de dates) : elle
# n'est pas dans TABLES pour ne pas être vidée à chaque /database/ingest global.
