import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Home,
  Plus,
  History,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  Moon,
  Sun,
  Receipt,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";
import {
  HealthIndicator,
  type HealthCheck,
  type HealthStatus as HS,
} from "@/components/domain/HealthIndicator";
import { Separator } from "@/components/ui/separator";
import { useHealth } from "@/lib/queries";

const navItems = [
  { to: "/", label: "Dashboard", icon: Home, end: true },
  { to: "/new", label: "Nuovo run", icon: Plus, end: false },
  { to: "/history", label: "Storico", icon: History, end: false },
  { to: "/settings", label: "Impostazioni", icon: Settings, end: false },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { theme, toggle } = useTheme();
  const { data: health, isError: healthError } = useHealth();

  let healthStatus: HS = "unknown";
  let healthChecks: HealthCheck[] = [];
  if (healthError) {
    healthStatus = "down";
  } else if (health) {
    const ficOk = health.fic_token_valid;
    const dbOk = health.db_ok;
    const gmailPersonal = health.gmail_tokens_ok?.personal;
    const gmailBusiness = health.gmail_tokens_ok?.business;
    const anthropicOk = health.anthropic_api_ok;
    const gmailAnyOk = gmailPersonal || gmailBusiness;
    const allOk =
      ficOk && dbOk && gmailPersonal && gmailBusiness && anthropicOk;
    const anyDown = !ficOk || !dbOk || (!gmailAnyOk);
    healthStatus = allOk ? "ok" : anyDown ? "down" : "warn";
    healthChecks = [
      {
        label: "Fatture in Cloud",
        status: ficOk ? "ok" : "down",
        detail: health.company?.name ?? undefined,
      },
      { label: "Database", status: dbOk ? "ok" : "down" },
      {
        label: "Gmail personale",
        status: gmailPersonal ? "ok" : "down",
      },
      {
        label: "Gmail business",
        status: gmailBusiness ? "ok" : "down",
      },
      {
        label: "Anthropic API",
        status: anthropicOk ? "ok" : "warn",
      },
    ];
  }

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-border bg-card/50 backdrop-blur transition-[width] duration-200",
        collapsed ? "w-[56px]" : "w-[240px]",
        className
      )}
      aria-label="Navigazione principale"
    >
      {/* Brand */}
      <div
        className={cn(
          "flex h-14 items-center gap-2 px-3",
          collapsed && "justify-center px-0"
        )}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Receipt className="h-4 w-4" />
        </div>
        {!collapsed && (
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-sm font-semibold">Autofatture</span>
            <span className="truncate text-[10px] uppercase tracking-wide text-muted-foreground">
              Mailift Srl
            </span>
          </div>
        )}
      </div>
      <Separator />

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-3">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground",
                collapsed && "justify-center px-0"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <Separator />
      <div
        className={cn(
          "space-y-2 p-2",
          collapsed && "flex flex-col items-center"
        )}
      >
        <HealthIndicator
          status={healthStatus}
          checks={healthChecks}
          collapsed={collapsed}
        />

        <div
          className={cn(
            "flex items-center gap-1",
            collapsed ? "flex-col" : "justify-between"
          )}
        >
          <button
            type="button"
            onClick={toggle}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Cambia tema"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={collapsed ? "Espandi sidebar" : "Collassa sidebar"}
          >
            {collapsed ? (
              <ChevronsRight className="h-4 w-4" />
            ) : (
              <ChevronsLeft className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
