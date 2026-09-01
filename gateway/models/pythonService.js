const axios = require("axios");

const PYTHON_SERVICE_URL = "http://python-service:8000";
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

module.exports = {
  getCentrales,
  getRegions,
  getLiaisons,
  getSimulation,
};
