type StepName = "upload" | "processing" | "review" | "creating" | "results";

const ORDER: StepName[] = ["upload", "processing", "review", "creating", "results"];
const LABELS: Record<StepName, string> = {
  upload: "1. Carica",
  processing: "2. Analizza",
  review: "3. Rivedi",
  creating: "4. Crea",
  results: "5. Risultati",
};

export function Steps({ current }: { current: StepName }) {
  const idx = ORDER.indexOf(current);
  return (
    <div className="steps">
      {ORDER.map((s, i) => {
        const cls = i === idx ? "active" : i < idx ? "done" : "";
        return (
          <div key={s} className={`step ${cls}`}>
            {LABELS[s]}
          </div>
        );
      })}
    </div>
  );
}

export type { StepName };
