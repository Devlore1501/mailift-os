import { useEffect, useState } from "react";
import { FlaskConical, Radio } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "autofatture-environment";

export type Environment = "live" | "dry-run";

export function getStoredEnvironment(): Environment {
  if (typeof window === "undefined") return "dry-run";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "live" ? "live" : "dry-run";
}

/**
 * Top-bar switch that toggles between Live and Dry-run.
 * Persisted in localStorage so the choice sticks across reloads.
 * Consumers can observe the same key or listen for the "autofatture:env" event
 * on window to sync their React Query params.
 */
export function EnvironmentSwitch() {
  const [env, setEnv] = useState<Environment>(getStoredEnvironment);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, env);
    window.dispatchEvent(
      new CustomEvent("autofatture:env", { detail: env })
    );
  }, [env]);

  const isLive = env === "live";

  return (
    <div className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/40 px-2.5 py-1">
      <FlaskConical
        className={cn(
          "h-3.5 w-3.5 transition-colors",
          isLive ? "text-muted-foreground" : "text-primary"
        )}
      />
      <span
        className={cn(
          "text-[11px] font-medium uppercase tracking-wide",
          isLive ? "text-muted-foreground" : "text-primary"
        )}
      >
        Dry-run
      </span>
      <Switch
        checked={isLive}
        onCheckedChange={(v) => setEnv(v ? "live" : "dry-run")}
        aria-label="Cambia ambiente Live / Dry-run"
      />
      <Radio
        className={cn(
          "h-3.5 w-3.5 transition-colors",
          isLive ? "text-destructive" : "text-muted-foreground"
        )}
      />
      <span
        className={cn(
          "text-[11px] font-medium uppercase tracking-wide",
          isLive ? "text-destructive" : "text-muted-foreground"
        )}
      >
        Live
      </span>
    </div>
  );
}
