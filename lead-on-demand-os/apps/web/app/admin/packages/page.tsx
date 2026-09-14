"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Badge, Empty, ErrorBox, Field, Modal, PageTitle, useApi } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate, fmtMoney } from "@/lib/format";
import { PACKAGE_STATUS_LABELS } from "@/lib/labels";

interface Pkg { id: string; code: string; clientId: string; clientName: string; productName: string; quantity: number; unitPrice: string; totalPrice: string; status: string; paid: boolean; balance: number; deliveredCount: number; replacementCount: number; createdAt: string }
interface Tx { id: string; type: string; quantity: number; reason: string | null; leadId: string | null; createdAt: string }
const COLORS: Record<string, string> = { ACTIVE: "bg-emerald-100 text-emerald-800", LOW_BALANCE: "bg-amber-100 text-amber-800", COMPLETED: "bg-slate-200 text-slate-700", DRAFT: "bg-slate-100 text-slate-600", AWAITING_PAYMENT: "bg-sky-100 text-sky-800", PAUSED: "bg-violet-100 text-violet-800", EXPIRED: "bg-slate-200 text-slate-700", CANCELLED: "bg-red-100 text-red-800" };

function PackagesInner() {
  const params = useSearchParams();
  const { user } = useAuth();
  const [status, setStatus] = useState("");
  const clientId = params.get("clientId") ?? "";
  const { data, error, reload } = useApi<Pkg[]>(`/packages${qs({ status, clientId })}`);
  const [ledger, setLedger] = useState<Pkg | null>(null);
  const { data: txs } = useApi<Tx[]>(ledger ? `/packages/${ledger.id}/transactions` : null);
  const [adjust, setAdjust] = useState<Pkg | null>(null);
  const [adj, setAdj] = useState({ quantity: "", reason: "" });
  const [err, setErr] = useState<string | null>(null);
  async function run(fn: () => Promise<unknown>) {
    setErr(null);
    try {
      await fn();
      setAdjust(null);
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div>
      <PageTitle title="Pacchetti" subtitle="Ogni acquisto è un oggetto autonomo con il proprio ledger di crediti" />
      <ErrorBox error={error ?? err} />
      <div className="mb-3 flex gap-2">
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tutti gli stati</option>
          {Object.entries(PACKAGE_STATUS_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        {clientId && <Link href="/admin/packages" className="btn-secondary">Tutti i clienti</Link>}
      </div>
      {data && data.length === 0 && <Empty text="Nessun pacchetto. I pacchetti si creano dalla scheda cliente." />}
      {data && data.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead><tr><th>Codice</th><th>Cliente</th><th>Prodotto</th><th>Qtà</th><th>Prezzo</th><th>Totale</th><th>Pagato</th><th>Consegnati</th><th>Repl.</th><th>Residui</th><th>Stato</th><th></th></tr></thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td className="font-mono">{p.code}</td>
                  <td><Link className="text-brand-600 hover:underline" href={`/admin/clients/${p.clientId}`}>{p.clientName}</Link></td>
                  <td>{p.productName}</td><td>{p.quantity}</td><td>{fmtMoney(p.unitPrice)}</td><td>{fmtMoney(p.totalPrice)}</td><td>{p.paid ? "Sì" : "No"}</td><td>{p.deliveredCount}</td><td>{p.replacementCount}</td>
                  <td className="font-semibold">{p.balance}</td>
                  <td><Badge className={COLORS[p.status]}>{PACKAGE_STATUS_LABELS[p.status]}</Badge></td>
                  <td className="whitespace-nowrap space-x-2">
                    <button className="text-xs text-brand-600 hover:underline" onClick={() => setLedger(p)}>Ledger</button>
                    {(p.status === "DRAFT" || p.status === "AWAITING_PAYMENT") && <button className="text-xs text-emerald-700 hover:underline" onClick={() => run(() => api(`/packages/${p.id}/activate`, { method: "POST", json: {} }))}>Registra pagamento</button>}
                    {(p.status === "ACTIVE" || p.status === "LOW_BALANCE") && <button className="text-xs text-amber-700 hover:underline" onClick={() => run(() => api(`/packages/${p.id}/status`, { method: "POST", json: { status: "PAUSED" } }))}>Pausa</button>}
                    {p.status === "PAUSED" && <button className="text-xs text-emerald-700 hover:underline" onClick={() => run(() => api(`/packages/${p.id}/status`, { method: "POST", json: { status: "ACTIVE" } }))}>Riattiva</button>}
                    {user?.role === "SUPER_ADMIN" && <button className="text-xs text-slate-600 hover:underline" onClick={() => setAdjust(p)}>Rettifica</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={!!ledger} onClose={() => setLedger(null)} title={`Ledger ${ledger?.code ?? ""}`}>
        <p className="mb-2 text-sm text-slate-600">Saldo attuale: <strong>{ledger?.balance}</strong>. Ogni riga è immutabile.</p>
        <table className="table">
          <thead><tr><th>Data</th><th>Tipo</th><th>Qtà</th><th>Motivo</th></tr></thead>
          <tbody>
            {txs?.map((t) => (
              <tr key={t.id}><td className="whitespace-nowrap">{fmtDate(t.createdAt)}</td><td>{t.type}</td><td className={t.quantity < 0 ? "text-red-700" : "text-emerald-700"}>{t.quantity > 0 ? "+" : ""}{t.quantity}</td><td>{t.leadId ? <Link className="text-brand-600 hover:underline" href={`/admin/leads/${t.leadId}`}>{t.reason}</Link> : t.reason}</td></tr>
            ))}
          </tbody>
        </table>
      </Modal>
      <Modal open={!!adjust} onClose={() => setAdjust(null)} title={`Rettifica manuale ${adjust?.code ?? ""}`}>
        <div className="space-y-3">
          <Field label="Quantità (positiva o negativa)"><input className="input" type="number" value={adj.quantity} onChange={(e) => setAdj({ ...adj, quantity: e.target.value })} /></Field>
          <Field label="Motivazione (obbligatoria, finisce nell'audit log)"><input className="input" value={adj.reason} onChange={(e) => setAdj({ ...adj, reason: e.target.value })} /></Field>
          <button className="btn-warn" disabled={!adj.quantity || adj.reason.length < 3} onClick={() => adjust && run(() => api(`/packages/${adjust.id}/adjust`, { method: "POST", json: { quantity: Number(adj.quantity), reason: adj.reason } }))}>Applica rettifica</button>
        </div>
      </Modal>
    </div>
  );
}

export default function PackagesPage() {
  return <Suspense fallback={null}><PackagesInner /></Suspense>;
}
