import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepStatus = "pending" | "current" | "done" | "error";

export interface Step {
  id: string;
  label: string;
  status: StepStatus;
}

interface StepProgressProps {
  steps: Step[];
  currentStep: number;
  className?: string;
}

/**
 * Horizontal stepper for the "Nuovo run" wizard.
 * Circles connected by lines; keyboard-accessible list semantics.
 * On narrow viewports the stepper scrolls horizontally.
 */
export function StepProgress({ steps, className }: StepProgressProps) {
  return (
    <ol
      className={cn(
        "flex w-full items-center gap-1 overflow-x-auto py-2 md:gap-0",
        className
      )}
      aria-label="Progresso del wizard"
    >
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        return (
          <li
            key={step.id}
            className={cn(
              "flex min-w-[120px] flex-1 items-center",
              isLast && "min-w-fit flex-none"
            )}
            aria-current={step.status === "current" ? "step" : undefined}
          >
            <div className="flex items-center gap-3">
              <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
                {step.status === "current" && (
                  <span className="absolute inset-0 animate-pulse-ring rounded-full bg-primary/40" />
                )}
                <div
                  className={cn(
                    "relative flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors",
                    step.status === "done" &&
                      "border-success bg-success text-success-foreground",
                    step.status === "current" &&
                      "border-primary bg-primary text-primary-foreground",
                    step.status === "pending" &&
                      "border-border bg-muted text-muted-foreground",
                    step.status === "error" &&
                      "border-destructive bg-destructive text-destructive-foreground"
                  )}
                >
                  {step.status === "done" ? (
                    <Check className="h-4 w-4" />
                  ) : step.status === "error" ? (
                    <X className="h-4 w-4" />
                  ) : (
                    i + 1
                  )}
                </div>
              </div>
              <span
                className={cn(
                  "text-xs font-medium leading-tight",
                  step.status === "pending" && "text-muted-foreground",
                  step.status === "current" && "text-foreground",
                  step.status === "done" && "text-muted-foreground",
                  step.status === "error" && "text-destructive"
                )}
              >
                {step.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={cn(
                  "mx-3 h-px flex-1 transition-colors",
                  step.status === "done" ? "bg-success/60" : "bg-border"
                )}
                aria-hidden
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
