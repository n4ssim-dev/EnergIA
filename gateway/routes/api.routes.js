const express = require("express");
const router = express.Router();
const apiController = require("../controllers/api.controller");


router.get("/centrales", apiController.getCentrales);
router.get("/regions", apiController.getRegions);
router.get("/liaisons", apiController.getLiaisons);
router.get("/simulation", apiController.getSimulation);


router.get("/etat-centrale", apiController.getEtatCentrale);


module.exports = router;
