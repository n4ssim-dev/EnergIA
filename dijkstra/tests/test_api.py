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


def test_rapport():
    response = client.get("/dijkstra/rapport")
    assert response.status_code == 200

    body = response.json()
    assert body["centrales_count"] == 18
    assert body["regions_count"] > 0
    assert body["liaisons_count"] > 0
    assert body["puissance_installee_totale_mw"] > 0
    assert isinstance(body["anomalies_count"], int)


def test_liste_centrales():
    response = client.get("/dijkstra/centrales")
    assert response.status_code == 200

    body = response.json()
    assert len(body["centrales"]) == 18
    assert {"id", "name", "installed_power_mw"} <= body["centrales"][0].keys()


def test_get_centrale_ok():
    response = client.get("/dijkstra/centrales/bugey")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == "bugey"
    assert body["installed_power_mw"] > 0


def test_get_centrale_unknown():
    response = client.get("/dijkstra/centrales/atlantide")
    assert response.status_code == 404


def test_liste_regions():
    response = client.get("/dijkstra/regions")
    assert response.status_code == 200

    body = response.json()
    assert len(body["regions"]) > 0
    assert {"id", "name"} <= body["regions"][0].keys()


def test_get_region_ok():
    response = client.get("/dijkstra/regions/ile_de_france")
    assert response.status_code == 200
    assert response.json()["id"] == "ile_de_france"


def test_get_region_unknown():
    response = client.get("/dijkstra/regions/atlantide")
    assert response.status_code == 404


def test_liste_liaisons():
    response = client.get("/dijkstra/liaisons")
    assert response.status_code == 200

    body = response.json()
    assert len(body["liaisons"]) > 0
    assert {"id", "from_id", "to_id", "distance_km"} <= body["liaisons"][0].keys()


def test_anomalies():
    response = client.get("/dijkstra/anomalies")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == len(body["anomalies"])
