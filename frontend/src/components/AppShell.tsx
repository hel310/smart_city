import { NavLink, Outlet } from "react-router-dom";
import { Activity, BarChart3, Database, Moon, Sparkles, Sun, Terminal, Workflow } from "lucide-react";
import { BackendStatus } from "./BackendStatus";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Tableau de bord", icon: BarChart3, end: true },
  { to: "/compiler", label: "Compilateur NL→SQL", icon: Terminal },
  { to: "/fsm", label: "Automates FSM", icon: Workflow },
  { to: "/ai", label: "Rapports IA", icon: Sparkles },
  { to: "/data", label: "Données & Stats", icon: Database },
];

export const AppShell = () => {
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-background bg-gradient-glow">
      {/* Sidebar (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r bg-sidebar lg:flex">
        <div className="flex items-center gap-3 border-b px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg hero-gradient shadow-glow">
            <Activity className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-bold leading-tight">Neo-Sousse</h1>
            <p className="text-[11px] font-medium text-muted-foreground">Smart City 2030</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-3 border-t p-4">
          <BackendStatus />
          <button
            onClick={toggle}
            className="flex w-full items-center justify-center gap-2 rounded-lg border bg-card/50 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            {theme === "dark" ? "Mode clair" : "Mode sombre"}
          </button>
          <p className="text-center text-[10px] text-muted-foreground">v1.0 · FSM · IA · NL→SQL</p>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b bg-background/80 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md hero-gradient">
            <Activity className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-bold leading-tight">Neo-Sousse 2030</h1>
            <BackendStatus compact />
          </div>
        </div>
        <button onClick={toggle} className="rounded-md border p-2">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </header>

      <main className="lg:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-6 pb-24 lg:px-8 lg:py-8 lg:pb-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t bg-background/95 backdrop-blur lg:hidden">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex flex-1 flex-col items-center gap-1 px-1 py-2 text-[10px] font-medium",
                isActive ? "text-accent" : "text-muted-foreground",
              )
            }
          >
            <Icon className="h-5 w-5" />
            <span className="truncate">{label.split(" ")[0]}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
};
