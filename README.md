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
- **energia-python** : microservice développé avec FastAPI. Il expose les données relatives aux centrales, aux régions et aux liaisons, et permet de lancer une simulation avec le moteur prescriptif ;

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

Créer un fichier `.env` dans chacune des dossiers "python-service" et "gateway" 
en vous basant sur le fichier `.env.example`.

Exemple :

cp gateway/.env.example gateway/.env
cp python-service/.env.example python-service/.env

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


# Fonctionnnement 

liste des éléments à ajouter au Readme : 

- le lancement de l’application ;
- l’exécution des tests ;
- le format des requêtes ;
- le format des réponses ;
- le fonctionnement du moteur prescriptif ;
- la formule ou les règles utilisées pour classer les centrales ;
- les limites connues du prototype.

