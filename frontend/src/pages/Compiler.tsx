import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Loader2, Play, Sparkles, Terminal, AlertTriangle,
  CheckCircle2, XCircle, Database, Code2, Braces, Search
} from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import type { CompileResult, QueryResult, TokenInfo } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/* ── Example queries covering all query types ─────────────────────────────── */
const EXAMPLES = [
  { nl: "Affiche les capteurs", type: "SELECT" },
  { nl: "Affiche les 5 zones les plus polluées", type: "SELECT" },
  { nl: "Combien de capteurs sont hors service ?", type: "SELECT" },
  { nl: "Quels citoyens ont un score écologique > 80 ?", type: "SELECT" },
  { nl: "Donne-moi le trajet le plus économique en CO2", type: "SELECT" },
  { nl: "Quelles interventions sont en cours ?", type: "SELECT" },
  { nl: "Capteurs qui ne sont pas actifs", type: "SELECT" },
  { nl: "Capteurs signalé", type: "SELECT" },
  { nl: "Supprimer les capteurs hors service", type: "DELETE" },
  { nl: "Modifier le statut des capteurs signalé", type: "UPDATE" },
];

/* ── Token color mapping ──────────────────────────────────────────────────── */
const TOKEN_COLORS: Record<string, string> = {
  SHOW: "#3b82f6", SELECT: "#3b82f6", COUNT: "#3b82f6",
  DELETE: "#ef4444", UPDATE: "#f59e0b", INSERT: "#22c55e",
  CAPTEURS: "#10b981", INTERVENTIONS: "#10b981", CITOYENS: "#10b981",
  VEHICULES: "#10b981", MESURES: "#10b981", ZONES: "#10b981", TRAJETS: "#10b981",
  POLLUTION: "#f97316", SCORE_ECOLO: "#f97316", STATUT: "#f97316",
  TAUX_ERREUR: "#f97316", ECO_CO2: "#f97316", NOM: "#f97316", TYPE: "#f97316",
  GT: "#a855f7", LT: "#a855f7", GTE: "#a855f7", LTE: "#a855f7",
  EQ: "#a855f7", NEQ: "#a855f7",
  NUMBER: "#c084fc", STRING: "#c084fc", STATUS_VAL: "#06b6d4",
  WHERE: "#6366f1", AND: "#6366f1", OR: "#6366f1",
  NEG: "#ef4444",
  DESC_ORDER: "#8b5cf6", ASC_ORDER: "#8b5cf6", ORDER: "#8b5cf6",
  LIMIT: "#6b7280", GROUP: "#6b7280",
  AVG: "#ec4899", MAX: "#ec4899", MIN: "#ec4899", SUM: "#ec4899",
  UNKNOWN: "#475569",
};

/* ── Query type badge config ──────────────────────────────────────────────── */
const QUERY_TYPE_CONFIG: Record<string, { color: string; label: string; icon: string }> = {
  SELECT: { color: "bg-blue-500/20 text-blue-400 border-blue-500/30", label: "SELECT", icon: "🔍" },
  DELETE: { color: "bg-red-500/20 text-red-400 border-red-500/30", label: "DELETE", icon: "🗑️" },
  UPDATE: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "UPDATE", icon: "✏️" },
  INSERT: { color: "bg-green-500/20 text-green-400 border-green-500/30", label: "INSERT", icon: "➕" },
};

/* ── Example type badge config ────────────────────────────────────────────── */
const EXAMPLE_TYPE_COLORS: Record<string, string> = {
  SELECT: "border-blue-500/40 text-blue-400",
  DELETE: "border-red-500/40 text-red-400",
  UPDATE: "border-amber-500/40 text-amber-400",
  INSERT: "border-green-500/40 text-green-400",
};

