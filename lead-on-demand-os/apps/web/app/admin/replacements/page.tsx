"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Empty, ErrorBox, Modal, PageTitle, useApi } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { REPLACEMENT_REASON_LABELS, REPLACEMENT_STATUS_LABELS } from "@/lib/labels";

interface Repl { id: string; leadId: string; leadCode: string; leadName: string; clientName: string; reason: string; note: string | null; status: string; decisionNote: string | null; createdAt: string; decidedAt: string | null }
const COLORS: Record<string, string> = { REQUESTED: "bg-amber-100 text-amber-800", APPROVED: "bg-emerald-100 text-emerald-800", REJECTED: "bg-slate-200 text-slate-700" };

export default function ReplacementsPage() {
  const [status, setStatus] = useState("REQUESTED");
  const { data, error, reload } = useApi<Repl[]>(`/replacements${qs({ status })}`);
  const [deciding, setDeciding] = useState<{ r: Repl; decision: "APPROVED" | "REJECTED" } | null>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  async function decide() {
    if (!deciding) return;
    setErr(null);
    try {
      await api(`/replacements/${deciding.r.id}/decide`, { method: "POST", json: { decision: deciding.decision, note: note || null } });
      setDeciding(null);
      setNote("");
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div>
      <PageTitle title="Richieste di sostituzione" subtitle="Se approvata, il credito torna sul pacchetto e il lead resta in storico come sostituito" />
      <ErrorBox error={error ?? err} />
      <div className="mb-3 flex gap-2">
        {["REQUESTED", "APPROVED", "REJECTED", ""].map((s) => (
          <button key={s} className={status === s ? "btn-primary" : "btn-secondary"} onClick={() => setStatus(s)}>{s ? REPLACEMENT_STATUS_LABELS[s] : "Tutte"}</button>
        ))}
      </div>
      {data && data.length === 0 && <Empty text="Nessuna richiesta in questo stato." />}
      {data && data.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Richiesta il</th><th>Lead</th><th>Cliente</th><th>Motivo</th><th>Nota</th><th>Stato</th><th></th></tr></thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id}>
                  <td className="whitespace-nowrap">{fmtDate(r.createdAt)}</td>
                  <td><Link className="text-brand-600 hover:underline" href={`/admin/leads/${r.leadId}`}>{r.leadCode}</Link><div className="text-xs text-slate-500">{r.leadName}</div></td>
                  <td>{r.clientName}</td>
                  <td>{REPLACEMENT_REASON_LABELS[r.reason]}</td>
                  <td className="max-w-xs text-slate-600">{r.note}{r.decisionNote && <div className="text-xs text-slate-400">Decisione: {r.decisionNote}</div>}</td>
                  <td><Badge className={COLORS[r.status]}>{REPLACEMENT_STATUS_LABELS[r.status]}</Badge></td>
                  <td className="whitespace-nowrap space-x-2">
                    {r.status === "REQUESTED" && <><button className="btn-success" onClick={() => setDeciding({ r, decision: "APPROVED" })}>Approva</button><button className="btn-secondary" onClick={() => setDeciding({ r, decision: "REJECTED" })}>Rifiuta</button></>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={!!deciding} onClose={() => setDeciding(null)} title={deciding?.decision === "APPROVED" ? `Approva sostituzione ${deciding.r.leadCode}` : `Rifiuta sostituzione ${deciding?.r.leadCode ?? ""}`}>
        <p className="mb-2 text-sm text-slate-600">{deciding?.decision === "APPROVED" ? "Il pacchetto riceve +1 credito e il lead viene marcato come sostituito." : "Il lead resta consegnato e conteggiato."}</p>
        <textarea className="input" rows={3} placeholder="Nota per il cliente (facoltativa)" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className={deciding?.decision === "APPROVED" ? "btn-success mt-3" : "btn-danger mt-3"} onClick={decide}>Conferma</button>
      </Modal>
    </div>
  );
}
