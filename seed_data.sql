-- ============================================================
-- Smart City Platform -- Neo-Sousse 2030
-- Seed data: 1000+ records, 90-day time series
-- Compatible: PostgreSQL standard (no TimescaleDB)
-- ============================================================
-- Usage:
--   psql -U postgres -f seed_data_fixed.sql
-- ============================================================

-- ============================================================
-- SECTION 0 : Safe database recreation
-- ============================================================

-- Connect to postgres first, then drop/recreate smart_city
\c postgres

SELECT pg_terminate_backend(pid)
FROM   pg_stat_activity
WHERE  datname = 'smart_city'
  AND  pid <> pg_backend_pid();

DROP DATABASE IF EXISTS smart_city;

CREATE DATABASE smart_city
    ENCODING    'UTF8'
    LC_COLLATE  'en_US.UTF-8'
    LC_CTYPE    'en_US.UTF-8'
    TEMPLATE    template0;

\c smart_city

-- ============================================================
-- SECTION 1 : Schema (tables, FK constraints, triggers)
-- ============================================================

-- ── zones ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zones (
    id           SERIAL PRIMARY KEY,
    nom          TEXT        NOT NULL,
    surface_km2  NUMERIC(8,2),
    population   INTEGER,
    latitude     NUMERIC(9,6),
    longitude    NUMERIC(9,6)
);

-- ── citoyens ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS citoyens (
    id                SERIAL PRIMARY KEY,
    nom               TEXT        NOT NULL,
    email             TEXT        UNIQUE NOT NULL,
    score_ecolo       INTEGER     CHECK (score_ecolo BETWEEN 0 AND 100),
    zone_id           INTEGER     REFERENCES zones(id),
    date_inscription  TIMESTAMPTZ DEFAULT NOW()
);

-- ── techniciens ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS techniciens (
    id           SERIAL PRIMARY KEY,
    nom          TEXT    NOT NULL,
    specialite   TEXT,
    disponible   BOOLEAN DEFAULT TRUE,
    zone_id      INTEGER REFERENCES zones(id)
);

-- ── capteurs ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS capteurs (
    id                TEXT PRIMARY KEY,
    nom               TEXT NOT NULL,
    type              TEXT CHECK (type IN ('pollution','temperature','humidite','bruit','co2')),
    statut            TEXT CHECK (statut IN ('ACTIF','INACTIF','SIGNALE','EN_MAINTENANCE','HORS_SERVICE')),
    zone_id           INTEGER REFERENCES zones(id),
    taux_erreur       NUMERIC(6,4),
    installation_date DATE,
    fabricant         TEXT,
    modele            TEXT
);

-- ── vehicules ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicules (
    id            TEXT PRIMARY KEY,
    modele        TEXT,
    statut        TEXT CHECK (statut IN ('STATIONNE','EN_ROUTE','ARRIVE','EN_PANNE')),
    zone_id       INTEGER REFERENCES zones(id),
    batterie_pct  NUMERIC(5,2),
    vitesse_kmh   NUMERIC(5,2)
);

-- ── trajets ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trajets (
    trajet_id       SERIAL PRIMARY KEY,
    vehicule_id     TEXT        REFERENCES vehicules(id),
    zone_depart_id  INTEGER     REFERENCES zones(id),
    zone_arrivee_id INTEGER     REFERENCES zones(id),
    economie_co2    NUMERIC(8,3),
    distance_km     NUMERIC(8,3),
    duree_min       INTEGER,
    date_debut      TIMESTAMPTZ,
    date_fin        TIMESTAMPTZ,
    statut          TEXT CHECK (statut IN ('EN_COURS','TERMINE','ANNULE'))
);

-- ── interventions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interventions (
    id              SERIAL PRIMARY KEY,
    capteur_id      TEXT        REFERENCES capteurs(id),
    tech1_id        INTEGER     REFERENCES techniciens(id),
    tech2_id        INTEGER     REFERENCES techniciens(id),
    statut          TEXT        CHECK (statut IN (
                                    'DEMANDE','TECH_ASSIGN','TECH_VALID',
                                    'IA_VALID','TERMINE'
                                )),
    ia_validee      BOOLEAN     DEFAULT FALSE,
    ia_commentaire  TEXT,
    date_demande    TIMESTAMPTZ,
    date_debut      TIMESTAMPTZ,
    date_fin        TIMESTAMPTZ,
    zone_id         INTEGER     REFERENCES zones(id),
    description     TEXT,
    priorite        INTEGER     CHECK (priorite BETWEEN 1 AND 5)
);

