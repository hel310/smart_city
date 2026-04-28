import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  loading?: boolean;
  className?: string;
}

export const PageHeader = ({ title, subtitle, icon, actions, loading, className }: PageHeaderProps) => (
  <div className={cn("mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
    <div className="flex items-start gap-3">
      {icon && (
        <div className="mt-1 flex h-11 w-11 items-center justify-center rounded-xl hero-gradient shadow-glow text-primary-foreground">
          {icon}
        </div>
      )}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight lg:text-3xl">
          {title}
          {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
);
