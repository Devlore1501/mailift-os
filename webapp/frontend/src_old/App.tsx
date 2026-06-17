import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { Autofattura, CreateResult, Health } from "./api/types";
import { Steps, type StepName } from "./components/Steps";
import { UploadPage } from "./pages/Upload";
import { ProcessingPage } from "./pages/Processing";
import { ReviewPage } from "./pages/Review";
import { CreatingPage } from "./pages/Creating";
import { ResultsPage } from "./pages/Results";

export default function App() {
  const [step, setStep] = useState<StepName>("upload");
  const [health, setHealth] = useState<Health | null>(null);
  const [statementId, setStatementId] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const [autofatture, setAutofatture] = useState<Autofattura[]>([]);
  const [confirmed, setConfirmed] = useState<Autofattura[]>([]);
  const [dryRun, setDryRun] = useState(false);
  const [result, setResult] = useState<CreateResult | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setGlobalError(e.message));
  }, []);

  function reset() {
    setStep("upload");
    setStatementId("");
    setFilename("");
    setAutofatture([]);
    setConfirmed([]);
    setResult(null);
    setGlobalError(null);
  }

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>Autofatture passive</h1>
          <div className="sub">
            {health?.company?.name || "—"} · TD17 / TD18 / TD19 reverse charge
          </div>
        </div>
        <div className="right">
          {health ? (
            health.fic_token_valid ? (
              <span className="health-ok">● FiC token valido</span>
            ) : (
              <span className="health-bad">● FiC error: {health.detail}</span>
            )
          ) : (
            <span style={{ color: "var(--muted)" }}>Verifica connessione…</span>
          )}
        </div>
      </div>

      <Steps current={step} />

      {globalError && (
        <div className="alert error">
          <strong>Errore</strong>
          {globalError}
          <div style={{ marginTop: 8 }}>
            <button className="ghost" onClick={reset}>Ricomincia</button>
          </div>
        </div>
      )}

      {!globalError && step === "upload" && (
        <UploadPage
          onUploaded={(id, fn) => {
            setStatementId(id);
            setFilename(fn);
            setStep("processing");
          }}
        />
      )}

      {!globalError && step === "processing" && (
        <ProcessingPage
          statementId={statementId}
          filename={filename}
          onReady={(afs) => {
            setAutofatture(afs);
            setStep("review");
          }}
          onError={(msg) => setGlobalError(msg)}
        />
      )}

      {!globalError && step === "review" && (
        <ReviewPage
          initial={autofatture}
          dryRunDefault={health?.dry_run || false}
          onConfirm={(afs, dr) => {
            setConfirmed(afs);
            setDryRun(dr);
            setStep("creating");
          }}
          onBack={reset}
        />
      )}

      {!globalError && step === "creating" && (
        <CreatingPage
          autofatture={confirmed}
          dryRun={dryRun}
          onDone={(r) => {
            setResult(r);
            setStep("results");
          }}
          onError={(msg) => setGlobalError(msg)}
        />
      )}

      {!globalError && step === "results" && result && (
        <ResultsPage result={result} onRestart={reset} />
      )}
    </div>
  );
}
