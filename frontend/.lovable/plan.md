## Smart City — Neo-Sousse 2030 Frontend

A polished React + TypeScript dashboard that consumes the FastAPI backend exclusively via REST. French UI, dark/light mode, modern smart-city aesthetic.

### Backend connection
- API base URL read from `VITE_API_BASE_URL` (default `http://localhost:8000`).
- Single typed `apiClient` with React Query for caching, retries, and loading/error states.
- Live backend status pill in the sidebar (polls `/health`), red/green dot.
- Toast notifications for API errors and successful FSM transitions (Sonner).
- Note: the Lovable preview cannot reach `localhost:8000`. You'll see real data when running the frontend locally (`npm run dev`) against your FastAPI server. I'll also add a small "Backend offline" empty state so the UI degrades gracefully in the preview.

### Design system
Modern smart-city aesthetic, defined in `index.css` + `tailwind.config.ts` as HSL tokens:
- Deep navy background (`#0b1020` family), elevated glassy cards with subtle border + soft shadow.
- Primary: refined navy/indigo. Accent: teal/cyan for data viz highlights.
- Semantic states: green (healthy/ACTIF), orange (warning/SIGNALÉ/EN_MAINTENANCE), red (HORS_SERVICE/alerts).
- Subtle gradient hero strip on the dashboard, animated KPI counters, skeleton loaders everywhere.
- Light mode mirrors the same palette with bright surfaces.
- Typography: Inter, tabular numerals for KPIs.

### Layout & navigation
- Desktop: collapsible sidebar with project name "Neo-Sousse 2030", backend status, module list, theme toggle.
- Mobile: bottom nav bar with 5 icons.
- Top bar: page title + breadcrumb + quick refresh button.

### Pages

1. **Dashboard (`/`)**
   - 4 animated KPI cards: capteurs actifs, interventions en cours, pollution moyenne (µg/m³), score écolo moyen (from `/capteurs/kpi`, `/interventions`, `/mesures/pollution-par-zone`, `/citoyens/stats`).
   - Recharts bar chart: pollution par zone.
   - Recharts line chart: série temporelle (zone selector).
   - Alerts panel: capteurs `SIGNALÉ`/`HORS_SERVICE` + interventions non `TERMINÉ`, color-coded with priority.

2. **Compilateur NL→SQL (`/compiler`)**
   - Large French text input + clickable example chips.
   - Two actions: "Compiler" (`/compiler/compile` → SQL, AST viewer, warnings, ambiguity badge) and "Compiler & Exécuter" (`/compiler/query` → SQL + paginated result table).
   - Syntax-highlighted SQL block, collapsible AST tree.

3. **Automates FSM (`/fsm`)**
   - 3 tabs: Capteurs, Interventions, Véhicules.
   - Entity dropdown → current state highlighted.
   - **React Flow** interactive graph: nodes for each state, animated edges for transitions, current state pulsing. Pan/zoom enabled.
   - Action buttons for valid events from current state → POST `/{entity}/{id}/event`, optimistic update + toast.
   - Transition history table (pulled from sequential events on the entity).

4. **Rapports IA (`/ai`)**
   - Report generator card: type dropdown (sensors/interventions/air_quality/citizens/vehicles), row count slider, "Générer" → renders markdown report (`/ai/report`).
   - Suggestion engine card: entity type, ID, state, free-text context → "Suggérer" → AI suggestion (`/ai/suggest`).

5. **Données & Stats (`/data`)**
   - Table picker: capteurs, interventions, citoyens, vehicules, mesures, zones, trajets.
   - Paginated, sortable, filterable data table (TanStack-style on top of shadcn Table).
   - Conditional viz: `mesures` → time series; `citoyens` → score histogram.
   - Descriptive stats panel (count, mean, min, max, std) for numeric columns, computed client-side.

### Stack additions
- `@tanstack/react-query`, `recharts`, `reactflow`, `react-markdown` (for AI reports), `lucide-react`.
- Strong TypeScript types for every API entity (Capteur, Intervention, Mesure, Zone, Citoyen, Vehicule, Trajet, FSM event).

### CORS reminder
Your FastAPI `CORSMiddleware` currently allows `localhost:8501`. Add `http://localhost:5173` (Vite default) to `allow_origins` so the frontend can call the API locally. I'll include this note in the README of the project.

### Out of scope (can add later)
- Authentication (no auth endpoints in the spec).
- Map view of zones (lat/lon are present — easy follow-up with Mapbox/Leaflet).
- Persisting user preferences to a backend (theme stored in localStorage only).