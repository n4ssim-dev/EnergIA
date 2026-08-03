const axios = require("axios");
const express = require("express");
const app = express();
const port = 3000;

app.use (express.json())


// Recevoir une requête : vérifier les informations de bas, appeler l'API python, récupérer sa réponse, envoyer cette réponse au client, gérer les erreurs

// Route test
app.get("/test", (req, res) => {
  res.status(200).json({
    success: true,
    message: "La gateway fonctionne correctement",
  });
});

// Route Centrales
// get/api/centrales

// Route Régions
// get/api/regions

// Route Réseau
// get/api/reseau

// Route simulation
// post/api/simulation

app.listen(port, () => {
  console.log(`Gateway démarrée sur http://localhost:${port}`);
});