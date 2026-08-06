# EnergIA — Sprint 4 : Moteur prescriptif

Ce document décrit la partie du projet EnergIA développée pour le Sprint 4 :
le calcul du score de sélection des centrales, la priorisation des centrales
locales, la recherche des centrales distantes et la répartition de la demande.

Le reste du projet (gateway Node.js/Express, Dijkstra du Sprint 3, tests
unitaires du Sprint 6) est développé par le reste de l'équipe et n'est pas
couvert par ce document.

## Prérequis

- Python 3.13 ou supérieur
- [uv](https://docs.astral.sh/uv/) comme gestionnaire de paquets et
  d'environnements virtuels
- Le service Python du projet (dossier `dijkstra/`) déjà configuré, avec
  `store` (via `graph.datastore.get_store`) fonctionnel

## Installation

Depuis le dossier `dijkstra/` du projet :

```bash
uv sync
```

Cette commande installe toutes les dépendances déclarées dans
`pyproject.toml`, y compris `haversine`, utilisée pour estimer la distance
entre une région et une centrale externe lorsqu'aucune centrale locale n'est
disponible.

Si une dépendance manque, elle peut être ajoutée avec :

```bash
uv add nom_du_paquet
```

## Configuration

Cette partie du projet ne nécessite pas de variable d'environnement propre :
elle s'appuie sur le `store` global déjà chargé par le service (données
issues du fichier JSON du parc nucléaire). Se référer au `.env.example` du
projet pour la configuration générale du service.

## Lancement

Le lancement se fait via le service FastAPI global du projet, par exemple :

```bash
docker compose up --build
```

ou, en local, avec `uvicorn` depuis le dossier `dijkstra/` (se référer au
`main.py` du service pour la commande exacte).

Une fois le service démarré, l'API interactive (Swagger) est disponible à
l'adresse habituelle du service, par exemple `http://127.0.0.1:8000/docs`.

## Exécution des tests

Les tests unitaires sur ces fonctions ne sont pas encore écrits (Sprint 6,
hors périmètre de ce document). Une fois disponibles, ils seront lancés avec :

```bash
uv run pytest
```

## Route disponible

### `GET /dijkstra/calcule`

Calcule la répartition d'une hausse de consommation sur une région donnée,
en s'appuyant sur les centrales locales puis, si besoin, sur les centrales
externes.

**Paramètres de requête**

| Paramètre         | Type    | Requis | Description                                      |
|--------------------|---------|--------|---------------------------------------------------|
| `region`            | `str`   | oui    | Identifiant de la région (ex : `occitanie`)        |
| `augmentation_mw`   | `float` | oui    | Hausse de consommation à couvrir, en mégawatts     |

**Exemple de requête**

```
GET /dijkstra/calcule?region=occitanie&augmentation_mw=1200
```

**Format de la réponse**

```json
{
  "region": "occitanie",
  "demande_mw": 1200,
  "repartition": [
    { "plant_id": "golfech", "allocated_mw": 89 },
    { "plant_id": "tricastin", "allocated_mw": 177 }
  ],
  "puissance_manquante_mw": 934,
  "note": "Aucune centrale locale dans cette région : la distance vers les centrales externes est estimée via la formule de Haversine (région -> centrale, à vol d'oiseau), et les pertes réseau sont fixées à 0% par défaut (non calculables sans liaison directe connue)."
}
```

Le champ `"note"` n'apparaît que lorsque la région ne possède aucune
centrale locale (voir la section Limites connues).

**Erreurs**

| Code | Cas                                   |
|------|----------------------------------------|
| 404  | La région demandée n'existe pas         |

## Fonctionnement du moteur prescriptif

Le moteur suit le pipeline suivant pour une région et une demande MW données :

1. **Centrales locales** — toutes les centrales de `local_plant_ids` sont
   évaluées avec une distance et des pertes nulles (déjà sur place).
2. **Centrales externes** — deux cas de figure :
   - S'il existe au moins une centrale locale, elle sert de point de départ
     à l'algorithme de Dijkstra (`store.graph.shortest_path`, implémenté au
     Sprint 3) pour calculer la distance et le chemin vers chaque centrale
     de `external_entry_plant_ids`.
   - S'il n'existe aucune centrale locale (ex : Île-de-France), les
     centrales de `external_entry_plant_ids` sont traitées comme des points
     d'entrée directs : la distance est estimée par la formule de Haversine
     entre le centroïde de la région et la centrale, et les pertes réseau
     sont fixées à 0 (voir Limites connues).
   - Les centrales déjà présentes dans `local_plant_ids` sont exclues de ce
     traitement pour éviter qu'une même centrale soit comptée deux fois.
3. **Score** — chaque candidat reçoit un score (voir formule ci-dessous).
4. **Classement** — les candidats sont triés du meilleur score (le plus bas)
   au moins bon.
5. **Répartition** — la demande est allouée aux candidats dans l'ordre du
   classement, chacun recevant le minimum entre ce qu'il reste à couvrir et
   sa puissance encore disponible, jusqu'à couverture complète ou
   épuisement des candidats. La puissance non couverte est indiquée
   explicitement dans la réponse.

## Formule de classement des centrales

```
score = distance_km * distance_weight
      + loss_percent * loss_weight
      + pow(taux_saturation, 4) * saturation_weight
      + technical_penalty * technical_penalty_weight
      + bonus_regional (si centrale locale)
```

Un score **plus bas** indique une centrale plus intéressante à sélectionner.

**Poids utilisés** (issus des paramètres de simulation du jeu de données) :

| Paramètre                     | Valeur |
|--------------------------------|--------|
| `distance_weight`               | 1.0    |
| `loss_weight`                   | 45.0   |
| `saturation_weight`             | 900.0  |
| `technical_penalty_weight`      | 200.0  |
| `regional_priority_bonus`       | -250   |

Le taux de saturation est un ratio entre 0 et 1 (production actuelle sur
puissance maximale autorisée), élevé à la puissance 4 pour pénaliser
fortement les centrales proches de leur limite. Le bonus régional
(`-250`) est appliqué uniquement si la centrale appartient à
`local_plant_ids` de la région demandée, ce qui la favorise mécaniquement
dans le classement sans jamais l'imposer de façon rigide.

## Limites connues du prototype

- **Régions sans centrale locale** : en l'absence de centrale locale pour
  servir de point de départ à Dijkstra, la distance vers les centrales
  externes est estimée à vol d'oiseau (formule de Haversine, région →
  centrale) plutôt que via le graphe de liaisons réel. Cette distance est
  donc une approximation, pas une distance réseau réelle.
- **Pertes réseau non calculées dans ce même cas** : une estimation d'un
  taux de perte moyen par kilomètre a été testée à partir des liaisons
  existantes, mais les ratios observés se sont révélés trop variables
  (jusqu'à un facteur 3 d'une liaison à l'autre) pour être fiables. Les
  pertes sont donc fixées à 0% par défaut dans ce cas précis, ce qui
  favorise légèrement ces centrales dans le score par rapport à la réalité.
- **Chemins à plusieurs sauts** : le détail complet du chemin parcouru
  (liste des centrales intermédiaires) est disponible via Dijkstra
  (`chemin` dans le résultat de `rechercher_centrales_distantes`), mais
  n'est pas encore exposé dans la réponse finale de `/calcule`.
- **Tests unitaires** non encore écrits sur ces fonctions (prévu Sprint 6).
