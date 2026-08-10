# api — Graphe, Dijkstra & moteur prescriptif

Fusion de `dijkstra/` (graphe, plus court chemin, moteur de répartition)
et `python-service/` (surface HTTP consommée par le gateway) dans un seul
service, gérée avec `pip` plutôt que `uv`. `dijkstra/` et `python-service/`
restent en place tels quels ; ce dossier ne les remplace pas encore dans
`docker-compose.yml`.

## Prérequis

- Python 3.12
- Dépendances listées dans `requirements.txt`

## Installation

Depuis `api/` :

```
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Lancer le projet

```
uvicorn main:app --reload
```

Copier `.env.example` vers `.env` pour ajuster `HOST`, `PORT` et
`API_PASSWORD` (utilisé par le header `X-Password`, exigé sur toutes les
routes sauf `/` et `/health`).

## Rôles des fichiers

| Fichier / dossier | Rôle |
| --- | --- |
| `data/data.json` | Les données brutes : centrales, régions, liaisons, params |
| `graph/models.py` | Les classes : `Reactor`, `Centrale`, `Region`, `Liaison`, `Graph` |
| `graph/datastore.py` | Charge le JSON en mémoire, vérifie que ça tient debout |
| `graph/parsing.py` | Transforme le JSON brut en objets Python |
| `graph/serializers.py` | Fait l'inverse : objets -> dict JSON |
| `routes/auth.py` | Dépendance FastAPI qui vérifie le header `X-Password` |
| `routes/dijkstra.py` | Les endpoints détaillés `/dijkstra/...` (hérités de `dijkstra/`) |
| `routes/calcul.py` | Le moteur prescriptif : score des candidats, répartition de la demande |
| `routes/public.py` | Les endpoints à plat (`/centrales`, `/regions`, `/liaisons`, `/simulation`) hérités de `python-service/` — la surface HTTP consommée par le gateway Express (`lola/gateway/`), pas une réimplémentation de celui-ci |
| `main.py` | Démarre l'app FastAPI, branche les routes et l'auth |

## Deux surfaces d'API pour les mêmes données

- `/dijkstra/...` : l'API détaillée héritée de `dijkstra/` (recherche par
  id, rapport, anomalies, plus court chemin, `/dijkstra/calcule` pour le
  moteur prescriptif).
- `/centrales`, `/regions`, `/liaisons`, `/simulation` : les routes à plat
  historiquement exposées par `python-service/`, consommées par
  `lola/gateway/index.js`. Elles utilisent désormais le même `DataStore`
  et les mêmes sérialiseurs que `/dijkstra/...` (au lieu d'un simple
  passage brut du JSON), et `/simulation` appelle directement
  `executer_simulation()` en mémoire — il n'y a plus de saut HTTP vers un
  service `dijkstra` séparé sur le port 8001 comme le faisait
  `python-service` (ce service n'était de toute façon jamais démarré nulle
  part dans le repo).

Toutes ces routes (sauf `/` et `/health`) exigent le header `X-Password`
(valeur par défaut `5`, configurable via `API_PASSWORD`).

## Le graphe et Dijkstra

Voir `graph/models.py::Graph.shortest_path` : Dijkstra fait à la main,
sans `heapq` (à chaque tour on balaie les nœuds non visités pour trouver
la plus petite distance connue — O(V²), largement suffisant pour la
vingtaine de centrales du jeu de données).

## Tests

```
pytest
```

`conftest.py` ajoute la racine de `api/` au `sys.path` pour que les
imports `from graph...` / `from routes...` fonctionnent sans package
installé.

## Ce qui n'a pas été repris

- `entrainement/` (brouillons de `dijkstra/`, non branchés à l'API) n'a
  pas été copié ici — toujours disponible dans `dijkstra/` si besoin.
- Le mot de passe reste une valeur simple comparée en clair (comme dans
  `python-service/`), maintenant au moins lue depuis `API_PASSWORD`
  plutôt que codée en dur.