-- ── mesures (time series) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS mesures (
    id           BIGSERIAL PRIMARY KEY,
    capteur_id   TEXT        REFERENCES capteurs(id),
    zone_id      INTEGER     REFERENCES zones(id),
    pollution    NUMERIC(10,3),
    temperature  NUMERIC(6,2),
    humidite     NUMERIC(6,2),
    bruit        NUMERIC(6,2),
    co2_ppm      NUMERIC(8,2),
    timestamp    TIMESTAMPTZ NOT NULL,
    qualite      TEXT        CHECK (qualite IN ('bon','moyen','mauvais','dangereux'))
);

-- ── fsm_events ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fsm_events (
    id           BIGSERIAL PRIMARY KEY,
    entity_type  TEXT        NOT NULL,
    entity_id    TEXT        NOT NULL,
    from_state   TEXT,
    event        TEXT,
    to_state     TEXT,
    triggered_by TEXT,
    timestamp    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECTION 2 : Disable FK triggers for bulk insert
-- ============================================================
SET session_replication_role = replica;

-- ============================================================
-- SECTION 3 : Truncate all tables (restart sequences)
-- ============================================================
TRUNCATE TABLE fsm_events, interventions, trajets, mesures,
               vehicules, capteurs, techniciens, citoyens, zones
RESTART IDENTITY CASCADE;

-- ============================================================
-- SECTION 4 : ZONES (8 records)
-- ============================================================
INSERT INTO zones (nom, surface_km2, population, latitude, longitude) VALUES
    ('Zone A',  8.50,  52000, 35.8200, 10.6300),
    ('Zone B',  5.20,  31000, 35.8380, 10.6520),
    ('Zone C', 12.10,  78000, 35.8560, 10.6740),
    ('Zone D',  3.90,  18000, 35.8740, 10.6960),
    ('Zone E',  9.70,  64000, 35.8920, 10.7180),
    ('Zone F',  6.30,  42000, 35.9100, 10.7400),
    ('Zone G', 14.80,  89000, 35.9280, 10.7620),
    ('Zone H',  4.60,  27000, 35.9460, 10.7840);
-- Total: 8 zones

-- ============================================================
-- SECTION 5 : CITOYENS (200 records)
-- ============================================================
INSERT INTO citoyens (nom, email, score_ecolo, zone_id, date_inscription)
SELECT
    (ARRAY['Ahmed','Fatima','Mohamed','Amira','Yassine','Nour','Karim',
            'Leila','Omar','Sana','Ali','Rim','Mehdi','Asma','Bilel',
            'Ines','Wael','Donia','Rami','Hela'])[1 + (i % 20)]
    || ' ' ||
    (ARRAY['Ben Ali','Trabelsi','Hamdi','Mansouri','Gharbi','Khelifi',
            'Ayari','Mbarki','Jebali','Saidani','Chaabane','Ferchichi',
            'Belhaj','Zghal','Amamou'])[1 + (i % 15)]        AS nom,

    'citoyen' || i || '@neosousse.tn'                        AS email,

    GREATEST(0, LEAST(100,
        (50 + (i * 7 + i * i * 3) % 51 - 25)::INTEGER
    ))                                                         AS score_ecolo,

    (i % 8) + 1                                               AS zone_id,

    NOW() - (INTERVAL '730 days' * random() + INTERVAL '30 days')
FROM generate_series(1, 200) AS s(i);
-- Total: 200 citoyens

-- ============================================================
-- SECTION 6 : TECHNICIENS (20 records)
-- ============================================================
INSERT INTO techniciens (nom, specialite, disponible, zone_id) VALUES
    ('Tarek Mansouri',    'Electronique',  TRUE,  1),
    ('Sirine Khelifi',    'Mecanique',     TRUE,  2),
    ('Bilel Hamdi',       'Reseau IoT',    FALSE, 3),
    ('Marwa Gharbi',      'Logiciel',      TRUE,  4),
    ('Sami Trabelsi',     'Hydraulique',   TRUE,  5),
    ('Rania Ben Ali',     'Capteurs IoT',  TRUE,  6),
    ('Fares Jebali',      'Electronique',  FALSE, 7),
    ('Nadia Ayari',       'Mecanique',     TRUE,  8),
    ('Khalil Mbarki',     'Reseau IoT',    TRUE,  1),
    ('Amina Saidani',     'Logiciel',      TRUE,  2),
    ('Youssef Chaabane',  'Hydraulique',   FALSE, 3),
    ('Imen Ferchichi',    'Capteurs IoT',  TRUE,  4),
    ('Adel Belhaj',       'Electronique',  TRUE,  5),
    ('Cyrine Zghal',      'Mecanique',     TRUE,  6),
    ('Hassen Amamou',     'Reseau IoT',    FALSE, 7),
    ('Salma Turki',       'Logiciel',      TRUE,  8),
    ('Mondher Dridi',     'Hydraulique',   TRUE,  1),
    ('Farah Nasri',       'Capteurs IoT',  TRUE,  2),
    ('Wassim Boussaid',   'Electronique',  FALSE, 3),
    ('Emna Oueslati',     'Mecanique',     TRUE,  4);
-- Total: 20 techniciens

-- ============================================================
-- SECTION 7 : CAPTEURS (150 records)
-- ============================================================
INSERT INTO capteurs (id, nom, type, statut, zone_id, taux_erreur, installation_date, fabricant, modele)
SELECT
    'C-' || LPAD(i::TEXT, 3, '0')                            AS id,

    'Capteur ' ||
    (ARRAY['Pollution','Temperature','Humidite','Bruit','CO2'])[1 + (i % 5)]
    || ' ' || i                                               AS nom,

    (ARRAY['pollution','temperature','humidite','bruit','co2'])[1 + (i % 5)]
                                                              AS type,

    -- Status: 70% ACTIF, rest distributed
    -- Normalized: no accented characters
    CASE
        WHEN i % 10 IN (0)          THEN 'HORS_SERVICE'
        WHEN i % 10 IN (1, 2)       THEN 'SIGNALE'
        WHEN i % 10 IN (3)          THEN 'EN_MAINTENANCE'
        WHEN i % 10 IN (4)          THEN 'INACTIF'
        ELSE                             'ACTIF'
    END                                                       AS statut,

    (i % 8) + 1                                               AS zone_id,

    CASE
        WHEN i % 10 = 0  THEN ROUND((0.30 + random() * 0.30)::NUMERIC, 4)
        WHEN i % 10 IN (1,2) THEN ROUND((0.10 + random() * 0.20)::NUMERIC, 4)
        ELSE              ROUND((random() * 0.05)::NUMERIC, 4)
    END                                                       AS taux_erreur,

    (NOW() - (INTERVAL '1095 days' * random() + INTERVAL '30 days'))::DATE
                                                              AS installation_date,

    (ARRAY['SensorTech','UrbanSense','CityMonitor','SmartNode','EcoSense'])[1 + (i % 5)]
                                                              AS fabricant,

    'M' || (100 + (i % 900))::TEXT                           AS modele

FROM generate_series(1, 150) AS s(i);
-- Total: 150 capteurs

-- ============================================================
-- SECTION 8 : VEHICULES (50 records)
-- ============================================================
INSERT INTO vehicules (id, modele, statut, zone_id, batterie_pct, vitesse_kmh)
SELECT
    'V-' || LPAD(i::TEXT, 3, '0')                            AS id,

    (ARRAY['Tesla Model 3','BYD Han','NIO ES6','VW ID.4',
            'Rivian R1T','Hyundai Ioniq 6','BMW iX3',
            'Renault Megane E-Tech','Peugeot e-208'])[1 + (i % 9)]
                                                              AS modele,

    -- Normalized status values (no accented chars)
    CASE
        WHEN i % 10 IN (0,1)   THEN 'EN_PANNE'
        WHEN i % 10 IN (2,3,4) THEN 'EN_ROUTE'
        WHEN i % 10 = 5        THEN 'ARRIVE'
        ELSE                        'STATIONNE'
    END                                                       AS statut,

    (i % 8) + 1                                               AS zone_id,

    ROUND((20 + random() * 80)::NUMERIC, 2)                  AS batterie_pct,

    CASE WHEN i % 10 IN (2,3,4)
        THEN ROUND((30 + random() * 60)::NUMERIC, 2)
        ELSE 0
    END                                                       AS vitesse_kmh

FROM generate_series(1, 50) AS s(i);
-- Total: 50 vehicules

-- ============================================================
-- SECTION 9 : TRAJETS (300 records)
-- ============================================================
INSERT INTO trajets (vehicule_id, zone_depart_id, zone_arrivee_id,
                     economie_co2, distance_km, duree_min,
                     date_debut, date_fin, statut)
SELECT
    'V-' || LPAD((1 + (i % 50))::TEXT, 3, '0')               AS vehicule_id,

    (i % 8) + 1                                               AS zone_depart_id,
    ((i + 3) % 8) + 1                                         AS zone_arrivee_id,

    ROUND((2 + random() * 8)::NUMERIC, 3)                    AS economie_co2,
    ROUND((2 + random() * 43)::NUMERIC, 3)                   AS distance_km,
    (10 + (i * 7) % 120)::INTEGER                            AS duree_min,

    NOW() - (INTERVAL '90 days' * random())                  AS date_debut,
    NOW() - (INTERVAL '1 day'   * random())                  AS date_fin,

    -- Normalized status values
    CASE
        WHEN i % 8 = 0 THEN 'ANNULE'
        WHEN i % 8 = 1 THEN 'EN_COURS'
        ELSE                'TERMINE'
    END                                                       AS statut

FROM generate_series(1, 300) AS s(i);
-- Total: 300 trajets

-- ============================================================
-- SECTION 10 : INTERVENTIONS (100 records)
-- ============================================================
-- Status values normalized:
--   TECH1_ASSIGNÉ -> TECH_ASSIGN
--   TECH2_VALIDÉ  -> TECH_VALID
--   IA_VALIDÉ     -> IA_VALID
--   TERMINÉ       -> TERMINE
-- ============================================================
INSERT INTO interventions (capteur_id, tech1_id, tech2_id, statut,
                           ia_validee, ia_commentaire,
                           date_demande, date_debut, date_fin,
                           zone_id, description, priorite)
SELECT
    'C-' || LPAD((1 + (i % 150))::TEXT, 3, '0')             AS capteur_id,
    (1 + (i % 20))::INTEGER                                  AS tech1_id,
    (1 + ((i + 7) % 20))::INTEGER                            AS tech2_id,

    -- Normalized: no TECH1_/TECH2_ prefix, no accented chars
    (ARRAY['DEMANDE','TECH_ASSIGN','TECH_VALID','IA_VALID','TERMINE',
            'TERMINE','TERMINE'])[1 + (i % 7)]               AS statut,

    (i % 7) >= 4                                              AS ia_validee,

    CASE WHEN (i % 7) >= 4
        THEN 'Validation IA automatique - anomalie confirmee, intervention requise.'
        ELSE NULL
    END                                                       AS ia_commentaire,

    NOW() - (INTERVAL '60 days' * random())                  AS date_demande,

    CASE WHEN (i % 7) >= 1
        THEN NOW() - (INTERVAL '50 days' * random())
        ELSE NULL
    END                                                       AS date_debut,

    CASE WHEN (i % 7) = 6
        THEN NOW() - (INTERVAL '1 day' * random())
        ELSE NULL
    END                                                       AS date_fin,

    (i % 8) + 1                                               AS zone_id,

    'Anomalie detectee sur capteur C-' ||
    LPAD((1 + (i % 150))::TEXT, 3, '0')                      AS description,

    (1 + (i % 5))::INTEGER                                   AS priorite

FROM generate_series(1, 100) AS s(i);
-- Total: 100 interventions

-- ============================================================
-- SECTION 11 : MESURES -- TIME SERIES
-- ============================================================
-- Strategy: 90-day history, one reading every 15 min
-- for each ACTIF or SIGNALE sensor (~105 capteurs)
-- ~105 x 90 x 24 x 4 = ~907,200 records
-- ============================================================

-- 11a. Readings for ACTIF sensors (90 days x 15 min)
INSERT INTO mesures (capteur_id, zone_id, pollution, temperature,
                     humidite, bruit, co2_ppm, timestamp, qualite)
SELECT
    c.id                                                        AS capteur_id,
    c.zone_id                                                   AS zone_id,

    -- Pollution with daily pattern + zone-dependent noise
    GREATEST(0, ROUND((
        (10 + c.zone_id * 6.5)
        * CASE
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 7 AND 9   THEN 1.40
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 17 AND 19 THEN 1.35
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 0  AND 5  THEN 0.55
            ELSE 1.00
          END
        * CASE
            WHEN EXTRACT(DOW FROM ts.t) IN (0, 6) THEN 0.70
            ELSE 1.00
          END
        + (random() * 2 - 1) * (10 + c.zone_id * 6.5) * 0.15
        + CASE WHEN random() < 0.003
               THEN (10 + c.zone_id * 6.5) * 2.5
               ELSE 0
          END
    )::NUMERIC, 3))                                             AS pollution,

    -- Temperature: base 22C + daily variation +/- 5C + noise
    ROUND((
        22.0 + c.zone_id * 0.3
        + 5 * SIN(2 * PI() * EXTRACT(HOUR FROM ts.t) / 24.0 - PI())
        + (random() * 2 - 1) * 2.0
    )::NUMERIC, 2)                                              AS temperature,

    -- Humidity: between 35% and 85%
    ROUND((60 + (random() * 2 - 1) * 25)::NUMERIC, 2)          AS humidite,

    -- Noise: louder during rush hours
    ROUND((
        50
        + CASE
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 7 AND 9   THEN 12
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 17 AND 19 THEN 10
            WHEN EXTRACT(HOUR FROM ts.t) BETWEEN 0  AND 5  THEN -8
            ELSE 0
          END
        + (random() * 2 - 1) * 8
    )::NUMERIC, 2)                                              AS bruit,

    -- CO2 ppm: atmospheric baseline + local pollution
    ROUND((415 + c.zone_id * 3 + (random() * 2 - 1) * 20)::NUMERIC, 2)
                                                                AS co2_ppm,

    ts.t                                                        AS timestamp,

    -- Quality derived from pollution level
    CASE
        WHEN (10 + c.zone_id * 6.5) * 1.4 * 1.0 + 30 < 25  THEN 'bon'
        WHEN (10 + c.zone_id * 6.5) < 35                     THEN 'moyen'
        WHEN (10 + c.zone_id * 6.5) < 70                     THEN 'mauvais'
        ELSE                                                       'dangereux'
    END                                                         AS qualite

FROM capteurs c
CROSS JOIN generate_series(
    NOW() - INTERVAL '90 days',
    NOW(),
    INTERVAL '15 minutes'
) AS ts(t)
WHERE c.statut = 'ACTIF';

-- 11b. Readings for SIGNALE sensors (partial data, 50% timestamps)
INSERT INTO mesures (capteur_id, zone_id, pollution, temperature,
                     humidite, bruit, co2_ppm, timestamp, qualite)
SELECT
    c.id,
    c.zone_id,
    -- Flagged sensors: abnormally high pollution
    GREATEST(0, ROUND((
        (15 + c.zone_id * 8)
        * (1 + random() * 0.5)
        + (random() * 2 - 1) * 15
    )::NUMERIC, 3))                                             AS pollution,
    ROUND((22 + (random() * 2 - 1) * 4)::NUMERIC, 2),
    ROUND((60 + (random() * 2 - 1) * 20)::NUMERIC, 2),
    ROUND((58 + (random() * 2 - 1) * 10)::NUMERIC, 2),
    ROUND((420 + (random() * 2 - 1) * 25)::NUMERIC, 2),
    ts.t,
    CASE
        WHEN (15 + c.zone_id * 8) < 25  THEN 'bon'
        WHEN (15 + c.zone_id * 8) < 50  THEN 'moyen'
        WHEN (15 + c.zone_id * 8) < 100 THEN 'mauvais'
        ELSE                                  'dangereux'
    END
FROM capteurs c
CROSS JOIN generate_series(
    NOW() - INTERVAL '30 days',
    NOW(),
    INTERVAL '30 minutes'
) AS ts(t)
WHERE c.statut = 'SIGNALE'
  AND random() > 0.50;

-- 11c. Historical readings for HORS_SERVICE sensors
--      (data from 7 days before failure)
INSERT INTO mesures (capteur_id, zone_id, pollution, temperature,
                     humidite, bruit, co2_ppm, timestamp, qualite)
SELECT
    c.id,
    c.zone_id,
    GREATEST(0, ROUND((
        (20 + c.zone_id * 9) * (1 + random() * 0.8) + (random() * 2 - 1) * 20
    )::NUMERIC, 3))                                             AS pollution,
    ROUND((23 + (random() * 2 - 1) * 5)::NUMERIC, 2),
    ROUND((55 + (random() * 2 - 1) * 25)::NUMERIC, 2),
    ROUND((60 + (random() * 2 - 1) * 15)::NUMERIC, 2),
    ROUND((425 + (random() * 2 - 1) * 30)::NUMERIC, 2),
    ts.t,
    'dangereux'                                                 AS qualite
FROM capteurs c
CROSS JOIN generate_series(
    NOW() - INTERVAL '37 days',
    NOW() - INTERVAL '30 days',
    INTERVAL '1 hour'
) AS ts(t)
WHERE c.statut = 'HORS_SERVICE';

-- ============================================================
-- SECTION 12 : FSM_EVENTS (500 records)
-- ============================================================

-- 12a. Sensor lifecycle transitions
INSERT INTO fsm_events (entity_type, entity_id, from_state, event, to_state, triggered_by, timestamp)
SELECT
    'capteur'                                                   AS entity_type,
    'C-' || LPAD(i::TEXT, 3, '0')                             AS entity_id,
    unnested.from_state,
    unnested.event,
    unnested.to_state,
    (ARRAY['system','technicien','ia','system','technicien'])[1 + (i % 5)]
                                                                AS triggered_by,
    NOW() - (INTERVAL '200 days' * random())                  AS timestamp
FROM generate_series(1, 40) AS s(i)
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('INACTIF',        'installation',       'ACTIF'),
        ('ACTIF',          'detection_anomalie',  'SIGNALE'),
        ('SIGNALE',        'prise_en_charge',    'EN_MAINTENANCE'),
        ('EN_MAINTENANCE', 'reparation',          'ACTIF')
    ) AS t(from_state, event, to_state)
) AS unnested;

