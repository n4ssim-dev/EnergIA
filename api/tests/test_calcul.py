import pytest

from graph.datastore import get_store
from routes.calcul import calcul_puissanceDispo, calcul_taux_saturation, executer_simulation, repartir_demande


# Vérifier si le calcul de la puissance restante marche correctement
def test_puissance_disponible():
    result = calcul_puissanceDispo(100, 70)

    assert result == 30


# La puissance produite atteint exactement la limite
def test_puissance_atteint_limite():
    result = calcul_puissanceDispo(100, 100)

    assert result == 0


# La production dépasse la limite
def test_puissance_depasse_limite():
    result = calcul_puissanceDispo(100, 120)

    assert result == 0


# Formule taux de saturation = puissance produite / puissance maximale


# tester le cas normal
# puissance produite = 50 MW et puissance maximale = 100 MW
def test_saturation_50_pourcent():
    assert calcul_taux_saturation(50, 100) == 0.5


# Production de la puissance maximale
def test_saturation_100_pourcent():
    assert calcul_taux_saturation(100, 100) == 1


# taux de saturation 0
def test_saturation_zero():
    assert calcul_taux_saturation(0, 100) == 0


# puissance maximal = 0
# Exemple la centrale est désactivée et n'est pas autorisé à produire
def test_saturation_max_power_zero():
    assert calcul_taux_saturation(50, 0) == 1


# puissance produite négative
def test_saturation_negative_output():
    assert calcul_taux_saturation(-20, 100) == 0


def test_repartir_demande_epuise_les_candidats():
    candidats_tries = [
        {"plant_id": "a", "soft_upper_bound_mw": 100, "initial_output_mw": 90},
        {"plant_id": "b", "soft_upper_bound_mw": 100, "initial_output_mw": 50},
    ]
    resultat = repartir_demande(60, candidats_tries)

    assert resultat["allocation"] == [
        {"plant_id": "a", "allocated_mw": 10},
        {"plant_id": "b", "allocated_mw": 50},
    ]
    assert resultat["unsatisfied_mw"] == 0


def test_repartir_demande_non_satisfaite():
    candidats_tries = [
        {"plant_id": "a", "soft_upper_bound_mw": 100, "initial_output_mw": 90},
    ]
    resultat = repartir_demande(50, candidats_tries)

    assert resultat["allocation"] == [{"plant_id": "a", "allocated_mw": 10}]
    assert resultat["unsatisfied_mw"] == 40


def test_executer_simulation_region_connue():
    store = get_store()
    resultat = executer_simulation(store, "ile_de_france", 100)

    assert resultat["region"] == "ile_de_france"
    assert resultat["demande_mw"] == 100
    assert "repartition" in resultat
    assert "puissance_manquante_mw" in resultat


def test_executer_simulation_region_inconnue():
    store = get_store()
    with pytest.raises(ValueError):
        executer_simulation(store, "atlantide", 100)
