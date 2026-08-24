## Développement d'une plateforme d'aide à la décision pour le pilotage d'un parc de production électrique

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=node.js&logoColor=white)
![Express](https://img.shields.io/badge/Express.js-000000?style=for-the-badge&logo=express&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)



# Présentation du projet

Présentation du projet

EnergIA est une plateforme d’aide à la décision destinée au pilotage d’un parc de production nucléaire.

Elle permet de recommander une répartition de l’effort de production lorsqu’une région connaît une augmentation de sa consommation électrique.

À partir d’une région et d’une demande supplémentaire exprimée en mégawatts, le moteur prescriptif recherche les centrales capables d’augmenter leur production.

Les centrales locales sont examinées en priorité. Lorsqu’elles ne disposent pas d’une capacité suffisante, le moteur recherche des centrales plus éloignées en tenant compte notamment :

de la distance ;
des pertes estimées sur le réseau ;
de la puissance encore disponible ;
du taux de saturation des centrales ;
de la disponibilité des centrales et des liaisons.

Le réseau utilisé dans ce projet est une représentation du réseau électrique français. Les données de production instantanée, les pertes, les capacités de transfert et certaines liaisons sont simulées.

---

# Architecture du projet

Utilisateur
↓
Gateway Express
↓
FastAPI
↓
Moteur Prescriptif
↓
JSON

Le projet a été réalisé avec **Docker** (voir le fichier `compose.yaml`).

L'application est composée de deux conteneurs :

- **energia-gateway** : le backend basé sur une API Express, exposant les ressources nécessaires au     fonctionnement de l'application ;
- **energia-fastapi** : microservice développé avec FastAPI, à partir du dossier [`fastapi/`](fastapi/). Il expose les données relatives aux centrales, aux régions et aux liaisons, et permet de lancer une simulation avec le moteur prescriptif (voir [`fastapi/README.md`](fastapi/README.md)) ;

`fastapi/` reprend la structure et le moteur de [`dijkstra/`](dijkstra/) et y agrège les routes historiquement portées par [`python-service/`](python-service/). Ces deux derniers dossiers restent présents dans le dépôt à titre de référence mais ne sont plus branchés à `docker-compose` ni à `gateway/`.

---
# Prérequis

Avant de lancer l’application, les outils suivants doivent être installés :

Git ;
Docker ;
Docker Compose.

Grâce à la conteneurisation, il n’est pas nécessaire d’installer directement Node.js, Python, Express ou FastAPI sur la machine utilisée pour lancer l’application.

---

# Installation

## 1. Cloner le depôt Git 
```
git clone <https://github.com/n4ssim-dev/EnergIA.git>
```
Puis se placer dans le dossier du projet :
```
cd <EnergIA>
```
## 2. Configuration des variables d'environnement

Créer un fichier `.env` dans chacune des dossiers "fastapi" et "gateway" 
en vous basant sur le fichier `.env.example`.

Exemple :

cp gateway/.env.example gateway/.env
cp fastapi/.env.example fastapi/.env

Les valeurs des variables doivent être adaptées à l’environnement utilisé.

Les fichiers .env ne doivent pas être ajoutés au dépôt Git.

## 3. Lancement des conteneurs Docker

Exécuter la commande suivante :

```bash
docker compose up --build
```

Une fois le démarrage terminé :

- le micro service python sera disponible à l'adresse :

```
http://127.0.0.1:8000/

```

- le gateway sera accessible à l'adresse :

```
http://127.0.0.1:3000/

```
En utilisation normale, les requêtes doivent être envoyées uniquement à la gateway.

Pour arrêter les conteneurs :
```
docker compose down
```
## 4. Eléments de configuration
| Service | Variable             | Rôle                                   | Contenu                      |
| ------- | -------------------- | -------------------------------------- | ---------------------------- |
| Gateway | `PORT`               | Port d’écoute de la gateway            | `3000`                       |
| Gateway | `PYTHON_SERVICE_URL` | Adresse interne du microservice Python | `http://python-service:8000` |
| Gateway | `API_PASSWORD`       | Mot de passe envoyé au service Python  | `5`                          |
| Python  | `PORT`               | Port d’écoute de FastAPI               | `8000`                       |
| Python  | `API_PASSWORD`       | Mot de passe attendu dans l’en-tête    | `5`                          |
| Python  | `DATA_FILE_PATH`     | Chemin du fichier JSON                 | `data/projet-energia.json`   |

---
# Routes disponibles

##  Routes du "gateway"

| Méthode | Route | Description | Body JSON |
|---|---|---|---|
| GET | `api/centrales` | retourner la liste des centrales nucléaires  | Aucun |
| GET | `api/regions` | Retourne la liste de toutes les régions | Aucun |
| GET | `api/liaisons` | retourner la liste des liaisons  | Aucun |
| POST | `api/simulation` | faire une nouvelle simulation,Par exemple Une région a besoin de X MW supplémentaires : quelles centrales doivent augmenter leur production, et de combien ? | ```json { "region": "centre_val_de_loire", "augmentation": "500" } ``` 

## Routes du "micro service Python"

| Méthode | Route | Description | Body JSON |
|---|---|---|---|
| GET | `/centrales` | retourner la liste des centrales nucléaires  | Aucun |
| GET | `/regions` | Retourne la liste de toutes les régions | Aucun |
| GET | `/liaisons` | retourner la liste des liaisons  | Aucun |
| POST | `/simulation` | faire une nouvelle simulation,Par exemple Une région a besoin de X MW supplémentaires : quelles centrales doivent augmenter leur production, et de combien ? | ```json { "region": "centre_val_de_loire", "augmentation": "500" } ``` 


## Format d’une demande de simulation

La route suivante permet de demander une nouvelle répartition de la production :

POST /api/simulation

Exemple de corps JSON :
```
{
  "region": "centre_val_de_loire",
  "augmentation": 500
}
```

## Description des champs
Champ	Type	Description
region	chaîne de caractères	Identifiant de la région concernée par la hausse de consommation.
augmentation	nombre	Puissance supplémentaire demandée, exprimée en mégawatts.

La valeur augmentation doit être envoyée sous la forme d’un nombre et non d’une chaîne de caractères.

---


liste des éléments à ajouter au Readme : 

- le lancement de l’application ;
- l’exécution des tests ;
- le format des requêtes ;
- le format des réponses ;
- le fonctionnement du moteur prescriptif ;
- la formule ou les règles utilisées pour classer les centrales ;
- les limites connues du prototype.

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
- Quelques tests rudimentaires dans `tests/` (health, load-datastore,
  shortest-path). Ça vérifie que ça tourne, pas que c'est juste dans
  tous les cas.

### Nouvelle étape :

```bash
Charger le JSON de consommation
        ↓
Charger l’état initial du parc nucléaire
        ↓
Pour chaque index de 0 à 95
        ↓
Récupérer le timestamp correspondant
        ↓
Récupérer la consommation de chaque région à cet index
        ↓
Donner ces besoins au moteur prescriptif
        ↓
Le moteur calcule la nouvelle production des centrales
        ↓
Respect des min/max et des rampes
        ↓
Conserver le nouvel état des centrales
        ↓
Utiliser cet état au tour suivant
```