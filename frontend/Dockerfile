FROM node:24.15.0-alpine

WORKDIR /app

COPY ./frontend/package.json ./frontend/package-lock.json ./

RUN npm ci

EXPOSE 8081

CMD ["npm", "start", "--", "--host", "0.0.0.0", "--port", "8081", "--poll", "1000"]