# ms_data — ETL + Postgres EnergIA

Service FastAPI qui extrait les fichiers JSON de `ms_dijkstra/data`, les
charge dans `data/analytics.db` (SQLite, lue par `ms_dijkstra`), puis
mirroir le résultat vers une base Postgres dockerisée bundlée dans ce même
service.

## Lancer le projet (API seule, sans Postgres)

```
uv sync
uv run fastapi dev
```

`POST /database/ingest` (protégée par le header `x-password`, `API_PASSWORD`
en env) échouera si Postgres n'est pas joignable — démarrer `docker compose
up postgres` au moins, ou tout lancer via Docker (voir plus bas).

## Lancer API + Postgres via Docker

```
docker compose up --build
```

- `ms-data` (l'API) écoute sur `${PORT:-8004}`.
- `postgres` écoute sur `${POSTGRES_PORT:-5434}` (host) -> `5432` (conteneur).
  Sur le réseau docker-compose, `ms-data` s'y connecte via `POSTGRES_HOST=postgres`
  (surchargé automatiquement dans `docker-compose.yml`, indépendamment de `.env`).

## Variables d'environnement

Voir `.env.example` : `HOST`, `PORT`, `API_PASSWORD`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Rôles des fichiers

| Fichier / dossier | Rôle |
| --- | --- |
| `data/*.json` | Copie des fichiers sources extraits (miroir de `ms_dijkstra/data`) |
| `data/mcd_analytique.sql` | Schéma SQLite |
| `data/analytics.db` | Base SQLite générée, lue par `ms_dijkstra` |
| `postgres/init/001_schema.sql` | Schéma Postgres (même modèle, `LOGICAL` -> `BOOLEAN`). Rejoué à chaque ingestion par `routes/database.py`, et monté dans `docker-entrypoint-initdb.d` pour le bootstrap initial du conteneur |
| `routes/database.py` | Extraction JSON -> SQLite, puis mirroir SQLite -> Postgres (`POST /database/ingest`) |
| `routes/auth.py` | Dépendance `check_password` (`API_PASSWORD`) |
| `catalog.py` | Catalogue statique des routes de `ms_dijkstra` + liste des tables, utilisés par l'ingestion |
| `docker-compose.yml` | Services `ms-data` (API) et `postgres`, réseau partagé |
