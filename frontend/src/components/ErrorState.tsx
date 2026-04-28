import { AlertCircle, ServerCrash } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const ErrorState = ({ error, onRetry }: { error: unknown; onRetry?: () => void }) => {
  const message = error instanceof Error ? error.message : "Erreur inconnue";
  const isOffline = message.includes("injoignable");
  const Icon = isOffline ? ServerCrash : AlertCircle;
  return (
    <div className="glass-card flex flex-col items-center justify-center gap-3 rounded-xl p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold">{isOffline ? "Backend hors-ligne" : "Erreur de chargement"}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
      {isOffline && (
        <p className="font-mono text-xs text-muted-foreground">
          API : <span className="text-foreground">{API_BASE_URL}</span>
        </p>
      )}
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          Réessayer
        </Button>
      )}
    </div>
  );
};
