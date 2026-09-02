
const express = require('express');
const axios = require('axios');

const app = express();

app.use(express.json());

app.post('/normaliser', async (req, res) => {
  const { question } = req.body;

  if (!question) {
    return res.status(400).json({
      error: 'Question manquante'
    });
  }

  const prompt = `
Tu es le module de normalisation de EnergIA.

Transforme la question utilisateur en JSON.

Actions possibles :
- liste_regions
- liste_centrales
- etat_centrale
- consommation_region
- production_region
- simulation

Format attendu :
{
  "action": "...",
  "region": null,
  "centrale": null,
  "heure": null
}

Question :
${question}

Réponds uniquement avec le JSON.
`;

  try {
    const response = await axios.post(
      'http://langage:11434/api/generate',
      {
        model: 'qwen2.5:7b',
        prompt: prompt,
        format: 'json',
        stream: false
      }
    );

    const resultat = JSON.parse(
      response.data.response
    );

    res.json(resultat);

  } catch (error) {
    console.error(error);

    res.status(503).json({
      error: 'Ollama indisponible'
    });
  }
});

app.listen(3001, () => {
  console.log('Service Ollama lancé sur le port 3001');
});






// Routes pour interroger l'assistant
app.post('/assistant', async (req, res) => {
  let { question } = req.body;

  if (!question || typeof question !== "string") {
    return res.status(400).json({
      message: "Le champ question est obligatoire",
    });
  }

  try {
    const questionInitiale = question;

    question = new Set(
      question
        .toLowerCase()
        .replace(/[?!.,;:]/g, "")
        .split(" ")
        .filter((mot) => mot !== "")
    );

    const regionList = await liste_regions();

    const regionTrouvee = question.intersection(regionList);

    console.log("Mots de la question :", question);
    console.log("Tags de la base :", tagList);
    console.log("Intersection :", tagsPertinents);

    if (regionTrouvee.size === 0) {
      return res.status(404).json({
        message: "Aucune region trouvé dans la question",
      });
    }

//     const recupByTag = await findByTags(
//       Array.from(tagsPertinents)
//     );

//     if (!recupByTag || recupByTag.length === 0) {
//       return res.status(404).json({
//         message: "Aucune connaissance trouvée avec ce tag",
//       });
    // }

    const prompt = `
Tu es l'assistant d'EnergIA.

// Voici les seules connaissances que tu peux utiliser :
// ${JSON.stringify(recupByTag, null, 2)}

// Question de l'utilisateur :
// "${questionInitiale}"

// Réponds directement et simplement à la question.

// Règles :
// - utilise uniquement les informations fournies ci-dessus ;
// - lorsqu'une commande pertinente existe dans le champ "code", donne cette commande ;
// - n'ajoute aucune information extérieure ;
// - si aucune connaissance ne permet réellement de répondre, indique :
//   "Je n'ai pas assez d'informations dans BrainBox pour répondre."
// `;

    console.log(prompt);

    const reponseOllama = await axios.post(
  "http://langage:11434/api/generate",
  {
    model: "qwen2.5:7b",
    prompt: prompt,
    stream: false,
  }
);

//     return res.status(200).json({
//       tags: Array.from(liste_regions),
//       connaissances: regionList,
//       reponse_ia: reponseOllama.data.response,
//     });
//   } catch (err) {
//     console.error(
//       "Erreur assistant :",
//       err.response?.data || err.message
//     );

    return res.status(500).json({
      message: "Erreur lors de l'appel à l'assistant",
      erreur: err.response?.data || err.message,
    });
  } 
  catch (err) {
    console.error(
      "Erreur assistant :",
      err.response?.data || err.message
    );
});

// };


// app.post("/alimentation", async (req, res) => {
//   const {
//     titre,
//     type,
//     technologies,
//     contenu,
//     description,
//     projet,
//     fichier,
//     tags
//   } = req.body;

//   if (!titre || !type || !contenu) {
//     return res.status(400).json({
//       message: "Les champs titre, type et contenu sont obligatoires"
//     });
//   }

//   try {
//     const nouvelleConnaissance = {
//       titre,
//       type,
//       technologies: technologies || [],
//       contenu,
//       description: description || "",
//       projet: projet || "",
//       fichier: fichier || null,
//       tags: tags || [],
//       date_ajout: new Date(),
//       date_modification: new Date()
//     };

//     const result = await global.connexion
//       .db("brainboxlola")
//       .collection("connaissances_techniques")
//       .insertOne(nouvelleConnaissance);

//     return res.status(201).json({
//       message: "Connaissance technique ajoutée avec succès",
//       id: result.insertedId,
//       connaissance: {
//         _id: result.insertedId,
//         ...nouvelleConnaissance
//       }
//     });
//   } catch (err) {
//     console.error("Erreur MongoDB :", err);

//     return res.status(500).json({
//       message: "Erreur lors de l'ajout dans MongoDB",
//       erreur: err.message
//     });
//   }
// });

// port de lancement du serveur
const PORT = process.env.PORT || 3001;

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});
