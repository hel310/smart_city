// Typed API client for the Smart City — Neo-Sousse 2030 FastAPI backend.
// Base URL is read from VITE_API_BASE_URL (defaults to http://localhost:8000).
import type {
  AiEntity,
  AiFsmMeta,
  AiFsmValidation,
  AiReport,
  AiStatusReport,
  AiSuggestion,
  Capteur,
  CapteurKPI,
  Citoyen,
  CitoyenStats,
  CompileResult,
  FsmEventResponse,
  HealthStatus,
  Intervention,
  Mesure,
  PollutionParZone,
  QueryResult,
  ReportType,
  SerieTemporelle,
  Trajet,
  Vehicule,
  Zone,
} from "./types";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
  } catch (err) {
    throw new Error(`Backend injoignable (${API_BASE_URL}). Vérifiez que le serveur FastAPI tourne.`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(`HTTP ${res.status} — ${detail}`);
  }
  return (await res.json()) as T;
}

const qs = (params: Record<string, unknown>) => {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
};

export const api = {
  // Health
  health: () => request<HealthStatus>("/health"),
  root: () => request<{ service: string; version: string; status: string }>("/"),

  // Capteurs
  capteurKpi: () => request<CapteurKPI>("/capteurs/kpi"),
  capteurs: (params: { statut?: string; zone_id?: number; limit?: number } = {}) =>
    request<Capteur[]>(`/capteurs${qs(params)}`),
  capteur: (id: string) => request<Capteur>(`/capteurs/${id}`),
  capteurEvent: (id: string, body: { event: string; triggered_by?: string }) =>
    request<FsmEventResponse>(`/capteurs/${id}/event`, { method: "POST", body: JSON.stringify(body) }),

  // Interventions
  interventions: (params: { statut?: string; limit?: number } = {}) =>
    request<Intervention[]>(`/interventions${qs(params)}`),
  intervention: (id: number) => request<Intervention>(`/interventions/${id}`),
  interventionEvent: (id: number, body: { event: string; triggered_by?: string }) =>
    request<FsmEventResponse>(`/interventions/${id}/event`, { method: "POST", body: JSON.stringify(body) }),

  // Mesures
  mesures: (params: { zone_id?: number; capteur_id?: string; limit?: number } = {}) =>
    request<Mesure[]>(`/mesures${qs(params)}`),
  pollutionParZone: () => request<PollutionParZone[]>("/mesures/pollution-par-zone"),
  serieTemporelle: (zone_id?: number) =>
    request<SerieTemporelle[]>(`/mesures/serie-temporelle${qs({ zone_id })}`),

  // Zones
  zones: () => request<Zone[]>("/zones"),
  zone: (id: number) => request<Zone>(`/zones/${id}`),

  // Citoyens
  citoyens: (params: { score_min?: number; zone_id?: number; limit?: number } = {}) =>
    request<Citoyen[]>(`/citoyens${qs(params)}`),
  citoyenStats: () => request<CitoyenStats>("/citoyens/stats"),

  // Véhicules
  vehicules: (params: { statut?: string; limit?: number } = {}) =>
    request<Vehicule[]>(`/vehicules${qs(params)}`),

  // Trajets
  trajets: (params: { limit?: number } = {}) => request<Trajet[]>(`/trajets${qs(params)}`),

  // Compiler
  compilerCompile: (query: string) =>
    request<CompileResult>("/compiler/compile", { method: "POST", body: JSON.stringify({ query }) }),
  compilerQuery: (query: string) =>
    request<QueryResult>("/compiler/query", { method: "POST", body: JSON.stringify({ query }) }),

  // AI — Data for dropdowns
  aiEntities: (entity_type: string) =>
    request<AiEntity[]>(`/ai/entities${qs({ entity_type })}`),
  aiFsmMeta: (entity_type: string) =>
    request<AiFsmMeta>(`/ai/fsm-meta${qs({ entity_type })}`),

  // AI — Generation
  aiReport: (body: { report_type: ReportType; n_rows: number }) =>
    request<AiReport>("/ai/report", { method: "POST", body: JSON.stringify(body) }),
  aiSuggest: (body: { entity_type: string; entity_id: string | number; state: string; context: string }) =>
    request<AiSuggestion>("/ai/suggest", { method: "POST", body: JSON.stringify(body) }),
  aiValidateFsm: (body: {
    entity_type: string;
    entity_id: string;
    from_state: string;
    event: string;
    to_state: string;
    context?: string;
  }) =>
    request<AiFsmValidation>("/ai/validate-fsm", { method: "POST", body: JSON.stringify(body) }),
  aiStatusReport: () =>
    request<AiStatusReport>("/ai/status-report", { method: "POST" }),
};
