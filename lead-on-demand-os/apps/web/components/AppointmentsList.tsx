"use client";

import Link from "next/link";
import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { APPOINTMENT_KIND_LABELS, APPOINTMENT_STATUS_LABELS } from "@/lib/labels";

interface Appt { id: string; leadId: string; leadCode: string; leadName: string; leadPhone: string | null; clientName: string; kind: string; status: string; startsAt: string; notes: string | null }

const COLORS: Record<string, string> = { BOOKED: "bg-sky-100 text-sky-800", CONFIRMED: "bg-teal-100 text-teal-800", CANCELLED: "bg-slate-200 text-slate-700", RESCHEDULED: "bg-amber-100 text-amber-800", SHOW: "bg-emerald-100 text-emerald-800", NO_SHOW: "bg-red-100 text-red-800", COMPLETED: "bg-emerald-200 text-emerald-900" };

export function AppointmentsList({ path, leadBase, statusPath, allowed }: { path: string; leadBase: string; statusPath: (id: string) => string; allowed: string[] }) {
  const { data, error, reload } = useApi<Appt[]>(path);
  async function setStatus(id: string, status: string) {
    await api(statusPath(id), { method: "POST", json: { status } });
    reload();
  }
  return (
    <div>
      <PageTitle title="Appuntamenti" subtitle={data ? `${data.length} appuntamenti` : undefined} />
      <ErrorBox error={error} />
      {data && data.length === 0 && <Empty text="Nessun appuntamento." />}
      {data && data.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Quando</th><th>Lead</th><th>Cliente</th><th>Tipo</th><th>Stato</th><th>Esito</th></tr></thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td className="whitespace-nowrap">{fmtDate(a.startsAt)}</td>
                  <td><Link href={`${leadBase}/${a.leadId}`} className="text-brand-600 hover:underline">{a.leadCode}</Link><div className="text-xs text-slate-500">{a.leadName}{a.leadPhone ? ` · ${a.leadPhone}` : ""}</div></td>
                  <td>{a.clientName}</td>
                  <td>{APPOINTMENT_KIND_LABELS[a.kind] ?? a.kind}</td>
                  <td><Badge className={COLORS[a.status]}>{APPOINTMENT_STATUS_LABELS[a.status] ?? a.status}</Badge></td>
                  <td>
                    <select className="rounded border border-slate-200 text-xs" value="" onChange={(e) => e.target.value && setStatus(a.id, e.target.value)} aria-label="Aggiorna stato">
                      <option value="">Aggiorna…</option>
                      {allowed.filter((s) => s !== a.status).map((s) => <option key={s} value={s}>{APPOINTMENT_STATUS_LABELS[s]}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
