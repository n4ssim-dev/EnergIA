# nassim — Graphe & Dijkstra

Partie du projet **EnergIA** dont j'ai la charge : transformer le jeu de données
`data/data.json` (centrales, régions, liaisons) en graphe pondéré et calculer le
plus court chemin entre deux centrales avec l'algorithme de Dijkstra.

## Prérequis

- Python 3.13 (voir `.python-version`)
- Aucune dépendance externe (stdlib uniquement : `json`, `pathlib`)

## Structure des fichiers

| Fichier | Rôle |
| --- | --- |
| `data/data.json` | Jeu de données fourni (centrales, régions, liaisons, paramètres de simulation) |
| `models.py` | Classes métier : `Reactor`, `Centrale`, `Region`, `Liaison`, `Graph` |
| `main.py` | Chargement du JSON (`DataStore`), vérification de cohérence, rapport |
| `dijsktra.py` | Brouillon initial de Dijkstra sur un petit graphe codé en dur (A-G), utilisé pour valider l'algorithme avant de l'intégrer dans `models.Graph` |

## Lancer

```
python main.py
```

## Flux de `main.py`

1. `load_datastore()` crée un `DataStore` et appelle `.load()`.
2. `.load()` lit `data/data.json` et remplit le `DataStore` :
   - `plants` -> `parse_centrale()` -> objets `Centrale` (+ ajout des nœuds au `Graph`).
   - `regions` -> `parse_region()` -> objets `Region`.
   - `plant_edges` -> `parse_liaison()` -> objets `Liaison` (+ ajout des arêtes au `Graph`).
3. `.verify()` vérifie la cohérence des données chargées et renvoie la liste des
   anomalies :
   - centrale référençant une région inconnue ;
   - région référençant une centrale (locale ou externe) inconnue ;
   - liaison référençant une centrale source/cible inconnue ;
   - centrale sans aucune liaison (nœud isolé) ;
   - production actuelle ou plafond de sécurité supérieur à la puissance installée.
4. `.print_report()` affiche un résumé du chargement, un exemple de centrale/région/
   liaison, un exemple de chemin calculé avec `Graph.shortest_path()` (Dijkstra,
   cas trouvé et cas absent) et la liste des anomalies.

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

Exemple (`main.py`) :

```
flamanville -> tricastin : flamanville -> chinon -> saint_laurent -> belleville -> bugey -> tricastin (949.8 km)
flamanville -> centrale_inconnue : aucun chemin trouvé
```

## Limites connues

- La topologie des liaisons, les pertes et les capacités de transfert sont
  simulées pour l'exercice — elles ne représentent pas le réseau RTE réel
  (seules les positions et puissances des centrales sont des données réelles).
- `shortest_path()` optimise uniquement la distance géodésique. Le score
  multi-critère (pertes, marge disponible, saturation, priorité régionale) fait
  partie du moteur prescriptif, développé séparément.
- Pas de tests unitaires dans ce dossier pour l'instant.
