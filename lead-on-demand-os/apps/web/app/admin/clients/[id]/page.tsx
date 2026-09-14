"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ClientForm, fromClient, toPayload } from "@/components/ClientForm";
import { Badge, ErrorBox, Field, Kpi, Modal, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate, fmtMoney, fmtNum } from "@/lib/format";
import { PACKAGE_STATUS_LABELS, TERRITORY_LEVEL_LABELS } from "@/lib/labels";

interface ClientDetail { id: string; code: string; tradeName: string; status: string; balance: number; deliveredCount: number; openReplacements: number; activePackages: number; portalUsers: Array<{ id: string; email: string; fullName: string; active: boolean }>; criteria: Array<{ field: string; op: string; value?: unknown; kind: string; label: string }>; [k: string]: unknown }
interface Pkg { id: string; code: string; productName: string; quantity: number; unitPrice: string; totalPrice: string; status: string; balance: number; deliveredCount: number; replacementCount: number; paid: boolean; createdAt: string }
interface Terr { id: string; level: string; value: string; exclusive: boolean; province: string | null; region: string | null }
interface Analytics { received: number; contacted: number; appointments: number; show: number; quotes: number; won: number; salesValue: number; leadCost: number; costPerCustomer: number | null; revenueOverCost: number | null; missingOutcome: number; replacementRate: { delivered: number; approved: number; rate: number } }

