import json
from pathlib import Path

from .models import Graph
from .parsing import parse_centrale, parse_liaison, parse_region


DATA_PATH = Path(__file__).parent.parent / "data" / "data.json"


# Conteneur central (centrales, régions, liaisons et graphe associé)

class DataStore:
    def __init__(self):
        self.metadata = {}
        self.simulation_parameters = {}
        self.centrales = {}
        self.regions = {}
        self.liaisons = []
        self.graph = Graph()

    def load(self, path=DATA_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Fichier de données introuvable : {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.metadata = raw.get("metadata", {})
        self.simulation_parameters = raw.get("simulation_parameters", {})

        for raw_plant in raw.get("plants", []):
            centrale = parse_centrale(raw_plant)
            self.centrales[centrale.id] = centrale
            self.graph.add_node(centrale.id)

        for raw_region in raw.get("regions", []):
            region = parse_region(raw_region)
            self.regions[region.id] = region

        for raw_edge in raw.get("plant_edges", []):
            liaison = parse_liaison(raw_edge)
            self.liaisons.append(liaison)
            self.graph.add_edge(liaison)

        return self

    def verify(self):
        # vérifie la cohérence des données chargées et retourne la liste des anomalies détectées.
        anomalies = []

        # 1. Chaque centrale doit référencer une région existante
        for centrale in self.centrales.values():
            if centrale.region_id not in self.regions:
                anomalies.append(
                    f"Centrale '{centrale.id}' référence une région inconnue "
                    f"'{centrale.region_id}'"
                )

        # 2. Les local_plant_ids / external_entry_plant_ids des régions doivent référencer des centrales existantes
        for region in self.regions.values():
            for plant_id in region.local_plant_ids:
                if plant_id not in self.centrales:
                    anomalies.append(
                        f"Region '{region.id}' référence une centrale locale "
                        f"inconnue '{plant_id}'"
                    )
            for plant_id in region.external_entry_plant_ids:
                if plant_id not in self.centrales:
                    anomalies.append(
                        f"Region '{region.id}' référence une centrale externe "
                        f"inconnue '{plant_id}'"
                    )

        # 3. Chaque liaison doit relier deux centrales existantes
        for liaison in self.liaisons:
            if liaison.from_id not in self.centrales:
                anomalies.append(
                    f"Liaison '{liaison.id}' référence une centrale source "
                    f"inconnue '{liaison.from_id}'"
                )
            if liaison.to_id not in self.centrales:
                anomalies.append(
                    f"Liaison '{liaison.id}' référence une centrale cible "
                    f"inconnue '{liaison.to_id}'"
                )

        # 4. Centrales isolées (aucune liaison)
        isolees = self.graph.isolated_nodes()
        if isolees:
            anomalies.append(f"Centrales sans aucune liaison : {isolees}")

        # 5. Cohérence des valeurs simulées
        for centrale in self.centrales.values():
            if centrale.initial_output_mw > centrale.installed_power_mw:
                anomalies.append(
                    f"Centrale '{centrale.id}' : production actuelle "
                    f"({centrale.initial_output_mw}MW) > puissance installée "
                    f"({centrale.installed_power_mw}MW)"
                )
            if centrale.soft_upper_bound_mw > centrale.installed_power_mw:
                anomalies.append(
                    f"Centrale '{centrale.id}' : plafond de sécurité "
                    f"({centrale.soft_upper_bound_mw}MW) > puissance installée "
                    f"({centrale.installed_power_mw}MW)"
                )

        return anomalies


def load_datastore(path=DATA_PATH):
    """Fonction utilitaire réutilisable ailleurs (routes API, tests, etc.)."""
    return DataStore().load(path)


_store = None


def get_store():
    """Retourne le DataStore partagé, en le chargeant au besoin (singleton)."""
    global _store
    if _store is None:
        _store = load_datastore()
    return _store


def reload_store():
    """Force un rechargement du DataStore partagé et le retourne."""
    global _store
    _store = load_datastore()
    return _store
