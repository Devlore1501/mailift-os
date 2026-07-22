import { useMemo, useState } from "react";
import type { Autofattura } from "../api/types";

export function ReviewPage({
  initial,
  dryRunDefault,
  onConfirm,
  onBack,
}: {
  initial: Autofattura[];
  dryRunDefault: boolean;
  onConfirm: (afs: Autofattura[], dryRun: boolean) => void;
  onBack: () => void;
}) {
  const [items, setItems] = useState<Autofattura[]>(initial);
  const [dryRun, setDryRun] = useState(dryRunDefault);

  const totals = useMemo(() => {
    const active = items.filter((i) => !i.excluded);
    const total = active.reduce(
      (sum, i) => sum + i.lines.reduce((s, l) => s + l.amount_net, 0),
      0
    );
    return { count: active.length, total };
  }, [items]);

  function update(id: string, patch: Partial<Autofattura>) {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }

  function updateLine(id: string, patch: Partial<{ amount_net: number; description: string }>) {
    setItems((prev) =>
      prev.map((i) =>
        i.id === id
          ? {
              ...i,
              lines: i.lines.map((l, idx) => (idx === 0 ? { ...l, ...patch } : l)),
            }
          : i
      )
    );
  }

  return (
    <div className="card">
      <h2>Rivedi le autofatture proposte</h2>
      <p>
        L'AI ha aggregato i movimenti per fornitore. Puoi modificare i dati,
        escludere righe o confermare per crearle su Fatture in Cloud.
      </p>

      {items.length === 0 ? (
        <div className="alert">
          <strong>Nessuna autofattura individuata</strong>
          Nessun movimento nell'estratto conto richiede emissione di autofattura
          passiva.
        </div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Fornitore</th>
                  <th>Paese</th>
                  <th>P.IVA</th>
                  <th>Descrizione</th>
                  <th className="num">Imponibile</th>
                  <th>Val.</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((af) => (
                  <tr key={af.id} className={af.excluded ? "excluded" : ""}>
                    <td>
                      <span className={`tag ${af.type_doc.toLowerCase()}`}>
                        {af.type_doc}
                      </span>
                    </td>
                    <td>
                      <input
                        value={af.supplier_name}
                        onChange={(e) => update(af.id, { supplier_name: e.target.value })}
                      />
                    </td>
                    <td style={{ width: 70 }}>
                      <input
                        value={af.supplier_country}
                        onChange={(e) =>
                          update(af.id, { supplier_country: e.target.value.toUpperCase() })
                        }
                      />
                    </td>
                    <td style={{ width: 140 }}>
                      <input
                        value={af.supplier_vat_number}
                        onChange={(e) =>
                          update(af.id, { supplier_vat_number: e.target.value })
                        }
                        placeholder="—"
                      />
                    </td>
                    <td>
                      <input
                        value={af.lines[0]?.description || ""}
                        onChange={(e) => updateLine(af.id, { description: e.target.value })}
                      />
                    </td>
                    <td className="num" style={{ width: 130 }}>
                      <input
                        type="number"
                        step="0.01"
                        value={af.lines[0]?.amount_net ?? 0}
                        onChange={(e) =>
                          updateLine(af.id, {
                            amount_net: parseFloat(e.target.value) || 0,
                          })
                        }
                        style={{ textAlign: "right" }}
                      />
                    </td>
                    <td>{af.currency}</td>
                    <td>
                      <button
                        className="ghost"
                        onClick={() => update(af.id, { excluded: !af.excluded })}
                      >
                        {af.excluded ? "Includi" : "Escludi"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="totals">
            <div className="stat">
              <div className="label">Autofatture attive</div>
              <div className="value">{totals.count}</div>
            </div>
            <div className="stat">
              <div className="label">Totale imponibile</div>
              <div className="value">€ {totals.total.toFixed(2)}</div>
            </div>
            <div className="stat">
              <div className="label">Modalita</div>
              <div className="value" style={{ fontSize: 14 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    style={{ width: "auto" }}
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                  />
                  Dry-run (non crea su FiC)
                </label>
              </div>
            </div>
          </div>
        </>
      )}

      <div className="footer-actions">
        <button className="ghost" onClick={onBack}>
          Indietro
        </button>
        <button
          disabled={totals.count === 0}
          onClick={() => onConfirm(items, dryRun)}
        >
          {dryRun
            ? `Simula creazione di ${totals.count}`
            : `Crea ${totals.count} autofatture su FiC`}
        </button>
      </div>
    </div>
  );
}