-- 12b. Intervention workflow transitions
--      Normalized: TECH1_ASSIGNE -> TECH_ASSIGN, etc.
INSERT INTO fsm_events (entity_type, entity_id, from_state, event, to_state, triggered_by, timestamp)
SELECT
    'intervention'                                              AS entity_type,
    'INT-' || LPAD(i::TEXT, 3, '0')                           AS entity_id,
    unnested.from_state,
    unnested.event,
    unnested.to_state,
    (ARRAY['technicien','technicien','ia','system'])[1 + (i % 4)],
    NOW() - (INTERVAL '60 days' * random())
FROM generate_series(1, 30) AS s(i)
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('DEMANDE',      'assigner_tech',  'TECH_ASSIGN'),
        ('TECH_ASSIGN',  'valider_tech',   'TECH_VALID'),
        ('TECH_VALID',   'valider_ia',     'IA_VALID'),
        ('IA_VALID',     'terminer',       'TERMINE')
    ) AS t(from_state, event, to_state)
) AS unnested;

-- 12c. Vehicle state transitions
INSERT INTO fsm_events (entity_type, entity_id, from_state, event, to_state, triggered_by, timestamp)
SELECT
    'vehicule'                                                  AS entity_type,
    'V-' || LPAD(i::TEXT, 3, '0')                             AS entity_id,
    unnested.from_state,
    unnested.event,
    unnested.to_state,
    'system',
    NOW() - (INTERVAL '90 days' * random())
