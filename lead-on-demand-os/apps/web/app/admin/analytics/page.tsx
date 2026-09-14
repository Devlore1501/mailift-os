"use client";

import { useState } from "react";
import { ErrorBox, Kpi, PageTitle, useApi } from "@/components/ui";
import { qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtMoney, fmtNum, fmtPct } from "@/lib/format";

interface ClientAn { period: { from: string; to: string }; received: number; replaced: number; contacted: number; appointments: number; show: number; quotes: number; won: number; salesValue: number; leadCost: number; costPerCustomer: number | null; revenueOverCost: number | null; missingOutcome: number; replacementRate: { delivered: number; approved: number; rate: number } }

export default function AnalyticsPage() {
  const { user } = useAuth();
  const { data: clients } = useApi<Array<{ id: string; tradeName: string }>>("/clients");
  const [clientId, setClientId] = useState("");
  const [range, setRange] = useState({ from: "", to: "" });
  const { data, error } = useApi<ClientAn>(clientId ? `/clients/${clientId}/analytics${qs({ from: range.from ? new Date(range.from).toISOString() : "", to: range.to ? new Date(range.to + "T23:59:59").toISOString() : "" })}` : null);
  const rate = (a: number, b: number) => (b ? a / b : null);
  return (
    <div>
      <PageTitle title="Analytics per cliente" subtitle="Funnel, tassi e valore generato. Le metriche di esito dipendono da quanto il cliente registra nel portale." />
      <ErrorBox error={error} />
      <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-3">
        <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
          <option value="">Seleziona un cliente…</option>
          {clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName}</option>)}
        </select>
        <input className="input" type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} aria-label="Dal" />
        <input className="input" type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} aria-label="Al" />
      </div>
      {data && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Funnel</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
              <Kpi label="Lead consegnati" value={data.received} hint={`${data.replaced} sostituiti`} />
              <Kpi label="Contattati" value={data.contacted} />
              <Kpi label="Appuntamenti" value={data.appointments} hint={`appointment rate ${fmtPct(rate(data.appointments, data.received))}`} />
              <Kpi label="Show" value={data.show} hint={`show rate ${fmtPct(rate(data.show, data.appointments))}`} />
              <Kpi label="Preventivi" value={data.quotes} />
              <Kpi label="Vendite" value={data.won} hint={`close rate ${fmtPct(rate(data.won, data.received))}`} />
            </div>
          </section>
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Valore</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <Kpi label="Valore vendite" value={fmtMoney(data.salesValue)} />
              <Kpi label="Costo lead per il cliente" value={fmtMoney(data.leadCost)} />
              <Kpi label="Costo per cliente acquisito" value={data.costPerCustomer != null ? fmtMoney(data.costPerCustomer) : "n.d."} />
              <Kpi label="Revenue / costo Lead on Demand" value={data.revenueOverCost != null ? `${fmtNum(data.revenueOverCost, 2)}x` : "n.d."} />
              <Kpi label="Replacement rate 30gg" value={fmtPct(data.replacementRate.rate)} tone={data.replacementRate.rate > 0.2 ? "text-red-700" : ""} hint={`${data.replacementRate.approved} approvate su ${data.replacementRate.delivered} consegnati`} />
            </div>
          </section>
          <p className="text-sm text-slate-500">Lead senza esito registrato: {data.missingOutcome}. Le percentuali sopra sono calcolate solo sui dati confermati.</p>
          {user?.role === "MANAGER" && <p className="text-xs text-slate-400">Costi e margini interni di Lead on Demand sono riservati al Super Admin (dashboard e campagne).</p>}
        </div>
      )}
    </div>
  );
}
