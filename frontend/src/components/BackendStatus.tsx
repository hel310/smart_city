import { useQuery } from "@tanstack/react-query";
import { api, API_BASE_URL } from "@/lib/api";
import { cn } from "@/lib/utils";

export const BackendStatus = ({ compact = false }: { compact?: boolean }) => {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15000,
    retry: 1,
  });

  const ok = !isError && data?.status?.toLowerCase() === "ok";
  const color = isLoading ? "bg-muted-foreground" : ok ? "bg-success" : "bg-destructive";
  const label = isLoading ? "Connexion…" : ok ? "Backend en ligne" : "Backend hors-ligne";

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className={cn("h-2 w-2 rounded-full pulse-dot", color)} />
        <span>{label}</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card/50 p-3">
      <div className="flex items-center gap-2">
        <span className={cn("h-2.5 w-2.5 rounded-full pulse-dot", color)} />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{API_BASE_URL}</p>
    </div>
  );
};
