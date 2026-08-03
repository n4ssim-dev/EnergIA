import json
from pathlib import Path

from models import Centrale, Graph, Liaison, Reactor, Region


DATA_PATH = Path(__file__).parent / "data" / "data.json"


# parsing json brute > classes
def parse_centrale(raw):
    location = raw["location"]
    sim = raw.get("simulation", {})

    reactors = []
    for r in raw.get("reactors", []):
        reactors.append(Reactor(
            id=r["id"],
            name=r["name"],
            installed_power_mw=r["installed_power_mw"],
            minimum_design_power_mw=r.get("minimum_design_power_mw", 0),
            status=r.get("status", "unknown"),
        ))

    return Centrale(
        id=raw["id"],
        name=raw["name"],
        latitude=location["latitude"],
        longitude=location["longitude"],
        commune=location.get("commune", ""),
        department=location.get("department", ""),
        region_id=location["region_id"],
        region_name=location.get("region_name", ""),
        reactor_count=raw.get("reactor_count", len(reactors)),
        installed_power_mw=raw["installed_power_mw"],
        reactors=reactors,
        available=sim.get("available", True),
        initial_output_mw=sim.get("initial_output_mw", 0.0),
        initial_load_ratio=sim.get("initial_load_ratio", 0.0),
        soft_upper_bound_mw=sim.get("soft_upper_bound_mw", raw["installed_power_mw"]),
        soft_upper_bound_ratio=sim.get("soft_upper_bound_ratio", 0.95),
        initial_dispatchable_margin_mw=sim.get("initial_dispatchable_margin_mw", 0.0),
        max_ramp_up_mw_per_15_min=sim.get("max_ramp_up_mw_per_15_min", 0.0),
        technical_penalty=sim.get("technical_penalty", 1.0),
    )


def parse_region(raw):
    centroid = raw.get("centroid", {})
    return Region(
        id=raw["id"],
        insee_code=raw.get("insee_code", ""),
        name=raw["name"],
        latitude=centroid.get("latitude", 0.0),
        longitude=centroid.get("longitude", 0.0),
        population_2023=raw.get("population_2023", 0),
        annual_consumption_twh_2024=raw.get("annual_consumption_twh_2024", 0.0),
        average_consumption_mw_2024=raw.get("average_consumption_mw_2024", 0.0),
        illustrative_peak_consumption_mw=raw.get("illustrative_peak_consumption_mw", 0.0),
        connected_to_continental_grid=raw.get("connected_to_continental_grid", True),
        local_plant_ids=raw.get("local_plant_ids", []),
        external_entry_plant_ids=raw.get("external_entry_plant_ids", []),
    )


def parse_liaison(raw):
    return Liaison(
        id=raw["id"],
        from_id=raw["from"],
        to_id=raw["to"],
        bidirectional=raw.get("bidirectional", True),
        distance_km=raw["geodesic_distance_km"],
        loss_percent=raw["estimated_loss_percent"],
        max_transfer_mw=raw["max_transfer_mw"],
        available=raw.get("available", True),
    )


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

    def print_report(self):
        print("=" * 70)
        print("EnergIA — Rapport de chargement des données")
        print("=" * 70)
        print(f"Jeu de données : {self.metadata.get('dataset_name', 'inconnu')}")
        print(f"Version        : {self.metadata.get('version', '?')}")
        print()
        print(f"Centrales chargées : {len(self.centrales)}")
        print(f"Régions chargées   : {len(self.regions)}")
        print(f"Liaisons chargées  : {len(self.liaisons)}")
        print(f"Graphe             : {self.graph}")
        print(f"Puissance installée totale : "
              f"{sum(c.installed_power_mw for c in self.centrales.values()):.0f} MW")
        print()

        print("-- Exemple de centrale --")
        exemple_centrale = next(iter(self.centrales.values()))
        print(f"  {exemple_centrale}")
        print()

        print("-- Exemple de région --")
        exemple_region = next(iter(self.regions.values()))
        print(f"  {exemple_region}")
        print()

        print("-- Exemple de liaison --")
        if self.liaisons:
            print(f"  {self.liaisons[0]}")
        print()

        print("-- Exemple de chemin (Dijkstra) --")
        distance, chemin = self.graph.shortest_path("flamanville", "tricastin")
        if chemin:
            print(f"  flamanville -> tricastin : {' -> '.join(chemin)} ({distance:.1f} km)")
        else:
            print("  flamanville -> tricastin : aucun chemin trouvé")

        distance, chemin = self.graph.shortest_path("flamanville", "centrale_inconnue")
        if chemin:
            print(f"  flamanville -> centrale_inconnue : {' -> '.join(chemin)} ({distance:.1f} km)")
        else:
            print("  flamanville -> centrale_inconnue : aucun chemin trouvé")
        print()

        anomalies = self.verify()
        print("-" * 70)
        if anomalies:
            print(f"⚠️  {len(anomalies)} anomalie(s) détectée(s) :")
            for a in anomalies:
                print(f"   - {a}")
        else:
            print("✅ Aucune anomalie détectée : les données sont cohérentes.")
        print("=" * 70)


def load_datastore(path=DATA_PATH):
    """Fonction utilitaire réutilisable ailleurs (routes API, tests, etc.)."""
    return DataStore().load(path)


if __name__ == "__main__":
    store = load_datastore()
    store.print_report()
