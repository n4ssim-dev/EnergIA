# Architecture et flux de données du projet

## Cataloguer les dimensions intéressantes pour prédire une consommation
À produire par le groupe : sélectionner les 4 à 6 dimensions jugées les plus utiles pour un premier modèle, en justifiant les choix (pertinence attendue vs facilité d'obtention de la donnée).

réponse : 
- Dimension temporelle : jour, heure, saisons et mois.
- Dimension météo : température (min/max par jour)
- Dimension évent : fériés, vacances, catastrophe naturelle, évenement spécial (culture,sport, ect..), 
- Dimension régional : démographie, part industrielle lourde, nom de la région, code insee, nombre de central, part électrique hors nucléaire et part nucléaire absolu


## Cartographier les sources de données disponibles
Pour chaque dimension retenue à l'étape 1, identifiez une source de données réelle et remplissez :

| Source | Dimension(s) couverte(s) | Fréquence de mise à jour | Format | Contraintes d'accès |
|---|---|---|---|---|
| https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/temperature-quotidienne-regionale/exports/json | dim_meteo | Mise à jour  mensuelle, pas temporel des données est journalier | JSON | API publique OpenDataSoft, sans clé API indiquée ; Licence Ouverte v2.0 (Etalab) |
| Construire à partir d'un calendrier et compléter les jours féries avec une api https://www.data.gouv.fr/dataservices/jours-feries | dim_temps | -- | JSON | API publique data.gouv.fr |
| Population : https://www.insee.fr/fr/statistiques/8680653<br>Code région : https://www.insee.fr/fr/information/8377162 | dim_region | -- | CSV | CSV publique insee.fr |
| https://www.data.gouv.fr/datasets/donnees-touristiques-de-la-base-datatourisme | dim_evenement | -- | CSV | CSV publique data.gouv.fr |
| https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/consommation-quotidienne-brute-regionale/exports/json | fait_consommation_electrique | Mise à jour mensuelle | JSON | Open Data Réseaux énergies ODRE |
|METEO|: https://open-meteo.com/ | n'importe quelle région en réglant sur le site
|population par région | https://www.insee.fr/fr/statistiques/8721456 | csv publique de 1975 à 2026 |
|Consomation energétique par région | https://www.data.gouv.fr/dataservices/consommation-annuelle-delectricite-et-gaz-par-region
|consomation part industrie lourde | https://opendata.agenceore.fr/data-fair/api/v1/datasets/consommation-annuelle-d-electricite-et-gaz-par-region/


## Distinguer les types de flux
- `Batch` (traitement périodique) : ex. récupérer l'historique RTE une fois par jour via un script planifié (cron).
- `Streaming/temps réel` : ex. interroger une API météo à chaque requête de prédiction.
Pour chaque source retenue, précisez si elle relève d'un flux batch ou temps réel, et pourquoi.

Météo : streaming
Dim région : batch
Dim évènement : batch

## Schématiser le flux de données
Questions à trancher :

- Le module de prédiction est-il un nouveau microservice séparé, ou une extension du service existant?
Le module de prédiction sera dans un autre micro-service pour avoir cette séparation :
  - Analyse prédictive de la consommation pour pouvoir être utilisé par Dijsktra.
  - Dijsktra lui sert à gérer la distribution en fonction de la prédiction de consommation.

- Comment le résultat de prédiction (ex. additional_demand_mw) est-il transmis au moteur déjà développé ?
Par une route définit qui à partir d'une plage de date donnée fait une prédiction de consommation mw, qui est envoyé au moteur prescriptif.

- Qui gère les erreurs si une source externe (météo, calendrier) est indisponible (fallback, valeur par défaut, message d'erreur propagé) ?
Dashboard des alertes pour la vérification des services externes indisponibles. Par la suite code pour gérer les exeptions et réagir sur la perte de données.

## Modéliser un schéma de base de données

## Anticiper les questions opérationnelles
- Où et comment stocker les clés API (météo, éventuellement autres) de façon sécurisée (variables d'environnement, jamais en dur dans le code) ?
.env, sécurisation des routes et mise en place des variables environnements.

- Que se passe-t-il si le modèle ML n'est pas encore entraîné au moment de la requête (valeur par défaut, erreur explicite) ?
Nous choisissons un message explicite "Trop tôt" ou "Attent ton tour", "Merci de patienter", "Vas boire un café", "Tu devrais rentrer chez toi".

- Faut-il mettre en cache les prédictions récentes pour éviter de recalculer à chaque appel ?
Oui

## Piloter le modèle une fois en production (MLOps)
Dans l'idéal, on veut tous ! À voir ce qu'on arrive à faire.

- Traçabilité
- Suivi de la performance
- Détection de drift
- Réentraînement
- Versionning