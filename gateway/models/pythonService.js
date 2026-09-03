const axios = require("axios");

//const PYTHON_SERVICE_URL = "http://energia-api:8000";  
const PYTHON_SERVICE_URL = "http://127.0.0.1:8000/"; 
const AUTH_HEADERS = { "x-password": "5" };

function getCentrales() {
  return axios.get(`${PYTHON_SERVICE_URL}/centrales`, {
    headers: AUTH_HEADERS,
  });
}

function getRegions() {
  return axios.get(`${PYTHON_SERVICE_URL}/regions`, {
    headers: AUTH_HEADERS,
  });
}

function getLiaisons() {
  return axios.get(`${PYTHON_SERVICE_URL}/liaisons`, {
    headers: AUTH_HEADERS,
  });
}

function getSimulation(region, augmentation_mw) {
  return axios.get(`${PYTHON_SERVICE_URL}/simulation`, {
    params: {
      region,
      augmentation_mw,
    },
    headers: AUTH_HEADERS,
  });
}


function getEtatCentrale(centrale_id) {
  return axios.get(`${PYTHON_SERVICE_URL}/analytics/centrales/${centrale_id}/etat`, {
    params: {
      centrale_id,
    },
    headers: AUTH_HEADERS,
  });
}

module.exports = {
  getCentrales,
  getRegions,
  getLiaisons,
  getSimulation,
  getEtatCentrale
};
