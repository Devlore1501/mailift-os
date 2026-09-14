"use client";

import { useState } from "react";
import { Field } from "@/components/ui";
import { CLIENT_STATUS_LABELS, CLIENT_TYPE_LABELS, OFFER_TYPE_LABELS } from "@/lib/labels";

export interface ClientFormValues {
  legalName: string; tradeName: string; vatNumber: string; contactName: string; phone: string; email: string; address: string; region: string; website: string;
  clientType: string; offerType: string; defaultLeadPrice: string; status: string; capDaily: string; capWeekly: string; capMonthly: string; priority: string;
  ghlLocationId: string; ghlPipelineId: string; ghlPipelineStageId: string; ghlCalendarId: string; webhookUrl: string; webhookSecret: string; externalCrm: string; notificationEmail: string; notificationPhone: string; replacementSlaHours: string; notes: string;
}

export const emptyClient: ClientFormValues = { legalName: "", tradeName: "", vatNumber: "", contactName: "", phone: "", email: "", address: "", region: "", website: "", clientType: "RESIDENTIAL", offerType: "PHONE_PREQUALIFIED", defaultLeadPrice: "200", status: "ACTIVE", capDaily: "", capWeekly: "", capMonthly: "", priority: "0", ghlLocationId: "", ghlPipelineId: "", ghlPipelineStageId: "", ghlCalendarId: "", webhookUrl: "", webhookSecret: "", externalCrm: "", notificationEmail: "", notificationPhone: "", replacementSlaHours: "72", notes: "" };

export function fromClient(c: Record<string, unknown>): ClientFormValues {
  const out = { ...emptyClient };
  for (const k of Object.keys(emptyClient) as Array<keyof ClientFormValues>) {
    const v = c[k];
    out[k] = v === null || v === undefined ? "" : String(v);
  }
  return out;
}

export function toPayload(v: ClientFormValues) {
  const num = (s: string) => (s === "" ? null : Number(s));
  return {
    legalName: v.legalName, tradeName: v.tradeName, vatNumber: v.vatNumber || null, contactName: v.contactName || null, phone: v.phone || null, email: v.email || null, address: v.address || null, region: v.region ? v.region.toUpperCase() : null, website: v.website || null,
    clientType: v.clientType, offerType: v.offerType, defaultLeadPrice: num(v.defaultLeadPrice), status: v.status, capDaily: num(v.capDaily), capWeekly: num(v.capWeekly), capMonthly: num(v.capMonthly), priority: Number(v.priority || 0),
    ghlLocationId: v.ghlLocationId || null, ghlPipelineId: v.ghlPipelineId || null, ghlPipelineStageId: v.ghlPipelineStageId || null, ghlCalendarId: v.ghlCalendarId || null, webhookUrl: v.webhookUrl || null, webhookSecret: v.webhookSecret || null, externalCrm: v.externalCrm || null, notificationEmail: v.notificationEmail || null, notificationPhone: v.notificationPhone || null, replacementSlaHours: Number(v.replacementSlaHours || 72), notes: v.notes || null,
  };
}

export function ClientForm({ initial, onSubmit, busy, submitLabel }: { initial: ClientFormValues; onSubmit: (v: ClientFormValues) => void; busy: boolean; submitLabel: string }) {
  const [v, setV] = useState(initial);
  const set = (k: keyof ClientFormValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value });
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(v); }} className="space-y-4">
      <section className="card grid grid-cols-1 gap-3 md:grid-cols-3">
        <h2 className="font-semibold md:col-span-3">Informazioni aziendali</h2>
        <Field label="Ragione sociale"><input className="input" value={v.legalName} onChange={set("legalName")} required /></Field>
        <Field label="Nome commerciale"><input className="input" value={v.tradeName} onChange={set("tradeName")} required /></Field>
        <Field label="Partita IVA"><input className="input" value={v.vatNumber} onChange={set("vatNumber")} /></Field>
        <Field label="Referente"><input className="input" value={v.contactName} onChange={set("contactName")} /></Field>
        <Field label="Telefono"><input className="input" value={v.phone} onChange={set("phone")} /></Field>
        <Field label="Email"><input className="input" type="email" value={v.email} onChange={set("email")} /></Field>
        <Field label="Indirizzo"><input className="input" value={v.address} onChange={set("address")} /></Field>
        <Field label="Regione"><input className="input" value={v.region} onChange={set("region")} /></Field>
        <Field label="Sito"><input className="input" value={v.website} onChange={set("website")} /></Field>
      </section>
      <section className="card grid grid-cols-1 gap-3 md:grid-cols-3">
        <h2 className="font-semibold md:col-span-3">Configurazione commerciale</h2>
        <Field label="Tipologia cliente"><select className="input" value={v.clientType} onChange={set("clientType")}>{Object.entries(CLIENT_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Offerta"><select className="input" value={v.offerType} onChange={set("offerType")}>{Object.entries(OFFER_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Prezzo per lead (euro)"><input className="input" type="number" step="0.01" value={v.defaultLeadPrice} onChange={set("defaultLeadPrice")} /></Field>
        <Field label="Stato"><select className="input" value={v.status} onChange={set("status")}>{Object.entries(CLIENT_STATUS_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Cap giornaliero" hint="Vuoto = nessun limite"><input className="input" type="number" value={v.capDaily} onChange={set("capDaily")} /></Field>
        <Field label="Cap settimanale"><input className="input" type="number" value={v.capWeekly} onChange={set("capWeekly")} /></Field>
        <Field label="Cap mensile"><input className="input" type="number" value={v.capMonthly} onChange={set("capMonthly")} /></Field>
        <Field label="Priorità routing" hint="A parità di territorio vince la priorità più alta"><input className="input" type="number" value={v.priority} onChange={set("priority")} /></Field>
        <Field label="SLA replacement (ore)"><input className="input" type="number" value={v.replacementSlaHours} onChange={set("replacementSlaHours")} /></Field>
      </section>
      <section className="card grid grid-cols-1 gap-3 md:grid-cols-3">
        <h2 className="font-semibold md:col-span-3">Configurazione operativa</h2>
        <Field label="GHL Location ID"><input className="input" value={v.ghlLocationId} onChange={set("ghlLocationId")} /></Field>
        <Field label="GHL Pipeline ID"><input className="input" value={v.ghlPipelineId} onChange={set("ghlPipelineId")} /></Field>
        <Field label="GHL Pipeline Stage ID"><input className="input" value={v.ghlPipelineStageId} onChange={set("ghlPipelineStageId")} /></Field>
        <Field label="GHL Calendar ID"><input className="input" value={v.ghlCalendarId} onChange={set("ghlCalendarId")} /></Field>
        <Field label="Webhook URL (eventi in uscita)"><input className="input" value={v.webhookUrl} onChange={set("webhookUrl")} /></Field>
        <Field label="Webhook secret (firma HMAC)"><input className="input" value={v.webhookSecret} onChange={set("webhookSecret")} /></Field>
        <Field label="CRM esterno"><input className="input" value={v.externalCrm} onChange={set("externalCrm")} /></Field>
        <Field label="Email notifiche"><input className="input" value={v.notificationEmail} onChange={set("notificationEmail")} /></Field>
        <Field label="Telefono notifiche"><input className="input" value={v.notificationPhone} onChange={set("notificationPhone")} /></Field>
        <Field label="Note interne"><textarea className="input md:col-span-3" rows={2} value={v.notes} onChange={set("notes")} /></Field>
      </section>
      <button className="btn-primary" disabled={busy}>{submitLabel}</button>
    </form>
  );
}
