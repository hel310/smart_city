import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  Loader2, Sparkles, Wand2, Workflow, FileText, Copy, Check,
  CheckCircle2, XCircle, AlertTriangle, ClipboardList,
} from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import type { ReportType, AiEntity, AiFsmMeta, AiFsmEventOption } from "@/lib/types";

const REPORT_TYPES: { value: ReportType; label: string; icon: string }[] = [
  { value: "sensors", label: "Capteurs", icon: "🔧" },
  { value: "interventions", label: "Interventions", icon: "🛠️" },
  { value: "air_quality", label: "Qualité de l'air", icon: "🌿" },
  { value: "citizens", label: "Citoyens", icon: "👥" },
  { value: "vehicles", label: "Véhicules", icon: "🚗" },
];
const ENTITY_TYPES = [
  { value: "capteur", label: "Capteur" },
  { value: "intervention", label: "Intervention" },
  { value: "vehicule", label: "Véhicule" },
];
const TABS = [
  { id: "reports", label: "Rapports", icon: FileText },
  { id: "suggest", label: "Suggestions", icon: Wand2 },
  { id: "fsm", label: "Validation FSM", icon: Workflow },
] as const;
type TabId = (typeof TABS)[number]["id"];

function CopyBtn({ text }: { text: string }) {
  const [c, setC] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setC(true); setTimeout(() => setC(false), 2000); }}
      className="inline-flex items-center gap-1.5 rounded-md border border-border/60 bg-card/50 px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-all hover:bg-card hover:text-foreground">
      {c ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
      {c ? "Copié !" : "Copier"}
    </button>
  );
}

function Typing() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-accent/20 bg-accent/5 p-5">
      <div className="flex gap-1">
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:0ms]" />
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:150ms]" />
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:300ms]" />
      </div>
      <span className="text-sm text-muted-foreground">L'IA génère votre réponse…</span>
    </div>
  );
}

