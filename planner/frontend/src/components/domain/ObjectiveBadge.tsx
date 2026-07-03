import { cn } from "@/lib/utils";
import type { EmailObjective } from "@/types/api";

const OBJECTIVE_CONFIG: Record<
  EmailObjective,
  { label: string; className: string }
> = {
  nurturing: {
    label: "Nurturing",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  promo: {
    label: "Promo",
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  storytelling: {
    label: "Storytelling",
    className: "bg-violet-50 text-violet-700 border-violet-200",
  },
  vendita: {
    label: "Vendita",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
};

/** Obiettivi considerati promozionali per la regola 70/20/10. */
export function isPromoObjective(objective: EmailObjective): boolean {
  return objective === "promo" || objective === "vendita";
}

export function ObjectiveBadge({
  objective,
  className,
}: {
  objective: EmailObjective;
  className?: string;
}) {
  const cfg = OBJECTIVE_CONFIG[objective] ?? {
    label: objective,
    className: "bg-zinc-100 text-zinc-700 border-zinc-200",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold",
        cfg.className,
        className
      )}
    >
      {cfg.label}
    </span>
  );
}
