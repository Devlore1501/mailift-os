"use client";

import { useState } from "react";
import { ErrorBox, Kpi, PageTitle, useApi } from "@/components/ui";
import { qs } from "@/lib/api";
import { fmtMoney, fmtNum } from "@/lib/format";

interface Stats { period: { from: string; to: string }; received: number; replaced: number; contacted: number; appointments: number; show: number; quotes: number; won: number; salesValue: number; leadCost: number; costPerCustomer: number | null; revenueOverCost: number | null; missingOutcome: number }

export default function PortalStats() {
  const [range, setRange] = useState({ from: "", to: "" });
  const { data, error } = useApi<Stats>(`/portal/stats${qs({ from: range.from ? new Date(range.from).toISOString() : "", to: range.to ? new Date(range.to + "T23:59:59").toISOString() : "" })}`);
  return (
    <div>
      <PageTitle title="Statistiche" subtitle="Funnel dei lead ricevuti. I dati di esito dipendono da quanto registrate sui lead." />
      <ErrorBox error={error} />
      <div className="mb-4 flex gap-2">
        <input className="input max-w-xs" type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} aria-label="Dal" />
        <input className="input max-w-xs" type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} aria-label="Al" />
      </div>
      {data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Kpi label="Lead ricevuti" value={data.received} hint={`${data.replaced} sostituiti`} />
          <Kpi label="Contattati" value={data.contacted} />
          <Kpi label="Appuntamenti" value={data.appointments} />
          <Kpi label="Show" value={data.show} />
          <Kpi label="Preventivi" value={data.quotes} />
          <Kpi label="Vendite" value={data.won} />
          <Kpi label="Valore vendite" value={fmtMoney(data.salesValue)} />
          <Kpi label="Costo lead" value={fmtMoney(data.leadCost)} />
          <Kpi label="Costo per cliente acquisito" value={data.costPerCustomer != null ? fmtMoney(data.costPerCustomer) : "n.d."} />
          <Kpi label="Revenue / costo lead" value={data.revenueOverCost != null ? `${fmtNum(data.revenueOverCost, 2)}x` : "n.d."} />
          <Kpi label="Lead senza esito" value={data.missingOutcome} hint="Dati mancanti: registra l'esito per statistiche complete" tone={data.missingOutcome ? "text-amber-700" : ""} />
        </div>
      )}
    </div>
  );
}
