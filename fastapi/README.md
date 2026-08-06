# fastapi — service unifié EnergIA

Fusion de [`dijkstra/`](../dijkstra) (graphe, Dijkstra, moteur de score/répartition)
et de [`python-service/`](../python-service) (routes exposées à `gateway/`) en un
seul service FastAPI. Structure reprise telle quelle depuis `dijkstra/` ;
les fonctionnalités de `python-service/` sont ajoutées par-dessus plutôt que
dupliquées.

## Prérequis

- Python 3.13
- `fastapi[standard]`, `pydantic`, `uvicorn` (tout est dans `pyproject.toml`, géré avec `uv`)

## Rôles des fichiers

| Fichier / dossier | Rôle |
| --- | --- |
| `data/data.json` | Les données brutes : centrales, régions, liaisons, params |
| `graph/models.py` | Les classes : `Reactor`, `Centrale`, `Region`, `Liaison`, `Graph` |
| `graph/datastore.py` | Charge le JSON en mémoire, vérifie que ça tient debout |
| `graph/parsing.py` | Transforme le JSON brut en objets Python |
| `graph/serializers.py` | Fait l'inverse : objets -> dict JSON |
| `main.py` | Démarre l'app FastAPI, branche les deux routers |
| `routes/dijkstra.py` | Les endpoints `/dijkstra/...` (repris de `dijkstra/`), plus `run_simulation()` factorisée |
| `routes/api.py` | Les endpoints racine `/centrales`, `/regions`, `/liaisons`, `/simulation` (repris de `python-service/`), protégés par l'en-tête `x-password` |
| `routes/calcul.py` | Le moteur de score / répartition (repris de `dijkstra/`) |

## Deux familles de routes

- **`/dijkstra/...`** : routes détaillées d'origine (rapport, anomalies, shortest-path, `calcule`...), sans authentification, pour l'exploration/le debug.
- **`/centrales`, `/regions`, `/liaisons`, `/simulation`** : routes racine attendues par `gateway/`, protégées par l'en-tête `x-password: 5`. Elles s'appuient sur le même `DataStore`/mêmes sérialiseurs que `/dijkstra/...` — `/simulation` appelle directement `run_simulation()` (plus d'appel HTTP interne comme le faisait `python-service` vers `dijkstra`).

## Lancer le projet

Depuis `fastapi/` :

```
uv sync
uv run fastapi dev
```

## Lancer les tests

```
uv run pytest
```

## Docker

```
docker compose up --build fastapi
```

Le service écoute sur le port `8000` et est celui que `gateway/` appelle
(`http://fastapi:8000` dans le réseau Docker).
