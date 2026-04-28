import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDown, ArrowUp, Database } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

type TableKey = "capteurs" | "interventions" | "citoyens" | "vehicules" | "mesures" | "zones" | "trajets";

const FETCHERS: Record<TableKey, () => Promise<any[]>> = {
  capteurs: () => api.capteurs({ limit: 500 }),
  interventions: () => api.interventions({ limit: 500 }),
  citoyens: () => api.citoyens({ limit: 500 }),
  vehicules: () => api.vehicules({ limit: 500 }),
  mesures: () => api.mesures({ limit: 500 }),
  zones: () => api.zones(),
  trajets: () => api.trajets({ limit: 500 }),
};

const TABLE_LABELS: Record<TableKey, string> = {
  capteurs: "Capteurs",
  interventions: "Interventions",
  citoyens: "Citoyens",
  vehicules: "Véhicules",
  mesures: "Mesures",
  zones: "Zones",
  trajets: "Trajets",
};

const PAGE_SIZE = 25;

function describe(values: number[]) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const sum = values.reduce((s, v) => s + v, 0);
  const mean = sum / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  return {
    count: values.length,
    mean,
    min: sorted[0],
    max: sorted[sorted.length - 1],
    median: sorted[Math.floor(sorted.length / 2)],
    std: Math.sqrt(variance),
  };
}

export default function Data() {
  const [tableKey, setTableKey] = useState<TableKey>("capteurs");
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const q = useQuery({ queryKey: ["data-table", tableKey], queryFn: FETCHERS[tableKey] });

  const cols = q.data?.[0] ? Object.keys(q.data[0]) : [];

  const filtered = useMemo(() => {
    let rows = q.data || [];
    if (filter) {
      const f = filter.toLowerCase();
      rows = rows.filter((r) => Object.values(r).some((v) => String(v ?? "").toLowerCase().includes(f)));
    }
    if (sortKey) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av === bv) return 0;
        const cmp = av > bv ? 1 : -1;
        return sortDir === "asc" ? cmp : -cmp;
      });
    }
    return rows;
  }, [q.data, filter, sortKey, sortDir]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  // Numeric stats
  const numericStats = useMemo(() => {
    if (!q.data?.length) return [];
    const stats: { col: string; s: ReturnType<typeof describe> }[] = [];
    for (const c of cols) {
      const vals = q.data.map((r) => r[c]).filter((v) => typeof v === "number" && !Number.isNaN(v));
      if (vals.length > q.data.length * 0.5) {
        const s = describe(vals as number[]);
        if (s) stats.push({ col: c, s });
      }
    }
    return stats;
  }, [q.data, cols]);

  // Conditional viz
  const mesuresSeries = useMemo(() => {
    if (tableKey !== "mesures" || !q.data) return null;
    return [...q.data]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(-50)
      .map((m) => ({ t: new Date(m.timestamp).toLocaleDateString(), pollution: m.pollution }));
  }, [tableKey, q.data]);

  const citoyensHisto = useMemo(() => {
    if (tableKey !== "citoyens" || !q.data) return null;
    const buckets = Array.from({ length: 10 }, (_, i) => ({ bucket: `${i * 10}-${i * 10 + 9}`, n: 0 }));
    q.data.forEach((c: any) => {
      const idx = Math.min(9, Math.floor((c.score_ecolo || 0) / 10));
      buckets[idx].n += 1;
    });
    return buckets;
  }, [tableKey, q.data]);

  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;

  const toggleSort = (c: string) => {
    if (sortKey === c) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(c); setSortDir("asc"); }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Données & Statistiques"
        subtitle="Explorez les tables Smart City avec tri, filtre, pagination et statistiques descriptives."
        icon={<Database className="h-5 w-5" />}
      />

      <div className="glass-card flex flex-wrap items-center gap-3 rounded-xl p-4">
        <Select value={tableKey} onValueChange={(v) => { setTableKey(v as TableKey); setPage(0); setSortKey(null); }}>
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            {(Object.keys(TABLE_LABELS) as TableKey[]).map((k) => (
              <SelectItem key={k} value={k}>{TABLE_LABELS[k]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Filtrer toutes les colonnes…"
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setPage(0); }}
          className="max-w-xs"
        />
        <Badge variant="outline" className="ml-auto font-mono">
          {filtered.length} ligne{filtered.length > 1 ? "s" : ""}
        </Badge>
      </div>

      {(mesuresSeries || citoyensHisto) && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">
            {tableKey === "mesures" ? "Évolution de la pollution (50 dernières mesures)" : "Distribution des scores écologiques"}
          </h3>
          {q.isLoading ? (
            <Skeleton className="h-60 w-full" />
          ) : mesuresSeries ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={mesuresSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                <Line type="monotone" dataKey="pollution" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={citoyensHisto!}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="bucket" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                <Bar dataKey="n" fill="hsl(var(--success))" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {numericStats.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold">Statistiques descriptives</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {numericStats.map(({ col, s }) => s && (
              <div key={col} className="rounded-lg border bg-background/40 p-3">
                <p className="mb-2 font-mono text-xs font-semibold text-accent">{col}</p>
                <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs tabular-nums">
                  <dt className="text-muted-foreground">Moyenne</dt><dd>{s.mean.toFixed(2)}</dd>
                  <dt className="text-muted-foreground">Médiane</dt><dd>{s.median.toFixed(2)}</dd>
                  <dt className="text-muted-foreground">Min</dt><dd>{s.min.toFixed(2)}</dd>
                  <dt className="text-muted-foreground">Max</dt><dd>{s.max.toFixed(2)}</dd>
                  <dt className="text-muted-foreground">Écart-type</dt><dd>{s.std.toFixed(2)}</dd>
                  <dt className="text-muted-foreground">Compte</dt><dd>{s.count}</dd>
                </dl>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden rounded-xl">
        {q.isLoading ? (
          <div className="space-y-2 p-5">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {cols.map((c) => (
                    <TableHead
                      key={c}
                      onClick={() => toggleSort(c)}
                      className="cursor-pointer select-none whitespace-nowrap font-mono text-[11px] uppercase hover:text-accent"
                    >
                      <span className="inline-flex items-center gap-1">
                        {c}
                        {sortKey === c && (sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                      </span>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {paged.map((r, i) => (
                  <TableRow key={i}>
                    {cols.map((c) => (
                      <TableCell key={c} className="whitespace-nowrap font-mono text-xs">
                        {r[c] === null || r[c] === undefined ? <span className="text-muted-foreground">—</span> : String(r[c])}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div className="flex items-center justify-between border-t bg-background/30 px-4 py-2 text-xs">
          <span className="text-muted-foreground">
            Page {page + 1} / {totalPages}
          </span>
          <div className="flex gap-1">
            <Button size="sm" variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Précédent
            </Button>
            <Button size="sm" variant="outline" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
              Suivant
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
