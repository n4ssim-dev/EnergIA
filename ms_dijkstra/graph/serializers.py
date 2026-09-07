# serialisation classes > dict (JSON)

def serialize_reactor(reactor):
    return {
        "id": reactor.id,
        "name": reactor.name,
        "installed_power_mw": reactor.installed_power_mw,
        "minimum_design_power_mw": reactor.minimum_design_power_mw,
        "status": reactor.status,
    }


def serialize_centrale(centrale):
    return {
        "id": centrale.id,
        "name": centrale.name,
        "latitude": centrale.latitude,
        "longitude": centrale.longitude,
        "commune": centrale.commune,
        "department": centrale.department,
        "region_id": centrale.region_id,
        "region_name": centrale.region_name,
        "reactor_count": centrale.reactor_count,
        "installed_power_mw": centrale.installed_power_mw,
        "reactors": [serialize_reactor(r) for r in centrale.reactors],
        "available": centrale.available,
        "initial_output_mw": centrale.initial_output_mw,
        "initial_load_ratio": centrale.initial_load_ratio,
        "soft_upper_bound_mw": centrale.soft_upper_bound_mw,
        "soft_upper_bound_ratio": centrale.soft_upper_bound_ratio,
        "initial_dispatchable_margin_mw": centrale.initial_dispatchable_margin_mw,
        "max_ramp_up_mw_per_15_min": centrale.max_ramp_up_mw_per_15_min,
        "max_ramp_down_mw_per_15_min":centrale.max_ramp_down_mw_per_15_min,
        "technical_penalty": centrale.technical_penalty,
        "available_capacity_mw": centrale.available_capacity_mw(),
    }


def serialize_region(region):
    return {
        "id": region.id,
        "insee_code": region.insee_code,
        "name": region.name,
        "latitude": region.latitude,
        "longitude": region.longitude,
        "population_2023": region.population_2023,
        "annual_consumption_twh_2024": region.annual_consumption_twh_2024,
        "average_consumption_mw_2024": region.average_consumption_mw_2024,
        "illustrative_peak_consumption_mw": region.illustrative_peak_consumption_mw,
        "connected_to_continental_grid": region.connected_to_continental_grid,
        "local_plant_ids": region.local_plant_ids,
        "external_entry_plant_ids": region.external_entry_plant_ids,
    }


def serialize_liaison(liaison):
    return {
        "id": liaison.id,
        "from_id": liaison.from_id,
        "to_id": liaison.to_id,
        "bidirectional": liaison.bidirectional,
        "distance_km": liaison.distance_km,
        "loss_percent": liaison.loss_percent,
        "max_transfer_mw": liaison.max_transfer_mw,
        "available": liaison.available,
    }