FROM generate_series(1, 30) AS s(i)
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('STATIONNE', 'depart',   'EN_ROUTE'),
        ('EN_ROUTE',  'arrivee',  'ARRIVE'),
        ('ARRIVE',    'garer',    'STATIONNE')
    ) AS t(from_state, event, to_state)
) AS unnested;

-- ============================================================
-- SECTION 13 : Re-enable FK triggers
-- ============================================================
SET session_replication_role = DEFAULT;

COMMIT;

-- ============================================================
-- SECTION 14 : Performance indexes
-- ============================================================

-- mesures: most queries filter by timestamp and capteur_id
CREATE INDEX IF NOT EXISTS idx_mesures_timestamp
    ON mesures (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_mesures_capteur_ts
    ON mesures (capteur_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_mesures_zone_ts
    ON mesures (zone_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_mesures_qualite
    ON mesures (qualite);

-- fsm_events: lookups by entity
CREATE INDEX IF NOT EXISTS idx_fsm_entity
    ON fsm_events (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_fsm_timestamp
    ON fsm_events (timestamp DESC);

-- interventions: status-based queries
CREATE INDEX IF NOT EXISTS idx_interventions_statut
    ON interventions (statut);

CREATE INDEX IF NOT EXISTS idx_interventions_zone
    ON interventions (zone_id);

-- capteurs: status-based queries
CREATE INDEX IF NOT EXISTS idx_capteurs_statut
    ON capteurs (statut);

-- trajets: date range queries
CREATE INDEX IF NOT EXISTS idx_trajets_date_debut
    ON trajets (date_debut DESC);

-- ============================================================
-- SECTION 15 : Utility trigger — updated_at on interventions
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.date_fin := CASE
        WHEN NEW.statut = 'TERMINE' AND OLD.statut <> 'TERMINE'
        THEN NOW()
        ELSE NEW.date_fin
    END;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_interventions_updated ON interventions;
CREATE TRIGGER trg_interventions_updated
    BEFORE UPDATE ON interventions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- SECTION 16 : Views
-- ============================================================

-- View: Pollution analysis per zone (last 7 days)
CREATE OR REPLACE VIEW v_pollution_par_zone AS
SELECT
    z.nom                                         AS zone,
    z.id                                          AS zone_id,
    ROUND(AVG(m.pollution)::NUMERIC, 2)           AS pollution_moy,
    ROUND(MAX(m.pollution)::NUMERIC, 2)           AS pollution_max,
    ROUND(MIN(m.pollution)::NUMERIC, 2)           AS pollution_min,
    ROUND(STDDEV(m.pollution)::NUMERIC, 2)        AS pollution_stddev,
    COUNT(*)                                      AS nb_mesures,
    MAX(m.timestamp)                              AS derniere_mesure
FROM mesures m
JOIN zones z ON z.id = m.zone_id
WHERE m.timestamp >= NOW() - INTERVAL '7 days'
  AND m.pollution IS NOT NULL
GROUP BY z.id, z.nom;

-- View: Eco score per citizen with zone info
CREATE OR REPLACE VIEW v_eco_scores AS
SELECT
    c.id                                          AS citoyen_id,
    c.nom                                         AS citoyen,
    c.score_ecolo,
    CASE
        WHEN c.score_ecolo >= 80 THEN 'excellent'
        WHEN c.score_ecolo >= 60 THEN 'bon'
        WHEN c.score_ecolo >= 40 THEN 'moyen'
        ELSE                          'faible'
    END                                           AS categorie,
    z.nom                                         AS zone,
    c.date_inscription
FROM citoyens c
JOIN zones z ON z.id = c.zone_id;

-- View: Active interventions summary
CREATE OR REPLACE VIEW v_interventions_actives AS
SELECT
    i.id,
    i.statut,
    i.priorite,
    i.date_demande,
    i.date_debut,
    z.nom                                         AS zone,
    cap.nom                                       AS capteur,
    cap.type                                      AS capteur_type,
    t1.nom                                        AS tech1,
    t2.nom                                        AS tech2,
    i.ia_validee,
    EXTRACT(EPOCH FROM (NOW() - i.date_demande))/3600
                                                  AS heures_depuis_demande
FROM interventions i
JOIN zones      z   ON z.id   = i.zone_id
JOIN capteurs   cap ON cap.id = i.capteur_id
LEFT JOIN techniciens t1 ON t1.id = i.tech1_id
LEFT JOIN techniciens t2 ON t2.id = i.tech2_id
WHERE i.statut <> 'TERMINE'
ORDER BY i.priorite DESC, i.date_demande ASC;

-- View: Sensor health dashboard
CREATE OR REPLACE VIEW v_capteurs_sante AS
SELECT
    c.statut,
    COUNT(*)                                      AS nb_capteurs,
    ROUND(AVG(c.taux_erreur)::NUMERIC, 4)         AS taux_erreur_moy,
    z.nom                                         AS zone
FROM capteurs c
JOIN zones z ON z.id = c.zone_id
GROUP BY c.statut, z.id, z.nom
ORDER BY z.nom, c.statut;

-- ============================================================
-- SECTION 17 : Row counts verification
-- ============================================================
SELECT
    'zones'          AS table_name, COUNT(*) AS nb_lignes FROM zones
UNION ALL SELECT 'citoyens',        COUNT(*) FROM citoyens
UNION ALL SELECT 'techniciens',     COUNT(*) FROM techniciens
UNION ALL SELECT 'capteurs',        COUNT(*) FROM capteurs
UNION ALL SELECT 'vehicules',       COUNT(*) FROM vehicules
UNION ALL SELECT 'trajets',         COUNT(*) FROM trajets
UNION ALL SELECT 'interventions',   COUNT(*) FROM interventions
UNION ALL SELECT 'mesures',         COUNT(*) FROM mesures
UNION ALL SELECT 'fsm_events',      COUNT(*) FROM fsm_events
ORDER BY table_name;

-- ============================================================
-- SECTION 18 : Demo queries
-- ============================================================

-- Average hourly pollution by zone -- last 7 days
SELECT
    z.nom                                           AS zone,
    DATE_TRUNC('hour', m.timestamp)                 AS heure,
    ROUND(AVG(m.pollution)::NUMERIC, 2)             AS pollution_moy,
    ROUND(MAX(m.pollution)::NUMERIC, 2)             AS pollution_max,
    COUNT(*)                                        AS nb_mesures
FROM mesures m
JOIN zones z ON z.id = m.zone_id
WHERE m.timestamp >= NOW() - INTERVAL '7 days'
  AND m.pollution IS NOT NULL
GROUP BY z.nom, DATE_TRUNC('hour', m.timestamp)
ORDER BY heure DESC, pollution_moy DESC
LIMIT 20;

-- Top 5 most polluted zones
SELECT z.nom, ROUND(AVG(m.pollution)::NUMERIC, 2) AS pollution_avg
FROM mesures m
JOIN zones z ON z.id = m.zone_id
GROUP BY z.nom
ORDER BY pollution_avg DESC
LIMIT 5;

-- Out-of-service sensor count
SELECT COUNT(*) AS capteurs_hors_service
FROM capteurs WHERE statut = 'HORS_SERVICE';

-- Citizens with eco score > 80
SELECT nom, score_ecolo
FROM citoyens
WHERE score_ecolo > 80
ORDER BY score_ecolo DESC;

-- Most CO2-efficient trip
SELECT trajet_id, economie_co2
FROM trajets
ORDER BY economie_co2 ASC
LIMIT 1;

-- Open interventions
SELECT id, statut, date_demande, zone_id
FROM interventions
WHERE statut <> 'TERMINE'
ORDER BY priorite DESC;

-- Eco score distribution from view
SELECT categorie, COUNT(*) AS nb_citoyens
FROM v_eco_scores
GROUP BY categorie
ORDER BY nb_citoyens DESC;

-- Pollution summary from view
SELECT * FROM v_pollution_par_zone
ORDER BY pollution_moy DESC;
