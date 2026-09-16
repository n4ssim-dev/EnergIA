FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Empêche Python de créer les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Affiche directement les logs dans le terminal
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les dépendances
COPY ./ms_mcp/pyproject.toml ./ms_mcp/uv.lock ./

# Installer les dépendances
RUN uv sync --frozen --no-dev

# Copier le reste du projet
COPY ./ms_mcp .
COPY ./ms_data/data /ms_data/data

# Exposer le port de l'API
EXPOSE 8003

# Lancer l'application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]