export default function Compiler() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<(CompileResult | QueryResult) | null>(null);
  const [compileError, setCompileError] = useState<{
    error: string;
    error_pos?: number;
    error_arrow?: string;
    expected?: string;
    tokens?: TokenInfo[];
  } | null>(null);

  const compileM = useMutation({
    mutationFn: (q: string) => api.compilerCompile(q),
    onSuccess: (r) => {
      setResult(r);
      setCompileError(null);
      toast.success("Requête compilée avec succès");
    },
    onError: (e: Error) => {
      setResult(null);
      try {
        // Try to extract structured error from the response
        const msg = e.message;
        const jsonMatch = msg.match(/\{.*\}/s);
        if (jsonMatch) {
          const errorData = JSON.parse(jsonMatch[0]);
          setCompileError(errorData);
        } else {
          setCompileError({ error: msg });
        }
      } catch {
        setCompileError({ error: e.message });
      }
      toast.error("Erreur de compilation");
    },
  });

  const queryM = useMutation({
    mutationFn: (q: string) => api.compilerQuery(q),
    onSuccess: (r) => {
      setResult(r);
      setCompileError(null);
      const qr = r as QueryResult;
      if (qr.executed) {
        toast.success(`${qr.row_count} ligne(s) retournée(s)`);
      } else {
        toast.info(`Requête ${qr.query_type} compilée (non exécutée)`);
      }
    },
    onError: (e: Error) => {
      setResult(null);
      try {
        const msg = e.message;
        const jsonMatch = msg.match(/\{.*\}/s);
        if (jsonMatch) {
          setCompileError(JSON.parse(jsonMatch[0]));
        } else {
          setCompileError({ error: msg });
        }
      } catch {
        setCompileError({ error: e.message });
      }
      toast.error("Erreur de compilation");
    },
  });

  const isLoading = compileM.isPending || queryM.isPending;
  const queryResult = result as QueryResult | undefined;
  const rows = queryResult?.executed ? queryResult.rows : undefined;
  const cols = rows?.[0] ? Object.keys(rows[0]) : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compilateur NL → SQL"
        subtitle="Décrivez votre besoin en français — le compilateur analyse, compile et exécute les requêtes SELECT. Les requêtes DELETE, UPDATE, INSERT sont compilées mais non exécutées."
        icon={<Terminal className="h-5 w-5" />}
      />

      {/* ── Input area ──────────────────────────────────────────────────── */}
      <div className="glass-card rounded-xl p-5">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ex : Affiche les 5 zones les plus polluées…"
          rows={3}
          className="resize-none border-card-border bg-background/40 font-medium"
        />

        {/* ── Example chips ────────────────────────────────────────────── */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.nl}
              onClick={() => setQuery(ex.nl)}
              className={`rounded-full border bg-background/50 px-3 py-1 text-xs transition-colors hover:bg-accent/10 ${EXAMPLE_TYPE_COLORS[ex.type] || "border-card-border text-muted-foreground"}`}
            >
              {ex.nl.length > 45 ? ex.nl.slice(0, 42) + "…" : ex.nl}
            </button>
          ))}
        </div>

        {/* ── Action buttons ───────────────────────────────────────────── */}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={!query.trim() || isLoading}
            onClick={() => compileM.mutate(query)}
          >
            {compileM.isPending ? <Loader2 className="animate-spin" /> : <Code2 className="h-4 w-4" />}
            Compiler
          </Button>
          <Button
            disabled={!query.trim() || isLoading}
            onClick={() => queryM.mutate(query)}
            className="bg-accent text-accent-foreground hover:bg-accent/90"
          >
            {queryM.isPending ? <Loader2 className="animate-spin" /> : <Play className="h-4 w-4" />}
            Compiler &amp; Exécuter
          </Button>
        </div>
      </div>

      {/* ── Compilation Error Display ───────────────────────────────────── */}
      {compileError && (
        <div className="animate-fade-in glass-card rounded-xl border-red-500/30 p-5">
          <div className="mb-3 flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-400" />
            <h3 className="text-sm font-semibold text-red-400">Erreur de compilation</h3>
          </div>

          {/* Error message */}
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
            <p className="font-mono text-sm text-red-300">{compileError.error}</p>

            {/* Error arrow visualization */}
            {compileError.error_arrow && (
              <pre className="mt-3 overflow-x-auto font-mono text-xs leading-relaxed text-red-400">
                {compileError.error_arrow}
              </pre>
            )}

            {compileError.expected && (
              <p className="mt-2 text-xs text-muted-foreground">
                <span className="text-amber-400">Attendu:</span> {compileError.expected}
              </p>
            )}
          </div>

          {/* Show tokens even on error */}
          {compileError.tokens && compileError.tokens.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-xs font-semibold text-muted-foreground">Tokens analysés avant l'erreur:</h4>
              <div className="flex flex-wrap gap-1">
                {compileError.tokens.map((tok, i) => {
                  const color = TOKEN_COLORS[tok.type] || "#475569";
                  return (
                    <span
                      key={i}
                      className="inline-flex flex-col items-center rounded px-2 py-1 font-mono text-[10px] leading-tight"
                      style={{
                        background: `${color}15`,
                        border: `1px solid ${color}40`,
                        color,
                      }}
                    >
                      <span className="font-semibold">{tok.type}</span>
                      <span className="opacity-70">{tok.value || "·"}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Successful Compilation Result ───────────────────────────────── */}
      {result && (
        <div className="space-y-4 animate-fade-in">

          {/* ── SQL Output ──────────────────────────────────────────────── */}
          <div className="glass-card rounded-xl p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold">SQL Généré</h3>
              </div>
              <div className="flex gap-1.5">
                {/* Query type badge */}
                {result.query_type && QUERY_TYPE_CONFIG[result.query_type] && (
                  <Badge className={`border ${QUERY_TYPE_CONFIG[result.query_type].color}`}>
                    {QUERY_TYPE_CONFIG[result.query_type].icon} {QUERY_TYPE_CONFIG[result.query_type].label}
                  </Badge>
                )}
                {/* Execution status badge */}
                {queryResult?.executed !== undefined && (
                  <Badge className={queryResult.executed
                    ? "border border-green-500/30 bg-green-500/20 text-green-400"
                    : "border border-amber-500/30 bg-amber-500/20 text-amber-400"
                  }>
                    {queryResult.executed ? "✅ Exécuté" : "⏸ Non exécuté"}
                  </Badge>
                )}
                {result.ambiguous && (
                  <Badge className="border border-warning/30 bg-warning/20 text-warning">⚠ Ambiguë</Badge>
                )}
              </div>
            </div>

            {/* SQL code block */}
            <pre className="overflow-x-auto rounded-lg border bg-background/60 p-4 font-mono text-xs leading-relaxed text-foreground">
              <code>{result.sql}</code>
            </pre>

            {/* Ambiguity warning */}
            {result.ambiguity_hint && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                <span>{result.ambiguity_hint}</span>
              </div>
            )}

            {/* Warnings list */}
            {result.warnings?.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs">
                {result.warnings.map((w, i) => (
                  <li key={i} className={
                    w.startsWith("ℹ")
                      ? "text-blue-400"
                      : w.startsWith("⚠")
                        ? "text-amber-400"
                        : "text-muted-foreground"
                  }>
                    {w}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* ── Tokens ──────────────────────────────────────────────────── */}
          {result.tokens && result.tokens.length > 0 && (
            <details className="glass-card rounded-xl p-5">
              <summary className="cursor-pointer text-sm font-semibold flex items-center gap-2">
                <Braces className="h-4 w-4 text-accent" />
                Flux de tokens ({result.tokens.length})
              </summary>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {result.tokens.map((tok, i) => {
                  const color = TOKEN_COLORS[tok.type] || "#475569";
                  return (
                    <span
                      key={i}
                      className="inline-flex flex-col items-center rounded-md px-2.5 py-1.5 font-mono text-[11px] leading-tight transition-transform hover:scale-105"
                      style={{
                        background: `${color}15`,
                        border: `1px solid ${color}40`,
                        color,
                      }}
                    >
                      <span className="font-bold">{tok.type}</span>
                      <span className="mt-0.5 opacity-70">{tok.value || "·"}</span>
                    </span>
                  );
                })}
              </div>
            </details>
          )}

          {/* ── AST ─────────────────────────────────────────────────────── */}
          {result.ast && (
            <details className="glass-card rounded-xl p-5">
              <summary className="cursor-pointer text-sm font-semibold flex items-center gap-2">
                <Search className="h-4 w-4 text-accent" />
                Arbre Syntaxique Abstrait (AST)
              </summary>
              <pre className="mt-3 overflow-x-auto rounded-lg border bg-background/60 p-4 font-mono text-[11px] text-muted-foreground">
                {JSON.stringify(result.ast, null, 2)}
              </pre>
            </details>
          )}

          {/* ── Query Results Table ─────────────────────────────────────── */}
          {queryResult?.executed && rows && (
            <div className="glass-card rounded-xl p-5">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                  <h3 className="text-sm font-semibold">Résultats</h3>
                </div>
                <Badge variant="outline">{queryResult.row_count} ligne(s)</Badge>
              </div>
              {rows.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">Aucune ligne retournée</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {cols.map((c) => (
                          <TableHead key={c} className="font-mono text-[11px] uppercase">{c}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rows.slice(0, 100).map((r, i) => (
                        <TableRow key={i}>
                          {cols.map((c) => (
                            <TableCell key={c} className="font-mono text-xs">
                              {r[c] === null ? <span className="text-muted-foreground">—</span> : String(r[c])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}

          {/* ── Non-executed notice ─────────────────────────────────────── */}
          {queryResult && !queryResult.executed && queryResult.query_type !== "SELECT" && (
            <div className="glass-card rounded-xl border-amber-500/20 p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-400" />
                <div>
                  <h3 className="text-sm font-semibold text-amber-400">
                    Requête {queryResult.query_type} — Compilation uniquement
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Par mesure de sécurité, seules les requêtes <code className="text-blue-400">SELECT</code> sont
                    exécutées sur la base de données. Les requêtes{" "}
                    <code className="text-red-400">DELETE</code>,{" "}
                    <code className="text-amber-400">UPDATE</code> et{" "}
                    <code className="text-green-400">INSERT</code> sont compilées
                    et validées syntaxiquement mais non exécutées.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}