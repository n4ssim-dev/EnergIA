from dijkstra.graph.models import Centrale, Liaison, Reactor, Region


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
