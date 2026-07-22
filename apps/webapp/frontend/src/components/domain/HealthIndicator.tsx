import { Check, X, AlertTriangle } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export type HealthStatus = "ok" | "warn" | "down" | "unknown";

export interface HealthCheck {
  label: string;
  status: HealthStatus;
  detail?: string;
}

interface HealthIndicatorProps {
  status?: HealthStatus;
  checks?: HealthCheck[];
  collapsed?: boolean;
}

const dotClass: Record<HealthStatus, string> = {
  ok: "bg-success shadow-[0_0_0_3px_hsl(var(--success)/0.2)]",
  warn: "bg-warning shadow-[0_0_0_3px_hsl(var(--warning)/0.2)]",
  down: "bg-destructive shadow-[0_0_0_3px_hsl(var(--destructive)/0.2)]",
  unknown: "bg-muted-foreground",
};

const labelMap: Record<HealthStatus, string> = {
  ok: "Tutti i servizi attivi",
  warn: "Warning attivi",
  down: "Servizio offline",
  unknown: "Stato sconosciuto",
};

function StatusIcon({ status }: { status: HealthStatus }) {
  if (status === "ok") return <Check className="h-3.5 w-3.5 text-success" />;
  if (status === "warn")
    return <AlertTriangle className="h-3.5 w-3.5 text-warning" />;
  if (status === "down") return <X className="h-3.5 w-3.5 text-destructive" />;
  return <span className="h-2 w-2 rounded-full bg-muted-foreground" />;
}

/**
 * Sidebar health dot + popover with a list of backend checks.
 * Parents can pass live data via React Query; here it stays presentational
 * so it can be reused in dev-time storybook-like contexts.
 */
export function HealthIndicator({
  status = "unknown",
  checks = [],
  collapsed = false,
}: HealthIndicatorProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            collapsed && "justify-center px-0"
          )}
          aria-label={`Stato sistema: ${labelMap[status]}`}
        >
          <span
            className={cn(
              "relative inline-block h-2.5 w-2.5 rounded-full",
              dotClass[status]
            )}
          />
          {!collapsed && (
            <span className="truncate text-[11px] font-medium uppercase tracking-wide">
              {labelMap[status]}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-72 p-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="text-sm font-semibold">Stato sistema</div>
          <span
            className={cn("inline-block h-2 w-2 rounded-full", dotClass[status])}
          />
        </div>
        <ul className="space-y-1.5 text-xs">
          {checks.length === 0 ? (
            <li className="text-muted-foreground">Nessun check disponibile.</li>
          ) : (
            checks.map((c) => (
              <li
                key={c.label}
                className="flex items-start justify-between gap-2"
              >
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <StatusIcon status={c.status} />
                  <span className="truncate font-medium">{c.label}</span>
                </div>
                {c.detail && (
                  <span className="shrink-0 text-right text-[10px] text-muted-foreground">
                    {c.detail}
                  </span>
                )}
              </li>
            ))
          )}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
