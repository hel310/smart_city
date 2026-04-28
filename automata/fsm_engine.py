"""
Finite State Machine Engine — Smart City Platform
Implements DFAs for:
  1. Sensor lifecycle  (capteur)
  2. Intervention validation  (intervention)
  3. Autonomous vehicle journey  (vehicule)

Each FSM supports:
  - transition validation
  - current state tracking
  - automatic side-effect actions (alerts, logs)
  - Graphviz DOT export (bonus: visual automata)
  - transition history
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Set, Tuple
import logging

logger = logging.getLogger("smart_city.automata")


# ── Core FSM infrastructure ───────────────────────────────────────────────────

@dataclass
class Transition:
    """A single transition edge in the DFA."""
    from_state: str
    event: str
    to_state: str
    action: Optional[Callable] = None   # side-effect hook


@dataclass
class HistoryEntry:
    timestamp: datetime.datetime
    from_state: str
    event: str
    to_state: str
    entity_id: str


class InvalidTransitionError(Exception):
    def __init__(self, entity_id: str, current: str, event: str):
        super().__init__(
            f"Entity '{entity_id}': event '{event}' is not valid from state '{current}'"
        )
        self.entity_id = entity_id
        self.current_state = current
        self.event = event


class FSM:
    """
    Generic Deterministic Finite Automaton.

    Parameters
    ----------
    name          : human-readable name for this machine type
    states        : set of all valid state names
    initial_state : starting state for new entities
    accepting_states : terminal/accepting states (optional)
    transitions   : list of Transition objects
    """

    def __init__(
        self,
        name: str,
        states: Set[str],
        initial_state: str,
        transitions: List[Transition],
        accepting_states: Optional[Set[str]] = None,
    ):
        self.name = name
        self.states = states
        self.initial_state = initial_state
        self.transitions = transitions
        self.accepting_states = accepting_states or set()

        # Build lookup table: (from_state, event) → Transition
        self._table: Dict[Tuple[str, str], Transition] = {}
        for t in transitions:
            key = (t.from_state, t.event)
            if key in self._table:
                raise ValueError(f"Duplicate transition: {key}")
            self._table[key] = t

        # Per-entity state tracking
        self._states: Dict[str, str] = {}
        self._history: List[HistoryEntry] = []

    # ── Entity management ─────────────────────────────────────────────────────

    def register(self, entity_id: str) -> str:
        """Register a new entity in the initial state."""
        self._states[entity_id] = self.initial_state
        logger.info(f"[{self.name}] {entity_id} registered in state '{self.initial_state}'")
        return self.initial_state

    def get_state(self, entity_id: str) -> str:
        """Return current state of entity (registers at initial if unknown)."""
        if entity_id not in self._states:
            return self.register(entity_id)
        return self._states[entity_id]

    # ── Transition ────────────────────────────────────────────────────────────

    def trigger(self, entity_id: str, event: str) -> str:
        """
        Fire an event for entity_id.
        Returns new state.
        Raises InvalidTransitionError if the transition is not defined.
        """
        current = self.get_state(entity_id)
        key = (current, event)
        transition = self._table.get(key)

        if transition is None:
            raise InvalidTransitionError(entity_id, current, event)

        new_state = transition.to_state
        self._states[entity_id] = new_state

        # Record history
        self._history.append(HistoryEntry(
            timestamp=datetime.datetime.now(),
            from_state=current,
            event=event,
            to_state=new_state,
            entity_id=entity_id,
        ))

        logger.info(f"[{self.name}] {entity_id}: {current} --[{event}]--> {new_state}")

        # Fire side-effect action if defined
        if transition.action:
            try:
                transition.action(entity_id, current, new_state)
            except Exception as e:
                logger.error(f"Action error for {key}: {e}")

        return new_state

    def is_valid_event(self, entity_id: str, event: str) -> bool:
        current = self.get_state(entity_id)
        return (current, event) in self._table

    def valid_events(self, entity_id: str) -> List[str]:
        current = self.get_state(entity_id)
        return [ev for (st, ev) in self._table if st == current]

    def is_accepting(self, entity_id: str) -> bool:
        return self.get_state(entity_id) in self.accepting_states

    def history(self, entity_id: Optional[str] = None) -> List[HistoryEntry]:
        if entity_id:
            return [h for h in self._history if h.entity_id == entity_id]
        return list(self._history)

    # ── Sequence validation ───────────────────────────────────────────────────

    def validate_sequence(self, events: List[str], start_state: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a sequence of events from start_state (or initial_state).
        Returns (valid: bool, reason: str).
        Does NOT modify entity state.
        """
        state = start_state or self.initial_state
        for ev in events:
            key = (state, ev)
            if key not in self._table:
                return False, f"Event '{ev}' invalid from state '{state}'"
            state = self._table[key].to_state
        return True, f"Sequence valid, final state: '{state}'"

    # ── Graphviz DOT export (Bonus) ───────────────────────────────────────────

    def to_dot(self) -> str:
        """
        Export the FSM as a Graphviz DOT string.
        Suitable for rendering with graphviz or display in Streamlit.
        """
        lines = [
            f'digraph "{self.name}" {{',
            '  rankdir=LR;',
            '  node [shape=circle fontname="Helvetica" fontsize=12];',
            '  graph [bgcolor=transparent];',
        ]

        # Mark initial state
        lines.append(f'  __start__ [shape=point style=invis];')
        lines.append(f'  __start__ -> "{self.initial_state}";')

        # Mark accepting states with double circle
        for st in self.accepting_states:
            lines.append(f'  "{st}" [shape=doublecircle];')

        # Edges
        for t in self.transitions:
            lines.append(f'  "{t.from_state}" -> "{t.to_state}" [label="{t.event}"];')

        lines.append("}")
        return "\n".join(lines)

    def get_all_entities(self) -> Dict[str, str]:
        return dict(self._states)


