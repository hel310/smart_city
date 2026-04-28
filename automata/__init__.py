"""
Automata package — Smart City Platform.
"""
from .fsm_engine import (
    FSM, Transition, HistoryEntry, InvalidTransitionError,
    SENSOR_FSM, INTERVENTION_FSM, VEHICLE_FSM,
    FSM_REGISTRY, get_fsm,
    get_alerts, clear_alerts,
)

# ── Transition tables for Part 1.1 deliverable ───────────────────────────────

SENSOR_TRANSITION_TABLE = {
    ("INACTIF",        "installation"):       "ACTIF",
    ("ACTIF",          "detection_anomalie"):  "SIGNALÉ",
    ("SIGNALÉ",        "prise_en_charge"):     "EN_MAINTENANCE",
    ("EN_MAINTENANCE", "reparation"):          "ACTIF",
    ("EN_MAINTENANCE", "panne"):               "HORS_SERVICE",
    ("ACTIF",          "panne"):               "HORS_SERVICE",
    ("HORS_SERVICE",   "remplacement"):        "INACTIF",
}

INTERVENTION_TRANSITION_TABLE = {
    ("DEMANDE",       "assigner_tech1"):  "TECH1_ASSIGNÉ",
    ("TECH1_ASSIGNÉ", "valider_tech2"):   "TECH2_VALIDÉ",
    ("TECH2_VALIDÉ",  "valider_ia"):      "IA_VALIDÉ",
    ("IA_VALIDÉ",     "terminer"):        "TERMINÉ",
    ("TECH2_VALIDÉ",  "rejeter"):         "DEMANDE",
    ("IA_VALIDÉ",     "rejeter"):         "TECH1_ASSIGNÉ",
}

VEHICLE_TRANSITION_TABLE = {
    ("STATIONNÉ",  "depart"):        "EN_ROUTE",
    ("EN_ROUTE",   "panne"):         "EN_PANNE",
    ("EN_ROUTE",   "arrivee"):       "ARRIVÉ",
    ("EN_PANNE",   "reparation"):    "EN_ROUTE",
    ("EN_PANNE",   "remorquage"):    "STATIONNÉ",
    ("ARRIVÉ",     "nouveau_trajet"):"EN_ROUTE",
    ("ARRIVÉ",     "garer"):         "STATIONNÉ",
}

__all__ = [
    "FSM", "Transition", "HistoryEntry", "InvalidTransitionError",
    "SENSOR_FSM", "INTERVENTION_FSM", "VEHICLE_FSM",
    "FSM_REGISTRY", "get_fsm",
    "get_alerts", "clear_alerts",
    "SENSOR_TRANSITION_TABLE", "INTERVENTION_TRANSITION_TABLE", "VEHICLE_TRANSITION_TABLE",
]
