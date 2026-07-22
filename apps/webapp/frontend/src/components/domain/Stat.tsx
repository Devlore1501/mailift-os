import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  value: string | number;
  hint?: string;
  delta?: { value: string; direction: "up" | "down" | "flat" };
  className?: string;
}

/**
 * Compact KPI card for the Dashboard: label + big number + optional delta.
 */
export function Stat({ label, value, hint, delta, className }: StatProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="space-y-1.5 p-5">
        <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-semibold tabular-nums tracking-tight">
            {value}
          </div>
          {delta && delta.direction !== "flat" && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 text-xs font-medium",
                delta.direction === "up"
                  ? "text-success"
                  : "text-destructive"
              )}
            >
              {delta.direction === "up" ? (
                <ArrowUpRight className="h-3 w-3" />
              ) : (
                <ArrowDownRight className="h-3 w-3" />
              )}
              {delta.value}
            </span>
          )}
        </div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}
