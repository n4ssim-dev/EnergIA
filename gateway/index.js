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
    const reponse = await axios.get(
      "http://python-service:8000/centrales",
      {
        headers: {
          "x-password": "5",
        },
      }
    );
    console.log(reponse)

    res.status(200).json({
      success: true,
      message: "La demande a été envoyée à python-service",
      reponse: reponse.data,
    });
  } catch (error) {
    res.status(error.response?.status || 500).json({
      success: false,
      message:
        error.response?.data?.detail ||
        "Impossible de contacter le service Python",
    });
  }
});

// Envoi de la demande des régions à python-service
app.get("/api/regions", async (req, res) => {
  try {
    const reponse = await axios.get("http://python-service:8000/regions",
      {
        headers: {
          "x-password": "5",
        },
      }
    );
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
    const reponse = await axios.get("http://python-service:8000/liaisons",
      {
        headers: {
          "x-password": "5",
        },
      }
    );
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

// Envoi de la demande de simulation à python-service avec les params region et augmentation_mw
app.get("/api/simulation", async (req, res) => {
  try {
    const { region, augmentation_mw } = req.query;

    console.log("Paramètres reçus :", req.query);

    if (!region || !augmentation_mw) {
      return res.status(400).json({
        success: false,
        message: "Les paramètres region et augmentation_mw sont obligatoires",
      });
    }

    const augmentation = Number(augmentation_mw);

    if (Number.isNaN(augmentation)) {
      return res.status(400).json({
        success: false,
        message: "augmentation_mw doit être un nombre",
      });
    }

    const reponse = await axios.get(
      "http://python-service:8000/simulation",
      {
        params: {
          region,
          augmentation_mw: augmentation,
        },
        headers: {
          "x-password": "5",
        },
      }
    );

    return res.status(200).json({
      success: true,
      message: "La demande a été envoyée à python-service",
      reponse: reponse.data,
    });
  } catch (error) {
    console.error("Code reçu :", error.response?.status);
    console.error("Réponse reçue :", error.response?.data);
    console.error("Message :", error.message);

    return res.status(error.response?.status || 500).json({
      success: false,
      message: error.response?.data || error.message,
    });
  }
});



app.listen(port, () => {
  console.log(`Gateway démarrée sur http://localhost:${port}`);
});