# ── Alert / action helpers ────────────────────────────────────────────────────

_alerts: List[dict] = []

def _alert(level: str, message: str, entity_id: str, state: str):
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": level,
        "entity": entity_id,
        "state": state,
        "message": message,
    }
    _alerts.append(entry)
    logger.warning(f"ALERT [{level}] {entity_id} in {state}: {message}")
    return entry

def get_alerts() -> List[dict]:
    return list(_alerts)

def clear_alerts():
    _alerts.clear()


# ── FSM 1: Sensor Lifecycle ───────────────────────────────────────────────────

def _on_sensor_signaled(entity_id, from_state, to_state):
    _alert("WARNING", f"Capteur {entity_id} signalé — vérification requise", entity_id, to_state)

def _on_sensor_hors_service(entity_id, from_state, to_state):
    _alert("CRITICAL", f"Capteur {entity_id} HORS SERVICE — intervention urgente", entity_id, to_state)

SENSOR_FSM = FSM(
    name="Capteur",
    states={"INACTIF", "ACTIF", "SIGNALÉ", "EN_MAINTENANCE", "HORS_SERVICE"},
    initial_state="INACTIF",
    accepting_states={"HORS_SERVICE"},
    transitions=[
        Transition("INACTIF",        "installation",       "ACTIF"),
        Transition("ACTIF",          "detection_anomalie",  "SIGNALÉ",         _on_sensor_signaled),
        Transition("SIGNALÉ",        "prise_en_charge",    "EN_MAINTENANCE"),
        Transition("EN_MAINTENANCE", "reparation",         "ACTIF"),
        Transition("EN_MAINTENANCE", "panne",              "HORS_SERVICE",    _on_sensor_hors_service),
        Transition("ACTIF",          "panne",              "HORS_SERVICE",    _on_sensor_hors_service),
        Transition("HORS_SERVICE",   "remplacement",       "INACTIF"),
    ],
)

# ── FSM 2: Intervention Validation ───────────────────────────────────────────

def _on_ia_validated(entity_id, from_state, to_state):
    _alert("INFO", f"Intervention {entity_id} validée par l'IA — en cours de traitement", entity_id, to_state)

