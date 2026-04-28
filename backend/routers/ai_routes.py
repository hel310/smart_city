"""
Router: /ai
GET  /ai/entities          — list entities (capteurs/interventions/vehicules) with their current state
GET  /ai/fsm-meta          — get FSM transition table for a given entity type
POST /ai/report            — generate AI report from live DB data
POST /ai/suggest           — suggest actions for a sensor/intervention
POST /ai/validate-fsm      — validate a FSM transition using AI
POST /ai/status-report     — generate full platform status report
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any, List

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/ai", tags=["IA Générative"])

TABLE_MAP = {
    "sensors":       "capteurs",
    "interventions": "interventions",
    "air_quality":   "mesures",
    "citizens":      "citoyens",
    "vehicles":      "vehicules",
}


# ── Request models ────────────────────────────────────────────────────────────

class ReportIn(BaseModel):
    report_type: str   # sensors | interventions | air_quality | citizens | vehicles
    n_rows: int = 20


class SuggestIn(BaseModel):
    entity_type: str   # capteur | intervention | vehicule
    entity_id: str
    state: str
    context: Optional[str] = None


class FsmValidateIn(BaseModel):
    entity_type: str   # capteur | intervention | vehicule
    entity_id: str
    from_state: str
    event: str
    to_state: str
    context: Optional[str] = None


# ── Data endpoints for dropdowns ──────────────────────────────────────────────

@router.get("/entities")
def list_entities(entity_type: str = Query(..., description="capteur | intervention | vehicule")):
    """Return a list of entities with their ID and current state for dropdown population."""
    if entity_type == "capteur":
        rows = fetch_all(
            """SELECT id, nom, statut, type, zone_id, taux_erreur
               FROM capteurs ORDER BY id"""
        )
    elif entity_type == "intervention":
        rows = fetch_all(
            """SELECT id::text as id, 
                      'Intervention #' || id as nom, 
                      statut, capteur_id, zone_id, priorite
               FROM interventions ORDER BY id"""
        )
    elif entity_type == "vehicule":
        rows = fetch_all(
            """SELECT id, modele as nom, statut, zone_id, batterie_pct, vitesse_kmh
               FROM vehicules ORDER BY id"""
        )
    else:
        raise HTTPException(400, f"Type d'entité inconnu: {entity_type}")
    return rows


@router.get("/fsm-meta")
def get_fsm_meta(entity_type: str = Query(..., description="capteur | intervention | vehicule")):
    """Return the full FSM metadata: states, transitions, events for a given entity type."""
    from automata import FSM_REGISTRY
    
    fsm = FSM_REGISTRY.get(entity_type)
    if not fsm:
        raise HTTPException(400, f"Type d'entité inconnu: {entity_type}")
    
    # Normalization map: DB stores statuses without accents
    _NORM = {
        "SIGNALÉ": "SIGNALE", "STATIONNÉ": "STATIONNE",
        "ARRIVÉ": "ARRIVE", "TERMINÉ": "TERMINE",
        "TECH1_ASSIGNÉ": "TECH_ASSIGN", "TECH2_VALIDÉ": "TECH_VALID",
        "IA_VALIDÉ": "IA_VALID",
    }
    _DENORM = {v: k for k, v in _NORM.items()}

    def _norm(state: str) -> str:
        return _NORM.get(state, state)
    
    # Build transition list (both accented FSM keys and normalized DB keys)
    transitions = []
    for t in fsm.transitions:
        transitions.append({
            "from_state": _norm(t.from_state),
            "event": t.event,
            "to_state": _norm(t.to_state),
        })
    
    # Build per-state available events using NORMALIZED keys (matching DB values)
    events_by_state = {}
    for t in fsm.transitions:
        key = _norm(t.from_state)
        if key not in events_by_state:
            events_by_state[key] = []
        events_by_state[key].append({
            "event": t.event,
            "to_state": _norm(t.to_state),
        })
    
    return {
        "entity_type": entity_type,
        "name": fsm.name,
        "states": sorted([_norm(s) for s in fsm.states]),
        "initial_state": _norm(fsm.initial_state),
        "accepting_states": sorted([_norm(s) for s in fsm.accepting_states]),
        "transitions": transitions,
        "events_by_state": events_by_state,
    }


# ── AI Endpoints ──────────────────────────────────────────────────────────────

@router.post("/report")
def generate_report(body: ReportIn):
    tbl = TABLE_MAP.get(body.report_type)
    if not tbl:
        raise HTTPException(400, f"Type de rapport inconnu: {body.report_type}")

    rows = fetch_all(f"SELECT * FROM {tbl} LIMIT %s", (body.n_rows,))

    try:
        from ai_module import generate_report as _gen
        text = _gen(body.report_type, rows)
    except Exception as e:
        raise HTTPException(503, f"IA indisponible : {e}")

    return {"report_type": body.report_type, "row_count": len(rows), "report": text}


@router.post("/suggest")
def suggest_actions(body: SuggestIn):
    # Enrich context from DB
    context = {}
    if body.context:
        context["user_context"] = body.context

    if body.entity_type == "capteur":
        row = fetch_one("SELECT * FROM capteurs WHERE id = %s", (body.entity_id,))
        if row:
            context = {**row, **context}
    elif body.entity_type == "intervention":
        row = fetch_one("SELECT * FROM interventions WHERE id = %s", (int(body.entity_id),))
        if row:
            context = {**{k: str(v) if v is not None else v for k, v in row.items()}, **context}
    elif body.entity_type == "vehicule":
        row = fetch_one("SELECT * FROM vehicules WHERE id = %s", (body.entity_id,))
        if row:
            context = {**row, **context}

    try:
        from ai_module import suggest_actions as _sug
        text = _sug(body.entity_type, body.entity_id, body.state, context)
    except Exception as e:
        raise HTTPException(503, f"IA indisponible : {e}")

    return {"entity_id": body.entity_id, "state": body.state, "suggestion": text}


@router.post("/validate-fsm")
def validate_fsm(body: FsmValidateIn):
    """Validate a FSM transition using AI reasoning with full business context."""
    # Gather rich context about the entity from DB
    db_context_parts = []
    
    if body.entity_type == "capteur":
        row = fetch_one("SELECT * FROM capteurs WHERE id = %s", (body.entity_id,))
        if row:
            db_context_parts.append(
                f"Données capteur: type={row.get('type')}, zone_id={row.get('zone_id')}, "
                f"taux_erreur={row.get('taux_erreur')}, fabricant={row.get('fabricant')}, "
                f"statut_actuel_db={row.get('statut')}"
            )
        # Recent measures
        measures = fetch_all(
            """SELECT ROUND(AVG(pollution)::NUMERIC,2) as pollution_moy,
                      ROUND(AVG(temperature)::NUMERIC,2) as temp_moy,
                      COUNT(*) as nb_mesures
               FROM mesures WHERE capteur_id = %s 
               AND timestamp >= NOW() - INTERVAL '7 days'""",
            (body.entity_id,)
        )
        if measures and measures[0].get("nb_mesures", 0) > 0:
            db_context_parts.append(
                f"Mesures récentes (7j): pollution_moy={measures[0]['pollution_moy']}, "
                f"temp_moy={measures[0]['temp_moy']}, nb_mesures={measures[0]['nb_mesures']}"
            )
        # Recent interventions on this sensor
        interventions = fetch_all(
            """SELECT id, statut, priorite, date_demande::text
               FROM interventions WHERE capteur_id = %s 
               ORDER BY date_demande DESC LIMIT 3""",
            (body.entity_id,)
        )
        if interventions:
            db_context_parts.append(
                f"Interventions récentes: {interventions}"
            )
    elif body.entity_type == "intervention":
        row = fetch_one(
            """SELECT i.*, c.type as capteur_type, c.taux_erreur, z.nom as zone_nom
               FROM interventions i
               LEFT JOIN capteurs c ON c.id = i.capteur_id
               LEFT JOIN zones z ON z.id = i.zone_id
               WHERE i.id = %s""",
            (int(body.entity_id),)
        )
        if row:
            db_context_parts.append(
                f"Intervention: priorité={row.get('priorite')}, capteur={row.get('capteur_id')}, "
                f"type_capteur={row.get('capteur_type')}, taux_erreur={row.get('taux_erreur')}, "
                f"zone={row.get('zone_nom')}, ia_validee={row.get('ia_validee')}"
            )
    elif body.entity_type == "vehicule":
        row = fetch_one("SELECT * FROM vehicules WHERE id = %s", (body.entity_id,))
        if row:
            db_context_parts.append(
                f"Véhicule: modèle={row.get('modele')}, batterie={row.get('batterie_pct')}%, "
                f"vitesse={row.get('vitesse_kmh')}km/h, zone_id={row.get('zone_id')}"
            )
        # Recent trips
        trips = fetch_all(
            """SELECT statut, distance_km, duree_min, date_debut::text
               FROM trajets WHERE vehicule_id = %s
               ORDER BY date_debut DESC LIMIT 3""",
            (body.entity_id,)
        )
        if trips:
            db_context_parts.append(f"Trajets récents: {trips}")

    # Combine user context with DB context
    full_context = "\n".join(db_context_parts)
    if body.context:
        full_context += f"\nContexte utilisateur: {body.context}"

    try:
        from ai_module import validate_fsm_transition as _val
        
        # Check formal validity
        is_formally_valid = False
        from automata import FSM_REGISTRY
        fsm = FSM_REGISTRY.get(body.entity_type)
        if fsm:
            _NORM = {
                "SIGNALÉ": "SIGNALE", "STATIONNÉ": "STATIONNE",
                "ARRIVÉ": "ARRIVE", "TERMINÉ": "TERMINE",
                "TECH1_ASSIGNÉ": "TECH_ASSIGN", "TECH2_VALIDÉ": "TECH_VALID",
                "IA_VALIDÉ": "IA_VALID",
            }
            def _norm(state: str) -> str:
                return _NORM.get(state, state)
                
            for t in fsm.transitions:
                if _norm(t.from_state) == body.from_state and t.event == body.event and _norm(t.to_state) == body.to_state:
                    is_formally_valid = True
                    break

        approved, reasoning = _val(
            body.entity_type,
            body.entity_id,
            body.from_state,
            body.event,
            body.to_state,
            full_context,
            is_formally_valid=is_formally_valid
        )
    except Exception as e:
        raise HTTPException(503, f"IA indisponible : {e}")

    return {
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "from_state": body.from_state,
        "event": body.event,
        "to_state": body.to_state,
        "approved": approved,
        "reasoning": reasoning,
    }


@router.post("/status-report")
def status_report():
    """Generate a comprehensive platform status report from aggregated data."""
    try:
        # Gather aggregated data from all key tables
        capteurs_stats = fetch_all(
            "SELECT statut, COUNT(*) as count FROM capteurs GROUP BY statut"
        )
        interventions_stats = fetch_all(
            "SELECT statut, COUNT(*) as count FROM interventions GROUP BY statut"
        )
        vehicules_stats = fetch_all(
            "SELECT statut, COUNT(*) as count FROM vehicules GROUP BY statut"
        )
        pollution = fetch_all(
            """SELECT z.nom as zone, ROUND(AVG(m.pollution)::NUMERIC, 2) as pollution_moy,
                      ROUND(MAX(m.pollution)::NUMERIC, 2) as pollution_max
               FROM mesures m JOIN zones z ON z.id = m.zone_id
               WHERE m.timestamp >= NOW() - INTERVAL '7 days'
               GROUP BY z.nom ORDER BY pollution_moy DESC"""
        )
        alertes = fetch_all(
            """SELECT id, type, statut, taux_erreur, zone_id
               FROM capteurs WHERE statut IN ('SIGNALE', 'HORS_SERVICE')
               ORDER BY taux_erreur DESC LIMIT 10"""
        )
        zones_count = fetch_one("SELECT COUNT(*) as total FROM zones")
        citoyens_count = fetch_one("SELECT COUNT(*) as total FROM citoyens")

        data_snapshot = {
            "capteurs": capteurs_stats,
            "interventions": interventions_stats,
            "vehicules": vehicules_stats,
            "pollution_par_zone": pollution,
            "alertes_capteurs": alertes,
            "total_zones": zones_count["total"] if zones_count else 0,
            "total_citoyens": citoyens_count["total"] if citoyens_count else 0,
        }

        from ai_module import generate_status_report as _status
        text = _status(data_snapshot)
    except Exception as e:
        raise HTTPException(503, f"IA indisponible : {e}")

    return {"report": text}
