const axios = require("axios");
const express = require("express");
const app = express();
const port = 3000;

app.use(express.json());

// // Route test
// app.get("/test", (req, res) => {
//   res.status(200).json({
//     success: true,
//     message: "La gateway fonctionne correctement",
//   });
// });

// Envoi de la demande des centrales à python-service
app.get("/api/centrales", async (req, res) => {
  try {
    const reponse = await axios.get("http://python-service:8000/centrales");
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
});

// Envoi de la demande des régions à python-service
app.get("/api/regions", async (req, res) => {
  try {
    const reponse = await axios.get("http://python-service:8000/regions");
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
});

//Envoi de la demande des réseaux à python-service
app.get("/api/liaisons", async (req, res) => {
  try {
    const reponse = await axios.get("http://python-service:8000/liaisons");
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
});

// Route simulation NON TERMINE
app.post("/api/simulation", async (req, res) => {
  try {
    const reponse = await axios.get("http://python-service:8000/simulation");
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
});


app.listen(port, () => {
  console.log(`Gateway démarrée sur http://localhost:${port}`);
});