export default function Ai() {
  const [activeTab, setActiveTab] = useState<TabId>("reports");

  // ── Reports ──
  const [reportType, setReportType] = useState<ReportType>("air_quality");
  const [nRows, setNRows] = useState(50);
  const reportM = useMutation({ mutationFn: () => api.aiReport({ report_type: reportType, n_rows: nRows }), onSuccess: () => toast.success("Rapport généré"), onError: (e: Error) => toast.error(e.message) });
  const statusM = useMutation({ mutationFn: () => api.aiStatusReport(), onSuccess: () => toast.success("Rapport de statut généré"), onError: (e: Error) => toast.error(e.message) });

  // ── Suggest ──
  const [sugEntityType, setSugEntityType] = useState("capteur");
  const [sugEntityId, setSugEntityId] = useState("");
  const [sugContext, setSugContext] = useState("");
  const sugEntitiesQ = useQuery({ queryKey: ["ai-entities", sugEntityType], queryFn: () => api.aiEntities(sugEntityType) });
  const sugEntities: AiEntity[] = sugEntitiesQ.data || [];
  const sugSelected = sugEntities.find((e) => e.id === sugEntityId);
  const sugState = sugSelected?.statut || "";
  useEffect(() => { setSugEntityId(""); }, [sugEntityType]);
  const suggestM = useMutation({ mutationFn: () => api.aiSuggest({ entity_type: sugEntityType, entity_id: sugEntityId, state: sugState, context: sugContext }), onSuccess: () => toast.success("Suggestion générée"), onError: (e: Error) => toast.error(e.message) });

  // ── FSM ──
  const [fsmEntityType, setFsmEntityType] = useState("capteur");
  const [fsmEntityId, setFsmEntityId] = useState("");
  const [fsmEvent, setFsmEvent] = useState("");
  const [fsmToState, setFsmToState] = useState("");
  const fsmEntitiesQ = useQuery({ queryKey: ["ai-entities", fsmEntityType], queryFn: () => api.aiEntities(fsmEntityType) });
  const fsmMetaQ = useQuery({ queryKey: ["ai-fsm-meta", fsmEntityType], queryFn: () => api.aiFsmMeta(fsmEntityType) });
  const fsmEntities: AiEntity[] = fsmEntitiesQ.data || [];
  const fsmMeta: AiFsmMeta | undefined = fsmMetaQ.data;
  const fsmSelected = fsmEntities.find((e) => e.id === fsmEntityId);
  const fsmFromState = fsmSelected?.statut || "";
  
  const allEvents = Array.from(new Set(fsmMeta?.transitions?.map(t => t.event) || []));
  const allStates = fsmMeta?.states || [];

  useEffect(() => { setFsmEntityId(""); setFsmEvent(""); setFsmToState(""); }, [fsmEntityType]);
  useEffect(() => { setFsmEvent(""); setFsmToState(""); }, [fsmEntityId]);

  useEffect(() => {
    if (fsmEvent && fsmFromState && fsmMeta) {
      const t = fsmMeta.transitions?.find(t => t.from_state === fsmFromState && t.event === fsmEvent);
      if (t) setFsmToState(t.to_state);
    }
  }, [fsmEvent, fsmFromState, fsmMeta]);
  const fsmM = useMutation({
    mutationFn: () => api.aiValidateFsm({ entity_type: fsmEntityType, entity_id: fsmEntityId, from_state: fsmFromState, event: fsmEvent, to_state: fsmToState }),
    onSuccess: (d) => toast.success(d.approved ? "Transition approuvée ✅" : "Transition rejetée ❌"),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Module d'IA Générative" subtitle="Rapports analytiques, suggestions intelligentes et validation de transitions — propulsé par Groq AI." icon={<Sparkles className="h-5 w-5" />} />

      {/* Tab Bar */}
      <div className="flex gap-1 rounded-xl border bg-card/50 p-1.5" id="ai-tab-bar">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} id={`ai-tab-${id}`} onClick={() => setActiveTab(id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${activeTab === id ? "bg-accent text-accent-foreground shadow-md shadow-accent/20" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"}`}>
            <Icon className="h-4 w-4" /><span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* ─── TAB 1: Reports ─── */}
      {activeTab === "reports" && (
        <div className="grid gap-6 lg:grid-cols-2 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
          <div className="glass-card space-y-5 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10"><FileText className="h-5 w-5 text-accent" /></div>
              <div><h3 className="text-sm font-semibold">Générateur de rapport</h3><p className="text-xs text-muted-foreground">Synthèse IA à partir des données réelles.</p></div>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Type de rapport</Label>
                <Select value={reportType} onValueChange={(v) => setReportType(v as ReportType)}>
                  <SelectTrigger id="report-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{REPORT_TYPES.map((r) => (<SelectItem key={r.value} value={r.value}>{r.icon} {r.label}</SelectItem>))}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Lignes : <span className="font-mono text-accent">{nRows}</span></Label>
                <Slider value={[nRows]} min={10} max={500} step={10} onValueChange={(v) => setNRows(v[0])} />
              </div>
              <div className="flex gap-2">
                <Button id="generate-report-btn" className="flex-1 bg-accent text-accent-foreground hover:bg-accent/90 shadow-md shadow-accent/20" disabled={reportM.isPending} onClick={() => reportM.mutate()}>
                  {reportM.isPending ? <Loader2 className="animate-spin" /> : <Sparkles className="h-4 w-4" />} Générer le rapport
                </Button>
                <Button id="generate-status-btn" variant="outline" disabled={statusM.isPending} onClick={() => statusM.mutate()}>
                  {statusM.isPending ? <Loader2 className="animate-spin" /> : <ClipboardList className="h-4 w-4" />}<span className="hidden sm:inline">Statut global</span>
                </Button>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            {(reportM.isPending || statusM.isPending) && <Typing />}
            {reportM.data && !reportM.isPending && (
              <div className="glass-card rounded-xl p-6 animate-in fade-in-0 duration-500">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground"><Sparkles className="h-3.5 w-3.5 text-accent" /><span>{REPORT_TYPES.find((r) => r.value === reportM.data!.report_type)?.icon} {REPORT_TYPES.find((r) => r.value === reportM.data!.report_type)?.label}</span><span className="rounded-full bg-secondary px-2 py-0.5 font-mono text-[10px]">{reportM.data.row_count} lignes</span></div>
                  <CopyBtn text={reportM.data.report} />
                </div>
                <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:text-foreground/85"><ReactMarkdown>{reportM.data.report}</ReactMarkdown></article>
              </div>
            )}
            {statusM.data && !statusM.isPending && (
              <div className="glass-card rounded-xl p-6 animate-in fade-in-0 duration-500">
                <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-xs text-muted-foreground"><ClipboardList className="h-3.5 w-3.5 text-accent" /><span>📊 Rapport de statut global</span></div><CopyBtn text={statusM.data.report} /></div>
                <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:text-foreground/85"><ReactMarkdown>{statusM.data.report}</ReactMarkdown></article>
              </div>
            )}
            {!reportM.data && !statusM.data && !reportM.isPending && !statusM.isPending && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-16 text-center"><FileText className="mb-3 h-10 w-10 text-muted-foreground/40" /><p className="text-sm text-muted-foreground">Sélectionnez un type et cliquez sur « Générer » pour obtenir votre rapport IA.</p></div>
            )}
          </div>
        </div>
      )}

      {/* ─── TAB 2: Suggestions ─── */}
      {activeTab === "suggest" && (
        <div className="grid gap-6 lg:grid-cols-2 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
          <div className="glass-card space-y-5 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10"><Wand2 className="h-5 w-5 text-warning" /></div>
              <div><h3 className="text-sm font-semibold">Moteur de suggestion</h3><p className="text-xs text-muted-foreground">Recommandations IA selon l'état d'une entité.</p></div>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Type d'entité</Label>
                <Select value={sugEntityType} onValueChange={setSugEntityType}>
                  <SelectTrigger id="suggest-entity-type"><SelectValue /></SelectTrigger>
                  <SelectContent>{ENTITY_TYPES.map((e) => (<SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>))}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Entité {sugEntitiesQ.isLoading && <Loader2 className="inline h-3 w-3 animate-spin ml-1" />}</Label>
                <Select value={sugEntityId} onValueChange={setSugEntityId}>
                  <SelectTrigger id="suggest-entity-id"><SelectValue placeholder="Sélectionnez une entité…" /></SelectTrigger>
                  <SelectContent className="max-h-60">
                    {sugEntities.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        <span className="font-mono text-xs">{e.id}</span> — {e.nom} <span className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${e.statut === "ACTIF" || e.statut === "STATIONNE" ? "bg-green-500/10 text-green-600" : e.statut === "HORS_SERVICE" || e.statut === "EN_PANNE" ? "bg-red-500/10 text-red-600" : "bg-yellow-500/10 text-yellow-600"}`}>{e.statut}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {sugSelected && (
                <div className="rounded-lg border border-border/60 bg-secondary/30 p-3">
                  <Label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">État actuel (auto-détecté)</Label>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-md px-3 py-1.5 font-mono text-sm font-semibold ${sugState === "ACTIF" || sugState === "STATIONNE" ? "bg-green-500/10 text-green-600 border border-green-500/20" : sugState === "HORS_SERVICE" || sugState === "EN_PANNE" ? "bg-red-500/10 text-red-600 border border-red-500/20" : "bg-yellow-500/10 text-yellow-600 border border-yellow-500/20"}`}>{sugState}</span>
                    <span className="text-xs text-muted-foreground">({sugSelected.nom})</span>
                  </div>
                </div>
              )}
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Contexte additionnel (optionnel)</Label>
                <Textarea id="suggest-context" rows={3} value={sugContext} onChange={(e) => setSugContext(e.target.value)} placeholder="Informations supplémentaires…" className="resize-none" />
              </div>
              <Button id="suggest-btn" className="w-full shadow-md transition-all" variant="outline" disabled={!sugEntityId || suggestM.isPending} onClick={() => suggestM.mutate()}>
                {suggestM.isPending ? <Loader2 className="animate-spin" /> : <Wand2 className="h-4 w-4" />} Suggérer une action
              </Button>
            </div>
          </div>
          <div>
            {suggestM.isPending && <Typing />}
            {suggestM.data && !suggestM.isPending && (
              <div className="glass-card rounded-xl p-6 animate-in fade-in-0 duration-500">
                <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-warning" /><span className="text-xs font-mono text-muted-foreground">{String(suggestM.data.entity_id)} · {suggestM.data.state}</span></div><CopyBtn text={suggestM.data.suggestion} /></div>
                <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:text-foreground/85"><ReactMarkdown>{suggestM.data.suggestion}</ReactMarkdown></article>
              </div>
            )}
            {!suggestM.data && !suggestM.isPending && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-16 text-center"><Wand2 className="mb-3 h-10 w-10 text-muted-foreground/40" /><p className="text-sm text-muted-foreground">Sélectionnez une entité pour obtenir des recommandations IA.</p></div>
            )}
          </div>
        </div>
      )}

      {/* ─── TAB 3: FSM Validation ─── */}
      {activeTab === "fsm" && (
        <div className="grid gap-6 lg:grid-cols-2 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
          <div className="glass-card space-y-5 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10"><Workflow className="h-5 w-5 text-primary" /></div>
              <div><h3 className="text-sm font-semibold">Validation IA des transitions</h3><p className="text-xs text-muted-foreground">L'IA évalue la cohérence métier d'une transition FSM.</p></div>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Type d'entité</Label>
                <Select value={fsmEntityType} onValueChange={setFsmEntityType}>
                  <SelectTrigger id="fsm-entity-type"><SelectValue /></SelectTrigger>
                  <SelectContent>{ENTITY_TYPES.map((e) => (<SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>))}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-1.5 block text-xs font-medium">Entité {fsmEntitiesQ.isLoading && <Loader2 className="inline h-3 w-3 animate-spin ml-1" />}</Label>
                <Select value={fsmEntityId} onValueChange={setFsmEntityId}>
                  <SelectTrigger id="fsm-entity-id"><SelectValue placeholder="Sélectionnez une entité…" /></SelectTrigger>
                  <SelectContent className="max-h-60">
                    {fsmEntities.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        <span className="font-mono text-xs">{e.id}</span> — {e.nom} <span className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${e.statut === "ACTIF" || e.statut === "STATIONNE" ? "bg-green-500/10 text-green-600" : e.statut === "HORS_SERVICE" || e.statut === "EN_PANNE" ? "bg-red-500/10 text-red-600" : "bg-yellow-500/10 text-yellow-600"}`}>{e.statut}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Transition visual */}
              {fsmSelected && (
                <div className="rounded-lg border border-border/60 bg-secondary/30 p-4 space-y-3">
                  <Label className="block text-xs font-medium text-center text-muted-foreground">Transition à valider</Label>
                  <div className="flex items-center gap-2">
                    {/* FROM state — read only */}
                    <div className="flex-1 text-center">
                      <div className="text-[10px] text-muted-foreground mb-1">État actuel</div>
                      <div className={`rounded-md px-3 py-2 font-mono text-sm font-semibold border ${fsmFromState === "ACTIF" || fsmFromState === "STATIONNE" ? "bg-green-500/10 text-green-600 border-green-500/20" : fsmFromState === "HORS_SERVICE" || fsmFromState === "EN_PANNE" ? "bg-red-500/10 text-red-600 border-red-500/20" : "bg-yellow-500/10 text-yellow-600 border-yellow-500/20"}`}>{fsmFromState}</div>
                    </div>
                    {/* Event dropdown */}
                    <div className="flex flex-col items-center gap-1">
                      <div className="text-[10px] text-muted-foreground">événement</div>
                      <div className="flex items-center gap-1">
                        <span className="text-muted-foreground">─</span>
                        <Select value={fsmEvent} onValueChange={setFsmEvent}>
                          <SelectTrigger id="fsm-event" className="w-40 font-mono text-xs"><SelectValue placeholder="choisir…" /></SelectTrigger>
                          <SelectContent>
                            {allEvents.length > 0 ? allEvents.map((ev) => (
                              <SelectItem key={ev} value={ev}>{ev}</SelectItem>
                            )) : <SelectItem value="__none" disabled>Aucun événement</SelectItem>}
                          </SelectContent>
                        </Select>
                        <span className="text-muted-foreground">→</span>
                      </div>
                    </div>
                    {/* TO state — auto */}
                    <div className="flex-1 text-center">
                      <div className="text-[10px] text-muted-foreground mb-1">État cible</div>
                      <Select value={fsmToState} onValueChange={setFsmToState}>
                        <SelectTrigger id="fsm-to-state" className={`h-10 px-3 py-2 font-mono text-sm font-semibold border ${fsmToState ? "bg-blue-500/10 text-blue-600 border-blue-500/20" : "bg-muted text-muted-foreground border-border"}`}>
                          <SelectValue placeholder="choisir…" />
                        </SelectTrigger>
                        <SelectContent>
                          {allStates.map((st) => (
                            <SelectItem key={st} value={st}>{st}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}

              <Button id="fsm-validate-btn" className="w-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-md transition-all" disabled={!fsmEntityId || !fsmEvent || !fsmToState || fsmM.isPending} onClick={() => fsmM.mutate()}>
                {fsmM.isPending ? <Loader2 className="animate-spin" /> : <Workflow className="h-4 w-4" />} Valider la transition
              </Button>
            </div>
          </div>

          {/* FSM Result */}
          <div>
            {fsmM.isPending && <Typing />}
            {fsmM.data && !fsmM.isPending && (
              <div className={`glass-card rounded-xl p-6 animate-in fade-in-0 duration-500 ${fsmM.data.approved ? "border-l-4 border-l-green-500" : "border-l-4 border-l-red-500"}`}>
                <div className="mb-5 flex items-center gap-3">
                  {fsmM.data.approved ? (
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10"><CheckCircle2 className="h-7 w-7 text-green-500" /></div>
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10"><XCircle className="h-7 w-7 text-red-500" /></div>
                  )}
                  <div>
                    <h4 className="text-lg font-bold">{fsmM.data.approved ? "Transition Approuvée" : "Transition Rejetée"}</h4>
                    <p className="text-xs text-muted-foreground">{fsmM.data.entity_type} · {fsmM.data.entity_id}</p>
                  </div>
                </div>
                <div className="mb-5 flex items-center justify-center gap-3 rounded-lg bg-secondary/40 px-4 py-3">
                  <span className="rounded-md bg-card px-3 py-1.5 font-mono text-sm font-medium">{fsmM.data.from_state}</span>
                  <span className="text-xs text-muted-foreground">─[<span className="font-semibold text-accent">{fsmM.data.event}</span>]→</span>
                  <span className="rounded-md bg-card px-3 py-1.5 font-mono text-sm font-medium">{fsmM.data.to_state}</span>
                </div>
                <div className="rounded-lg border bg-background/50 p-4">
                  <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Analyse IA</h5>
                  <article className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{fsmM.data.reasoning}</ReactMarkdown></article>
                </div>
              </div>
            )}
            {!fsmM.data && !fsmM.isPending && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-16 text-center">
                <Workflow className="mb-3 h-10 w-10 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground font-medium mb-2">Sélectionnez une entité et un événement pour valider la transition.</p>
                <div className="max-w-xl space-y-2 text-xs text-muted-foreground/80">
                  <p>
                    Le validateur basé sur l’IA générative enrichit le moteur d’automates en apportant une validation contextuelle et intelligente.
                  </p>
                  <p>
                    Il ne se limite pas à vérifier les transitions autorisées, mais analyse leur cohérence métier, détecte les anomalies, fournit des explications et propose des actions correctives.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
