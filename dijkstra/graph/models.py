class Reactor:
    def __init__(self, id, name, installed_power_mw, minimum_design_power_mw, status):
        self.id = id
        self.name = name
        self.installed_power_mw = installed_power_mw
        self.minimum_design_power_mw = minimum_design_power_mw
        self.status = status


class Centrale:
    def __init__(self, id, name, latitude, longitude, commune, department,
                 region_id, region_name, reactor_count, installed_power_mw,
                 reactors=None, available=True, initial_output_mw=0.0,
                 initial_load_ratio=0.0, soft_upper_bound_mw=0.0,
                 soft_upper_bound_ratio=0.95, initial_dispatchable_margin_mw=0.0,
                 max_ramp_up_mw_per_15_min=0.0, technical_penalty=1.0):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.commune = commune
        self.department = department
        self.region_id = region_id
        self.region_name = region_name
        self.reactor_count = reactor_count
        self.installed_power_mw = installed_power_mw
        self.reactors = reactors or []

        self.available = available
        self.initial_output_mw = initial_output_mw
        self.initial_load_ratio = initial_load_ratio
        self.soft_upper_bound_mw = soft_upper_bound_mw
        self.soft_upper_bound_ratio = soft_upper_bound_ratio
        self.initial_dispatchable_margin_mw = initial_dispatchable_margin_mw
        self.max_ramp_up_mw_per_15_min = max_ramp_up_mw_per_15_min
        self.technical_penalty = technical_penalty

    def available_capacity_mw(self):
        # puissance encore mobilisable avant d'atteindre le plafond de sécurité
        if not self.available:
            return 0.0
        return max(0.0, self.soft_upper_bound_mw - self.initial_output_mw)

    def __repr__(self):
        return (
            f"Centrale({self.id!r}, region={self.region_id!r}, "
            f"installed={self.installed_power_mw}MW, "
            f"output={self.initial_output_mw}MW, "
            f"margin={self.available_capacity_mw():.0f}MW)"
        )


class Region:
    def __init__(self, id, insee_code, name, latitude, longitude,
                 population_2023, annual_consumption_twh_2024,
                 average_consumption_mw_2024, illustrative_peak_consumption_mw,
                 connected_to_continental_grid, local_plant_ids=None,
                 external_entry_plant_ids=None):
        self.id = id
        self.insee_code = insee_code
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.population_2023 = population_2023
        self.annual_consumption_twh_2024 = annual_consumption_twh_2024
        self.average_consumption_mw_2024 = average_consumption_mw_2024
        self.illustrative_peak_consumption_mw = illustrative_peak_consumption_mw
        self.connected_to_continental_grid = connected_to_continental_grid
        self.local_plant_ids = local_plant_ids or []
        self.external_entry_plant_ids = external_entry_plant_ids or []

    def __repr__(self):
        return (
            f"Region({self.id!r}, plants_locales={self.local_plant_ids}, "
            f"conso_moy={self.average_consumption_mw_2024}MW)"
        )


class Liaison:
    def __init__(self, id, from_id, to_id, bidirectional, distance_km,
                 loss_percent, max_transfer_mw, available=True):
        self.id = id
        self.from_id = from_id
        self.to_id = to_id
        self.bidirectional = bidirectional
        self.distance_km = distance_km
        self.loss_percent = loss_percent
        self.max_transfer_mw = max_transfer_mw
        self.available = available

    def __repr__(self):
        sens = "<->" if self.bidirectional else "->"
        return (
            f"Liaison({self.from_id} {sens} {self.to_id}, "
            f"{self.distance_km}km, pertes={self.loss_percent}%, "
            f"cap={self.max_transfer_mw}MW, dispo={self.available})"
        )


class Graph:
    """Graphe pondéré des centrales : {centrale_id: {voisin_id: distance_km}}."""

    def __init__(self):
        self.adjacency = {}

    def add_node(self, node_id):
        if node_id not in self.adjacency:
            self.adjacency[node_id] = {}

    def add_edge(self, liaison):
        self.add_node(liaison.from_id)
        self.add_node(liaison.to_id)

        self.adjacency[liaison.from_id][liaison.to_id] = liaison.distance_km
        if liaison.bidirectional:
            self.adjacency[liaison.to_id][liaison.from_id] = liaison.distance_km

    def isolated_nodes(self):
        isoles = []
        for node, voisins in self.adjacency.items():
            if not voisins:
                isoles.append(node)
        return isoles

    def shortest_path(self, source, target):
        """Dijkstra : renvoie (distance_totale_km, chemin) entre deux centrales.
        Renvoie (None, None) si les centrales ne sont pas reliées"""
        if source not in self.adjacency or target not in self.adjacency:
            return None, None

        distances = {node: float("inf") for node in self.adjacency}
        previous = {node: None for node in self.adjacency}
        distances[source] = 0
        visited = set()

        while len(visited) < len(self.adjacency):
            current = None
            current_dist = float("inf")
            for node in self.adjacency:
                if node not in visited and distances[node] < current_dist:
                    current = node
                    current_dist = distances[node]

            if current is None:
                break
            visited.add(current)

            for voisin, poids in self.adjacency[current].items():
                nouvelle_distance = distances[current] + poids
                if nouvelle_distance < distances[voisin]:
                    distances[voisin] = nouvelle_distance
                    previous[voisin] = current

        if distances[target] == float("inf"):
            return None, None

        chemin = []
        node = target
        while node is not None:
            chemin.append(node)
            node = previous[node]
        chemin.reverse()

        return distances[target], chemin

    def __repr__(self):
        nb_arcs = sum(len(voisins) for voisins in self.adjacency.values())
        return f"Graph({len(self.adjacency)} nœuds, {nb_arcs} arcs)"
