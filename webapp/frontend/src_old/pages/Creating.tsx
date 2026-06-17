import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Autofattura, CreateResult } from "../api/types";

export function CreatingPage({
  autofatture,
  dryRun,
  onDone,
  onError,
}: {
  autofatture: Autofattura[];
  dryRun: boolean;
  onDone: (result: CreateResult) => void;
  onError: (msg: string) => void;
}) {
  const [step, setStep] = useState("Avvio…");
  const [progress, setProgress] = useState(2);
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(autofatture.filter((a) => !a.excluded).length);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        const { job_id } = await api.createAutofatture(autofatture, dryRun);
        for (;;) {
          await new Promise((r) => setTimeout(r, 800));
          const j = await api.job(job_id);
          if (j.step_name) setStep(j.step_name);
          if (j.progress) setProgress(j.progress);
          if (j.total) setTotal(j.total);
          if (j.current) setCurrent(j.current);
          if (j.status === "done") {
            onDone(j.result as CreateResult);
            return;
          }
          if (j.status === "error") {
            onError(j.error || "Errore creazione autofatture");
            return;
          }
        }
      } catch (e: any) {
        onError(e.message || String(e));
      }
    })();
  }, [autofatture, dryRun, onDone, onError]);

  return (
    <div className="card">
      <h2>{dryRun ? "Simulazione in corso" : "Creazione su Fatture in Cloud"}</h2>
      {dryRun && <div className="dry-run-banner">DRY-RUN: nessuna chiamata reale a FiC</div>}
      <div className="spinner" />
      <p style={{ textAlign: "center" }}>{step}</p>
      <div className="progress">
        <div style={{ width: `${progress}%` }} />
      </div>
      <p className="small" style={{ textAlign: "center", color: "var(--muted)" }}>
        {current} / {total}
      </p>
    </div>
  );
}
