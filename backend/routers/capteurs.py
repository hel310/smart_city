"""
Router: /capteurs
GET  /capteurs              — list all sensors (filterable by statut, zone_id)
GET  /capteurs/{id}         — single sensor
GET  /capteurs/kpi          — aggregated KPIs (actifs, hors_service, …)
POST /capteurs/{id}/event   — trigger an FSM event on a sensor
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..db import fetch_all, fetch_one, execute

router = APIRouter(prefix="/capteurs", tags=["Capteurs"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CapteurOut(BaseModel):
    id: str
    nom: str
    type: str
    statut: str
    zone_id: Optional[int]
    taux_erreur: Optional[float]
    installation_date: Optional[str]
    fabricant: Optional[str]
    modele: Optional[str]

    class Config:
        from_attributes = True


class CapteurKPI(BaseModel):
    total: int
    actifs: int
    inactifs: int
    signales: int
    en_maintenance: int
    hors_service: int


class FSMEventIn(BaseModel):
    event: str
    triggered_by: Optional[str] = "user"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/kpi", response_model=CapteurKPI)
def get_kpi():
    row = fetch_one("""
        SELECT
            COUNT(*)                                             AS total,
            COUNT(*) FILTER (WHERE statut = 'ACTIF')            AS actifs,
            COUNT(*) FILTER (WHERE statut = 'INACTIF')          AS inactifs,
            COUNT(*) FILTER (WHERE statut = 'SIGNALÉ')          AS signales,
            COUNT(*) FILTER (WHERE statut = 'EN_MAINTENANCE')   AS en_maintenance,
            COUNT(*) FILTER (WHERE statut = 'HORS_SERVICE')     AS hors_service
        FROM capteurs
    """)
    return row


@router.get("", response_model=list[CapteurOut])
def list_capteurs(
    statut:  Optional[str] = Query(None),
    zone_id: Optional[int] = Query(None),
    limit:   int           = Query(200, le=1000),
):
    conditions = []
    params: list = []

    if statut:
        conditions.append("statut = %s")
        params.append(statut)
    if zone_id is not None:
        conditions.append("zone_id = %s")
        params.append(zone_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    rows = fetch_all(f"""
        SELECT id, nom, type, statut, zone_id, taux_erreur,
               installation_date::text, fabricant, modele
        FROM capteurs {where}
        ORDER BY id
        LIMIT %s
    """, params)
    return rows


@router.get("/{capteur_id}", response_model=CapteurOut)
def get_capteur(capteur_id: str):
    row = fetch_one("""
        SELECT id, nom, type, statut, zone_id, taux_erreur,
               installation_date::text, fabricant, modele
        FROM capteurs WHERE id = %s
    """, (capteur_id,))
    if not row:
        raise HTTPException(404, f"Capteur '{capteur_id}' introuvable")
    return row


@router.post("/{capteur_id}/event")
def trigger_sensor_event(capteur_id: str, body: FSMEventIn):
    """
    Apply an FSM event to a sensor: validates the transition,
    updates capteurs.statut, and logs to fsm_events.
    """
    from automata import SENSOR_FSM, InvalidTransitionError

    # Register entity if first time seen
    current = SENSOR_FSM.get_state(capteur_id)
    if current is None:
        row = fetch_one("SELECT statut FROM capteurs WHERE id = %s", (capteur_id,))
        if not row:
            raise HTTPException(404, f"Capteur '{capteur_id}' introuvable")
        SENSOR_FSM.register(capteur_id)
        # Manually set state to match DB
        SENSOR_FSM._states[capteur_id] = row["statut"]
        current = row["statut"]

    try:
        new_state = SENSOR_FSM.trigger(capteur_id, body.event)
    except InvalidTransitionError as e:
        raise HTTPException(400, str(e))

    # Persist new state + log event
    execute("UPDATE capteurs SET statut = %s WHERE id = %s", (new_state, capteur_id))
    execute("""
        INSERT INTO fsm_events (entity_type, entity_id, from_state, event, to_state, triggered_by)
        VALUES ('capteur', %s, %s, %s, %s, %s)
    """, (capteur_id, current, body.event, new_state, body.triggered_by))

    return {"capteur_id": capteur_id, "from_state": current,
            "event": body.event, "to_state": new_state}