export default function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user } = useAuth();
  const { data: c, error, reload } = useApi<ClientDetail>(`/clients/${id}`);
  const { data: pkgs, reload: reloadPkgs } = useApi<Pkg[]>(`/packages?clientId=${id}`);
  const { data: terr, reload: reloadTerr } = useApi<Terr[]>(`/territories?clientId=${id}`);
  const { data: an } = useApi<Analytics>(`/clients/${id}/analytics`);
  const [tab, setTab] = useState<"overview" | "edit" | "criteria">("overview");
  const [modal, setModal] = useState<null | "package" | "territory" | "user">(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<unknown>) {
    setErr(null);
    setBusy(true);
    try {
      await fn();
      setModal(null);
      reload();
      reloadPkgs();
      reloadTerr();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (error) return <ErrorBox error={error} />;
  if (!c) return <div className="text-sm text-slate-500">Caricamento…</div>;
  return (
    <div>
      <PageTitle title={`${c.tradeName}`} subtitle={`${c.code} · ${c.status}`} actions={<><button className="btn-primary" onClick={() => setModal("package")}>Nuovo pacchetto</button><button className="btn-secondary" onClick={() => setModal("territory")}>Aggiungi territorio</button><button className="btn-secondary" onClick={() => setModal("user")}>Utente portale</button></>} />
      <ErrorBox error={err} />
      <div className="mb-4 flex gap-2 border-b border-slate-200 text-sm">
        {(["overview", "edit", "criteria"] as const).map((t) => (
          <button key={t} className={`border-b-2 px-3 py-2 ${tab === t ? "border-brand-600 font-medium text-brand-700" : "border-transparent text-slate-600"}`} onClick={() => setTab(t)}>{t === "overview" ? "Panoramica" : t === "edit" ? "Scheda" : "Criteri di qualifica"}</button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Lead residui" value={c.balance} tone={c.balance <= 3 ? "text-amber-700" : ""} />
            <Kpi label="Lead consegnati" value={c.deliveredCount} />
            <Kpi label="Pacchetti attivi" value={c.activePackages} />
            <Kpi label="Replacement aperti" value={c.openReplacements} />
          </div>
          <section className="card p-0">
            <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Pacchetti</h2>
            <table className="table">
              <thead><tr><th>Codice</th><th>Prodotto</th><th>Quantità</th><th>Prezzo</th><th>Totale</th><th>Consegnati</th><th>Repl.</th><th>Residui</th><th>Stato</th><th></th></tr></thead>
              <tbody>
                {pkgs?.map((p) => (
                  <tr key={p.id}>
                    <td className="font-mono"><Link className="text-brand-600 hover:underline" href={`/admin/packages?clientId=${id}`}>{p.code}</Link></td><td>{p.productName}</td><td>{p.quantity}</td><td>{fmtMoney(p.unitPrice)}</td><td>{fmtMoney(p.totalPrice)}</td><td>{p.deliveredCount}</td><td>{p.replacementCount}</td><td className="font-semibold">{p.balance}</td><td><Badge>{PACKAGE_STATUS_LABELS[p.status]}</Badge></td>
                    <td>{(p.status === "DRAFT" || p.status === "AWAITING_PAYMENT") && <button className="btn-success" disabled={busy} onClick={() => run(() => api(`/packages/${p.id}/activate`, { method: "POST", json: {} }))}>Registra pagamento</button>}</td>
                  </tr>
                ))}
                {pkgs?.length === 0 && <tr><td colSpan={10} className="text-slate-500">Nessun pacchetto.</td></tr>}
              </tbody>
            </table>
          </section>
          <section className="card p-0">
            <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Territori serviti</h2>
            <table className="table">
              <thead><tr><th>Livello</th><th>Valore</th><th>Provincia</th><th>Regione</th><th>Esclusiva</th><th></th></tr></thead>
              <tbody>
                {terr?.map((t) => (
                  <tr key={t.id}><td>{TERRITORY_LEVEL_LABELS[t.level]}</td><td className="font-medium">{t.value}</td><td>{t.province}</td><td>{t.region}</td><td>{t.exclusive ? <Badge className="bg-violet-100 text-violet-800">esclusivo</Badge> : "condiviso"}</td><td><button className="text-xs text-red-600 hover:underline" onClick={() => run(() => api(`/territories/${t.id}`, { method: "DELETE" }))}>Rimuovi</button></td></tr>
                ))}
                {terr?.length === 0 && <tr><td colSpan={6} className="text-slate-500">Nessun territorio: il cliente non riceverà lead finché non ne aggiungi uno.</td></tr>}
              </tbody>
            </table>
          </section>
          <section className="card">
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Utenti portale</h2>
            {c.portalUsers.length === 0 && <p className="text-sm text-slate-500">Nessun accesso al portale creato.</p>}
            <ul className="text-sm">{c.portalUsers.map((u) => <li key={u.id}>{u.fullName} · {u.email}{!u.active && " (disattivo)"}</li>)}</ul>
          </section>
          {an && (
            <section>
              <h2 className="mb-2 text-sm font-semibold text-slate-600">Performance ultimi 6 mesi</h2>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Kpi label="Ricevuti" value={an.received} />
                <Kpi label="Appuntamenti" value={an.appointments} hint={`${an.show} show`} />
                <Kpi label="Vendite" value={an.won} hint={fmtMoney(an.salesValue)} />
                <Kpi label="Replacement rate 30gg" value={`${(an.replacementRate.rate * 100).toFixed(0)}%`} tone={an.replacementRate.rate > 0.2 ? "text-red-700" : ""} hint={`${an.replacementRate.approved} su ${an.replacementRate.delivered}`} />
                {user?.role === "SUPER_ADMIN" && <Kpi label="Revenue / costo lead" value={an.revenueOverCost != null ? `${fmtNum(an.revenueOverCost, 2)}x` : "n.d."} hint={`Costo lead ${fmtMoney(an.leadCost)}`} />}
              </div>
            </section>
          )}
        </div>
      )}
      {tab === "edit" && (
        <div className="max-w-4xl">
          <ClientForm initial={fromClient(c)} busy={busy} submitLabel="Salva modifiche" onSubmit={(v) => run(() => api(`/clients/${id}`, { method: "PATCH", json: toPayload(v) }))} />
        </div>
      )}
      {tab === "criteria" && <CriteriaEditor clientId={id} initial={c.criteria ?? []} onSaved={reload} />}
      <PackageModal open={modal === "package"} onClose={() => setModal(null)} busy={busy} defaultPrice={String(c.defaultLeadPrice ?? "")} onSubmit={(body) => run(() => api("/packages", { method: "POST", json: { clientId: id, ...body } }))} />
      <TerritoryModal open={modal === "territory"} onClose={() => setModal(null)} busy={busy} onSubmit={(body) => run(() => api("/territories", { method: "POST", json: { clientId: id, ...body } }))} />
      <PortalUserModal open={modal === "user"} onClose={() => setModal(null)} busy={busy} onSubmit={(body) => run(() => api(`/clients/${id}/portal-users`, { method: "POST", json: body }))} />
      <p className="mt-6 text-xs text-slate-400">Creato il {fmtDate(String(c.createdAt))}</p>
    </div>
  );
}

function PackageModal({ open, onClose, onSubmit, busy, defaultPrice }: { open: boolean; onClose: () => void; onSubmit: (b: Record<string, unknown>) => void; busy: boolean; defaultPrice: string }) {
  const [f, setF] = useState({ productName: "Lead + prequalifica commerciale", quantity: "20", unitPrice: defaultPrice || "200", paid: true, paymentReference: "", warningThreshold: "5", alertThreshold: "3" });
  return (
    <Modal open={open} onClose={onClose} title="Nuovo pacchetto">
      <div className="space-y-3">
        <Field label="Prodotto"><input className="input" value={f.productName} onChange={(e) => setF({ ...f, productName: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantità lead"><input className="input" type="number" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          <Field label="Prezzo unitario (euro)"><input className="input" type="number" step="0.01" value={f.unitPrice} onChange={(e) => setF({ ...f, unitPrice: e.target.value })} /></Field>
          <Field label="Soglia warning"><input className="input" type="number" value={f.warningThreshold} onChange={(e) => setF({ ...f, warningThreshold: e.target.value })} /></Field>
          <Field label="Soglia alert commerciale"><input className="input" type="number" value={f.alertThreshold} onChange={(e) => setF({ ...f, alertThreshold: e.target.value })} /></Field>
        </div>
        <p className="text-sm text-slate-600">Totale: {fmtMoney(Number(f.quantity || 0) * Number(f.unitPrice || 0))}</p>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.paid} onChange={(e) => setF({ ...f, paid: e.target.checked })} /> Pagamento già ricevuto (attiva subito e registra +{f.quantity} crediti)</label>
        {f.paid && <Field label="Riferimento pagamento"><input className="input" value={f.paymentReference} onChange={(e) => setF({ ...f, paymentReference: e.target.value })} /></Field>}
        <button className="btn-primary" disabled={busy} onClick={() => onSubmit({ productName: f.productName, quantity: Number(f.quantity), unitPrice: Number(f.unitPrice), paid: f.paid, paymentReference: f.paymentReference || null, warningThreshold: Number(f.warningThreshold), alertThreshold: Number(f.alertThreshold) })}>Crea pacchetto</button>
      </div>
    </Modal>
  );
}

function TerritoryModal({ open, onClose, onSubmit, busy }: { open: boolean; onClose: () => void; onSubmit: (b: Record<string, unknown>) => void; busy: boolean }) {
  const [f, setF] = useState({ level: "PROVINCE", value: "", province: "", region: "", exclusive: false });
  return (
    <Modal open={open} onClose={onClose} title="Aggiungi territorio">
      <div className="space-y-3">
        <Field label="Livello"><select className="input" value={f.level} onChange={(e) => setF({ ...f, level: e.target.value })}>{Object.entries(TERRITORY_LEVEL_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Valore" hint="Sigla provincia (VI), nome comune, CAP, regione o IT"><input className="input" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} /></Field>
        {(f.level === "MUNICIPALITY" || f.level === "POSTAL_CODE") && <Field label="Provincia di appartenenza" hint="Serve per rilevare i conflitti con le esclusive provinciali"><input className="input" value={f.province} onChange={(e) => setF({ ...f, province: e.target.value })} /></Field>}
        {f.level !== "COUNTRY" && f.level !== "REGION" && <Field label="Regione"><input className="input" value={f.region} onChange={(e) => setF({ ...f, region: e.target.value })} /></Field>}
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.exclusive} onChange={(e) => setF({ ...f, exclusive: e.target.checked })} /> Esclusiva: nessun altro cliente riceverà lead da questo territorio</label>
        <button className="btn-primary" disabled={busy || !f.value} onClick={() => onSubmit({ level: f.level, value: f.value, province: f.province || null, region: f.region || null, exclusive: f.exclusive })}>Aggiungi</button>
      </div>
    </Modal>
  );
}

function PortalUserModal({ open, onClose, onSubmit, busy }: { open: boolean; onClose: () => void; onSubmit: (b: Record<string, unknown>) => void; busy: boolean }) {
  const [f, setF] = useState({ fullName: "", email: "", password: "" });
  return (
    <Modal open={open} onClose={onClose} title="Accesso al portale cliente">
      <div className="space-y-3">
        <Field label="Nome"><input className="input" value={f.fullName} onChange={(e) => setF({ ...f, fullName: e.target.value })} /></Field>
        <Field label="Email"><input className="input" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Password iniziale (min. 8 caratteri)"><input className="input" type="text" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <button className="btn-primary" disabled={busy || f.password.length < 8 || !f.email} onClick={() => onSubmit(f)}>Crea accesso</button>
      </div>
    </Modal>
  );
}

const OPS = ["eq", "neq", "gte", "lte", "in", "truthy", "falsy", "contains"];
function CriteriaEditor({ clientId, initial, onSaved }: { clientId: string; initial: Array<{ field: string; op: string; value?: unknown; kind: string; label: string }>; onSaved: () => void }) {
  const [rows, setRows] = useState(initial.map((c) => ({ ...c, value: c.value === undefined ? "" : Array.isArray(c.value) ? c.value.join(",") : String(c.value) })));
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const update = (i: number, k: string, v: string) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  async function save() {
    setErr(null);
    try {
      const criteria = rows.map((r) => ({ field: r.field, op: r.op, kind: r.kind, label: r.label, value: r.op === "in" ? r.value.split(",").map((s) => s.trim()) : r.value === "" ? undefined : Number.isNaN(Number(r.value)) ? r.value : Number(r.value) }));
      await api(`/clients/${clientId}`, { method: "PATCH", json: { criteria } });
      setSaved(true);
      onSaved();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div className="card space-y-3">
      <p className="text-sm text-slate-600">Criteri specifici del cliente, valutati sulle risposte dello script oltre al template del verticale. Gli obbligatori e le esclusioni escludono il cliente dal routing per quel lead.</p>
      <ErrorBox error={err} />
      <table className="table">
        <thead><tr><th>Campo risposta</th><th>Operatore</th><th>Valore</th><th>Tipo</th><th>Etichetta</th><th></th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td><input className="input" value={r.field} onChange={(e) => update(i, "field", e.target.value)} placeholder="monthly_bill" /></td>
              <td><select className="input" value={r.op} onChange={(e) => update(i, "op", e.target.value)}>{OPS.map((o) => <option key={o}>{o}</option>)}</select></td>
              <td><input className="input" value={r.value} onChange={(e) => update(i, "value", e.target.value)} placeholder="100 oppure a,b,c" /></td>
              <td><select className="input" value={r.kind} onChange={(e) => update(i, "kind", e.target.value)}><option value="MANDATORY">Obbligatorio</option><option value="PREFERRED">Preferenziale</option><option value="EXCLUSION">Esclusione</option></select></td>
              <td><input className="input" value={r.label} onChange={(e) => update(i, "label", e.target.value)} /></td>
              <td><button className="text-xs text-red-600" onClick={() => setRows(rows.filter((_, j) => j !== i))}>Rimuovi</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-2">
        <button className="btn-secondary" onClick={() => setRows([...rows, { field: "", op: "gte", value: "", kind: "MANDATORY", label: "" }])}>Aggiungi criterio</button>
        <button className="btn-primary" onClick={save}>Salva criteri</button>
        {saved && <span className="self-center text-sm text-emerald-700">Salvato.</span>}
      </div>
    </div>
  );
}
