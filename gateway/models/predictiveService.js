const axios = require("axios");

//const PYTHON_PREDICTION_URL = "http://127.0.0.1:8002"; 

const PYTHON_PREDICTION_URL = "http://energia-ms-predictive:8005"; 

const AUTH_HEADERS = {"x-password": "5"};

function getPredictions(region,date,heure) {
  return axios.get(`${PYTHON_PREDICTION_URL}/predictions/consommation`, {
    params: {
      region,
      date,
      heure
    },
    headers: AUTH_HEADERS,
  });
}


module.exports = {
  getPredictions
};
