"use client";

import Link from "next/link";
import { Badge, Empty, ErrorBox, Kpi, PageTitle, useApi } from "@/components/ui";
import { fmtDate, fmtMoney } from "@/lib/format";
import { PACKAGE_STATUS_LABELS } from "@/lib/labels";

interface Dash {
  client: { tradeName: string; offerType: string; replacementSlaHours: number; status: string };
  packages: Array<{ id: string; code: string; productName: string; quantity: number; status: string; balance: number; delivered: number; replacements: number }>;
  stats: { received: number; contacted: number; appointments: number; show: number; quotes: number; won: number; salesValue: number; missingOutcome: number };
}
interface PortalLead { id: string; code: string; deliveredAt: string; firstName: string | null; lastName: string | null; municipality: string | null; status: string; qualificationCategory: string | null }

export default function PortalHome() {
  const { data, error } = useApi<Dash>("/portal/dashboard");
  const { data: leads } = useApi<{ items: PortalLead[] }>("/portal/leads?limit=8");
  const current = data?.packages.find((p) => p.status === "ACTIVE" || p.status === "LOW_BALANCE") ?? data?.packages[0];
  return (
    <div>
      <PageTitle title={data ? data.client.tradeName : "Dashboard"} subtitle="Riepilogo del pacchetto e dei lead ricevuti" />
      <ErrorBox error={error} />
      {data && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Pacchetto attuale {current && <Badge>{PACKAGE_STATUS_LABELS[current.status]}</Badge>}</h2>
            {!current && <Empty text="Nessun pacchetto attivo. Contatta Lead on Demand per attivarne uno." />}
            {current && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Kpi label="Acquistati" value={current.quantity} hint={current.productName} />
                <Kpi label="Consegnati" value={current.delivered} />
                <Kpi label="Residui" value={current.balance} tone={current.balance <= 3 ? "text-amber-700" : ""} hint={current.balance <= 3 ? "Pacchetto in esaurimento" : undefined} />
                <Kpi label="Sostituzioni" value={current.replacements} />
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Ultimi 6 mesi</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <Kpi label="Lead ricevuti" value={data.stats.received} />
              <Kpi label="Appuntamenti" value={data.stats.appointments} hint={`${data.stats.show} show`} />
              <Kpi label="Preventivi" value={data.stats.quotes} />
              <Kpi label="Vendite" value={data.stats.won} hint={fmtMoney(data.stats.salesValue)} />
              <Kpi label="Senza esito" value={data.stats.missingOutcome} hint="Lead senza esito registrato" tone={data.stats.missingOutcome ? "text-amber-700" : ""} />
            </div>
          </section>
          <section className="card">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-600">Ultimi lead</h2>
              <Link href="/portal/leads" className="text-sm text-brand-600 hover:underline">Tutti i lead</Link>
            </div>
            {leads && leads.items.length === 0 && <p className="text-sm text-slate-500">Nessun lead ancora consegnato.</p>}
            <ul className="divide-y divide-slate-100 text-sm">
              {leads?.items.map((l) => (
                <li key={l.id} className="flex items-center justify-between py-2">
                  <Link href={`/portal/leads/${l.id}`} className="text-brand-600 hover:underline">{l.code} · {l.firstName} {l.lastName}</Link>
                  <span className="text-slate-500">{l.municipality} · {fmtDate(l.deliveredAt, false)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
