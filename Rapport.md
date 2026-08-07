# Architecture et flux de données du projet

## Cataloguer les dimensions intéressantes pour prédire une consommation
À produire par le groupe : sélectionner les 4 à 6 dimensions jugées les plus utiles pour un premier modèle, en justifiant les choix (pertinence attendue vs facilité d'obtention de la donnée).

## Cartographier les sources de données disponibles
Pour chaque dimension retenue à l'étape 1, identifiez une source de données réelle et remplissez :

| Source | Dimension(s) couverte(s) | Fréquence de mise à jour | Format | Contraintes d'accès |

| API météo (à choisir) | Température, humidité, ensoleillement | Horaire | JSON | Clé API, quota d'appels gratuits limité |

Livrable de cette étape : le tableau complété, avec au moins une source réelle testée (un appel ou téléchargement simple, même sans exploitation complète).

## Distinguer les types de flux
- `Batch` (traitement périodique) : ex. récupérer l'historique RTE une fois par jour via un script planifié (cron).
- `Streaming/temps réel` : ex. interroger une API météo à chaque requête de prédiction.
Pour chaque source retenue, précisez si elle relève d'un flux batch ou temps réel, et pourquoi.

## Schématiser le flux de données
Questions à trancher :

- Le module de prédiction est-il un nouveau microservice séparé, ou une extension du service existant?
- Comment le résultat de prédiction (ex. additional_demand_mw) est-il transmis au moteur déjà développé ?
- Qui gère les erreurs si une source externe (météo, calendrier) est indisponible (fallback, valeur par défaut, message d'erreur propagé) ?

## Modéliser un schéma de base de données

## Anticiper les questions opérationnelles
- Où et comment stocker les clés API (météo, éventuellement autres) de façon sécurisée (variables d'environnement, jamais en dur dans le code) ?
- Que se passe-t-il si le modèle ML n'est pas encore entraîné au moment de la requête (valeur par défaut, erreur explicite) ?
- Faut-il mettre en cache les prédictions récentes pour éviter de recalculer à chaque appel ?

## Piloter le modèle une fois en production (MLOps)
