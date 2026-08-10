# Architecture et flux de données du projet

## Cataloguer les dimensions intéressantes pour prédire une consommation
À produire par le groupe : sélectionner les 4 à 6 dimensions jugées les plus utiles pour un premier modèle, en justifiant les choix (pertinence attendue vs facilité d'obtention de la donnée).

réponse : 
- Dimension temporelle : jour, heure, saisons et mois.
- Dimension météo : température (min/max par jour)
- Dimension évent : évènement positif et évènement négatif, 
- Dimension régional : démographie, part industrielle lourde, nom de la région, code insee, nombre de central, part électrique hors nucléaire et part nucléaire absolu
1. Dimension temporelle

Variables envisagées : heure de la journée, jour de la semaine, mois, saison, week-end ou jour ouvré.

Cette dimension est prioritaire car la consommation électrique suit des cycles très marqués. Les besoins ne sont pas les mêmes la nuit, en journée, en semaine ou le week-end, ni en hiver ou en été. Ces données sont également très faciles à obtenir puisqu’elles peuvent être directement extraites de la date et de l’heure associées aux relevés de consommation.

Pertinence attendue : très forte — Facilité d’obtention : très forte.

2. Dimension météorologique

Variables envisagées : température minimale, maximale et moyenne, éventuellement humidité, dans un second temps nous utiliserons une matrice de corrélation pour voir si les intempéries ont un impact.

La météo influence fortement la consommation électrique, notamment à travers le chauffage en hiver et la climatisation en été. Pour un premier modèle, la température semble être la variable météorologique la plus pertinente et la plus simple à exploiter.

Pertinence attendue : très forte — Facilité d’obtention : forte.

Dimension événementielle

Variables envisagées : présence d’un événement, type d’événement et impact attendu sur la consommation.

Nous distinguons deux catégories :

Événements positifs, susceptibles d’entraîner une hausse de la consommation électrique, par exemple un grand match de football, un concert, un festival ou un événement rassemblant beaucoup de personnes.
Événements négatifs, susceptibles d’entraîner une baisse de la consommation observée, par exemple une coupure générale de courant, un incident majeur sur le réseau ou un arrêt exceptionnel d’activité.

Cette dimension permettrait d’expliquer certaines variations inhabituelles que les seules variables temporelles ou météorologiques ne suffisent pas à expliquer.

Pertinence attendue : moyenne à forte — Facilité d’obtention : moyenne.

4. Dimension géographique et démographique

Variables envisagées : région, code INSEE, population, densité de population.

La consommation dépend directement du nombre d'habitants et du type de territoire. Une région fortement peuplée aura généralement une demande électrique plus importante qu'une région moins peuplée. Le code INSEE permet également de relier facilement les données de consommation à d'autres sources publiques.

Pertinence attendue : forte — Facilité d’obtention : forte.

5. Dimension économique et industrielle

Variables envisagées : part de l'industrie dans l'activité régionale, présence d'industries lourdes, éventuellement nombre d'établissements industriels ou niveau d'activité économique.

Deux régions ayant une population comparable peuvent avoir des consommations très différentes selon leur tissu économique. Une région comprenant beaucoup d'industries énergivores peut présenter une consommation élevée et des profils horaires différents d'une région principalement résidentielle ou tertiaire.

Cette dimension est donc intéressante, mais les données sont légèrement plus complexes à obtenir et à mettre à jour que les dimensions temporelles ou météorologiques.

Pertinence attendue : forte — Facilité d’obtention : moyenne.

Pour un premier modèle de prédiction, nous retenons prioritairement les dimensions temporelle, météorologique, calendrier, géographique/démographique et économique/industrielle. Elles présentent un bon compromis entre leur capacité supposée à expliquer les variations de consommation électrique et la disponibilité des données. 

## Cartographier les sources de données disponibles
Pour chaque dimension retenue à l'étape 1, identifiez une source de données réelle et remplissez :

| Source | Dimension(s) couverte(s) | Fréquence de mise à jour | Format | Contraintes d'accès |
|---|---|---|---|---|
| https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/temperature-quotidienne-regionale/exports/json | dim_meteo | Mise à jour  mensuelle, pas temporel des données est journalier | JSON | API publique OpenDataSoft, sans clé API indiquée ; Licence Ouverte v2.0 (Etalab) |
| Construire à partir d'un calendrier et compléter les jours féries avec une api https://www.data.gouv.fr/dataservices/jours-feries | dim_temps | -- | JSON | API publique data.gouv.fr |
| Population : https://www.insee.fr/fr/statistiques/8680653<br>Code région : https://www.insee.fr/fr/information/8377162 | dim_region | -- | CSV | CSV publique insee.fr |
| https://www.data.gouv.fr/datasets/donnees-touristiques-de-la-base-datatourisme | dim_evenement | -- | CSV | CSV publique data.gouv.fr |
| https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/consommation-quotidienne-brute-regionale/exports/json | fait_consommation_electrique | Mise à jour mensuelle | JSON | Open Data Réseaux énergies ODRE |



## Distinguer les types de flux
- `Batch` (traitement périodique) : ex. récupérer l'historique RTE une fois par jour via un script planifié (cron).
- `Streaming/temps réel` : ex. interroger une API météo à chaque requête de prédiction.
Pour chaque source retenue, précisez si elle relève d'un flux batch ou temps réel, et pourquoi.

Les différentes sources de données ne nécessitent pas toutes le même mode de traitement. Nous distinguons les flux batch, adaptés aux données relativement stables ou mises à jour périodiquement, et les flux temps réel, adaptés aux données qui évoluent rapidement et doivent être récupérées au moment de la prédiction.

| Dimension/source | Type de flux | Justification |
|---|---|---|
|Météo |	Temps réel |	Les conditions météorologiques peuvent évoluer rapidement. Pour produire une prédiction pertinente, il est préférable de récupérer les informations les plus récentes au moment de la demande.|
|Dimension régionale |	Batch |	Les informations comme la population, le code INSEE ou la structure industrielle d’une région évoluent lentement. Elles peuvent donc être récupérées et mises à jour périodiquement.|
|Dimension événementielle	| Batch	| Les événements programmés, comme les matchs ou festivals, peuvent être récupérés à l’avance et intégrés régulièrement dans la base. Les événements négatifs exceptionnels, comme une coupure générale, pourraient toutefois nécessiter une source temps réel s’ils doivent être pris en compte immédiatement. |
|Dimension temporelle |	Batch / calculée localement |	Les informations comme le jour, l’heure, le mois, la saison ou le week-end sont connues à l’avance et peuvent être directement calculées à partir de la date sans appel à une API externe.|

## Schématiser le flux de données


- Qui gère les erreurs si une source externe (météo, calendrier) est indisponible (fallback, valeur par défaut, message d'erreur propagé) ?
Dashboard des alertes pour la vérification des services externes indisponibles. Par la suite code pour gérer les exeptions et réagir sur la perte de données.

## Schématiser le flux de données
### Séparation du module de prédiction

- Le module de prédiction est-il un nouveau microservice séparé, ou une extension du service existant?

Le module de prédiction sera développé sous la forme d’un microservice séparé du moteur prescriptif.

Cette séparation permet de distinguer clairement deux responsabilités :

 - le microservice de prédiction estime la consommation électrique future à partir des différentes dimensions retenues ;
 - le moteur prescriptif, basé notamment sur Dijkstra, utilise cette prédiction pour déterminer comment répartir la production entre les centrales disponibles.

Cette architecture facilite la maintenance, les tests et l’évolution de chaque composant indépendamment.

### Transmission de la prédiction au moteur prescriptif

- Comment le résultat de prédiction (ex. additional_demand_mw) est-il transmis au moteur déjà développé ?

Le microservice de prédiction exposera une route permettant de demander une estimation de consommation pour une région et une période données.

Le flux principal devient donc :

```bash
Sources de données
        ↓
Microservice de prédiction
        ↓
Prédiction de consommation
        ↓
additional_demand_mw
        ↓
Moteur prescriptif / Dijkstra
        ↓
Répartition de la production
        ↓
Gateway
        ↓
Interface utilisateur
```

### Gestion des erreurs des sources externes

Qui gère les erreurs si une source externe (météo, calendrier) est indisponible (fallback, valeur par défaut, message d'erreur propagé) ?

Les indisponibilités des services externes devront être gérées à plusieurs niveaux.

Un système de logs et d’alertes permettra d’identifier les API ou sources devenues indisponibles. Un dashboard de supervision pourra ensuite centraliser l’état des différents services.

Le code devra également gérer les exceptions afin d’éviter qu’une panne d’une seule source bloque systématiquement toute la chaîne de prédiction.

Selon la donnée concernée, plusieurs stratégies pourront être utilisées :

- utiliser la dernière donnée valide connue ;
- utiliser une valeur par défaut ou une valeur moyenne ;
- continuer la prédiction sans la variable si le modèle le permet ;
- renvoyer un message d’erreur explicite si la donnée est indispensable.

Par exemple, si l’API météo est temporairement indisponible, le système pourrait utiliser les dernières données météo enregistrées plutôt que d’interrompre immédiatement la prédiction.

## Modéliser un schéma de base de données

## Anticiper les questions opérationnelles


### Stockage sécurisé des clés API

- Où et comment stocker les clés API (météo, éventuellement autres) de façon sécurisée (variables d'environnement, jamais en dur dans le code) ?

Les clés API utilisées par les différents services, par exemple pour la météo, ne doivent jamais être écrites directement dans le code source.

Elles seront stockées dans des variables d’environnement, par exemple via un fichier .env en environnement local. Ce fichier devra être exclu du dépôt Git avec .gitignore.

Dans Docker, ces variables pourront être transmises aux conteneurs via le fichier compose.yaml ou via un mécanisme de gestion de secrets.

Exemple :

```bash

WEATHER_API_KEY=xxxxxxxx

```

Le code :

```bash

import os

api_key = os.getenv("WEATHER_API_KEY")

```

La sécurisation des routes pourra compléter ce dispositif, mais elle ne remplace pas la protection des clés API.

### Comportement si le modèle ML n’est pas entraîné

- Que se passe-t-il si le modèle ML n'est pas encore entraîné au moment de la requête (valeur par défaut, erreur explicite) ?

Si le modèle n’est pas encore disponible au moment d’une requête, le service ne doit pas retourner une prédiction inventée ou une valeur par défaut qui pourrait être interprétée comme fiable.

Nous choisissons donc de renvoyer une erreur explicite indiquant que le modèle n’est pas encore disponible.

Par exemple :
```bash 
{
  "success": false,
  "message": "Le modèle de prédiction n'est pas encore entraîné. Veuillez réessayer ultérieurement."
}
```
Côté API, un code HTTP comme 503 Service Unavailable serait cohérent :

```bash 
raise HTTPException(
    status_code=503,
    detail="Le modèle de prédiction n'est pas encore disponible"
)
```

### Mise en cache des prédictions

- Faut-il mettre en cache les prédictions récentes pour éviter de recalculer à chaque appel ?

Oui, il est pertinent de mettre en cache certaines prédictions récentes.

Cela permet d’éviter de recalculer plusieurs fois une prédiction identique lorsque plusieurs utilisateurs ou services demandent les mêmes informations sur une courte période.

Par exemple, une prédiction pourrait être identifiée par :
```bash
région + date + heure
```
Ainsi :
```bash
Occitanie
2026-08-10
18:00
```

## Piloter le modèle une fois en production (MLOps)
Dans l'idéal, on veut tous ! À voir ce qu'on arrive à faire.

- Traçabilité
- Suivi de la performance
- Détection de drift
- Réentraînement
- Versionning