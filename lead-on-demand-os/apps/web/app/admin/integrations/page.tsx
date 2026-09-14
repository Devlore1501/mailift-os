"use client";

import { useState } from "react";
import { Badge, ErrorBox, Field, Modal, PageTitle, useApi } from "@/components/ui";
import { api, API_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";

interface Mapping { id: string; clientId: string | null; lodField: string; ghlField: string; kind: string }
interface Integration { id: string; clientId: string | null; provider: string; config: Record<string, unknown>; active: boolean }
interface WebhookEvent { id: string; provider: string; externalEventId: string; eventType: string; status: string; error: string | null; receivedAt: string }
interface QueueRow { status: string; kind: string; n: number }

export default function IntegrationsPage() {
  const { user } = useAuth();
  const isSuper = user?.role === "SUPER_ADMIN";
  const { data: clients } = useApi<Array<{ id: string; tradeName: string }>>("/clients");
  const { data: mappings, reload: reloadMap } = useApi<Mapping[]>("/ghl-mappings");
  const { data: integrations, reload: reloadInt } = useApi<Integration[]>(isSuper ? "/integrations" : null);
  const { data: events } = useApi<WebhookEvent[]>("/webhook-events");
  const { data: queue } = useApi<QueueRow[]>("/system/queue");
  const [modal, setModal] = useState<null | "mapping" | "integration">(null);
  const [m, setM] = useState({ clientId: "", lodField: "", ghlField: "", kind: "custom_field" });
  const [i, setI] = useState({ clientId: "", apiKey: "", locationId: "" });
  const [err, setErr] = useState<string | null>(null);
  const clientName = (id: string | null) => (id ? clients?.find((c) => c.id === id)?.tradeName ?? id : "Default (tutti)");
  async function run(fn: () => Promise<unknown>) {
    setErr(null);
    try {
      await fn();
      setModal(null);
      reloadMap();
      reloadInt();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div className="space-y-6">
      <PageTitle title="Integrazioni" subtitle="GoHighLevel in uscita (contatti, opportunità, tag, custom field) e in entrata (webhook)" actions={<><button className="btn-primary" onClick={() => setModal("mapping")}>Nuovo mapping</button>{isSuper && <button className="btn-secondary" onClick={() => setModal("integration")}>Token GHL per cliente</button>}</>} />
      <ErrorBox error={err} />
      <section className="card text-sm">
        <h2 className="mb-2 font-semibold">Webhook in entrata da GHL</h2>
        <p className="text-slate-600">Configura nei workflow GHL un'azione Webhook verso <code className="rounded bg-slate-100 px-1">{API_URL}/webhooks/ghl</code> con header <code className="rounded bg-slate-100 px-1">x-webhook-secret</code>. Nel corpo: <code className="rounded bg-slate-100 px-1">type</code> (appointment.created, appointment.show, appointment.no_show, appointment.cancelled, sale.won, sale.lost, opportunity.updated), <code className="rounded bg-slate-100 px-1">contact_id</code> oppure <code className="rounded bg-slate-100 px-1">lead_code</code>, e per gli appuntamenti <code className="rounded bg-slate-100 px-1">appointment.id</code> e <code className="rounded bg-slate-100 px-1">appointment.start_time</code>. Un <code className="rounded bg-slate-100 px-1">event_id</code> rende l'evento idempotente.</p>
        <p className="mt-2 text-slate-600">Ingresso lead da landing, Make o Zapier: <code className="rounded bg-slate-100 px-1">POST {API_URL}/leads</code> con header <code className="rounded bg-slate-100 px-1">x-api-key</code>.</p>
      </section>
      {isSuper && (
        <section className="card p-0">
          <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Credenziali GHL</h2>
          <table className="table">
            <thead><tr><th>Cliente</th><th>Provider</th><th>Location</th><th>Token</th><th>Stato</th></tr></thead>
            <tbody>
              {integrations?.map((it) => <tr key={it.id}><td>{clientName(it.clientId)}</td><td>{it.provider}</td><td>{String(it.config.locationId ?? "")}</td><td>{String(it.config.apiKey ?? "")}</td><td>{it.active ? "attiva" : "disattiva"}</td></tr>)}
              {integrations?.length === 0 && <tr><td colSpan={5} className="text-slate-500">Nessuna integrazione per cliente: viene usato il token globale GHL_API_KEY con la Location ID della scheda cliente.</td></tr>}
            </tbody>
          </table>
        </section>
      )}
      <section className="card p-0">
        <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Mapping campi Lead on Demand → GHL</h2>
        <table className="table">
          <thead><tr><th>Cliente</th><th>Campo Lead on Demand</th><th>Campo GHL</th><th>Tipo</th><th></th></tr></thead>
          <tbody>
            {mappings?.map((mp) => <tr key={mp.id}><td>{clientName(mp.clientId)}</td><td className="font-mono">{mp.lodField}</td><td className="font-mono">{mp.ghlField}</td><td><Badge>{mp.kind}</Badge></td><td><button className="text-xs text-red-600" onClick={() => run(() => api(`/ghl-mappings/${mp.id}`, { method: "DELETE" }))}>Rimuovi</button></td></tr>)}
            {mappings?.length === 0 && <tr><td colSpan={5} className="text-slate-500">Nessun mapping: vengono inviati solo i campi standard, i tag e la nota di qualifica.</td></tr>}
          </tbody>
        </table>
      </section>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="card p-0">
          <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Ultimi eventi ricevuti</h2>
          <table className="table"><thead><tr><th>Ricevuto</th><th>Tipo</th><th>Stato</th></tr></thead><tbody>
            {events?.slice(0, 20).map((e) => <tr key={e.id}><td className="whitespace-nowrap">{fmtDate(e.receivedAt)}</td><td>{e.eventType}</td><td><Badge className={e.status === "FAILED" ? "bg-red-100 text-red-800" : e.status === "PROCESSED" ? "bg-emerald-100 text-emerald-800" : ""}>{e.status}</Badge>{e.error && <div className="text-xs text-red-700">{e.error}</div>}</td></tr>)}
            {events?.length === 0 && <tr><td colSpan={3} className="text-slate-500">Nessun evento ricevuto.</td></tr>}
          </tbody></table>
        </div>
        <div className="card p-0">
          <h2 className="px-4 pt-3 text-sm font-semibold text-slate-600">Coda job</h2>
          <table className="table"><thead><tr><th>Job</th><th>Stato</th><th>Numero</th></tr></thead><tbody>
            {queue?.map((q, idx) => <tr key={idx}><td>{q.kind}</td><td><Badge className={q.status === "DEAD" ? "bg-red-100 text-red-800" : q.status === "DONE" ? "bg-emerald-100 text-emerald-800" : ""}>{q.status}</Badge></td><td>{q.n}</td></tr>)}
            {queue?.length === 0 && <tr><td colSpan={3} className="text-slate-500">Coda vuota.</td></tr>}
          </tbody></table>
        </div>
      </section>
      <Modal open={modal === "mapping"} onClose={() => setModal(null)} title="Nuovo mapping GHL">
        <div className="space-y-3">
          <Field label="Cliente"><select className="input" value={m.clientId} onChange={(e) => setM({ ...m, clientId: e.target.value })}><option value="">Default per tutti i clienti</option>{clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName}</option>)}</select></Field>
          <Field label="Campo Lead on Demand" hint="Chiave della risposta (monthly_bill, timeline…) oppure lead_code, qualification_status, qualification_score, province, municipality, postal_code, campaign, source"><input className="input" value={m.lodField} onChange={(e) => setM({ ...m, lodField: e.target.value })} /></Field>
          <Field label="Campo GHL" hint="ID del custom field, oppure per i tag un template come lod-{value}"><input className="input" value={m.ghlField} onChange={(e) => setM({ ...m, ghlField: e.target.value })} /></Field>
          <Field label="Tipo"><select className="input" value={m.kind} onChange={(e) => setM({ ...m, kind: e.target.value })}><option value="custom_field">Custom field</option><option value="tag">Tag</option></select></Field>
          <button className="btn-primary" disabled={!m.lodField || !m.ghlField} onClick={() => run(() => api("/ghl-mappings", { method: "POST", json: { ...m, clientId: m.clientId || null } }))}>Salva</button>
        </div>
      </Modal>
      <Modal open={modal === "integration"} onClose={() => setModal(null)} title="Token GHL dedicato a un cliente">
        <div className="space-y-3">
          <Field label="Cliente"><select className="input" value={i.clientId} onChange={(e) => setI({ ...i, clientId: e.target.value })}><option value="">Seleziona…</option>{clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName}</option>)}</select></Field>
          <Field label="Private Integration Token (pit-…)"><input className="input" value={i.apiKey} onChange={(e) => setI({ ...i, apiKey: e.target.value })} /></Field>
          <Field label="Location ID"><input className="input" value={i.locationId} onChange={(e) => setI({ ...i, locationId: e.target.value })} /></Field>
          <button className="btn-primary" disabled={!i.clientId || !i.apiKey || !i.locationId} onClick={() => run(() => api("/integrations", { method: "POST", json: { clientId: i.clientId, provider: "ghl", config: { apiKey: i.apiKey, locationId: i.locationId } } }))}>Salva</button>
        </div>
      </Modal>
    </div>
  );
}
