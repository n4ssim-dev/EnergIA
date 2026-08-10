# -------------------------------------------
# Image Node.js
# -------------------------------------------
FROM node:latest

WORKDIR /app


# Copier les dépendances
COPY ./gateway/package*.json ./

# Installer les dépendances
RUN npm install

# Installer nodemon globalement (si pas dans package.json)
RUN npm install -g nodemon

# Copier le code source
COPY ./gateway .

# Exposer le port Express
EXPOSE 3000

# Utiliser l'entrypoint Node officiel
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Démarrer avec nodemon
CMD ["nodemon", "-L", "index.js"]