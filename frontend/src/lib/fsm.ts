// FSM definitions for Capteurs, Interventions, Véhicules.
// States and transitions used both for action buttons and React Flow diagrams.

export interface FsmTransition {
  from: string;
  event: string;
  to: string;
}

export interface FsmDefinition {
  states: string[];
  initial: string;
  finalStates: string[];
  transitions: FsmTransition[];
}

// ── Capteur ──────────────────────────────────────────────────────────────────
export const capteurFsm: FsmDefinition = {
  states: ["INACTIF", "ACTIF", "SIGNALÉ", "EN_MAINTENANCE", "HORS_SERVICE"],
  initial: "INACTIF",
  finalStates: ["HORS_SERVICE"],
  transitions: [
    { from: "INACTIF",        event: "installation",       to: "ACTIF"          },
    { from: "ACTIF",          event: "detection_anomalie",  to: "SIGNALÉ"        },
    { from: "SIGNALÉ",        event: "prise_en_charge",    to: "EN_MAINTENANCE" },
    { from: "EN_MAINTENANCE", event: "reparation",         to: "ACTIF"          },
    { from: "EN_MAINTENANCE", event: "panne",              to: "HORS_SERVICE"   },
    { from: "ACTIF",          event: "panne",              to: "HORS_SERVICE"   },
  ],
};

// ── Intervention ─────────────────────────────────────────────────────────────
export const interventionFsm: FsmDefinition = {
  states: ["DEMANDE", "TECH1_ASSIGNÉ", "TECH2_VALIDÉ", "IA_VALIDÉ", "TERMINÉ"],
  initial: "DEMANDE",
  finalStates: ["TERMINÉ"],
  transitions: [
    { from: "DEMANDE",       event: "assigner_tech1", to: "TECH1_ASSIGNÉ" },
    { from: "TECH1_ASSIGNÉ", event: "valider_tech2",  to: "TECH2_VALIDÉ"  },
    { from: "TECH2_VALIDÉ",  event: "valider_ia",     to: "IA_VALIDÉ"     },
    { from: "IA_VALIDÉ",     event: "terminer",       to: "TERMINÉ"       },
  ],
};

// ── Véhicule ─────────────────────────────────────────────────────────────────
export const vehiculeFsm: FsmDefinition = {
  states: ["STATIONNÉ", "EN_ROUTE", "EN_PANNE", "ARRIVÉ"],
  initial: "STATIONNÉ",
  finalStates: [], // aucun état final — tous ont des transitions sortantes
  transitions: [
    { from: "STATIONNÉ", event: "depart",         to: "EN_ROUTE"  },
    { from: "EN_ROUTE",  event: "arrivee",        to: "ARRIVÉ"    },
    { from: "EN_ROUTE",  event: "nouveau_trajet", to: "EN_ROUTE"  },
    { from: "EN_ROUTE",  event: "panne",          to: "EN_PANNE"  },
    { from: "EN_PANNE",  event: "reparation",     to: "EN_ROUTE"  },
    { from: "EN_PANNE",  event: "remorquage",     to: "STATIONNÉ" },
    { from: "ARRIVÉ",    event: "garer",          to: "STATIONNÉ" },
  ],
};

// ── API value → FSM state normalisation ──────────────────────────────────────
// The API returns values without accents (e.g. "SIGNALE", "ARRIVE", "STATIONNE",
// "TECH_ASSIGN", "TECH_VALID", "IA_VALID", "TERMINE").
// This map converts every known API variant to the canonical FSM state name.
const API_STATE_MAP: Record<string, string> = {
  // Capteur
  "INACTIF":        "INACTIF",
  "ACTIF":          "ACTIF",
  "SIGNALE":        "SIGNALÉ",
  "SIGNALÉ":        "SIGNALÉ",
  "EN_MAINTENANCE": "EN_MAINTENANCE",
  "HORS_SERVICE":   "HORS_SERVICE",

  // Intervention
  "DEMANDE":        "DEMANDE",
  "TECH_ASSIGN":    "TECH1_ASSIGNÉ",
  "TECH1_ASSIGNÉ":  "TECH1_ASSIGNÉ",
  "TECH1_ASSIGNE":  "TECH1_ASSIGNÉ",
  "TECH_VALID":     "TECH2_VALIDÉ",
  "TECH2_VALIDÉ":   "TECH2_VALIDÉ",
  "TECH2_VALIDE":   "TECH2_VALIDÉ",
  "IA_VALID":       "IA_VALIDÉ",
  "IA_VALIDÉ":      "IA_VALIDÉ",
  "IA_VALIDE":      "IA_VALIDÉ",
  "TERMINE":        "TERMINÉ",
  "TERMINÉ":        "TERMINÉ",

  // Véhicule
  "STATIONNE":      "STATIONNÉ",
  "STATIONNÉ":      "STATIONNÉ",
  "EN_ROUTE":       "EN_ROUTE",
  "EN_PANNE":       "EN_PANNE",
  "ARRIVE":         "ARRIVÉ",
  "ARRIVÉ":         "ARRIVÉ",
};

/**
 * Normalise a raw API statut value to the canonical FSM state name.
 * Falls back to the uppercased raw value if no mapping is found.
 */
export function normalizeState(raw: string): string {
  const upper = raw.toUpperCase().trim();
  return API_STATE_MAP[upper] ?? upper;
}

export const eventsFrom = (def: FsmDefinition, state: string): FsmTransition[] =>
  def.transitions.filter((t) => t.from === state);

export const fsmStateColor = (
  entity: "capteur" | "intervention" | "vehicule",
  state: string,
): string => {
  if (entity === "capteur") {
    if (state === "ACTIF")          return "success";
    if (state === "SIGNALÉ")        return "warning";
    if (state === "EN_MAINTENANCE") return "warning";
    if (state === "HORS_SERVICE")   return "destructive";
    return "muted"; // INACTIF
  }
  if (entity === "intervention") {
    if (state === "TERMINÉ")       return "success";
    if (state === "DEMANDE")       return "warning";
    if (state === "TECH1_ASSIGNÉ") return "primary";
    if (state === "TECH2_VALIDÉ")  return "primary";
    if (state === "IA_VALIDÉ")     return "primary";
    return "muted";
  }
  if (entity === "vehicule") {
    if (state === "EN_ROUTE")  return "success";
    if (state === "ARRIVÉ")    return "success";
    if (state === "EN_PANNE")  return "destructive";
    return "muted"; // STATIONNÉ
  }
  return "muted";
};
