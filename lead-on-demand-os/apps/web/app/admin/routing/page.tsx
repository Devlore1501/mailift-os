"use client";

import Link from "next/link";
import { useState } from "react";
import { Empty, ErrorBox, Kpi, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/format";
import { ROUTING_REASON_LABELS } from "@/lib/labels";

interface Waiting { total: number; byProvince: Record<string, number>; byReason: Record<string, number>; leads: Array<{ id: string; code: string; firstName: string | null; lastName: string | null; municipality: string | null; province: string | null; qualifiedAt: string | null; waitingReasons: string[] }> }

export default function RoutingPage() {
  const { data, error, reload } = useApi<Waiting>("/routing/waiting");
  const [result, setResult] = useState<string | null>(null);
  async function retry() {
    const r = await api<Array<{ leadId: string; outcome: string }>>("/routing/retry-queue", { method: "POST" });
    setResult(`${r.filter((x) => x.outcome === "ASSIGNED").length} assegnati su ${r.length} riprovati`);
    reload();
  }
  return (
    <div>
      <PageTitle title="Routing e coda di assegnazione" subtitle="Lead qualificati che nessun cliente può ricevere: territori dove c'è domanda senza buyer" actions={<button className="btn-primary" onClick={retry}>Riprova la coda</button>} />
      <ErrorBox error={error} />
      {result && <p className="mb-3 text-sm text-emerald-700">{result}</p>}
      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Kpi label="Lead qualificati non assegnati" value={data.total} tone={data.total ? "text-amber-700" : ""} />
            <div className="card"><div className="text-xs uppercase tracking-wide text-slate-500">Per provincia</div><ul className="mt-1 text-sm">{Object.entries(data.byProvince).map(([p, n]) => <li key={p}>{p}: {n}</li>)}</ul></div>
            <div className="card"><div className="text-xs uppercase tracking-wide text-slate-500">Per motivo</div><ul className="mt-1 text-sm">{Object.entries(data.byReason).map(([r, n]) => <li key={r}>{ROUTING_REASON_LABELS[r] ?? r}: {n}</li>)}</ul></div>
          </div>
          {data.leads.length === 0 && <Empty text="Nessun lead in attesa. Tutta la domanda qualificata ha un buyer." />}
          {data.leads.length > 0 && (
            <div className="card p-0">
              <table className="table">
                <thead><tr><th>Lead</th><th>Nome</th><th>Zona</th><th>Qualificato il</th><th>Motivi</th></tr></thead>
                <tbody>
                  {data.leads.map((l) => (
                    <tr key={l.id}>
                      <td><Link className="font-mono text-brand-600 hover:underline" href={`/admin/leads/${l.id}`}>{l.code}</Link></td>
                      <td>{fullName(l)}</td>
                      <td>{l.municipality} {l.province ? `(${l.province})` : ""}</td>
                      <td>{fmtDate(l.qualifiedAt)}</td>
                      <td className="text-slate-600">{l.waitingReasons.map((r) => ROUTING_REASON_LABELS[r] ?? r).join("; ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="card text-sm text-slate-600">
            <h2 className="mb-1 font-semibold text-slate-800">Come decide il Routing Engine</h2>
            <p>Un lead qualificato va al cliente attivo dello stesso verticale e tipologia, con un territorio che copre il lead, credito disponibile sul pacchetto, cap non raggiunti e criteri specifici soddisfatti. Se un territorio esclusivo copre il lead, solo quel cliente può riceverlo. A parità: territorio più specifico, poi priorità, poi chi ha ricevuto meno lead nel mese.</p>
          </div>
        </div>
      )}
    </div>
  );
}
