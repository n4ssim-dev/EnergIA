const express = require("express");
const router = express.Router();
const predictionController = require("../controllers/predictive.controller");


router.get("/predictions/consommation", predictionController.getPredictions);


module.exports = router;
