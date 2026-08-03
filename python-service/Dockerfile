# Image officielle Python
FROM python:3.12-slim

# Empêche Python de créer les fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Affiche directement les logs dans le terminal
ENV PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les dépendances
COPY ./python-service/requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY ./python-service .

# Exposer le port de FastAPI
EXPOSE 8000

# Lancer l'application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]