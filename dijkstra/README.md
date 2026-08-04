# nassim — Graphe & Dijkstra

Le bout que je gère dans EnergIA. En gros : on prend `data/data.json`
(des centrales, des régions, des liaisons entre centrales), on en fait un
graphe, et on calcule le chemin le plus court entre deux centrales avec
Dijkstra. Rien de plus.

## Prérequis

- Python 3.13
- `fastapi[standard]`, `pydantic`, `uvicorn` (tout est dans `pyproject.toml`)

## Rôles des fichiers

| Fichier / dossier | Rôle |
| --- | --- |
| `data/data.json` | Les données brutes : centrales, régions, liaisons, params |
| `graph/models.py` | Les classes : `Reactor`, `Centrale`, `Region`, `Liaison`, `Graph` |
| `graph/datastore.py` | Charge le JSON en mémoire, vérifie que ça tient debout |
| `graph/parsing.py` | Transforme le JSON brut en objets Python |
| `graph/serializers.py` | Fait l'inverse : objets -> dict JSON |
| `main.py` | Démarre l'app FastAPI, branche les routes |
| `routes/dijkstra.py` | Les endpoints `/dijkstra/...` |
| `entrainement/` | Brouillons, pas branchés à l'API (test de l'algo sur un petit graphe A-G, ancien rapport console) |

## Lancer le projet

`main.py` ne se lance plus avec `python main.py`, c'est une app FastAPI.
Depuis `dijkstra/` :

```
uv run fastapi dev
```

## Comment les données arrivent

1. Au premier appel, `get_store()` charge tout une fois (singleton). Y'a
   aussi une route `/dijkstra/load-datastore` pour forcer un rechargement.
2. Le chargement lit le JSON et remplit trois listes d'objets :
   centrales, régions, liaisons. Chaque centrale devient un nœud du
   graphe, chaque liaison devient une arête.
3. Ensuite on vérifie que les données ne racontent pas n'importe quoi :
   régions ou centrales qui pointent vers du vide, centrales toutes
   seules sans aucune liaison, production qui dépasse la puissance
   installée. La liste des soucis sort sur `/dijkstra/anomalies`.

## Le graphe

C'est juste un dictionnaire de dictionnaires : pour chaque centrale, la
liste de ses voisines avec la distance en km.

```python
adjacency = {
    "belleville": {"bugey": 263.3, ...},
    "bugey": {"belleville": 263.3, ...},
    ...
}
```

Une liaison bidirectionnelle (le cas normal) ajoute l'arête dans les
deux sens.

## Dijkstra

`Graph.shortest_path(source, target)` fait le calcul à la main, sans
`heapq` : à chaque tour de boucle on regarde tous les nœuds pas encore
visités et on prend celui qui a la plus petite distance connue.

Ça renvoie `(distance_totale, chemin)`, ou `(None, None)` si un des deux
noeuds n'existe pas ou si rien ne les relie.

Exemple concret (`GET /dijkstra/shortest-path?from_node=flamanville&to_node=tricastin`) :

```
flamanville -> chinon -> saint_laurent -> belleville -> bugey -> tricastin (949.8 km)
```

## Ce qui manque

- Les liaisons, pertes et capacités sont inventées pour l'exercice —
  seules les positions et puissances des centrales sont vraies.
- On optimise juste la distance. Un vrai score (pertes, marge,
  saturation, priorité régionale) c'est un autre chantier, pas fait ici.
- Pas de tests. Zéro.
