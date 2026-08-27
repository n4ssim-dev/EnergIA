import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends

from .auth import check_password

DATA_DIR = Path(__file__).parent.parent / "data"
REPO_ROOT = Path(__file__).parent.parent.parent
DB_PATH = REPO_ROOT / "documentation" / "test.db"
SCHEMA_PATH = REPO_ROOT / "documentation" / "mcd" / "mcd2.sql"

FILIERES = {
    "solar": "Solaire",
    "wind": "Éolien",
}

# Ordre sans contrainte particulière : PRAGMA foreign_keys est désactivé le
# temps du drop, pour ne pas avoir à respecter l'ordre des FK.
TABLES = [
    "evenement_consommation",
    "scenario_phase3",
    "scenario_override",
    "scenario",
    "accessible_via2",
    "reacteur",
    "liaison",
    "centrale",
    "consommation_reference",
    "production_non_pilotable",
    "capacitee_instalee_non_pilotable",
    "etat_initial_regional",
    "pas_de_temps",
    "filiere",
    "region",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def reset_schema(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("PRAGMA foreign_keys = ON")


def _load(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_data_json(conn):
    raw = _load("data.json")

    for r in raw.get("regions", []):
        centroid = r.get("centroid", {})
        notes = r.get("data_notes", {})
        conn.execute(
            """
            INSERT INTO region (
                id_region, insee_code, name, latitude, longitude,
                population_2023, annual_consumption_twh2024,
                average_consumption_mw_2024, illustrative_peak_consumption_mw,
                connected_to_continental_grid, data_notes_population,
                data_notes_illustrative_peak, data_notes_consumption
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["id"], r.get("insee_code", ""), r["name"],
                centroid.get("latitude", 0.0), centroid.get("longitude", 0.0),
                r.get("population_2023", 0), r.get("annual_consumption_twh_2024", 0.0),
                r.get("average_consumption_mw_2024", 0.0),
                r.get("illustrative_peak_consumption_mw", 0.0),
                r.get("connected_to_continental_grid", True),
                notes.get("population"), notes.get("illustrative_peak"),
                notes.get("consumption"),
            ),
        )

    for p in raw.get("plants", []):
        location = p["location"]
        sim = p.get("simulation", {})
        conn.execute(
            """
            INSERT INTO centrale (
                id_centrale, name, latitude, longitude, commune, departement,
                reactor_count, installed_power_mw, available, initial_output_mw,
                initial_load_ratio, soft_upper_bound_mw, soft_upper_bound_ratio,
                initial_dispatchable_margin_mw, max_ramp_up_mw_15_min,
                technical_penalty, values_are_simulated, id_region
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"], p["name"], location["latitude"], location["longitude"],
                location.get("commune", ""), location.get("department", ""),
                p.get("reactor_count", len(p.get("reactors", []))),
                p["installed_power_mw"], sim.get("available", True),
                sim.get("initial_output_mw", 0.0), sim.get("initial_load_ratio", 0.0),
                sim.get("soft_upper_bound_mw", p["installed_power_mw"]),
                sim.get("soft_upper_bound_ratio", 0.95),
                sim.get("initial_dispatchable_margin_mw", 0.0),
                sim.get("max_ramp_up_mw_per_15_min", 0.0),
                sim.get("technical_penalty", 1.0),
                sim.get("values_are_simulated", True),
                location["region_id"],
            ),
        )

        for reactor in p.get("reactors", []):
            conn.execute(
                """
                INSERT INTO reacteur (
                    id_reacteur, name, installed_power_mw, minimum_design_power_mw,
                    status, industrial_commisionning_date, data_kind, id_centrale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reactor["id"], reactor["name"], reactor["installed_power_mw"],
                    reactor.get("minimum_design_power_mw", 0),
                    reactor.get("status", "unknown"),
                    reactor.get("industrial_commissioning_date"),
                    reactor.get("data_kind"),
                    p["id"],
                ),
            )

    for edge in raw.get("plant_edges", []):
        conn.execute(
            """
            INSERT INTO liaison (
                id, bidirectional, distance_km, loss_percent, max_transfer_mw,
                available, topology_is_synthetic, capacity_and_loss_are_simulated,
                id_centrale, id_centrale_1
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge["id"], edge.get("bidirectional", True), edge["geodesic_distance_km"],
                edge["estimated_loss_percent"], edge["max_transfer_mw"],
                edge.get("available", True), edge.get("topology_is_synthetic", False),
                edge.get("capacity_and_loss_are_simulated", False),
                edge["from"], edge["to"],
            ),
        )

    for r in raw.get("regions", []):
        for plant_id in r.get("external_entry_plant_ids", []):
            conn.execute(
                "INSERT OR IGNORE INTO accessible_via2 (id_centrale, id_region) VALUES (?, ?)",
                (plant_id, r["id"]),
            )

    scenario_id = 0
    override_id = 0
    for s in raw.get("example_scenarios", []):
        scenario_id += 1
        conn.execute(
            """
            INSERT INTO scenario (id, description, expected_result, additionnal_demand_mw, id_region)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                scenario_id, s.get("description"), s.get("expected_result"),
                s.get("additional_demand_mw", 0.0), s["region_id"],
            ),
        )
        for plant_id, override in s.get("plant_overrides", {}).items():
            override_id += 1
            conn.execute(
                """
                INSERT INTO scenario_override (id, initial_output_mw, soft_upper_bound_mw, id_1, id_centrale)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    override_id, override.get("initial_output_mw"),
                    override.get("soft_upper_bound_mw"), scenario_id, plant_id,
                ),
            )

    return {
        "region": len(raw.get("regions", [])),
        "centrale": len(raw.get("plants", [])),
        "liaison": len(raw.get("plant_edges", [])),
        "scenario": scenario_id,
        "scenario_override": override_id,
    }


def ingest_nuclear_temporal_params(conn):
    raw = _load("energia_parametres_temporels_nucleaire.json")

    count = 0
    for p in raw.get("plants", []):
        conn.execute(
            """
            UPDATE centrale SET
                initial_output_mw_at_23_45_previous_day = ?,
                minimum_operating_power_mw = ?,
                max_ramp_down_mw_per_15min = ?,
                minimum_power_fallback_used = ?,
                values_are_simulated_except_maximum_power = ?
            WHERE id_centrale = ?
            """,
            (
                p.get("initial_output_mw_at_23_45_previous_day"),
                p.get("minimum_operating_power_mw"),
                p.get("max_ramp_down_mw_per_15_min"),
                p.get("minimum_power_fallback_used", False),
                p.get("values_are_simulated_except_maximum_power", True),
                p["plant_id"],
            ),
        )
        count += 1

    return {"centrale_enrichie": count}


def _ensure_pas_de_temps(conn, timestamps):
    for i, ts in enumerate(timestamps):
        conn.execute(
            "INSERT OR IGNORE INTO pas_de_temps (horodatage, step_index) VALUES (?, ?)",
            (ts, i),
        )


def ingest_consommation_reference(conn):
    raw = _load("energia-journee-reference-consommation.json")
    timestamps = raw["timestamps"]
    _ensure_pas_de_temps(conn, timestamps)

    row_id = 0
    for r in raw.get("regions", []):
        for ts, valeur in zip(timestamps, r["consumption_mw"]):
            row_id += 1
            conn.execute(
                """
                INSERT INTO consommation_reference (id, consommation_mw, horodatage, id_region)
                VALUES (?, ?, ?, ?)
                """,
                (row_id, valeur, ts, r["id"]),
            )

    return {"consommation_reference": row_id}


def ingest_etat_initial(conn):
    # energia-journee-reference-avec-t-moins-1.json reprend la même série que
    # energia-journee-reference-consommation.json (déjà ingérée) : on ne lit
    # ici que le bloc initial_state_t_minus_1, propre à ce fichier.
    raw = _load("energia-journee-reference-avec-t-moins-1.json")
    etat = raw["initial_state_t_minus_1"]
    horodatage = etat["timestamp"]
    jour_relatif = etat["relative_day"]

    row_id = 0
    for region_id, valeurs in etat["regions"].items():
        row_id += 1
        conn.execute(
            """
            INSERT INTO etat_initial_regional (id, consommation_mw, horodatage, jour_relatif, id_region)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row_id, valeurs["consumption_mw"], horodatage, jour_relatif, region_id),
        )

    return {"etat_initial_regional": row_id}


def ingest_production_non_pilotable(conn):
    raw = _load("energia-production-non-pilotable.json")
    timestamps = raw["timestamps"]
    _ensure_pas_de_temps(conn, timestamps)

    for code, libelle in FILIERES.items():
        conn.execute(
            "INSERT OR IGNORE INTO filiere (code_filiere, libelle_filiere) VALUES (?, ?)",
            (code, libelle),
        )

    capacite_id = 0
    production_id = 0
    for r in raw.get("regions", []):
        capacites = r.get("synthetic_installed_capacity_mw", {})
        productions = r.get("production_mw", {})

        for code_filiere, capacite_mw in capacites.items():
            capacite_id += 1
            conn.execute(
                """
                INSERT INTO capacitee_instalee_non_pilotable (id, capacitee_mw, code_filiere, id_region)
                VALUES (?, ?, ?, ?)
                """,
                (capacite_id, capacite_mw, code_filiere, r["id"]),
            )

        for code_filiere, valeurs in productions.items():
            for ts, valeur in zip(timestamps, valeurs):
                production_id += 1
                conn.execute(
                    """
                    INSERT INTO production_non_pilotable (id, production_mw, code_filiere, id_region, horodatage)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (production_id, valeur, code_filiere, r["id"], ts),
                )

    return {
        "capacitee_instalee_non_pilotable": capacite_id,
        "production_non_pilotable": production_id,
    }


def ingest_scenarios_phase3(conn):
    raw = _load("energia-scenarios-phase3-exemples.json")

    event_count = 0
    for s in raw.get("scenarios", []):
        conn.execute(
            "INSERT INTO scenario_phase3 (id_scenario_phase3, name) VALUES (?, ?)",
            (s["id"], s.get("name")),
        )
        for i, event in enumerate(s.get("events", [])):
            event_count += 1
            conn.execute(
                """
                INSERT INTO evenement_consommation (
                    id_evenement_consommation, type, start_, end_, delta_mw,
                    delta_percent, id_region, id_scenario_phase3
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{s['id']}#{i}", event.get("type"), event.get("start"),
                    event.get("end"), event.get("delta_mw"), event.get("delta_percent"),
                    event["region_id"], s["id"],
                ),
            )

    return {
        "scenario_phase3": len(raw.get("scenarios", [])),
        "evenement_consommation": event_count,
    }


def run_ingestion():
    """Recrée le schéma depuis mcd2.sql puis recharge tous les JSON de fastapi/data.
    Idempotent : rejouable sans accumulation de doublons."""
    conn = get_connection()
    try:
        reset_schema(conn)
        summary = {}
        summary.update(ingest_data_json(conn))
        summary.update(ingest_nuclear_temporal_params(conn))
        summary.update(ingest_consommation_reference(conn))
        summary.update(ingest_etat_initial(conn))
        summary.update(ingest_production_non_pilotable(conn))
        summary.update(ingest_scenarios_phase3(conn))
        conn.commit()
        return summary
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


router = APIRouter(prefix="/db", dependencies=[Depends(check_password)])


@router.post("/ingest")
def ingest():
    summary = run_ingestion()
    return {"message": "Ingestion terminée", "lignes_inserees": summary}
