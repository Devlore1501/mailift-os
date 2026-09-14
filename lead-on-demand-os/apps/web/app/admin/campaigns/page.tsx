"use client";

import { useState } from "react";
import { Empty, ErrorBox, Field, Modal, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtMoney } from "@/lib/format";

interface Camp { id: string; name: string; platform: string | null; spend: number; leadsRaw: number; leadsQualified: number; leadsSold: number; replacements: number; revenue: number; cplRaw: number | null; cplQualified: number | null; grossProfit: number }
interface CampBase { id: string; name: string; platform: string | null; active: boolean }

export default function CampaignsPage() {
  const { user } = useAuth();
  const isSuper = user?.role === "SUPER_ADMIN";
  const { data: eco, error, reload } = useApi<Camp[]>(isSuper ? "/analytics/campaigns" : null);
  const { data: list, reload: reloadList } = useApi<CampBase[]>("/campaigns");
  const [modal, setModal] = useState<null | "new" | "cost">(null);
  const [f, setF] = useState({ name: "", platform: "meta" });
  const [cost, setCost] = useState({ campaignId: "", periodStart: "", periodEnd: "", amount: "" });
  const [err, setErr] = useState<string | null>(null);
  async function run(fn: () => Promise<unknown>) {
    setErr(null);
    try {
      await fn();
      setModal(null);
      reload();
      reloadList();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div>
      <PageTitle title="Campagne" subtitle="Economics per campagna nel mese corrente: spesa, lead grezzi, qualificati, venduti, revenue" actions={<><button className="btn-primary" onClick={() => setModal("new")}>Nuova campagna</button>{isSuper && <button className="btn-secondary" onClick={() => setModal("cost")}>Registra spesa</button>}</>} />
      <ErrorBox error={error ?? err} />
      {!isSuper && list && (
        <div className="card p-0"><table className="table"><thead><tr><th>Campagna</th><th>Piattaforma</th></tr></thead><tbody>{list.map((c) => <tr key={c.id}><td>{c.name}</td><td>{c.platform}</td></tr>)}</tbody></table></div>
      )}
      {isSuper && eco && eco.length === 0 && <Empty text="Nessuna campagna. Le campagne vengono create anche automaticamente quando un lead arriva con un nome campagna nuovo." />}
      {isSuper && eco && eco.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead><tr><th>Campagna</th><th>Spesa</th><th>Lead raw</th><th>CPL raw</th><th>Qualificati</th><th>CPL qualificato</th><th>Venduti</th><th>Replacement</th><th>Revenue</th><th>Gross profit</th></tr></thead>
            <tbody>
              {eco.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}<div className="text-xs text-slate-500">{c.platform}</div></td>
                  <td>{fmtMoney(c.spend)}</td><td>{c.leadsRaw}</td><td>{c.cplRaw != null ? fmtMoney(c.cplRaw) : "–"}</td><td>{c.leadsQualified}</td><td>{c.cplQualified != null ? fmtMoney(c.cplQualified) : "–"}</td><td>{c.leadsSold}</td><td>{c.replacements}</td><td>{fmtMoney(c.revenue)}</td>
                  <td className={c.grossProfit < 0 ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>{fmtMoney(c.grossProfit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={modal === "new"} onClose={() => setModal(null)} title="Nuova campagna">
        <div className="space-y-3">
          <Field label="Nome (uguale a quello inviato dal form/landing)"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Piattaforma"><select className="input" value={f.platform} onChange={(e) => setF({ ...f, platform: e.target.value })}><option value="meta">Meta</option><option value="google">Google</option><option value="other">Altro</option></select></Field>
          <button className="btn-primary" disabled={!f.name} onClick={() => run(() => api("/campaigns", { method: "POST", json: f }))}>Crea</button>
        </div>
      </Modal>
      <Modal open={modal === "cost"} onClose={() => setModal(null)} title="Registra spesa advertising">
        <div className="space-y-3">
          <Field label="Campagna"><select className="input" value={cost.campaignId} onChange={(e) => setCost({ ...cost, campaignId: e.target.value })}><option value="">Seleziona…</option>{list?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Dal"><input className="input" type="date" value={cost.periodStart} onChange={(e) => setCost({ ...cost, periodStart: e.target.value })} /></Field>
            <Field label="Al"><input className="input" type="date" value={cost.periodEnd} onChange={(e) => setCost({ ...cost, periodEnd: e.target.value })} /></Field>
          </div>
          <Field label="Importo (euro)"><input className="input" type="number" step="0.01" value={cost.amount} onChange={(e) => setCost({ ...cost, amount: e.target.value })} /></Field>
          <button className="btn-primary" disabled={!cost.campaignId || !cost.amount || !cost.periodStart || !cost.periodEnd} onClick={() => run(() => api(`/campaigns/${cost.campaignId}/costs`, { method: "POST", json: { periodStart: new Date(cost.periodStart).toISOString(), periodEnd: new Date(cost.periodEnd + "T23:59:59").toISOString(), amount: Number(cost.amount) } }))}>Salva</button>
        </div>
      </Modal>
    </div>
  );
}
