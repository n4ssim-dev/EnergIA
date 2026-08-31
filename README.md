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

---
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
  
---
# EnergIA – Moteur de simulation temporelle

## Présentation

EnergIA est un moteur de simulation permettant de représenter l’évolution de la production électrique sur une journée de référence.

La simulation fonctionne par pas de temps de **15 minutes**, soit **96 états successifs sur une journée complète**.

Le moteur prend notamment en compte :

- la consommation électrique régionale ;
- la production solaire ;
- la production éolienne ;
- la production nucléaire ;
- les contraintes de montée et de descente en puissance des centrales ;
- la puissance minimale et maximale des centrales ;
- la disponibilité des centrales ;
- la réserve nucléaire minimale ;
- les éventuelles perturbations de consommation.

L’objectif est de déterminer, pour chaque région et chaque quart d’heure, si la production disponible permet de répondre au besoin électrique.

---

# Lancer une simulation

## Prérequis

Le projet nécessite notamment :

- Python ;
- FastAPI ;
- les dépendances présentes dans le projet ;
- les fichiers JSON nécessaires à la simulation.

Activer l’environnement virtuel :

```powershell
.\.venv\Scripts\Activate.ps1
```
Se placer dans le dossier fastapi :
```
cd fastapi
```
Lancer l'API
```
fastapi run .\main.py
```
Ouvrir le Swagger avec :
```
http://localhost:8000/docs
```
## Format des données temporelles

La simulation utilise une journée découpée en **96 pas de 15 minutes**.

Exemple de timestamps :

```
{
  "timestamps": [
    "00:00",
    "00:15",
    "00:30",
    "00:45"
  ]
}
```
Chaque région possède une liste de 96 valeurs correspondant aux 96 quarts d’heure de la journée.

Exemple pour la consommation :
```
{
  "id": "occitanie",
  "consumption_mw": [
    2894,
    2870,
    2850
  ]
}
```
Le même principe est utilisé pour la production **solaire** et **éolienne** :
```
{
  "id": "occitanie",
  "production_mw": {
    "solar": [
      0,
      0,
      0
    ],
    "wind": [
      926,
      910,
      895
    ]
  }
}
```
Les valeurs situées au même index correspondent au même pas de temps.

Par exemple :
```
index 0  → 00:00
index 1  → 00:15
index 2  → 00:30
...
index 95 → 23:45
```
## Calcul des états successifs

La simulation est dite stateful : l’état calculé à un instant donné est utilisé comme point de départ pour le pas de temps suivant.

Pour le premier pas de temps, la puissance précédente d’une centrale correspond à sa puissance à 23:45 la veille.

Exemple :
```
{
  "plant_id": "belleville",
  "initial_output_mw_at_23_45_previous_day": 1493
}
```
Ensuite :
```
- 23:45 veille
    
-> calcul de 00:00
    
-> puissance réelle à 00:00
    
-> utilisée comme puissance précédente à 00:15
    
-> puissance réelle à 00:15
    
-> utilisée à 00:30
    
...
```
Ainsi, chaque calcul dépend directement de l’état précédent.

## Règles de montée et de descente en puissance

Une centrale nucléaire ne peut pas modifier instantanément sa production.

Chaque centrale dispose donc :

- d’une puissance minimale ;
- d’une puissance maximale ;
- d’une vitesse maximale de montée sur 15 minutes ;
- d’une vitesse maximale de descente sur 15 minutes.

Exemple :
```
{
  "plant_id": "belleville",
  "minimum_operating_power_mw": 520,
  "maximum_power_mw": 2620,
  "max_ramp_up_mw_per_15_min": 240,
  "max_ramp_down_mw_per_15_min": 264
}
```
Si une centrale produit 1500 MW et que la puissance souhaitée est de 1900 MW, avec une rampe maximale de montée de 240 MW :

- puissance précédente = 1500 MW
- puissance souhaitée = 1900 MW

- augmentation demandée = 400 MW
- augmentation autorisée = 240 MW

- puissance réellement atteignable = 1740 MW

Le même principe est appliqué lors d’une diminution de puissance.

La puissance finale doit également rester comprise entre les limites minimale et maximale de la centrale.

## Production non pilotable

La production solaire et éolienne est considérée comme non pilotable.

Pour chaque région et chaque quart d’heure :
```
production hors nucléaire = production solaire + production éolienne
```
Exemple :
```
solaire = 400 MW
éolien = 600 MW

production hors nucléaire = 1000 MW
```
## Calcul de la demande résiduelle

Dans le moteur, un premier besoin restant est calculé après prise en compte des productions solaire et éolienne.

