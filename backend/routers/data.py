"""
Routers for: mesures, zones, citoyens, vehicules, trajets
Each exposes simple GET endpoints for the dashboard.
"""
from fastapi import APIRouter, Query
from typing import Optional
from ..db import fetch_all, fetch_one

# ── Mesures ───────────────────────────────────────────────────────────────────

mesures_router = APIRouter(prefix="/mesures", tags=["Mesures"])


@mesures_router.get("")
def list_mesures(
    zone_id:    Optional[int] = Query(None),
    capteur_id: Optional[str] = Query(None),
    limit:      int           = Query(500, le=5000),
):
    conditions, params = [], []
    if zone_id is not None:
        conditions.append("zone_id = %s"); params.append(zone_id)
    if capteur_id:
        conditions.append("capteur_id = %s"); params.append(capteur_id)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    return fetch_all(f"""
        SELECT id, capteur_id, zone_id, pollution, temperature,
               humidite, bruit, co2_ppm, timestamp::text, qualite
        FROM mesures {where}
        ORDER BY timestamp DESC
        LIMIT %s
    """, params)


@mesures_router.get("/pollution-par-zone")
def pollution_par_zone():
    """Average pollution per zone — used by the dashboard bar chart."""
    return fetch_all("""
        SELECT z.nom AS zone, z.id AS zone_id,
               ROUND(AVG(m.pollution)::numeric, 2) AS pollution
        FROM mesures m
        JOIN zones z ON z.id = m.zone_id
        WHERE m.pollution IS NOT NULL
        GROUP BY z.id, z.nom
        ORDER BY pollution DESC
    """)


@mesures_router.get("/serie-temporelle")
def serie_temporelle(zone_id: Optional[int] = Query(None)):
    """Daily average pollution — used by the time-series chart."""
    conditions, params = [], []
    if zone_id is not None:
        conditions.append("zone_id = %s"); params.append(zone_id)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return fetch_all(f"""
        SELECT DATE(timestamp) AS date,
               ROUND(AVG(pollution)::numeric, 2) AS pollution
        FROM mesures {where}
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, params)


# ── Zones ─────────────────────────────────────────────────────────────────────

zones_router = APIRouter(prefix="/zones", tags=["Zones"])


@zones_router.get("")
def list_zones():
    return fetch_all("SELECT * FROM zones ORDER BY nom")


@zones_router.get("/{zone_id}")
def get_zone(zone_id: int):
    return fetch_one("SELECT * FROM zones WHERE id = %s", (zone_id,))


# ── Citoyens ──────────────────────────────────────────────────────────────────

citoyens_router = APIRouter(prefix="/citoyens", tags=["Citoyens"])


@citoyens_router.get("")
def list_citoyens(
    score_min: Optional[int] = Query(None),
    zone_id:   Optional[int] = Query(None),
    limit:     int           = Query(200, le=1000),
):
    conditions, params = [], []
    if score_min is not None:
        conditions.append("score_ecolo >= %s"); params.append(score_min)
    if zone_id is not None:
        conditions.append("zone_id = %s"); params.append(zone_id)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    return fetch_all(f"""
        SELECT id, nom, email, score_ecolo, zone_id,
               date_inscription::text
        FROM citoyens {where}
        ORDER BY score_ecolo DESC
        LIMIT %s
    """, params)


@citoyens_router.get("/stats")
def stats_citoyens():
    return fetch_one("""
        SELECT
            COUNT(*)                               AS total,
            ROUND(AVG(score_ecolo)::numeric, 1)    AS score_moyen,
            MAX(score_ecolo)                       AS score_max,
            MIN(score_ecolo)                       AS score_min,
            COUNT(*) FILTER (WHERE score_ecolo>80) AS haute_ecologie
        FROM citoyens
    """)


# ── Véhicules ─────────────────────────────────────────────────────────────────

vehicules_router = APIRouter(prefix="/vehicules", tags=["Véhicules"])


@vehicules_router.get("")
def list_vehicules(statut: Optional[str] = Query(None), limit: int = Query(100)):
    conditions, params = [], []
    if statut:
        conditions.append("statut = %s"); params.append(statut)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    return fetch_all(f"""
        SELECT id, modele, statut, zone_id, batterie_pct, vitesse_kmh
        FROM vehicules {where}
        ORDER BY id
        LIMIT %s
    """, params)


# ── Trajets ───────────────────────────────────────────────────────────────────

trajets_router = APIRouter(prefix="/trajets", tags=["Trajets"])


@trajets_router.get("")
def list_trajets(limit: int = Query(100, le=500)):
    return fetch_all("""
        SELECT trajet_id, vehicule_id, zone_depart_id, zone_arrivee_id,
               economie_co2, distance_km, duree_min,
               date_debut::text, date_fin::text, statut
        FROM trajets
        ORDER BY date_debut DESC
        LIMIT %s
    """, (limit,))
