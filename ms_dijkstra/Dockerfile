# Image officielle avec uv (gestionnaire de paquets utilisé par ms_dijkstra/)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Empêche Python de créer les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Affiche directement les logs dans le terminal
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les dépendances
COPY ./ms_dijkstra/pyproject.toml ./ms_dijkstra/uv.lock ./

# Installer les dépendances
RUN uv sync --frozen --no-dev

# Copier le reste du projet
COPY ./ms_dijkstra .
# relationnal.db est produite par ms_data ; graph/datastore.py la lit depuis
# /ms_data/data (chemin cross-service, cf. ms_dijkstra/graph/datastore.py).
COPY ./ms_data/data /ms_data/data

# Exposer le port de FastAPI
EXPOSE 8000

# Lancer l'application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