La formule utilisée est :
```
besoin résiduel = consommation - production solaire - production éolienne

ou :

besoin résiduel = consommation - production hors nucléaire
```
Le calcul est effectué pour chaque région et chacun des 96 pas de temps.

Exemple :
```
consommation = 3000 MW
solaire = 400 MW
éolien = 600 MW

besoin résiduel = 3000 - 400 - 600
                = 2000 MW
```
Ce besoin doit ensuite être couvert par le nucléaire.

Après prise en compte de la production nucléaire réellement disponible, un déficit final peut être calculé :
```
déficit final = besoin résiduel - production nucléaire réellement fournie
```
Si le résultat est supérieur à 0, cette puissance n’a pas pu être couverte par le moteur et doit être considérée comme un besoin complémentaire d’approvisionnement.

## Réserve nucléaire minimale

**A COMPLETER**


## Perturbation de consommation

Une perturbation de consommation est un événement temporaire qui modifie la demande électrique d'une région pendant une période donnée.

Elle est définie par :

* `regionId` : identifiant de la région concernée ;
* `start` : heure de début de la perturbation ;
* `end` : heure de fin de la perturbation ;
* `deltaMw` : variation de consommation en MW.

### Exemple

```json
"perturbations": [
  {
    "regionId": "ile_de_france",
    "start": "00:00",
    "end": "00:15",
    "deltaMw": -500
  },
  {
    "regionId": "grand_est",
    "start": "10:00",
    "end": "12:30",
    "deltaMw": -12
  }
]
```

Une valeur positive de `deltaMw` augmente la consommation tandis qu'une valeur négative la diminue.

Par exemple, si la consommation normale de l'Île-de-France est de `5 335 MW` et qu'une perturbation de `-500 MW` est active :

```text
Consommation normale
       5 335 MW
          ↓
Perturbation
       -500 MW
          ↓
Consommation perturbée
       4 835 MW
```

La consommation perturbée est ensuite utilisée comme demande d'entrée pour le calcul de répartition des centrales.

### Application temporelle

La perturbation est appliquée uniquement lorsque :

1. la région de la perturbation correspond à la région en cours de calcul ;
2. l'heure du quart d'heure se situe dans l'intervalle `[start, end]`.

Par exemple :

```text
Perturbation Grand Est
10:00 → 12:30
deltaMw = -12 MW
```

Elle est donc prise en compte lors des quarts d'heure concernés :

```text
10:00 → -12 MW
10:15 → -12 MW
10:30 → -12 MW
...
12:15 → -12 MW
```
Puis elle n'est plus appliquée à partir de `12:30`.

### Fonction `appliquer_perturbation`

La fonction `appliquer_perturbation` reçoit :

```python
appliquer_perturbation(
    region_id,
    heure,
    demande_mw,
    perturbations
)
```

Elle vérifie si une perturbation est active pour la région et le quart d'heure courant.

Si une perturbation correspond, elle modifie la demande :

```text
demande_perturbée = demande_normale + deltaMw
```

La demande ainsi obtenue est ensuite transmise au calcul Dijkstra.

### Absence de perturbation

Le paramètre `perturbations` peut être `null`.

Dans ce cas, aucune perturbation n'est appliquée et la consommation normale est utilisée pour la simulation.

```json
"perturbations": null
```

Le comportement est alors équivalent à :

```text
demande perturbée = demande normale
```

### Déroulement dans la simulation

Les perturbations sont appliquées **avant le lancement du calcul Dijkstra** pour chaque région et chaque quart d'heure.

Le déroulement est donc :

```text
Consommation normale
        ↓
Vérification des perturbations
        ↓
Application de deltaMw si une perturbation est active
        ↓
Consommation perturbée
        ↓
Dijkstra
        ↓
Répartition de la demande entre les centrales
        ↓
Mise à jour de l'état du parc
```

Ainsi, une perturbation de consommation influence directement la demande à satisfaire par le parc de centrales pendant la période concernée.


## Principales limites connues
**A COMPLETER**

## Résumé du fonctionnement
```
Consommation régionale
        ↓
Production solaire + éolienne
        ↓
Calcul du besoin résiduel
        ↓
Sélection des centrales nucléaires
        ↓
Application des contraintes
        ↓
Puissance nucléaire réellement disponible
        ↓
Mise à jour de l'état des centrales
        ↓
Passage au quart d'heure suivant
        ↓
Calcul du déficit éventuel
        ↓
Contrôle de la réserve nucléaire
```
La simulation est répétée sur les 96 quarts d’heure de la journée.