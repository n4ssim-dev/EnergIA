const axios = require("axios");


const PYTHON_PREDICTION_URL = "http://energia-ms-predictive:8005"; 

const AUTH_HEADERS = {"x-api-key": "5"};

function getPredictions(region,date,heure) {
  return axios.get(`${PYTHON_PREDICTION_URL}/predictions/consommation/${region}/${date}/${heure}`, {
    headers: AUTH_HEADERS,
  });
}

module.exports = {
  getPredictions
};
