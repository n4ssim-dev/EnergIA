FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Empêche Python de créer les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Affiche directement les logs dans le terminal
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les dépendances
COPY ./mcp_fastapi/pyproject.toml ./mcp_fastapi/uv.lock ./

# Installer les dépendances
RUN uv sync --frozen --no-dev

# Copier le reste du projet
COPY ./mcp_fastapi .
COPY ./fastapi/data /fastapi/data

# Exposer le port de l'API
EXPOSE 8003

# Lancer l'application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]
