-- Schéma Postgres pour la base analytique ms_predictive (entraînement ML).
-- Miroir de ms_predictive/data/mcd_analytique.sql, ré-exécuté au premier
-- démarrage du volume (docker-entrypoint-initdb.d).

CREATE TABLE dim_regionale (
    id_region VARCHAR(50),
    code_insee INT NOT NULL,
    nom VARCHAR(50) NOT NULL,
    demographie INT,
    part_indus_lourde DECIMAL(5,2),
    PRIMARY KEY (id_region),
    UNIQUE (code_insee),
    UNIQUE (nom)
);

CREATE TABLE dim_meteo (
    id_region VARCHAR(50),
    date_meteo DATE,
    temperature_min DECIMAL(5,2),
    temperature_max DECIMAL(5,2),
    temperature_moy DECIMAL(5,2),
    -- true si la valeur a été interpolée (API météo sans donnée ce jour-là),
    -- pour qu'un futur ingest puisse encore la remplacer par une vraie
    -- mesure sans écraser les lignes réelles déjà présentes.
    est_interpole BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (date_meteo, id_region),
    FOREIGN KEY (id_region) REFERENCES dim_regionale(id_region)
);

CREATE TABLE dim_temps (
    date_heure TIMESTAMP,
    annee INT NOT NULL,
    saison VARCHAR(10) NOT NULL,
    mois INT NOT NULL,
    jour_semaine VARCHAR(10) NOT NULL,
    quart_heure INT NOT NULL,
    est_weekend BOOLEAN NOT NULL,
    est_ferie BOOLEAN NOT NULL,
    PRIMARY KEY (date_heure)
);

CREATE TABLE dim_event (
    id_region VARCHAR(50),
    date_event DATE,
    taux_impact_attendu DECIMAL(4,2) NOT NULL,
    PRIMARY KEY (date_event, id_region),
    FOREIGN KEY (id_region) REFERENCES dim_regionale(id_region)
);

CREATE TABLE fait_consommation (
    id_conso VARCHAR(50),
    consommation_mw DECIMAL(15,2) NOT NULL,
    date_heure TIMESTAMP NOT NULL,
    id_region VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_conso),
    FOREIGN KEY (date_heure) REFERENCES dim_temps(date_heure),
    FOREIGN KEY (id_region) REFERENCES dim_regionale(id_region)
);
