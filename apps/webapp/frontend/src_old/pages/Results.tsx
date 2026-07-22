import type { CreateResult } from "../api/types";

export function ResultsPage({
  result,
  onRestart,
}: {
  result: CreateResult;
  onRestart: () => void;
}) {
  return (
    <div className="card">
      <h2>Risultati</h2>
      {result.dry_run && (
        <div className="dry-run-banner">DRY-RUN — nessuna autofattura e' stata davvero creata</div>
      )}

      <div className="totals">
        <div className="stat">
          <div className="label">Create OK</div>
          <div className="value" style={{ color: "var(--good)" }}>{result.ok}</div>
        </div>
        <div className="stat">
          <div className="label">Errori</div>
          <div className="value" style={{ color: result.errors ? "var(--bad)" : undefined }}>
            {result.errors}
          </div>
        </div>
        <div className="stat">
          <div className="label">Saltate (dry-run)</div>
          <div className="value">{result.skipped}</div>
        </div>
      </div>

      {!result.dry_run && result.ok > 0 && (
        <div className="alert">
          <strong>⚠ Le autofatture NON sono state inviate al SDI</strong>
          Vai su Fatture in Cloud, rivedi ciascuna e clicca "Verifica formale" +
          "Firma e invia" per ciascuna.
        </div>
      )}

      <div style={{ overflowX: "auto", marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Stato</th>
              <th>Fornitore</th>
              <th>Tipo</th>
              <th className="num">Imponibile</th>
              <th>Numero FiC</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {result.items.map((it, i) => (
              <tr key={i}>
                <td>
                  {it.status === "ok" && <span style={{ color: "var(--good)" }}>✓ OK</span>}
                  {it.status === "error" && <span style={{ color: "var(--bad)" }}>✗ ERR</span>}
                  {it.status === "skipped" && <span style={{ color: "var(--muted)" }}>– skip</span>}
                </td>
                <td>{it.supplier}</td>
                <td>
                  <span className={`tag ${it.type_doc.toLowerCase()}`}>{it.type_doc}</span>
                </td>
                <td className="num">€ {it.total_net.toFixed(2)}</td>
                <td>
                  {it.fic_number
                    ? `${it.fic_number}${it.fic_numeration ? "/" + it.fic_numeration : ""}`
                    : "—"}
                </td>
                <td>
                  {it.fic_url ? (
                    <a href={it.fic_url} target="_blank" rel="noreferrer">
                      Apri su FiC ↗
                    </a>
                  ) : it.error ? (
                    <span style={{ color: "var(--bad)", fontSize: 11 }}>{it.error}</span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="footer-actions">
        <button onClick={onRestart}>Carica un altro estratto</button>
      </div>
    </div>
  );
}
