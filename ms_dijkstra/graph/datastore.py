import sqlite3
from pathlib import Path

from .models import Centrale, Graph, Liaison, Reactor, Region


DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"

# Conteneur central (centrales, régions, liaisons et graphe associé)

class DataStore:
    def __init__(self):
        self.metadata = {}
        self.simulation_parameters = {}
        self.centrales = {}
        self.regions = {}
        self.liaisons = []
        self.timestamps = []
        self.graph = Graph()

    def load(self, path=DB_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Base de données introuvable : {path}")

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            self._load_regions(conn)
            self._load_centrales(conn)
            self._load_liaisons(conn)
        finally:
            conn.close()

        return self

    def _load_regions(self, conn):
        local_plant_ids = {}
        for row in conn.execute("SELECT id, id_1 FROM centrale"):
            local_plant_ids.setdefault(row["id_1"], []).append(row["id"])

        external_entry_plant_ids = {}
        for row in conn.execute("SELECT id, id_1 FROM accessible_via"):
            external_entry_plant_ids.setdefault(row["id_1"], []).append(row["id"])

        for row in conn.execute("SELECT * FROM region"):
            region = Region(
                id=row["id"],
                insee_code=row["insee_code"] or "",
                name=row["name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                population_2023=row["population_2023"] or 0,
                annual_consumption_twh_2024=row["annual_consumption_twh2024"] or 0.0,
                average_consumption_mw_2024=row["annual_consumption_mw_2024"] or 0.0,
                illustrative_peak_consumption_mw=row["illustrative_peak_consumption_mw"] or 0.0,
                connected_to_continental_grid=bool(row["connected_to_continental_grid"]),
                local_plant_ids=local_plant_ids.get(row["id"], []),
                external_entry_plant_ids=external_entry_plant_ids.get(row["id"], []),
            )
            self.regions[region.id] = region

    def _load_centrales(self, conn):
        region_names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM region")}

        reactors_by_centrale = {}
        for row in conn.execute("SELECT * FROM reacteur"):
            reactors_by_centrale.setdefault(row["id"], []).append(
                Reactor(
                    id=row["id_reacteur"],
                    name=row["name"],
                    installed_power_mw=row["installed_power_mw"],
                    minimum_design_power_mw=row["minimum_design_power_mw"] or 0,
                    status=row["status"] or "unknown",
                )
            )

        for row in conn.execute("SELECT * FROM centrale"):
            centrale = Centrale(
                id=row["id"],
                name=row["name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                commune=row["commune"] or "",
                department=row["departement"] or "",
                region_id=row["id_1"],
                region_name=region_names.get(row["id_1"], ""),
                reactor_count=row["reactor_count"],
                installed_power_mw=row["installed_power_mw"],
                reactors=reactors_by_centrale.get(row["id"], []),
                available=bool(row["available"]),
                initial_output_mw=row["initial_output_mw"] or 0.0,
                initial_load_ratio=row["initial_load_ratio"] or 0.0,
                soft_upper_bound_mw=row["soft_upper_bound_mw"] or row["installed_power_mw"],
                soft_upper_bound_ratio=row["soft_upper_bound_ratio"] or 0.95,
                initial_dispatchable_margin_mw=row["initial_dispatchable_margin_mw"] or 0.0,
                max_ramp_up_mw_per_15_min=row["max_ramp_up_mw_15_min"] or 0.0,
                max_ramp_down_mw_per_15_min=row["max_ramp_down_mw_per_15min"] or 0.0,
                initial_output_mw_at_23_45_previous_day=row["initial_output_mw_at_23_45_previous_day"] or 0.0,
                technical_penalty=row["technical_penalty"] or 1.0,
            )
            self.centrales[centrale.id] = centrale
            self.graph.add_node(centrale.id)

    def _load_liaisons(self, conn):
        for row in conn.execute("SELECT * FROM liaison"):
            liaison = Liaison(
                id=row["id"],
                from_id=row["id_1"],
                to_id=row["id_2"],
                bidirectional=bool(row["bidirectional"]),
                distance_km=row["distance_km"],
                loss_percent=row["loss_percent"],
                max_transfer_mw=row["max_transfer_mw"],
                available=bool(row["available"]),
            )
            self.liaisons.append(liaison)
            self.graph.add_edge(liaison)

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


def load_datastore(path=DB_PATH):
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
