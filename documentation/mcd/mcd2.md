# MCD 2 — Modèle destiné à se substituer aux fichiers JSON du moteur temporel

## Contenu des fichiers JSON (vérifié)

| Fichier | Contenu | Rôle dans ce MCD |
|---|---|---|
| `data.json` — `metadata` | description du dataset, sources, avertissements | non modélisé (documentation, pas une donnée opérationnelle) |
| `data.json` — `simulation_parameters` | poids/règles de l'algorithme d'allocation | non modélisé (configuration globale, pas une entité) |
| `data.json` — `plants[]` (18) | centrales, avec `location{}`, `reactors[]`, `simulation{}` | `centrale` + `reacteur` |
| `data.json` — `regions[]` (13) | régions, avec `centroid{}`, `local_plant_ids[]`, `external_entry_plant_ids[]` | `region` |
| `data.json` — `plant_edges[]` (33) | liaisons entre deux centrales | `liaison` |
| `data.json` — `example_scenarios[]` (4) | scénarios de démonstration, `plant_overrides{}` | `scenario` + `scenario_override` |
| `energia_parametres_temporels_nucleaire.json` | `plants[]` reprend les mêmes 18 `plant_id` | **enrichit** `centrale` (5 nouvelles colonnes) ; `global_nuclear_reserve` non modélisé (configuration) |
| `energia-journee-reference-consommation.json` | `region.consumption_mw` = 96 valeurs (pas de 15 min) | nouvelle table de faits `consommation_reference` |
| `energia-journee-reference-avec-t-moins-1.json` | même profil + `initial_state_t_minus_1` | même table + nouvelle table `etat_initial_regional` |
| `energia-production-non-pilotable.json` | `region.production_mw{solar,wind}` = 96 × 2 filières | nouvelle table de faits `production_non_pilotable` + `capacite_installee_non_pilotable` |
| `energia-scenarios-phase3-exemples.json` | `scenarios[].events[]` (type, région, fenêtre horaire, delta) | nouvelles tables `scenario_phase3` + `evenement_consommation` |

Aucun de ces fichiers n'ajoute de colonne à `region` autrement qu'au travers
d'une nouvelle table liée (`region` reste l'entité de rattachement commune à
`data.json` et aux 4 autres fichiers — c'est elle qui fait tenir le modèle en un
seul MCD).

## Table des associations (un seul MCD, à reproduire dans Looping)

| Association | Entité A | Card. A | Card. B | Entité B | Origine JSON |
|---|---|---|---|---|---|
| situee_dans | region | (0,n) | (1,1) | centrale | `location.region_id` / `region.local_plant_ids` |
| accessible_via | region | (0,n) | (0,n) | centrale | `region.external_entry_plant_ids` |
| comprend | centrale | (0,n) | (1,1) | reacteur | `plants[].reactors[]` |
| origine | centrale | (0,n) | (1,1) | liaison | `plant_edges[].from` |
| destination | centrale | (0,n) | (1,1) | liaison | `plant_edges[].to` |
| concerne | scenario | (1,1) | (0,n) | region | `example_scenarios[].region_id` |
| surcharge | scenario | (0,n) | (1,1) | scenario_override | `example_scenarios[].plant_overrides` |
| cible | centrale | (0,n) | (1,1) | scenario_override | clé de `plant_overrides{plant_id: ...}` |
| concerne | region | (0,n) | (1,1) | consommation_reference | `regions[].consumption_mw` |
| horodate | pas_de_temps | (0,n) | (1,1) | consommation_reference | `timestamps[]` |
| possede | region | (0,1) | (1,1) | etat_initial_regional | `initial_state_t_minus_1.regions` |
| possede | region | (0,n) | (1,1) | capacite_installee_non_pilotable | `regions[].synthetic_installed_capacity_mw` |
| concerne | filiere | (0,n) | (1,1) | capacite_installee_non_pilotable | clé `solar`/`wind` |
| concerne | region | (0,n) | (1,1) | production_non_pilotable | `regions[].production_mw` |
| concerne | filiere | (0,n) | (1,1) | production_non_pilotable | clé `solar`/`wind` |
| horodate | pas_de_temps | (0,n) | (1,1) | production_non_pilotable | `timestamps[]` |
| comprend | scenario_phase3 | (0,n) | (1,1) | evenement_consommation | `scenarios[].events[]` |
| concerne | region | (0,n) | (1,1) | evenement_consommation | `events[].region_id` |

## Vue Mermaid — un seul diagramme

