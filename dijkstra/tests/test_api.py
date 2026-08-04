"""Tests rudimentaires des routes principales de l'API : /health,
/dijkstra/load-datastore et /dijkstra/shortest-path."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_load_datastore():
    response = client.get("/dijkstra/load-datastore")
    assert response.status_code == 200

    body = response.json()
    assert body["message"] == "Données chargées avec succès"
    assert body["centrales"] == 18
    assert body["regions"] > 0
    assert body["liaisons"] > 0


def test_shortest_path_ok():
    response = client.get(
        "/dijkstra/shortest-path",
        params={"from_node": "flamanville", "to_node": "tricastin"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["from"] == "flamanville"
    assert body["to"] == "tricastin"
    assert body["distance_km"] == pytest.approx(949.8)
    assert body["chemin"][0] == "flamanville"
    assert body["chemin"][-1] == "tricastin"


def test_shortest_path_same_node():
    response = client.get(
        "/dijkstra/shortest-path",
        params={"from_node": "bugey", "to_node": "bugey"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["distance_km"] == 0
    assert body["chemin"] == ["bugey"]


def test_shortest_path_unknown_node():
    response = client.get(
        "/dijkstra/shortest-path",
        params={"from_node": "atlantide", "to_node": "bugey"},
    )
    assert response.status_code == 404


def test_shortest_path_missing_params():
    response = client.get("/dijkstra/shortest-path", params={"from_node": "bugey"})
    assert response.status_code == 422
