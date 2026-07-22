import { useState } from "react";
import { api } from "../api/client";

export function UploadPage({
  onUploaded,
}: {
  onUploaded: (statementId: string, filename: string) => void;
}) {
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setBusy(true);
    try {
      const res = await api.uploadFile(file);
      onUploaded(res.statement_id, res.filename);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Carica l'estratto conto</h2>
      <p>
        Trascina qui il file (CSV, XLS, XLSX o PDF) dell'estratto conto bancario.
        Sara' analizzato per individuare le spese che richiedono autofattura passiva
        TD17 / TD18 / TD19.
      </p>
      <label
        className={`dropzone ${over ? "over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
      >
        <input
          type="file"
          accept=".csv,.xls,.xlsx,.pdf"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
          disabled={busy}
        />
        {busy ? (
          <>
            <div className="spinner" />
            <p>Caricamento…</p>
          </>
        ) : (
          <>
            <p style={{ fontSize: 16 }}>Trascina qui il file o clicca per selezionarlo</p>
            <p className="small">Formati supportati: CSV, XLSX, XLS, PDF</p>
          </>
        )}
      </label>
      {error && (
        <div className="alert error">
          <strong>Errore</strong>
          {error}
        </div>
      )}
    </div>
  );
}
