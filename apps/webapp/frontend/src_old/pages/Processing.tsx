import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Autofattura } from "../api/types";

type Stage = "parsing" | "classifying" | "done" | "error";

export function ProcessingPage({
  statementId,
  filename,
  onReady,
  onError,
}: {
  statementId: string;
  filename: string;
  onReady: (autofatture: Autofattura[]) => void;
  onError: (msg: string) => void;
}) {
  const [stage, setStage] = useState<Stage>("parsing");
  const [outflows, setOutflows] = useState(0);
  const [step, setStep] = useState("Lettura del file…");
  const [progress, setProgress] = useState(5);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        const parseRes = await api.parse(statementId);
        setOutflows(parseRes.outflows_count);
        setStep(`Trovate ${parseRes.outflows_count} uscite, classifico con AI…`);
        setStage("classifying");
        setProgress(15);

        const { job_id } = await api.classify(statementId);
        // poll
        for (;;) {
          await new Promise((r) => setTimeout(r, 1000));
          const j = await api.job(job_id);
          if (j.step_name) setStep(j.step_name);
          if (j.progress) setProgress(Math.max(15, j.progress));
          if (j.status === "done") {
            const afs = (j.result?.autofatture || []) as Autofattura[];
            setStage("done");
            setProgress(100);
            onReady(afs);
            return;
          }
          if (j.status === "error") {
            setStage("error");
            onError(j.error || "Errore classificazione");
            return;
          }
        }
      } catch (e: any) {
        setStage("error");
        onError(e.message || String(e));
      }
    })();
  }, [statementId, onReady, onError]);

  return (
    <div className="card">
      <h2>Analisi in corso</h2>
      <p>File: <code>{filename}</code></p>
      <div className="spinner" />
      <p style={{ textAlign: "center" }}>{step}</p>
      <div className="progress">
        <div style={{ width: `${progress}%` }} />
      </div>
      {outflows > 0 && (
        <p className="small" style={{ textAlign: "center", color: "var(--muted)" }}>
          {outflows} movimenti in uscita da classificare
        </p>
      )}
    </div>
  );
}
