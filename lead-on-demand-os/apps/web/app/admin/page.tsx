"use client";

import Link from "next/link";
import { useState } from "react";
import { Kpi, PageTitle, ErrorBox, useApi } from "@/components/ui";
import { qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtMoney, fmtDate } from "@/lib/format";
import { NOTIFICATION_LABELS } from "@/lib/labels";

interface Dashboard {
  period: { from: string; to: string };
  leads: { today: number; period: number; toContact: number; qualified: number; notQualified: number; delivered: number; inReview: number; waitingAssignment: number; deliveryFailed: number; duplicates: number };
  replacements: { open: number; requested: number; approved: number };
  appointments: { booked: number; show: number; noShow: number };
  clients: { active: number; activePackages: number; remainingToDeliver: number };
  economics: { revenueSold: number; revenueRecognized: number; acquisitionCost: number; grossMargin: number; marginPerLead: number } | null;
}
interface Notification { id: string; event: string; title: string; body: string | null; severity: string; leadId: string | null; readAt: string | null; createdAt: string }

export default function AdminDashboard() {
  const { user } = useAuth();
  const [filters, setFilters] = useState({ from: "", to: "", clientId: "", province: "" });
  const { data, error } = useApi<Dashboard>(`/analytics${qs({ from: filters.from ? new Date(filters.from).toISOString() : "", to: filters.to ? new Date(filters.to + "T23:59:59").toISOString() : "", clientId: filters.clientId, province: filters.province })}`);
  const { data: clients } = useApi<Array<{ id: string; tradeName: string }>>("/clients");
  const { data: notifications, reload } = useApi<Notification[]>("/notifications?unread=true&limit=15");

  return (
    <div>
      <PageTitle title="Dashboard" subtitle={data ? `Periodo ${fmtDate(data.period.from, false)} – ${fmtDate(data.period.to, false)}` : undefined} />
      <ErrorBox error={error} />
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        <input className="input" type="date" value={filters.from} onChange={(e) => setFilters({ ...filters, from: e.target.value })} aria-label="Dal" />
        <input className="input" type="date" value={filters.to} onChange={(e) => setFilters({ ...filters, to: e.target.value })} aria-label="Al" />
        <select className="input" value={filters.clientId} onChange={(e) => setFilters({ ...filters, clientId: e.target.value })}>
          <option value="">Tutti i clienti</option>
          {clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName}</option>)}
        </select>
        <input className="input" placeholder="Provincia (es. VI)" value={filters.province} onChange={(e) => setFilters({ ...filters, province: e.target.value })} />
      </div>
      {data && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Lead</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <Kpi label="Generati oggi" value={data.leads.today} />
              <Kpi label="Generati nel periodo" value={data.leads.period} hint={`${data.leads.duplicates} duplicati scartati`} />
              <Kpi label="Da contattare" value={data.leads.toContact} />
              <Kpi label="Qualificati" value={data.leads.qualified} hint={`${data.leads.notQualified} non qualificati`} />
              <Kpi label="Consegnati" value={data.leads.delivered} />
              <Kpi label="In review" value={data.leads.inReview} />
              <Kpi label="Senza buyer" value={<Link href="/admin/routing" className="hover:underline">{data.leads.waitingAssignment}</Link>} tone={data.leads.waitingAssignment ? "text-amber-700" : ""} hint="Lead qualificati non assegnati" />
              <Kpi label="Invio GHL fallito" value={data.leads.deliveryFailed} tone={data.leads.deliveryFailed ? "text-red-700" : ""} />
              <Kpi label="Replacement richiesti" value={data.replacements.requested} hint={`${data.replacements.open} in attesa di decisione`} />
              <Kpi label="Replacement approvati" value={data.replacements.approved} />
            </div>
          </section>
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-600">Appuntamenti e clienti</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
              <Kpi label="Appuntamenti fissati" value={data.appointments.booked} />
              <Kpi label="Show" value={data.appointments.show} />
              <Kpi label="No-show" value={data.appointments.noShow} />
              <Kpi label="Clienti attivi" value={data.clients.active} />
              <Kpi label="Pacchetti attivi" value={data.clients.activePackages} />
              <Kpi label="Lead ancora da consegnare" value={data.clients.remainingToDeliver} />
            </div>
          </section>
          {data.economics && (
            <section>
              <h2 className="mb-2 text-sm font-semibold text-slate-600">Economics</h2>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Kpi label="Revenue venduta" value={fmtMoney(data.economics.revenueSold)} hint="Pacchetti pagati nel periodo" />
                <Kpi label="Revenue riconosciuta" value={fmtMoney(data.economics.revenueRecognized)} hint="Sui lead consegnati" />
                <Kpi label="Costo acquisizione" value={fmtMoney(data.economics.acquisitionCost)} hint="Costo attribuito ai lead" />
                <Kpi label="Margine lordo" value={fmtMoney(data.economics.grossMargin)} tone={data.economics.grossMargin < 0 ? "text-red-700" : "text-emerald-700"} />
                <Kpi label="Margine per lead" value={fmtMoney(data.economics.marginPerLead)} />
              </div>
            </section>
          )}
          {user?.role === "MANAGER" && <p className="text-xs text-slate-500">I dati economici sono visibili solo al Super Admin.</p>}
          <section className="card">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-600">Notifiche da leggere</h2>
              {notifications && notifications.length > 0 && (
                <button className="text-xs text-brand-600 hover:underline" onClick={async () => { const { api } = await import("@/lib/api"); await api("/notifications/read-all", { method: "POST" }); reload(); }}>Segna tutte come lette</button>
              )}
            </div>
            {!notifications?.length && <p className="text-sm text-slate-500">Nessuna notifica non letta.</p>}
            <ul className="divide-y divide-slate-100">
              {notifications?.map((n) => (
                <li key={n.id} className="flex items-start gap-3 py-2 text-sm">
                  <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${n.severity === "critical" ? "bg-red-500" : n.severity === "warning" ? "bg-amber-500" : "bg-sky-500"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium">{n.leadId ? <Link className="hover:underline" href={`/admin/leads/${n.leadId}`}>{n.title}</Link> : n.title}</div>
                    {n.body && <div className="text-slate-600">{n.body}</div>}
                    <div className="text-xs text-slate-400">{NOTIFICATION_LABELS[n.event] ?? n.event} · {fmtDate(n.createdAt)}</div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