```mermaid
erDiagram
    REGION ||--o{ CENTRALE : situee_dans
    REGION }o--o{ CENTRALE : accessible_via
    CENTRALE ||--o{ REACTEUR : comprend
    CENTRALE ||--o{ LIAISON : origine
    CENTRALE ||--o{ LIAISON : destination
    SCENARIO }o--|| REGION : concerne
    SCENARIO ||--o{ SCENARIO_OVERRIDE : surcharge
    CENTRALE ||--o{ SCENARIO_OVERRIDE : cible
    REGION ||--o{ CONSOMMATION_REFERENCE : concerne
    PAS_DE_TEMPS ||--o{ CONSOMMATION_REFERENCE : horodate
    REGION |o--o| ETAT_INITIAL_REGIONAL : possede
    REGION ||--o{ CAPACITE_INSTALLEE_NON_PILOTABLE : possede
    FILIERE ||--o{ CAPACITE_INSTALLEE_NON_PILOTABLE : concerne
    REGION ||--o{ PRODUCTION_NON_PILOTABLE : concerne
    FILIERE ||--o{ PRODUCTION_NON_PILOTABLE : concerne
    PAS_DE_TEMPS ||--o{ PRODUCTION_NON_PILOTABLE : horodate
    SCENARIO_PHASE3 ||--o{ EVENEMENT_CONSOMMATION : comprend
    REGION ||--o{ EVENEMENT_CONSOMMATION : concerne

    REGION {
        string id PK
        string insee_code
        string name
        float latitude
        float longitude
        int population_2023
        float annual_consumption_twh_2024
        float average_consumption_mw_2024
        float illustrative_peak_consumption_mw
        bool connected_to_continental_grid
        string data_notes_population
        string data_notes_consumption
        string data_notes_illustrative_peak
    }
    CENTRALE {
        string id PK
        string name
        float latitude
        float longitude
        string commune
        string department
        int reactor_count
        float installed_power_mw
        bool available
        float initial_output_mw
        float initial_load_ratio
        float soft_upper_bound_mw
        float soft_upper_bound_ratio
        float initial_dispatchable_margin_mw
        float max_ramp_up_mw_per_15_min
        float technical_penalty
        bool values_are_simulated
        float initial_output_mw_at_23_45_previous_day
        float minimum_operating_power_mw
        float max_ramp_down_mw_per_15_min
        bool minimum_power_fallback_used
        bool values_are_simulated_except_maximum_power
    }
    REACTEUR {
        string id PK
        string name
        float installed_power_mw
        float minimum_design_power_mw
        string status
        date industrial_commissioning_date
        string data_kind
    }
    LIAISON {
        string id PK
        bool bidirectional
        float distance_km
        float loss_percent
        float max_transfer_mw
        bool available
        bool topology_is_synthetic
        bool capacity_and_loss_are_simulated
    }
    SCENARIO {
        string id PK
        string description
        float additional_demand_mw
        string expected_result
    }
    SCENARIO_OVERRIDE {
        float initial_output_mw
        float soft_upper_bound_mw
    }
    PAS_DE_TEMPS {
        string horodatage PK
        int step_index
    }
    FILIERE {
        string code_filiere PK
        string libelle_filiere
    }
    CONSOMMATION_REFERENCE {
        float consommation_mw
    }
    ETAT_INITIAL_REGIONAL {
        float consommation_mw
        string horodatage
        string jour_relatif
    }
    CAPACITE_INSTALLEE_NON_PILOTABLE {
        float capacite_mw
    }
    PRODUCTION_NON_PILOTABLE {
        float production_mw
    }
    SCENARIO_PHASE3 {
        string id PK
        string name
    }
    EVENEMENT_CONSOMMATION {
        string id PK
        string type
        string start
        string end
        float delta_mw
        float delta_percent
    }
```

Ce diagramme ne contient que des entités ayant une clé et au moins une
association : `simulation_parameters` (data.json) et le bloc de configuration
du fichier nucléaire temporel restent hors MCD (voir plus haut) — pas de bloc
flottant.

## Notes de lecture

- `situee_dans` et `accessible_via` sont deux associations **distinctes** entre
  `region` et `centrale` : la première pour `local_plant_ids` (rattachement
  territorial, la centrale a exactement 1 région), la seconde pour
  `external_entry_plant_ids` (accès de secours, many-to-many).
- `liaison`, `scenario_override`, `consommation_reference` et
  `production_non_pilotable` sont chacune une entité à part entière reliée par
  **deux associations** (voire trois pour `production_non_pilotable` : région,
  filière, pas de temps) — jamais une colonne ajoutée à une ligne existante.
  C'est le même principe partout dans ce document.
- `region` est le point de jonction entre `data.json` (parc nucléaire, graphe)
  et les 4 autres fichiers (séries temporelles, scénarios phase 3) : c'est elle
  qui permet de n'avoir qu'un seul MCD au lieu de deux schémas disjoints.
- `metadata`, `simulation_parameters` (data.json) et le bloc de config du
  fichier nucléaire temporel ne sont modélisés nulle part : ce sont soit de la
  documentation sur le jeu de données, soit des paramètres globaux à
  occurrence unique sans clé ni relation — donc pas des entités Merise.
- Pas d'entité `source_donnees` : l'indépendance vis-à-vis de la source
  (JSON aujourd'hui, BDD demain) n'est pas un fait à modéliser dans le MCD —
  chaque entité de ce document a déjà une forme stable et neutre vis-à-vis de
  son origine ; c'est cette stabilité qui permet l'ingestion multi-source, pas
  une entité dédiée. Voir la table des sous-tâches ci-dessous pour où cette
  indépendance se joue réellement (au niveau du code, pas du MCD).

## Correspondance avec le code et les sous-tâches

| Sous-tâche | Traduction concrète |
|---|---|
| Définir l'interface/source de données | Une interface (ex: `DataSource`) dont dépend `DataStore.load()` (`fastapi/graph/datastore.py`), au lieu du `json.load(path)` codé en dur — pas une entité du MCD, un contrat côté code |
| Créer le provider JSON | Une implémentation de cette interface qui encapsule `parse_centrale`/`parse_region`/`parse_liaison` (`fastapi/graph/parsing.py`) et les parseurs équivalents pour les 4 autres fichiers, et restitue les entités de ce MCD |
| Faire dépendre le moteur de l'interface | `DataStore`, `Graph` et les routes (`dijkstra.py`, `calcul.py`) ne manipulent que les entités de ce MCD, jamais le JSON brut |
| Vérifier que le moteur ne lit pas directement le JSON | Aucun `open()`/`json.load()` en dehors du provider JSON ; une future implémentation BDD interrogerait directement les tables de ce MCD sans toucher `DataStore`, `Graph` ni les routes — le MCD ne change pas, seule l'implémentation de l'interface change |
