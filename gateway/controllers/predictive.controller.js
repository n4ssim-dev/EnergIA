const predictionService = require("../models/predictiveService");


async function getPredictions(req, res) {
  try {
    const { region, date,heure } = req.query;

    console.log("Paramètres reçus :", req.query);

    if (!region || !date || !heure) {
      return res.status(400).json({
        success: false,
        message: "Les paramètres region, date et heure sont obligatoires",
      });
    }

    const reponse = await predictionService.getPredictions(region, date,heure);

    return res.status(200).json({
      success: true,
      message: "La demande a été envoyée à ms predictive",
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
}




module.exports = {
  getPredictions
};
