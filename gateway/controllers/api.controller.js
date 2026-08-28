const pythonService = require("../models/pythonService");

// Envoi de la demande des centrales à python-service
async function getCentrales(req, res) {
  try {
    const reponse = await pythonService.getCentrales();
    console.log(reponse);

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
}

// Envoi de la demande des régions à python-service
async function getRegions(req, res) {
  try {
    const reponse = await pythonService.getRegions();
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data,
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
}

// Envoi de la demande des réseaux à python-service
async function getLiaisons(req, res) {
  try {
    const reponse = await pythonService.getLiaisons();
    res.status(200).json({
      success: true,
      message: "La demande a été envoyé à python-service",
      reponse: reponse.data,
    });
  } catch (error) {
    // Si le moindre echec envoi le catch
    res.status(500).json({
      message: error.message,
    });
  }
}

// Envoi de la demande de simulation à python-service avec les params region et augmentation_mw
async function getSimulation(req, res) {
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

    const reponse = await pythonService.getSimulation(region, augmentation);

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
}

module.exports = {
  getCentrales,
  getRegions,
  getLiaisons,
  getSimulation,
};
