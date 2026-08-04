## Développement d'une plateforme d'aide à la décision pour le pilotage d'un parc de production électrique

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=node.js&logoColor=white)
![Express](https://img.shields.io/badge/Express.js-000000?style=for-the-badge&logo=express&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)



# Présentation du projet

EnergIA est une plateforme d'aide à la décision pour le pilotage d'un parc nucléaire, capable de recommander une répartition de la production lorsqu'une région connaît une hausse de sa consommation électrique:


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
- **energia-python** :  ;


---

# Installation


## 1. Configuration des variables d'environnement

Créer un fichier `.env` dans chacune des dossiers "python-service" et "gateway" 
en vous basant sur le fichier `.env.example`.

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

---



# Routes disponibles "micro service Python"

| Méthode | Route | Description | Body JSON |
|---|---|---|---|
| GET | `/centrales` | retourner la liste des centrales nucléaires  | Aucun |
| GET | `/regions` | Retourne la liste de toutes les régions | Aucun |
| GET | `/liaisons` | retourner la liste des liaisons  | Aucun |
| POST | `/simulation` | faire une nouvelle simulation,Par exemple Une région a besoin de X MW supplémentaires : quelles centrales doivent augmenter leur production, et de combien ? | ```json { "region": "centre_val_de_loire", "augmentation": "500" } ``` 
---

