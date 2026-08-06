# Gateway

## Installation

1. Initialiser Node.js

```bash
npm init -y
```
2. Installer express

```bash
npm install express
```
3. Installer axios

```bash
npm install axios
```
## Fonctionnement gateway

Gateway sert d'interface entre le client et le micro-service python.
Il envoit les questions et récupère les réponses du mocro-service.
Pour plus de sécurité, une identifcation est demandé par le micro-service à **gateway**.