-- ============================================================
-- Smart City Platform — Neo-Sousse 2030
-- Schema: PostgreSQL + TimescaleDB (3NF normalized)
-- ============================================================

-- Enable TimescaleDB extension (bonus)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── 1. Zones ──────────────────────────────────────────────────────────────────
CREATE TABLE zones (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(100)   NOT NULL UNIQUE,
    surface_km2     DECIMAL(8,2),
    population      INTEGER,
    latitude        DECIMAL(9,6),
    longitude       DECIMAL(9,6),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ── 2. Citoyens ───────────────────────────────────────────────────────────────
CREATE TABLE citoyens (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(100)   NOT NULL,
    email           VARCHAR(150)   UNIQUE,
    score_ecolo     INTEGER        NOT NULL DEFAULT 50 CHECK (score_ecolo BETWEEN 0 AND 100),
    zone_id         INTEGER        REFERENCES zones(id) ON DELETE SET NULL,
    date_inscription TIMESTAMP     DEFAULT NOW()
);

-- ── 3. Capteurs ───────────────────────────────────────────────────────────────
CREATE TABLE capteurs (
    id              VARCHAR(20)    PRIMARY KEY,        -- e.g. 'C-001'
    nom             VARCHAR(100)   NOT NULL,
    type            VARCHAR(50)    NOT NULL,            -- 'pollution', 'temperature', 'humidite', 'bruit'
    statut          VARCHAR(20)    NOT NULL DEFAULT 'INACTIF'
                        CHECK (statut IN ('INACTIF','ACTIF','SIGNALÉ','EN_MAINTENANCE','HORS_SERVICE')),
    zone_id         INTEGER        REFERENCES zones(id),
    taux_erreur     DECIMAL(5,4)   DEFAULT 0.0 CHECK (taux_erreur BETWEEN 0 AND 1),
    installation_date DATE,
    fabricant       VARCHAR(100),
    modele          VARCHAR(100)
);

-- ── 4. Mesures (TimescaleDB hypertable) ──────────────────────────────────────
CREATE TABLE mesures (
    id              BIGSERIAL,
    capteur_id      VARCHAR(20)    NOT NULL REFERENCES capteurs(id),
    zone_id         INTEGER        REFERENCES zones(id),
    pollution       DECIMAL(8,3),     -- µg/m³
    temperature     DECIMAL(5,2),     -- °C
    humidite        DECIMAL(5,2),     -- %
    bruit           DECIMAL(6,2),     -- dB
    co2_ppm         DECIMAL(8,2),
    timestamp       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    qualite         VARCHAR(20)    CHECK (qualite IN ('bon','moyen','mauvais','dangereux')),
    PRIMARY KEY (id, timestamp)
);

-- Convert mesures to TimescaleDB hypertable (time-series optimization — bonus)
SELECT create_hypertable('mesures', 'timestamp', if_not_exists => TRUE);

-- ── 5. Techniciens ────────────────────────────────────────────────────────────
CREATE TABLE techniciens (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(100)   NOT NULL,
    specialite      VARCHAR(100),
    disponible      BOOLEAN        DEFAULT TRUE,
    zone_id         INTEGER        REFERENCES zones(id)
);

-- ── 6. Interventions ──────────────────────────────────────────────────────────
CREATE TABLE interventions (
    id              SERIAL PRIMARY KEY,
    capteur_id      VARCHAR(20)    REFERENCES capteurs(id),
    tech1_id        INTEGER        REFERENCES techniciens(id),
    tech2_id        INTEGER        REFERENCES techniciens(id),
    statut          VARCHAR(20)    NOT NULL DEFAULT 'DEMANDE'
                        CHECK (statut IN ('DEMANDE','TECH1_ASSIGNÉ','TECH2_VALIDÉ','IA_VALIDÉ','TERMINÉ')),
    ia_validee      BOOLEAN        DEFAULT FALSE,
    ia_commentaire  TEXT,
    date_demande    TIMESTAMP      DEFAULT NOW(),
    date_debut      TIMESTAMP,
    date_fin        TIMESTAMP,
    zone_id         INTEGER        REFERENCES zones(id),
    description     TEXT,
    priorite        INTEGER        DEFAULT 2 CHECK (priorite BETWEEN 1 AND 5)
);

-- ── 7. Véhicules ──────────────────────────────────────────────────────────────
CREATE TABLE vehicules (
    id              VARCHAR(20)    PRIMARY KEY,        -- e.g. 'V-001'
    modele          VARCHAR(100),
    statut          VARCHAR(20)    NOT NULL DEFAULT 'STATIONNÉ'
                        CHECK (statut IN ('STATIONNÉ','EN_ROUTE','EN_PANNE','ARRIVÉ')),
    zone_id         INTEGER        REFERENCES zones(id),
    batterie_pct    DECIMAL(5,2)   CHECK (batterie_pct BETWEEN 0 AND 100),
    vitesse_kmh     DECIMAL(6,2)   DEFAULT 0
);

-- ── 8. Trajets ────────────────────────────────────────────────────────────────
CREATE TABLE trajets (
    trajet_id       SERIAL PRIMARY KEY,
    vehicule_id     VARCHAR(20)    REFERENCES vehicules(id),
    zone_depart_id  INTEGER        REFERENCES zones(id),
    zone_arrivee_id INTEGER        REFERENCES zones(id),
    economie_co2    DECIMAL(8,3),  -- kg CO2 économisés
    distance_km     DECIMAL(8,3),
    duree_min       INTEGER,
    date_debut      TIMESTAMP,
    date_fin        TIMESTAMP,
    statut          VARCHAR(20)    DEFAULT 'EN_COURS'
                        CHECK (statut IN ('EN_COURS','TERMINÉ','ANNULÉ'))
);

-- ── 9. FSM Event Log ─────────────────────────────────────────────────────────
CREATE TABLE fsm_events (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(20)    NOT NULL,  -- 'capteur' | 'intervention' | 'vehicule'
    entity_id       VARCHAR(50)    NOT NULL,
    from_state      VARCHAR(50)    NOT NULL,
    event           VARCHAR(100)   NOT NULL,
    to_state        VARCHAR(50)    NOT NULL,
    triggered_by    VARCHAR(100),             -- user id or 'system' or 'ia'
    timestamp       TIMESTAMPTZ    DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX idx_mesures_capteur_ts   ON mesures(capteur_id, timestamp DESC);
CREATE INDEX idx_mesures_zone_ts      ON mesures(zone_id, timestamp DESC);
CREATE INDEX idx_mesures_pollution    ON mesures(pollution) WHERE pollution IS NOT NULL;
CREATE INDEX idx_capteurs_statut      ON capteurs(statut);
CREATE INDEX idx_capteurs_zone        ON capteurs(zone_id);
CREATE INDEX idx_interventions_statut ON interventions(statut);
CREATE INDEX idx_fsm_events_entity    ON fsm_events(entity_type, entity_id, timestamp DESC);
CREATE INDEX idx_citoyens_score       ON citoyens(score_ecolo DESC);

-- ── TimescaleDB continuous aggregate (bonus) ──────────────────────────────────
-- Hourly pollution averages per zone — auto-refreshed
CREATE MATERIALIZED VIEW pollution_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    zone_id,
    AVG(pollution)    AS pollution_avg,
    MAX(pollution)    AS pollution_max,
    MIN(pollution)    AS pollution_min,
    COUNT(*)          AS nb_mesures
FROM mesures
WHERE pollution IS NOT NULL
GROUP BY bucket, zone_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('pollution_hourly',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ── Example queries matching the project requirements ─────────────────────────
-- "Affiche les 5 zones les plus polluées"
-- SELECT zone_id, AVG(pollution) FROM mesures GROUP BY zone_id ORDER BY AVG(pollution) DESC LIMIT 5;

-- "Combien de capteurs sont hors service ?"
-- SELECT COUNT(*) FROM capteurs WHERE statut = 'HORS_SERVICE';

-- "Quels citoyens ont un score écologique > 80 ?"
-- SELECT nom, score_ecolo FROM citoyens WHERE score_ecolo > 80 ORDER BY score_ecolo DESC;

-- "Donne-moi le trajet le plus économique en CO2"
-- SELECT trajet_id, economie_co2 FROM trajets ORDER BY economie_co2 ASC LIMIT 1;

-- "Quelles interventions sont en cours ?"
-- SELECT id, statut, date_debut, zone_id FROM interventions WHERE statut != 'TERMINÉ';
