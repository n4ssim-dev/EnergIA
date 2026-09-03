FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Empêche Python de créer les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Affiche directement les logs dans le terminal
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app


# COPY mcp_server/requirements.txt .

# RUN pip install --no-cache-dir -r requirements.txt

# COPY mcp_server ./mcp_server
# COPY fastapi ./fastapi

# WORKDIR /app

# EXPOSE 8002

# Copier les dépendances
COPY ./mcp_server/pyproject.toml ./mcp_server/uv.lock ./

# Installer les dépendances
RUN uv sync --frozen --no-dev

# Copier le reste du projet
COPY ./mcp_server .

# Exposer le port de FastAPI
EXPOSE 8002

# CMD ["python", "mcp_server/server.py"]

CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]