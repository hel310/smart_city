import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Workflow, Loader2, Play, CheckCircle2, XCircle, ChevronRight, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  capteurFsm,
  eventsFrom,
  fsmStateColor,
  interventionFsm,
  normalizeState,
  vehiculeFsm,
  type FsmDefinition,
  type FsmTransition,
} from "@/lib/fsm";
import { cn } from "@/lib/utils";

type EntityKind = "capteur" | "intervention" | "vehicule";

// ─── CSS variable helper ──────────────────────────────────────────────────────
function cssHsl(varName: string): string {
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim();
  return val ? `hsl(${val})` : "#888888";
}
function hslToHex(hslStr: string): string {
  const tmp = document.createElement("div");
  tmp.style.color = hslStr;
  document.body.appendChild(tmp);
  const computed = getComputedStyle(tmp).color;
  document.body.removeChild(tmp);
  const m = computed.match(/\d+/g);
  if (!m) return "#888888";
  const [r, g, b] = m.map(Number);
  return "#" + [r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("");
}
function cssHex(varName: string): string {
  return hslToHex(cssHsl(varName));
}

function toneHex(entity: EntityKind, state: string): { bg: string; fg: string; border: string } {
  const tone = fsmStateColor(entity, state);
  const varMap: Record<string, { bg: string; fg: string }> = {
    success:     { bg: "--success",     fg: "--success-foreground"     },
    warning:     { bg: "--warning",     fg: "--warning-foreground"     },
    destructive: { bg: "--destructive", fg: "--destructive-foreground" },
    primary:     { bg: "--primary",     fg: "--primary-foreground"     },
    muted:       { bg: "--muted",       fg: "--muted-foreground"       },
  };
  const vars = varMap[tone] ?? varMap["muted"];
  const bg   = cssHex(vars.bg);
  const fg   = cssHex(vars.fg);
  return { bg, fg, border: bg };
}

// ─── DOT generator ────────────────────────────────────────────────────────────
function buildDot(def: FsmDefinition, kind: EntityKind, currentState: string): string {
  const bgColor     = cssHex("--background");
  const cardColor   = cssHex("--card");
  const fgColor     = cssHex("--foreground");
  const mutedColor  = cssHex("--muted-foreground");
  const accentColor = cssHex("--accent");
  const lines: string[] = [];

  lines.push(`digraph FSM {`);
  lines.push(`  graph [rankdir=LR, bgcolor="${bgColor}", fontname="Inter", pad="0.4", nodesep="0.7", ranksep="1.0"];`);
  lines.push(`  node  [shape=circle, fixedsize=true, width=1.1, fontname="Inter", fontsize=11, penwidth=2];`);
  lines.push(`  edge  [fontname="Inter", fontsize=10, arrowsize=0.7];`);
  lines.push(`  __start [shape=point, width=0.15, color="${fgColor}"];`);
  lines.push(`  __start -> "${def.initial}" [color="${fgColor}", penwidth=1.5];`);

  def.states.forEach((s) => {
    const isCurrent   = s === currentState;
    const isFinal     = def.finalStates.includes(s);
    const { bg, fg, border } = toneHex(kind, s);
    const fillColor   = isCurrent ? bg          : cardColor;
    const fontColor   = isCurrent ? fg          : fgColor;
    const borderColor = isCurrent ? accentColor : border;
    const penWidth    = isCurrent ? 3           : 2;
    const shape       = isFinal   ? "doublecircle" : "circle";
    lines.push(
      `  "${s}" [shape=${shape}, label="${s}", fillcolor="${fillColor}", fontcolor="${fontColor}", color="${borderColor}", penwidth=${penWidth}, style=filled];`
    );
  });

  def.transitions.forEach((t) => {
    const isActive  = t.from === currentState;
    const edgeColor = isActive ? accentColor : mutedColor;
    const fontColor = isActive ? accentColor : mutedColor;
    const penWidth  = isActive ? 2.5         : 1.2;
    const style     = isActive ? "bold"      : "solid";
    lines.push(
      `  "${t.from}" -> "${t.to}" [label=" ${t.event} ", color="${edgeColor}", fontcolor="${fontColor}", penwidth=${penWidth}, style=${style}];`
    );
  });

  lines.push(`}`);
  return lines.join("\n");
}

// ─── FsmDiagram ──────────────────────────────────────────────────────────────
interface FsmDiagramProps { def: FsmDefinition; kind: EntityKind; currentState: string; }

function FsmDiagram({ def, kind, currentState }: FsmDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const dot = buildDot(def, kind, currentState);

    import("@hpcc-js/wasm").then(({ Graphviz }) => {
      if (cancelled) return;
      return Graphviz.load().then((graphviz) => {
        if (cancelled) return;
        try {
          const svg = graphviz.dot(dot, "svg");
          if (containerRef.current) {
            containerRef.current.innerHTML = svg;
            const svgEl = containerRef.current.querySelector("svg");
            if (svgEl) {
              svgEl.removeAttribute("width");
              svgEl.removeAttribute("height");
              svgEl.style.width  = "100%";
              svgEl.style.height = "100%";
            }
          }
          setLoading(false);
        } catch (e) { setError(String(e)); setLoading(false); }
      });
    }).catch((e) => {
      if (!cancelled) { setError(`@hpcc-js/wasm not installed.\n${e}`); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [def, kind, currentState]);

  return (
    <div className="relative w-full h-full">
      {loading && <div className="absolute inset-0 flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}
      {error   && <div className="absolute inset-0 flex items-center justify-center p-4"><pre className="text-xs text-destructive whitespace-pre-wrap">{error}</pre></div>}
      <div ref={containerRef} className="w-full h-full" style={{ opacity: loading ? 0 : 1, transition: "opacity 0.2s" }} />
    </div>
  );
}

// ─── Sequence Validator ───────────────────────────────────────────────────────
interface StepResult {
  event: string;
  fromState: string;
  toState: string | null;   // null = invalid
  valid: boolean;
}

interface SequenceValidatorProps {
  def: FsmDefinition;
  kind: EntityKind;
  examples: string[][];     // list of example sequences (arrays of event names)
  exampleLabels: string[];  // label for each example
}

function validateSequence(def: FsmDefinition, events: string[]): StepResult[] {
  let current = def.initial;
  return events.map((event) => {
    const match = def.transitions.find((t) => t.from === current && t.event === event);
    if (match) {
      const result: StepResult = { event, fromState: current, toState: match.to, valid: true };
      current = match.to;
      return result;
    } else {
      return { event, fromState: current, toState: null, valid: false };
    }
  });
}

function SequenceValidator({ def, kind, examples, exampleLabels }: SequenceValidatorProps) {
  const [input, setInput]     = useState("");
  const [results, setResults] = useState<StepResult[] | null>(null);

  const allEvents = Array.from(new Set(def.transitions.map((t) => t.event)));

  function run(raw: string) {
    const events = raw
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (events.length === 0) return;
    setResults(validateSequence(def, events));
  }

  function loadExample(seq: string[]) {
    const str = seq.join(", ");
    setInput(str);
    setResults(validateSequence(def, seq));
  }

  function reset() {
    setInput("");
    setResults(null);
  }

  const isValid   = results !== null && results.every((r) => r.valid);
  const isInvalid = results !== null && results.some((r) => !r.valid);
  const firstBad  = results?.findIndex((r) => !r.valid) ?? -1;

  return (
    <div className="glass-card rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Play className="h-4 w-4 text-muted-foreground" />
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Vérificateur de séquence
        </p>
      </div>

      {/* Examples */}
      <div>
        <p className="text-xs text-muted-foreground mb-2">Exemples :</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((seq, i) => (
            <button
              key={i}
              onClick={() => loadExample(seq)}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-1 text-[11px] font-mono text-muted-foreground hover:bg-accent/10 hover:text-accent hover:border-accent transition-colors"
            >
              <span className="text-[10px] font-sans font-medium text-foreground mr-1">{exampleLabels[i]} :</span>
              {seq.join(" → ")}
            </button>
          ))}
        </div>
      </div>

      {/* Available events hint */}
      <div>
        <p className="text-xs text-muted-foreground mb-1">Événements disponibles :</p>
        <div className="flex flex-wrap gap-1">
          {allEvents.map((e) => (
            <span key={e} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{e}</span>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(input)}
          placeholder="ex: installation, detection_anomalie, prise_en_charge"
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-xs font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button size="sm" onClick={() => run(input)} className="gap-1 text-xs">
          <Play className="h-3 w-3" /> Tester
        </Button>
        {results && (
          <Button size="sm" variant="ghost" onClick={reset} className="gap-1 text-xs text-muted-foreground">
            <RotateCcw className="h-3 w-3" />
          </Button>
        )}
      </div>

      {/* Result summary */}
      {results && (
        <div className={cn(
          "rounded-lg border px-4 py-3 flex items-center gap-2 text-sm font-medium",
          isValid   && "border-success/40 bg-success/10 text-success",
          isInvalid && "border-destructive/40 bg-destructive/10 text-destructive",
        )}>
          {isValid
            ? <><CheckCircle2 className="h-4 w-4 shrink-0" /> Séquence valide — l'automate accepte cette suite d'événements.</>
            : <><XCircle className="h-4 w-4 shrink-0" /> Séquence invalide — erreur à l'étape {firstBad + 1} ({results[firstBad].event}).</>
          }
        </div>
      )}

      {/* Step-by-step trace */}
      {results && (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground mb-2">Trace pas-à-pas :</p>

          {/* initial state */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="w-5 text-right text-muted-foreground/50 shrink-0">0</span>
            <span className="rounded bg-muted px-2 py-0.5 text-muted-foreground">{def.initial}</span>
            <span className="text-muted-foreground/40 text-[10px]">état initial</span>
          </div>

          {results.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-xs font-mono">
              <span className="w-5 text-right text-muted-foreground/50 shrink-0">{i + 1}</span>

              {/* event badge */}
              <span className={cn(
                "rounded px-2 py-0.5 text-[11px]",
                r.valid
                  ? "bg-accent/10 text-accent border border-accent/20"
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              )}>
                {r.event}
              </span>

              <ChevronRight className="h-3 w-3 text-muted-foreground/40 shrink-0" />

              {/* result state */}
              {r.valid ? (
                <span className={cn(
                  "rounded px-2 py-0.5",
                  fsmStateColor(kind, r.toState!) === "success"     && "bg-success/10 text-success",
                  fsmStateColor(kind, r.toState!) === "warning"     && "bg-warning/10 text-warning",
                  fsmStateColor(kind, r.toState!) === "destructive" && "bg-destructive/10 text-destructive",
                  fsmStateColor(kind, r.toState!) === "primary"     && "bg-primary/10 text-primary",
                  fsmStateColor(kind, r.toState!) === "muted"       && "bg-muted text-muted-foreground",
                )}>
                  {r.toState}
                </span>
              ) : (
                <span className="text-destructive/70 text-[10px]">
                  ✗ Transition impossible depuis {r.fromState}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── FsmPanel ─────────────────────────────────────────────────────────────────
const SEQUENCE_EXAMPLES: Record<EntityKind, { seqs: string[][]; labels: string[] }> = {
  capteur: {
    seqs: [
      ["installation", "detection_anomalie", "prise_en_charge", "reparation"],
      ["installation", "panne"],
      ["installation", "detection_anomalie", "prise_en_charge", "panne"],
      ["installation", "detection_anomalie", "panne"],           // invalid: panne not from SIGNALÉ
    ],
    labels: ["Cycle nominal", "Panne directe", "Panne en maintenance", "Invalide"],
  },
  intervention: {
    seqs: [
      ["assigner_tech1", "valider_tech2", "valider_ia", "terminer"],
      ["assigner_tech1", "valider_tech2", "terminer"],            // invalid: no terminer from TECH2_VALIDÉ
      ["valider_tech2"],                                          // invalid: can't start with valider_tech2
    ],
    labels: ["Cycle complet", "Invalide (saut étape)", "Invalide (mauvais début)"],
  },
  vehicule: {
    seqs: [
      ["depart", "arrivee"],
      ["depart", "nouveau_trajet", "arrivee"],
      ["depart", "panne", "reparation", "arrivee"],
      ["depart", "panne", "remorquage", "depart", "arrivee"],
      ["arrivee"],                                                // invalid: can't start with arrivee
    ],
    labels: ["Trajet simple", "Avec détour", "Panne réparée", "Remorquage puis redépart", "Invalide"],
  },
};

function FsmPanel({ kind, def }: { kind: EntityKind; def: FsmDefinition }) {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const listQ = useQuery({
    queryKey: [`${kind}-list`],
    queryFn: async (): Promise<
      Array<{ id: string | number; nom?: string; modele?: string; description?: string; statut: string }>
    > => {
      if (kind === "capteur")      return (await api.capteurs({ limit: 100 })) as any;
      if (kind === "intervention") return (await api.interventions({ limit: 100 })) as any;
      return (await api.vehicules({ limit: 100 })) as any;
    },
  });

  const items = (listQ.data || []) as Array<{
    id: string | number; nom?: string; modele?: string; description?: string; statut: string;
  }>;

  const current = items.find((x) => String(x.id) === selectedId);
  const state   = normalizeState(current?.statut ?? def.initial);

  const eventM = useMutation({
    mutationFn: ({ id, event }: { id: string | number; event: string }) => {
      if (kind === "capteur")
        return api.capteurEvent(String(id), { event, triggered_by: "ui" });
      if (kind === "intervention")
        return api.interventionEvent(Number(id), { event, triggered_by: "ui" });
      return Promise.reject(new Error("Transitions véhicules non exposées par l'API."));
    },
    onSuccess: (r) => {
      toast.success(`Transition : ${r.from_state} → ${r.to_state}`);
      qc.invalidateQueries({ queryKey: [`${kind}-list`] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const valid = eventsFrom(def, state);
  const tone  = fsmStateColor(kind, state);
  const ex    = SEQUENCE_EXAMPLES[kind];

  if (listQ.isError)
    return <ErrorState error={listQ.error} onRetry={() => listQ.refetch()} />;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        {/* ── Left panel ───────────────────────────────────────────────── */}
        <div className="space-y-4">
          <div className="glass-card rounded-xl p-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sélection</p>
            {listQ.isLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={selectedId ?? ""} onValueChange={setSelectedId}>
                <SelectTrigger>
                  <SelectValue placeholder={`Choisir un ${kind}…`} />
                </SelectTrigger>
                <SelectContent>
                  {items.slice(0, 50).map((it) => (
                    <SelectItem key={String(it.id)} value={String(it.id)}>
                      <span className="font-mono text-xs">{String(it.id)}</span>
                      {" — "}
                      {it.nom || it.modele || it.description || "—"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {current && (
              <div className="mt-4 space-y-2 border-t pt-3">
                <p className="text-xs text-muted-foreground">État actuel</p>
                <Badge className={cn(
                  "text-xs",
                  tone === "success"     && "bg-success text-success-foreground",
                  tone === "warning"     && "bg-warning text-warning-foreground",
                  tone === "destructive" && "bg-destructive text-destructive-foreground",
                  tone === "primary"     && "bg-primary text-primary-foreground",
                  tone === "muted"       && "bg-muted text-muted-foreground",
                )}>
                  {state}
                </Badge>
              </div>
            )}
          </div>

          {current && (
            <div className="glass-card rounded-xl p-4">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">Événements valides</p>
              {valid.length === 0 ? (
                <p className="text-xs text-muted-foreground">État terminal — aucune transition disponible.</p>
              ) : (
                <div className="space-y-2">
                  {valid.map((t) => (
                    <Button
                      key={`${t.event}-${t.to}`}
                      size="sm" variant="outline"
                      className="w-full justify-between"
                      disabled={eventM.isPending}
                    >
                      <span className="font-mono text-xs">{t.event}</span>
                      <span className="text-[10px] text-muted-foreground">→ {t.to}</span>
                    </Button>
                  ))}
                  {eventM.isPending && (
                    <div className="flex items-center justify-center pt-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="glass-card rounded-xl p-4">
            <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">Table de transition</p>
            <div className="space-y-1 text-xs">
              {def.transitions.map((t, i) => (
                <div key={i} className={cn(
                  "grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded px-2 py-1 font-mono",
                  t.from === state && "bg-accent/10 text-accent",
                )}>
                  <span className="truncate">{t.from}</span>
                  <span className="text-[10px] text-muted-foreground">{t.event} →</span>
                  <span className="truncate">{t.to}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Graphviz diagram ─────────────────────────────────────────── */}
        <div className="glass-card h-[420px] overflow-hidden rounded-xl p-2">
          <FsmDiagram def={def} kind={kind} currentState={state} />
        </div>
      </div>

      {/* ── Sequence Validator (full width below) ────────────────────── */}
      <SequenceValidator
        def={def}
        kind={kind}
        examples={ex.seqs}
        exampleLabels={ex.labels}
      />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Fsm() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Automates à états finis"
        subtitle="Visualisez et pilotez les transitions FSM des capteurs, interventions et véhicules."
        icon={<Workflow className="h-5 w-5" />}
      />
      <Tabs defaultValue="capteur">
        <TabsList>
          <TabsTrigger value="capteur">Capteurs</TabsTrigger>
          <TabsTrigger value="intervention">Interventions</TabsTrigger>
          <TabsTrigger value="vehicule">Véhicules</TabsTrigger>
        </TabsList>
        <TabsContent value="capteur" className="mt-4">
          <FsmPanel kind="capteur" def={capteurFsm} />
        </TabsContent>
        <TabsContent value="intervention" className="mt-4">
          <FsmPanel kind="intervention" def={interventionFsm} />
        </TabsContent>
        <TabsContent value="vehicule" className="mt-4">
          <FsmPanel kind="vehicule" def={vehiculeFsm} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
