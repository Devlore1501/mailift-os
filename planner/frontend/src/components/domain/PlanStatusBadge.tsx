import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlanStatus } from "@/types/api";

const STATUS_CONFIG: Record<
  PlanStatus,
  { label: string; className: string }
> = {
  generating: {
    label: "In generazione",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  draft: {
    label: "Bozza",
    className: "bg-zinc-100 text-zinc-700 border-zinc-200",
  },
  approved: {
    label: "Approvato",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  published: {
    label: "Pubblicato",
    className: "bg-violet-50 text-violet-700 border-violet-200",
  },
  error: {
    label: "Errore",
    className: "bg-red-50 text-red-700 border-red-200",
  },
};

export function PlanStatusBadge({
  status,
  className,
}: {
  status: PlanStatus | null | undefined;
  className?: string;
}) {
  if (!status) {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full border border-border px-2 py-0.5 text-xs font-medium text-muted-foreground",
          className
        )}
      >
        Nessun piano
      </span>
    );
  }
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        cfg.className,
        className
      )}
    >
      {status === "generating" && (
        <Loader2 className="h-3 w-3 animate-spin" />
      )}
      {cfg.label}
    </span>
  );
}
