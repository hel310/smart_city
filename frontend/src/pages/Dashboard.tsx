import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Activity, AlertTriangle, Cpu, Leaf, Wind } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fsmStateColor } from "@/lib/fsm";
import { cn } from "@/lib/utils";

const KpiCard = ({
  label,
  value,
  unit,
  icon: Icon,
  hint,
  loading,
  tone = "primary",
}: {
  label: string;
  value: string | number;
  unit?: string;
  icon: React.ElementType;
  hint?: string;
  loading?: boolean;
  tone?: "primary" | "success" | "warning" | "destructive";
}) => {
  const toneClass = {
    primary: "from-primary/20 to-accent/10 text-accent",
    success: "from-success/20 to-success/5 text-success",
    warning: "from-warning/20 to-warning/5 text-warning",
    destructive: "from-destructive/20 to-destructive/5 text-destructive",
  }[tone];

  return (
    <div className="glass-card relative overflow-hidden rounded-xl p-5">
      <div className={cn("absolute -right-8 -top-8 h-32 w-32 rounded-full bg-gradient-to-br opacity-60 blur-2xl", toneClass)} />
      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-9 w-24" />
          ) : (
            <p className="mt-2 flex items-baseline gap-1 text-3xl font-bold tabular-nums count-up">
              {value}
              {unit && <span className="text-base font-medium text-muted-foreground">{unit}</span>}
            </p>
          )}
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <div className={cn("rounded-lg p-2", toneClass)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
};

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card rounded-md px-3 py-2 text-xs shadow-card">
      <p className="font-semibold">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="tabular-nums" style={{ color: p.color }}>
          {p.name}: {Number(p.value).toFixed(1)}
        </p>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [selectedZone, setSelectedZone] = useState<string>("all");

  const kpiQ = useQuery({ queryKey: ["capteurKpi"], queryFn: api.capteurKpi });
  const interQ = useQuery({ queryKey: ["interventions"], queryFn: () => api.interventions({ limit: 200 }) });
  const pollutionQ = useQuery({ queryKey: ["pollutionParZone"], queryFn: api.pollutionParZone });
  const citoyensQ = useQuery({ queryKey: ["citoyenStats"], queryFn: api.citoyenStats });
  const zonesQ = useQuery({ queryKey: ["zones"], queryFn: api.zones });
  const serieQ = useQuery({
    queryKey: ["serieTemporelle", selectedZone],
    queryFn: () => api.serieTemporelle(selectedZone === "all" ? undefined : Number(selectedZone)),
  });
  const capteursQ = useQuery({ queryKey: ["capteurs"], queryFn: () => api.capteurs({ limit: 500 }) });

  const anyError = [kpiQ, interQ, pollutionQ, citoyensQ].find((q) => q.isError);
  if (anyError) return <ErrorState error={anyError.error} onRetry={() => anyError.refetch()} />;

  const interventionsActives = (interQ.data || []).filter((i) => i.statut !== "TERMINÉ");
  const pollutionMoyenne = pollutionQ.data?.length
    ? pollutionQ.data.reduce((s, p) => s + p.pollution, 0) / pollutionQ.data.length
    : 0;

  const alerteCapteurs = (capteursQ.data || []).filter(
    (c) => c.statut === "SIGNALÉ" || c.statut === "HORS_SERVICE",
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tableau de bord"
        subtitle="Vue temps-réel de l'écosystème Smart City — capteurs, interventions, qualité de l'air et engagement citoyen."
        icon={<Activity className="h-5 w-5" />}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Capteurs actifs"
          value={kpiQ.data?.actifs ?? "—"}
          hint={`/${kpiQ.data?.total ?? 0} déployés`}
          icon={Cpu}
          loading={kpiQ.isLoading}
          tone="success"
        />
        <KpiCard
          label="Interventions en cours"
          value={interventionsActives.length}
          hint={`${interQ.data?.length ?? 0} au total`}
          icon={AlertTriangle}
          loading={interQ.isLoading}
          tone="warning"
        />
        <KpiCard
          label="Pollution moyenne"
          value={pollutionMoyenne.toFixed(1)}
          unit="µg/m³"
          icon={Wind}
          loading={pollutionQ.isLoading}
          tone="primary"
        />
        <KpiCard
          label="Score écolo moyen"
          value={citoyensQ.data?.score_moyen?.toFixed(1) ?? "—"}
          unit="/100"
          hint={`${citoyensQ.data?.haute_ecologie ?? 0} ambassadeurs`}
          icon={Leaf}
          loading={citoyensQ.isLoading}
          tone="success"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass-card rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Pollution par zone</h3>
              <p className="text-xs text-muted-foreground">Niveau moyen mesuré (µg/m³)</p>
            </div>
          </div>
          {pollutionQ.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={pollutionQ.data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="pollutionGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.7} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="zone" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted) / 0.3)" }} />
                <Bar dataKey="pollution" fill="url(#pollutionGrad)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="glass-card rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold">Évolution temporelle</h3>
              <p className="text-xs text-muted-foreground">Pollution sur les derniers jours</p>
            </div>
            <Select value={selectedZone} onValueChange={setSelectedZone}>
              <SelectTrigger className="h-8 w-40 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes les zones</SelectItem>
                {(zonesQ.data || []).map((z) => (
                  <SelectItem key={z.id} value={String(z.id)}>
                    {z.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {serieQ.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={serieQ.data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="hsl(var(--primary-glow))" />
                    <stop offset="100%" stopColor="hsl(var(--accent))" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="pollution"
                  stroke="url(#lineGrad)"
                  strokeWidth={2.5}
                  dot={{ fill: "hsl(var(--accent))", r: 3 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Alerts */}
      <div className="glass-card rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold">Alertes actives</h3>
            <p className="text-xs text-muted-foreground">Capteurs défaillants et interventions en cours</p>
          </div>
          <Badge variant="outline" className="font-mono">
            {alerteCapteurs.length + interventionsActives.length}
          </Badge>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Capteurs</p>
            <div className="space-y-2">
              {alerteCapteurs.slice(0, 6).map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg border bg-card/40 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{c.nom}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{c.id} · {c.type}</p>
                  </div>
                  <Badge
                    className={cn(
                      "text-[10px]",
                      fsmStateColor("capteur", c.statut) === "destructive" && "bg-destructive text-destructive-foreground",
                      fsmStateColor("capteur", c.statut) === "warning" && "bg-warning text-warning-foreground",
                    )}
                  >
                    {c.statut}
                  </Badge>
                </div>
              ))}
              {!capteursQ.isLoading && alerteCapteurs.length === 0 && (
                <p className="text-xs text-muted-foreground">Aucun capteur en alerte ✓</p>
              )}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Interventions</p>
            <div className="space-y-2">
              {interventionsActives.slice(0, 6).map((i) => (
                <div
                  key={i.id}
                  className="flex items-center justify-between rounded-lg border bg-card/40 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">#{i.id} — {i.description}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">capteur {i.capteur_id} · prio {i.priorite}</p>
                  </div>
                  <Badge variant="outline" className="text-[10px]">{i.statut}</Badge>
                </div>
              ))}
              {!interQ.isLoading && interventionsActives.length === 0 && (
                <p className="text-xs text-muted-foreground">Aucune intervention en cours ✓</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
