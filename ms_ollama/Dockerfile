FROM node:22

WORKDIR /app

COPY ./ms_ollama/package*.json ./

RUN npm install

COPY ./ms_ollama/ .

EXPOSE 3001

CMD ["npm", "run", "dev"]