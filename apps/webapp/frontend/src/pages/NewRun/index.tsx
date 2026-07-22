import { Outlet, useLocation } from "react-router-dom";
import {
  StepProgress,
  type Step,
  type StepStatus,
} from "@/components/domain/StepProgress";

const STEP_ORDER: { id: string; label: string; match: (segments: string[]) => boolean }[] = [
  { id: "upload", label: "Upload", match: (s) => s.length === 1 && s[0] === "new" },
  {
    id: "processing",
    label: "Elaborazione",
    match: (s) => s[1] === "processing",
  },
  { id: "verify", label: "Verifica", match: (s) => s[1] === "verify" },
  { id: "review", label: "Revisione", match: (s) => s[1] === "review" },
  { id: "creating", label: "Creazione", match: (s) => s[1] === "creating" },
  { id: "results", label: "Fatto", match: (s) => s[1] === "results" },
];

function computeSteps(pathname: string): { steps: Step[]; currentStep: number } {
  const segments = pathname.split("/").filter(Boolean); // ["new", ...]
  const currentIdx = STEP_ORDER.findIndex((s) => s.match(segments));
  const idx = currentIdx === -1 ? 0 : currentIdx;
  const steps: Step[] = STEP_ORDER.map((s, i) => {
    let status: StepStatus = "pending";
    if (i < idx) status = "done";
    else if (i === idx) status = "current";
    return { id: s.id, label: s.label, status };
  });
  return { steps, currentStep: idx };
}

export function NewRunLayout() {
  const { pathname } = useLocation();
  const { steps, currentStep } = computeSteps(pathname);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Nuovo run</h1>
        <p className="text-sm text-muted-foreground">
          Flusso guidato per emettere autofatture dall&apos;estratto conto
        </p>
      </div>
      <StepProgress steps={steps} currentStep={currentStep} />
      <Outlet />
    </div>
  );
}
