CREATE TABLE region(
   id VARCHAR(50),
   insee_code VARCHAR(50),
   name VARCHAR(50),
   latitude DECIMAL(15,2),
   longitude DECIMAL(15,2),
   population_2023 INT,
   annual_consumption_twh2024 DECIMAL(15,2),
   annual_consumption_mw_2024 DECIMAL(15,2),
   illustrative_peak_consumption_mw DECIMAL(15,2),
   connected_to_continental_grid LOGICAL,
   data_notes_population VARCHAR(250),
   data_notes_illustrative_peak VARCHAR(250),
   data_notes_consumption VARCHAR(250),
   PRIMARY KEY(id)
);

CREATE TABLE filiere(
   code_filiere VARCHAR(50),
   libelle_filiere VARCHAR(50),
   PRIMARY KEY(code_filiere)
);

-- Remplace l'ancien couple dim_temps/fait_consommation (profil de référence
-- synthétique) : consommation électrique réelle par région, plus solaire/éolien
-- (seule production "non pilotable" utilisée par le calcul du besoin résiduel),
-- ingérée manuellement par plage de dates depuis eco2mix-regional-tr.csv (RTE).
-- Colonnes non retenues car hors périmètre "consommation électrique" ou non
-- consommées par aucun endpoint : thermique/nucléaire/hydraulique/pompage/
-- bioénergies/échanges physiques/stockage batterie, et les taux TCO/TCH.
CREATE TABLE IF NOT EXISTS mesure_eco2mix_regionale(
   id_region VARCHAR(50),
   date_heure TIMESTAMP,
   nature VARCHAR(50),
   consommation_mw DECIMAL(15,2),
   eolien_mw DECIMAL(15,2),
   solaire_mw DECIMAL(15,2),
   PRIMARY KEY(id_region, date_heure),
   FOREIGN KEY(id_region) REFERENCES region(id)
);

CREATE TABLE scenario(
   id INT,
   description VARCHAR(250),
   expected_result VARCHAR(250),
   additionnal_demand_mw DECIMAL(15,2),
   id_1 VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES region(id)
);

CREATE TABLE centrale(
   id VARCHAR(50),
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
   id_1 VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES region(id)
);

CREATE TABLE reacteur(
   id_reacteur VARCHAR(50),
   name VARCHAR(50),
   installed_power_mw DECIMAL(15,2),
   minimum_design_power_mw DECIMAL(15,2),
   status VARCHAR(50),
   industrial_commisionning_date DATE,
   data_kind VARCHAR(50),
   id VARCHAR(50) NOT NULL,
   PRIMARY KEY(id_reacteur),
   FOREIGN KEY(id) REFERENCES centrale(id)
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
   id_1 VARCHAR(50) NOT NULL,
   id_2 VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES centrale(id),
   FOREIGN KEY(id_2) REFERENCES centrale(id)
);

CREATE TABLE scenario_override(
   id INT,
   initial_output_mw DECIMAL(15,2),
   soft_upper_bound_mw DECIMAL(15,2),
   id_1 VARCHAR(50) NOT NULL,
   id_2 INT NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES centrale(id),
   FOREIGN KEY(id_2) REFERENCES scenario(id)
);

CREATE TABLE capacitee_instalee_non_pilotable(
   id INT,
   capacitee_mw DECIMAL(15,2),
   id_1 VARCHAR(50) NOT NULL,
   code_filiere VARCHAR(50) NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_1) REFERENCES region(id),
   FOREIGN KEY(code_filiere) REFERENCES filiere(code_filiere)
);

CREATE TABLE accessible_via(
   id VARCHAR(50),
   id_1 VARCHAR(50),
   PRIMARY KEY(id, id_1),
   FOREIGN KEY(id) REFERENCES centrale(id),
   FOREIGN KEY(id_1) REFERENCES region(id)
);

CREATE TABLE route(
   id INT,
   chemin VARCHAR(150),
   methode VARCHAR(10),
   fichier_source VARCHAR(50),
   description VARCHAR(250),
   authentification_requise LOGICAL,
   PRIMARY KEY(id)
);

CREATE TABLE parametre_route(
   id INT,
   nom VARCHAR(50),
   emplacement VARCHAR(10),
   type VARCHAR(30),
   requis LOGICAL,
   valeur_defaut VARCHAR(50),
   id_route INT NOT NULL,
   PRIMARY KEY(id),
   FOREIGN KEY(id_route) REFERENCES route(id)
);
