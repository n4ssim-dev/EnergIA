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


// Envoi de la requete à python-service avec le param centrale_id 
async function getEtatCentrale(req, res) {
  try {
    const { centrale_id } = req.query;

    console.log("Paramètre reçu :", req.query);

    if (!centrale_id ) {
      return res.status(400).json({
        success: false,
        message: "Le paramètre centrale_id est obligatoire",
      });
    }

    const reponse = await pythonService.getEtatCentrale(centrale_id);

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


// Envoi de la demande des centrales disponibles à python-service
async function getCentralesDisponibles(req, res) {
  try {
    const reponse = await pythonService.getCentralesDisponibles();
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

// Envoi de la requet region consommation à python-service 
// avec les params region_id,heure,jour_relatif
async function getRegionsConsommation(req, res) {
  try {
    const { region_id,heure,jour_relatif} = req.query;

    console.log("Paramètres reçus :", req.query);

    if (!region_id || !heure || !jour_relatif ) {
      return res.status(400).json({
        success: false,
        message: "Les paramètres region_id, heure, jour_relatif sont obligatoires",
      });
    }
    
    const reponse = await pythonService.getRegionsConsommation(region_id, heure, jour_relatif);

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

// Envoi de la requete region consommation max à python-service 
// avec les params heure,jour_relatif
async function getRegionsConsommationMax(req, res) {
  try {
    const {heure,jour_relatif} = req.query;

    console.log("Paramètres reçus :", req.query);

    if (!heure || !jour_relatif) {
      return res.status(400).json({
        success: false,
        message: "Les paramètres  heure, jour_relatif sont obligatoires",
      });
    }
    
    const reponse = await pythonService.getRegionsConsommationMax(heure, jour_relatif);

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



// Envoi de la requete region situation  à python-service 
// avec les params region_id,heure,jour_relatif
async function getRegionsSituation(req, res) {
  try {
    const {region_id,heure,jour_relatif} = req.query;

    console.log("Paramètres reçus :", req.query);

    if (!heure || !jour_relatif || !region_id) {
      return res.status(400).json({
        success: false,
        message: "Les paramètres region_id, heure, jour_relatif sont obligatoires",
      });
    }
    
    const reponse = await pythonService.getRegionsSituation(region_id,heure,jour_relatif);

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
  getEtatCentrale,
  getCentralesDisponibles,
  getRegionsConsommation,
  getRegionsConsommationMax,
  getRegionsSituation
};
