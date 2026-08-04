# nassim — Graphe & Dijkstra

Partie du projet **EnergIA** dont j'ai la charge : transformer le jeu de données
`data/data.json` (centrales, régions, liaisons) en graphe pondéré et calculer le
plus court chemin entre deux centrales avec l'algorithme de Dijkstra.

## Prérequis

- Python 3.13 (voir `.python-version`)
- Dépendances : `fastapi[standard]`, `pydantic`, `uvicorn` (voir `pyproject.toml`)

## Structure des fichiers

| Fichier / dossier | Rôle |
| --- | --- |
| `data/data.json` | Jeu de données fourni (centrales, régions, liaisons, paramètres de simulation) |
| `models.py` | Classes métier : `Reactor`, `Centrale`, `Region`, `Liaison`, `Graph` |
| `datastore.py` | `DataStore` (chargement/vérification du JSON) + singleton `get_store()` / `reload_store()` |
| `parsing.py` | Conversion JSON brut -> objets métier |
| `serializers.py` | Conversion des objets métier (`Centrale`, `Region`, `Liaison`) en dict JSON |
| `main.py` | Point d'entrée FastAPI : construit `app` et y branche les routes de `routes/dijkstra.py` |
| `routes/dijkstra.py` | Endpoints de l'API (`/dijkstra/...`) |
| `entrainement/` | Scripts d'entraînement/brouillons, non utilisés par l'API : `dijsktra-test.py` (validation de l'algo sur un petit graphe codé en dur A-G) et `rapport_print.py` (rapport console `print_report`, remplacé côté API par `/dijkstra/rapport`) |

## Lancer

`main.py` n'est plus un script à exécuter directement (`python main.py`) : il
définit désormais l'app FastAPI, à lancer via un serveur ASGI. Depuis ce
dossier (`dijkstra/`) :

```
uv run fastapi dev
```

## Flux de chargement des données

1. `get_store()` (dans `datastore.py`) crée un `DataStore` et appelle `.load()`
   au premier accès (singleton paresseux, utilisé par les routes) ; l'endpoint
   `/dijkstra/load-datastore` force un rechargement via `reload_store()`.
2. `.load()` lit `data/data.json` et remplit le `DataStore` :
   - `plants` -> `parse_centrale()` -> objets `Centrale` (+ ajout des nœuds au `Graph`).
   - `regions` -> `parse_region()` -> objets `Region`.
   - `plant_edges` -> `parse_liaison()` -> objets `Liaison` (+ ajout des arêtes au `Graph`).
3. `.verify()` vérifie la cohérence des données chargées et renvoie la liste des
   anomalies (exposée par `/dijkstra/anomalies`) :
   - centrale référençant une région inconnue ;
   - région référençant une centrale (locale ou externe) inconnue ;
   - liaison référençant une centrale source/cible inconnue ;
   - centrale sans aucune liaison (nœud isolé) ;
   - production actuelle ou plafond de sécurité supérieur à la puissance installée.

## Le graphe

`models.Graph` représente les centrales sous forme d'un dictionnaire d'adjacence :

```python
adjacency = {
    "belleville": {"bugey": 263.3, ...},
    "bugey": {"belleville": 263.3, ...},
    ...
}
```

- Un nœud par centrale (`add_node`), ajouté lors du parsing de `plants`.
- Une arête par liaison (`add_edge`), pondérée par `distance_km` ; si la liaison
  est bidirectionnelle (cas le plus fréquent dans le jeu de données), l'arête est
  ajoutée dans les deux sens.

## Dijkstra

`Graph.shortest_path(source, target)` :

- Implémentation « manuelle » (sans tas binaire / `heapq`) : à chaque itération on
  choisit parmi les nœuds non visités celui de plus petite distance connue —
  complexité en O(V²), largement suffisante pour les 18 centrales du jeu de données.
- Renvoie `(distance_totale_km, chemin)` où `chemin` est la liste ordonnée des
  identifiants de centrales traversées.
- Renvoie `(None, None)` si `source` ou `target` n'existe pas dans le graphe, ou
  si aucun chemin ne les relie.

Exemple (`GET /dijkstra/shortest-path?from_node=flamanville&to_node=tricastin`) :

```
flamanville -> chinon -> saint_laurent -> belleville -> bugey -> tricastin (949.8 km)
```

## Limites connues

- La topologie des liaisons, les pertes et les capacités de transfert sont
  simulées pour l'exercice — elles ne représentent pas le réseau RTE réel
  (seules les positions et puissances des centrales sont des données réelles).
- `shortest_path()` optimise uniquement la distance géodésique. Le score
  multi-critère (pertes, marge disponible, saturation, priorité régionale) fait
  partie du moteur prescriptif, développé séparément.
- Pas de tests unitaires dans ce dossier pour l'instant.
