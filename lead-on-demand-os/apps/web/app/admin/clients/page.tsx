"use client";

import Link from "next/link";
import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { CLIENT_STATUS_LABELS, CLIENT_TYPE_LABELS, OFFER_TYPE_LABELS } from "@/lib/labels";

interface ClientRow { id: string; code: string; tradeName: string; region: string | null; clientType: string; offerType: string; status: string; balance: number; deliveredCount: number; defaultLeadPrice: string | null }
const COLORS: Record<string, string> = { ACTIVE: "bg-emerald-100 text-emerald-800", PAUSED: "bg-amber-100 text-amber-800", OUT_OF_CREDIT: "bg-red-100 text-red-800", CANCELLED: "bg-slate-200 text-slate-700" };

export default function ClientsPage() {
  const { data, error } = useApi<ClientRow[]>("/clients");
  return (
    <div>
      <PageTitle title="Clienti" subtitle={data ? `${data.length} clienti` : undefined} actions={<Link href="/admin/clients/new" className="btn-primary">Nuovo cliente</Link>} />
      <ErrorBox error={error} />
      {data && data.length === 0 && <Empty text="Nessun cliente. Crea il primo." />}
      {data && data.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Codice</th><th>Cliente</th><th>Regione</th><th>Tipo</th><th>Offerta</th><th>Consegnati</th><th>Residui</th><th>Stato</th></tr></thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td className="font-mono">{c.code}</td>
                  <td><Link href={`/admin/clients/${c.id}`} className="font-medium text-brand-600 hover:underline">{c.tradeName}</Link></td>
                  <td>{c.region}</td>
                  <td>{CLIENT_TYPE_LABELS[c.clientType]}</td>
                  <td>{OFFER_TYPE_LABELS[c.offerType]}</td>
                  <td>{c.deliveredCount}</td>
                  <td className={c.balance <= 3 ? "font-semibold text-amber-700" : "font-semibold"}>{c.balance}</td>
                  <td><Badge className={COLORS[c.status]}>{CLIENT_STATUS_LABELS[c.status]}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
