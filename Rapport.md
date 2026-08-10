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
|API météo (à choisir)| température (min/max par jour) | Horaire | JSON | Clé API, quota d'appels gratuits limité |

Livrable de cette étape : le tableau complété, avec au moins une source réelle testée (un appel ou téléchargement simple, même sans exploitation complète).

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
Dans l'idéal on veut tous ! A voir ce qu'on arrive à faire.
