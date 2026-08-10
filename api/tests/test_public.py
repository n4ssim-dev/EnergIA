from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH = {"X-Password": "5"}


def test_centrales_requires_password():
    response = client.get("/centrales")
    assert response.status_code == 401


def test_centrales():
    response = client.get("/centrales", headers=AUTH)
    assert response.status_code == 200
    assert len(response.json()["centrales"]) == 18


def test_regions():
    response = client.get("/regions", headers=AUTH)
    assert response.status_code == 200
    assert len(response.json()["regions"]) > 0


def test_liaisons():
    response = client.get("/liaisons", headers=AUTH)
    assert response.status_code == 200
    assert len(response.json()["liaisons"]) > 0


def test_simulation():
    response = client.get(
        "/simulation",
        params={"region": "ile_de_france", "augmentation_mw": 100},
        headers=AUTH,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["message"] == "Simulation lancée"
    assert "repartition" in body["resultat"]


def test_simulation_unknown_region():
    response = client.get(
        "/simulation",
        params={"region": "atlantide", "augmentation_mw": 100},
        headers=AUTH,
    )
    assert response.status_code == 404
