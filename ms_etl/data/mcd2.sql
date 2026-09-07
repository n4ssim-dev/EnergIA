CREATE TABLE region(
   id_region VARCHAR(50),
   insee_code VARCHAR(50),
   name VARCHAR(50),
   latitude DECIMAL(15,2),
   longitude DECIMAL(15,2),
   population_2023 INT,
   annual_consumption_twh2024 DECIMAL(15,2),
   average_consumption_mw_2024 DECIMAL(15,2),
   illustrative_peak_consumption_mw DECIMAL(15,2),
   connected_to_continental_grid LOGICAL,
   data_notes_population VARCHAR(250),
   data_notes_illustrative_peak VARCHAR(250),
   data_notes_consumption VARCHAR(250),
   PRIMARY KEY(id_region)
);

CREATE TABLE etat_initial_regional(
   id INT,
   consommation_mw DECIMAL(15,2),
   horodatage VARCHAR(50),
   jour_relatif VARCHAR(50),
   id_region VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   UNIQUE(id_region),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);

CREATE TABLE filiere(
   code_filiere VARCHAR(50),
   libelle_filiere VARCHAR(50),
   PRIMARY KEY(code_filiere)
);

CREATE TABLE pas_de_temps(
   horodatage VARCHAR(50),
   step_index INT,
   PRIMARY KEY(horodatage)
);

CREATE TABLE scenario_phase3(
   id_scenario_phase3 VARCHAR(50),
   name VARCHAR(50),
   PRIMARY KEY(id_scenario_phase3)
);

CREATE TABLE evenement_consommation(
   id_evenement_consommation VARCHAR(50),
   type VARCHAR(50),
   start_ VARCHAR(50),
   end_ VARCHAR(50),
   delta_mw DECIMAL(15,2),
   delta_percent DECIMAL(15,2),
   id_region VARCHAR(50) NOT NULL,
   id_scenario_phase3 VARCHAR(50) NOT NULL,
   PRIMARY KEY(id_evenement_consommation),
   FOREIGN KEY(id_region) REFERENCES region(id_region),
   FOREIGN KEY(id_scenario_phase3) REFERENCES scenario_phase3(id_scenario_phase3)
);

CREATE TABLE scenario(
   id INT,
   description VARCHAR(250),
   expected_result VARCHAR(250),
   additionnal_demand_mw DECIMAL(15,2),
   id_region VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);

CREATE TABLE centrale(
   id_centrale VARCHAR(50),
   name VARCHAR(50),
   latitude DECIMAL(15,2),
   longitude DECIMAL(15,2),
   commune VARCHAR(50),
   departement VARCHAR(50),
   reactor_count INT,
   installed_power_mw DECIMAL(15,2),
   available LOGICAL,
   initial_output_mw DECIMAL(15,2),
   initial_load_ratio DECIMAL(15,2),
   soft_upper_bound_mw DECIMAL(15,2),
   soft_upper_bound_ratio DECIMAL(15,2),
   initial_dispatchable_margin_mw DECIMAL(15,2),
   max_ramp_up_mw_15_min DECIMAL(15,2),
   technical_penalty DECIMAL(15,2),
   values_are_simulated LOGICAL,
   initial_output_mw_at_23_45_previous_day DECIMAL(15,2),
   minimum_operating_power_mw DECIMAL(15,2),
   max_ramp_down_mw_per_15min DECIMAL(15,2),
   minimum_power_fallback_used LOGICAL,
   values_are_simulated_except_maximum_power LOGICAL,
   id_region VARCHAR(50) NOT NULL,
   PRIMARY KEY(id_centrale),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);

CREATE TABLE reacteur(
   id_reacteur VARCHAR(50),
   name VARCHAR(50),
   installed_power_mw DECIMAL(15,2),
   minimum_design_power_mw DECIMAL(15,2),
   status VARCHAR(50),
   industrial_commisionning_date DATE,
   data_kind VARCHAR(50),
   id_centrale VARCHAR(50) NOT NULL,
   PRIMARY KEY(id_reacteur),
   FOREIGN KEY(id_centrale) REFERENCES centrale(id_centrale)
);

CREATE TABLE liaison(
   id VARCHAR(50),
   bidirectional LOGICAL,
   distance_km DECIMAL(15,2),
   loss_percent DECIMAL(15,2),
   max_transfer_mw DECIMAL(15,2),
   available LOGICAL,
   topology_is_synthetic LOGICAL,
   capacity_and_loss_are_simulated LOGICAL,
   id_centrale VARCHAR(50) NOT NULL,
   id_centrale_1 VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_centrale) REFERENCES centrale(id_centrale),
   FOREIGN KEY(id_centrale_1) REFERENCES centrale(id_centrale)
);

CREATE TABLE scenario_override(
   id INT,
   initial_output_mw DECIMAL(15,2),
   soft_upper_bound_mw DECIMAL(15,2),
   id_1 INT NOT NULL,
   id_centrale VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES scenario(id),
   FOREIGN KEY(id_centrale) REFERENCES centrale(id_centrale)
);

CREATE TABLE production_non_pilotable(
   id INT,
   production_mw DECIMAL(15,2),
   code_filiere VARCHAR(50) NOT NULL,
   id_region VARCHAR(50) NOT NULL,
   horodatage VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(code_filiere) REFERENCES filiere(code_filiere),
   FOREIGN KEY(id_region) REFERENCES region(id_region),
   FOREIGN KEY(horodatage) REFERENCES pas_de_temps(horodatage)
);

CREATE TABLE capacitee_instalee_non_pilotable(
   id INT,
   capacitee_mw DECIMAL(15,2),
   code_filiere VARCHAR(50) NOT NULL,
   id_region VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(code_filiere) REFERENCES filiere(code_filiere),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);

CREATE TABLE consommation_reference(
   id INT,
   consommation_mw DECIMAL(15,2),
   horodatage VARCHAR(50) NOT NULL,
   id_region VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(horodatage) REFERENCES pas_de_temps(horodatage),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);

CREATE TABLE accessible_via2(
   id_centrale VARCHAR(50),
   id_region VARCHAR(50),
   PRIMARY KEY(id_centrale, id_region),
   FOREIGN KEY(id_centrale) REFERENCES centrale(id_centrale),
   FOREIGN KEY(id_region) REFERENCES region(id_region)
);
