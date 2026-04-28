"""
Router: /interventions
GET  /interventions         — list (filterable by statut)
GET  /interventions/{id}    — single intervention
POST /interventions/{id}/event — FSM event (assign tech, validate IA, …)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..db import fetch_all, fetch_one, execute

router = APIRouter(prefix="/interventions", tags=["Interventions"])


class InterventionOut(BaseModel):
    id: int
    capteur_id: Optional[str]
    tech1_id: Optional[int]
    tech2_id: Optional[int]
    statut: str
    ia_validee: Optional[bool]
    ia_commentaire: Optional[str]
    date_demande: Optional[str]
    date_debut: Optional[str]
    date_fin: Optional[str]
    zone_id: Optional[int]
    description: Optional[str]
    priorite: Optional[int]


class FSMEventIn(BaseModel):
    event: str
    triggered_by: Optional[str] = "user"


@router.get("", response_model=list[InterventionOut])
def list_interventions(
    statut: Optional[str] = Query(None),
    limit:  int           = Query(100, le=500),
):
    conditions = []
    params: list = []
    if statut:
        conditions.append("statut = %s")
        params.append(statut)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    rows = fetch_all(f"""
        SELECT id, capteur_id, tech1_id, tech2_id, statut,
               ia_validee, ia_commentaire,
               date_demande::text, date_debut::text, date_fin::text,
               zone_id, description, priorite
        FROM interventions {where}
        ORDER BY date_demande DESC
        LIMIT %s
    """, params)
    return rows


@router.get("/{intervention_id}", response_model=InterventionOut)
def get_intervention(intervention_id: int):
    row = fetch_one("""
        SELECT id, capteur_id, tech1_id, tech2_id, statut,
               ia_validee, ia_commentaire,
               date_demande::text, date_debut::text, date_fin::text,
               zone_id, description, priorite
        FROM interventions WHERE id = %s
    """, (intervention_id,))
    if not row:
        raise HTTPException(404, f"Intervention {intervention_id} introuvable")
    return row


@router.post("/{intervention_id}/event")
def trigger_intervention_event(intervention_id: int, body: FSMEventIn):
    from automata import INTERVENTION_FSM, InvalidTransitionError

    entity_id = str(intervention_id)
    current = INTERVENTION_FSM.get_state(entity_id)
    if current is None:
        row = fetch_one("SELECT statut FROM interventions WHERE id = %s", (intervention_id,))
        if not row:
            raise HTTPException(404, f"Intervention {intervention_id} introuvable")
        INTERVENTION_FSM.register(entity_id)
        INTERVENTION_FSM._states[entity_id] = row["statut"]
        current = row["statut"]

    try:
        new_state = INTERVENTION_FSM.trigger(entity_id, body.event)
    except InvalidTransitionError as e:
        raise HTTPException(400, str(e))

    ia_validee = new_state in ("IA_VALIDÉ", "TERMINÉ")
    execute("""
        UPDATE interventions
        SET statut = %s,
            ia_validee = CASE WHEN %s THEN TRUE ELSE ia_validee END,
            date_debut = CASE WHEN statut = 'DEMANDE' AND %s != 'DEMANDE'
                              THEN NOW() ELSE date_debut END,
            date_fin   = CASE WHEN %s = 'TERMINÉ' THEN NOW() ELSE date_fin END
        WHERE id = %s
    """, (new_state, ia_validee, new_state, new_state, intervention_id))

    execute("""
        INSERT INTO fsm_events (entity_type, entity_id, from_state, event, to_state, triggered_by)
        VALUES ('intervention', %s, %s, %s, %s, %s)
    """, (entity_id, current, body.event, new_state, body.triggered_by))

    return {"intervention_id": intervention_id, "from_state": current,
            "event": body.event, "to_state": new_state}
