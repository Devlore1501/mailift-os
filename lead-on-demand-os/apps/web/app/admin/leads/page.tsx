"use client";

import { useState } from "react";
import Link from "next/link";
import { LeadTable, type LeadRow } from "@/components/LeadTable";
import { Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { API_URL, getToken, qs } from "@/lib/api";
import { LEAD_STATUS_LABELS, QUAL_CATEGORY_LABELS } from "@/lib/labels";

export default function LeadsPage() {
  const [f, setF] = useState({ search: "", status: "", clientId: "", province: "", region: "", qualificationCategory: "", campaignId: "", from: "", to: "", replaced: "", offset: 0 });
  const query = qs({ ...f, from: f.from ? new Date(f.from).toISOString() : "", to: f.to ? new Date(f.to + "T23:59:59").toISOString() : "", limit: 50 });
  const { data, error, loading } = useApi<{ items: LeadRow[]; total: number; limit: number; offset: number }>(`/leads${query}`);
  const { data: clients } = useApi<Array<{ id: string; tradeName: string }>>("/clients");
  const { data: campaigns } = useApi<Array<{ id: string; name: string }>>("/campaigns");
  const set = (k: string, v: string) => setF({ ...f, [k]: v, offset: 0 });

  async function exportCsv() {
    const res = await fetch(`${API_URL}/leads/export.csv${query}`, { headers: { Authorization: `Bearer ${getToken()}` } });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "leads.csv";
    a.click();
  }

  return (
    <div>
      <PageTitle title="Lead" subtitle={data ? `${data.total} risultati` : undefined} actions={<><Link href="/admin/leads/new" className="btn-primary">Nuovo lead manuale</Link><button className="btn-secondary" onClick={exportCsv}>Esporta CSV</button></>} />
      <ErrorBox error={error} />
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <input className="input md:col-span-2" placeholder="Cerca nome, telefono, email, codice, comune" value={f.search} onChange={(e) => set("search", e.target.value)} />
        <select className="input" value={f.status} onChange={(e) => set("status", e.target.value)}>
          <option value="">Tutti gli stati</option>
          {Object.entries(LEAD_STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="input" value={f.clientId} onChange={(e) => set("clientId", e.target.value)}>
          <option value="">Tutti i clienti</option>
          {clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName}</option>)}
        </select>
        <select className="input" value={f.qualificationCategory} onChange={(e) => set("qualificationCategory", e.target.value)}>
          <option value="">Ogni qualifica</option>
          {Object.entries(QUAL_CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className="input" placeholder="Provincia" value={f.province} onChange={(e) => set("province", e.target.value)} />
        <input className="input" placeholder="Regione" value={f.region} onChange={(e) => set("region", e.target.value)} />
        <select className="input" value={f.campaignId} onChange={(e) => set("campaignId", e.target.value)}>
          <option value="">Tutte le campagne</option>
          {campaigns?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input className="input" type="date" value={f.from} onChange={(e) => set("from", e.target.value)} aria-label="Dal" />
        <input className="input" type="date" value={f.to} onChange={(e) => set("to", e.target.value)} aria-label="Al" />
        <select className="input" value={f.replaced} onChange={(e) => set("replaced", e.target.value)}>
          <option value="">Sostituiti e non</option>
          <option value="true">Solo sostituiti</option>
          <option value="false">Non sostituiti</option>
        </select>
      </div>
      <div className="card p-0">
        {loading && !data && <div className="p-4 text-sm text-slate-500">Caricamento…</div>}
        {data && data.items.length === 0 && <Empty text="Nessun lead con questi filtri." />}
        {data && data.items.length > 0 && <LeadTable leads={data.items} base="/admin/leads" />}
      </div>
      {data && data.total > data.limit && (
        <div className="mt-3 flex items-center gap-2 text-sm">
          <button className="btn-secondary" disabled={f.offset === 0} onClick={() => setF({ ...f, offset: Math.max(0, f.offset - 50) })}>Precedenti</button>
          <span className="text-slate-500">{f.offset + 1}–{Math.min(f.offset + 50, data.total)} di {data.total}</span>
          <button className="btn-secondary" disabled={f.offset + 50 >= data.total} onClick={() => setF({ ...f, offset: f.offset + 50 })}>Successivi</button>
        </div>
      )}
    </div>
  );
}