def _on_intervention_done(entity_id, from_state, to_state):
    _alert("SUCCESS", f"Intervention {entity_id} TERMINÉE", entity_id, to_state)

INTERVENTION_FSM = FSM(
    name="Intervention",
    states={"DEMANDE", "TECH1_ASSIGNÉ", "TECH2_VALIDÉ", "IA_VALIDÉ", "TERMINÉ"},
    initial_state="DEMANDE",
    accepting_states={"TERMINÉ"},
    transitions=[
        Transition("DEMANDE",       "assigner_tech1",   "TECH1_ASSIGNÉ"),
        Transition("TECH1_ASSIGNÉ", "valider_tech2",    "TECH2_VALIDÉ"),
        Transition("TECH2_VALIDÉ",  "valider_ia",       "IA_VALIDÉ",        _on_ia_validated),
        Transition("IA_VALIDÉ",     "terminer",         "TERMINÉ",          _on_intervention_done),
        # Rejection paths
        Transition("TECH2_VALIDÉ",  "rejeter",          "DEMANDE"),
        Transition("IA_VALIDÉ",     "rejeter",          "TECH1_ASSIGNÉ"),
    ],
)

# ── FSM 3: Autonomous Vehicle Journey ────────────────────────────────────────

def _on_vehicle_breakdown(entity_id, from_state, to_state):
    _alert("CRITICAL", f"Véhicule {entity_id} EN PANNE — assistance requise", entity_id, to_state)

VEHICLE_FSM = FSM(
    name="Vehicule",
    states={"STATIONNÉ", "EN_ROUTE", "EN_PANNE", "ARRIVÉ"},
    initial_state="STATIONNÉ",
    accepting_states={"ARRIVÉ"},
    transitions=[
        Transition("STATIONNÉ",  "depart",       "EN_ROUTE"),
        Transition("EN_ROUTE",   "panne",        "EN_PANNE",  _on_vehicle_breakdown),
        Transition("EN_ROUTE",   "arrivee",      "ARRIVÉ"),
        Transition("EN_PANNE",   "reparation",   "EN_ROUTE"),
        Transition("EN_PANNE",   "remorquage",   "STATIONNÉ"),
        Transition("ARRIVÉ",     "nouveau_trajet","EN_ROUTE"),
        Transition("ARRIVÉ",     "garer",        "STATIONNÉ"),
    ],
)

# ── Registry ─────────────────────────────────────────────────────────────────

FSM_REGISTRY = {
    "capteur":      SENSOR_FSM,
    "intervention": INTERVENTION_FSM,
    "vehicule":     VEHICLE_FSM,
}

def get_fsm(entity_type: str) -> FSM:
    fsm = FSM_REGISTRY.get(entity_type)
    if not fsm:
        raise KeyError(f"Unknown entity type '{entity_type}'. Valid: {list(FSM_REGISTRY.keys())}")
    return fsm


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Sensor FSM ===")
    SENSOR_FSM.register("C-001")
    print(SENSOR_FSM.trigger("C-001", "installation"))
    print(SENSOR_FSM.trigger("C-001", "detection_anomalie"))
    print(SENSOR_FSM.trigger("C-001", "prise_en_charge"))
    print(SENSOR_FSM.trigger("C-001", "panne"))
    print("Alerts:", get_alerts())

    print("\n=== Sequence Validation ===")
    valid, msg = SENSOR_FSM.validate_sequence(
        ["installation", "detection_anomalie", "prise_en_charge", "reparation"]
    )
    print(f"Valid: {valid}, {msg}")

    print("\n=== DOT export (Sensor) ===")
    print(SENSOR_FSM.to_dot())

    print("\n=== Intervention FSM ===")
    INTERVENTION_FSM.register("INT-001")
    for ev in ["assigner_tech1", "valider_tech2", "valider_ia", "terminer"]:
        print(INTERVENTION_FSM.trigger("INT-001", ev))

    print("\n=== Vehicle FSM ===")
    VEHICLE_FSM.register("V-001")
    for ev in ["depart", "panne", "reparation", "arrivee"]:
        print(VEHICLE_FSM.trigger("V-001", ev))
