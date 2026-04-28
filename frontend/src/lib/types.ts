// Smart City — Neo-Sousse 2030 API types

export type CapteurStatut = "INACTIF" | "ACTIF" | "SIGNALÉ" | "EN_MAINTENANCE" | "HORS_SERVICE";
export type CapteurType = "pollution" | "temperature" | "humidite" | "bruit";

export interface Capteur {
  id: string;
  nom: string;
  type: CapteurType;
  statut: CapteurStatut;
  zone_id: number;
  taux_erreur: number;
  installation_date: string;
  fabricant: string;
  modele: string;
}

export interface CapteurKPI {
  total: number;
  actifs: number;
  inactifs: number;
  signales: number;
  en_maintenance: number;
  hors_service: number;
}

export type InterventionStatut = "DEMANDE" | "TECH1_ASSIGNÉ" | "TECH2_VALIDÉ" | "IA_VALIDÉ" | "TERMINÉ";

export interface Intervention {
  id: number;
  capteur_id: string;
  tech1_id: number | null;
  tech2_id: number | null;
  statut: InterventionStatut;
  ia_validee: boolean | null;
  ia_commentaire: string | null;
  date_demande: string;
  date_debut: string | null;
  date_fin: string | null;
  zone_id: number;
  description: string;
  priorite: number;
}

export type Qualite = "bon" | "moyen" | "mauvais" | "dangereux";

export interface Mesure {
  id: number;
  capteur_id: string;
  zone_id: number;
  pollution: number;
  temperature: number;
  humidite: number;
  bruit: number;
  co2_ppm: number;
  timestamp: string;
  qualite: Qualite;
}

export interface PollutionParZone {
  zone: string;
  zone_id: number;
  pollution: number;
}

export interface SerieTemporelle {
  date: string;
  pollution: number;
}

export interface Zone {
  id: number;
  nom: string;
  surface_km2: number;
  population: number;
  latitude: number;
  longitude: number;
  created_at: string;
}

export interface Citoyen {
  id: number;
  nom: string;
  email: string;
  score_ecolo: number;
  zone_id: number;
  date_inscription: string;
}

export interface CitoyenStats {
  total: number;
  score_moyen: number;
  score_max: number;
  score_min: number;
  haute_ecologie: number;
}

export type VehiculeStatut = "STATIONNÉ" | "EN_ROUTE" | "EN_PANNE" | "ARRIVÉ";

export interface Vehicule {
  id: string;
  modele: string;
  statut: VehiculeStatut;
  zone_id: number;
  batterie_pct: number;
  vitesse_kmh: number;
}

export interface Trajet {
  trajet_id: number;
  vehicule_id: string;
  zone_depart_id: number;
  zone_arrivee_id: number;
  economie_co2: number;
  distance_km: number;
  duree_min: number;
  date_debut: string;
  date_fin: string | null;
  statut: string;
}

export interface FsmEventResponse {
  capteur_id?: string;
  intervention_id?: number;
  vehicule_id?: string;
  from_state: string;
  event: string;
  to_state: string;
}

export type QueryType = "SELECT" | "INSERT" | "UPDATE" | "DELETE";

export interface TokenInfo {
  type: string;
  value: string;
  pos: number;
}

export interface CompileResult {
  sql: string;
  warnings: string[];
  ambiguous: boolean;
  ambiguity_hint?: string;
  query_type: QueryType;
  ast?: Record<string, unknown>;
  tokens?: TokenInfo[];
  error?: string;
  error_pos?: number;
  error_arrow?: string;
}

export interface QueryResult extends CompileResult {
  rows: Record<string, unknown>[];
  row_count: number;
  executed: boolean;
}

export type ReportType = "sensors" | "interventions" | "air_quality" | "citizens" | "vehicles";

export interface AiReport {
  report_type: ReportType;
  row_count: number;
  report: string;
}

export interface AiSuggestion {
  entity_id: string | number;
  state: string;
  suggestion: string;
}

export interface AiFsmValidation {
  entity_type: string;
  entity_id: string;
  from_state: string;
  event: string;
  to_state: string;
  approved: boolean;
  reasoning: string;
}

export interface AiStatusReport {
  report: string;
}

export interface AiEntity {
  id: string;
  nom: string;
  statut: string;
  [key: string]: unknown;
}

export interface AiFsmTransitionDef {
  from_state: string;
  event: string;
  to_state: string;
}

export interface AiFsmEventOption {
  event: string;
  to_state: string;
}

export interface AiFsmMeta {
  entity_type: string;
  name: string;
  states: string[];
  initial_state: string;
  accepting_states: string[];
  transitions: AiFsmTransitionDef[];
  events_by_state: Record<string, AiFsmEventOption[]>;
}

export interface HealthStatus {
  status: string;
  database?: string;
}
