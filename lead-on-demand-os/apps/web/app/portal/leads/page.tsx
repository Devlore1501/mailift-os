"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { LeadStatusBadge } from "@/components/LeadTable";
import { API_URL, getToken, qs } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { LEAD_TYPE_LABELS, QUAL_CATEGORY_COLORS, QUAL_CATEGORY_LABELS } from "@/lib/labels";

interface PortalLead { id: string; code: string; deliveredAt: string; firstName: string | null; lastName: string | null; phone: string | null; municipality: string | null; province: string | null; leadType: string; status: string; qualificationCategory: string | null; qualificationScore: number | null; replaced: boolean }

export default function PortalLeads() {
  const [search, setSearch] = useState("");
  const { data, error } = useApi<{ items: PortalLead[]; total: number }>(`/portal/leads${qs({ search, limit: 200 })}`);
  async function exportCsv() {
    const res = await fetch(`${API_URL}/portal/leads/export.csv`, { headers: { Authorization: `Bearer ${getToken()}` } });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await res.blob());
    a.download = "lead.csv";
    a.click();
  }
  return (
    <div>
      <PageTitle title="Lead ricevuti" subtitle={data ? `${data.items.length} lead` : undefined} actions={<button className="btn-secondary" onClick={exportCsv}>Esporta CSV</button>} />
      <ErrorBox error={error} />
      <input className="input mb-3 max-w-md" placeholder="Cerca per nome, telefono, comune" value={search} onChange={(e) => setSearch(e.target.value)} />
      {data && data.items.length === 0 && <Empty text="Nessun lead consegnato finora." />}
      {data && data.items.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="table">
            <thead><tr><th>Nome</th><th>Data</th><th>Comune</th><th>Tipologia</th><th>Qualifica</th><th>Stato</th><th></th></tr></thead>
            <tbody>
              {data.items.map((l) => (
                <tr key={l.id}>
                  <td><Link href={`/portal/leads/${l.id}`} className="font-medium text-brand-600 hover:underline">{l.firstName} {l.lastName}</Link><div className="text-xs text-slate-500">{l.code} · {l.phone}</div></td>
                  <td className="whitespace-nowrap">{fmtDate(l.deliveredAt)}</td>
                  <td>{l.municipality} {l.province ? `(${l.province})` : ""}</td>
                  <td>{LEAD_TYPE_LABELS[l.leadType]}</td>
                  <td>{l.qualificationCategory && <Badge className={QUAL_CATEGORY_COLORS[l.qualificationCategory]}>{QUAL_CATEGORY_LABELS[l.qualificationCategory]}</Badge>}</td>
                  <td><LeadStatusBadge status={l.status} />{l.replaced && <Badge className="ml-1 bg-orange-100 text-orange-800">sostituito</Badge>}</td>
                  <td><Link href={`/portal/leads/${l.id}`} className="text-sm text-brand-600 hover:underline">Apri</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
