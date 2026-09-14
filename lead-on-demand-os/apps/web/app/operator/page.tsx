"use client";

import Link from "next/link";
import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { LeadStatusBadge } from "@/components/LeadTable";
import { fmtDate, fullName } from "@/lib/format";
import { LEAD_TYPE_LABELS } from "@/lib/labels";

interface QueueLead { id: string; code: string; status: string; firstName: string | null; lastName: string | null; phone: string | null; municipality: string | null; province: string | null; leadType: string; createdAt: string; callbackAt: string | null; attempts: number; ownerUserId: string | null; dedupeResult: string | null }

export default function OperatorQueue() {
  const { data, error, reload } = useApi<QueueLead[]>("/leads/queue");
  const now = Date.now();
  return (
    <div>
      <PageTitle title="Coda chiamate" subtitle={data ? `${data.length} lead da lavorare` : undefined} actions={<button className="btn-secondary" onClick={reload}>Aggiorna</button>} />
      <ErrorBox error={error} />
      {data && data.length === 0 && <Empty text="Nessun lead in coda. Bel lavoro." />}
      {data && data.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead>
              <tr><th>Lead</th><th>Nome</th><th>Zona</th><th>Tipo</th><th>Stato</th><th>Tentativi</th><th>Arrivato</th><th></th></tr>
            </thead>
            <tbody>
              {data.map((l) => {
                const due = l.callbackAt && new Date(l.callbackAt).getTime() <= now;
                return (
                  <tr key={l.id}>
                    <td className="font-mono">{l.code}</td>
                    <td>{fullName(l)}<div className="text-xs text-slate-500">{l.phone}</div></td>
                    <td>{l.municipality} {l.province ? `(${l.province})` : ""}</td>
                    <td>{LEAD_TYPE_LABELS[l.leadType]}</td>
                    <td>
                      <LeadStatusBadge status={l.status} />
                      {due && <Badge className="ml-1 bg-red-100 text-red-800">richiamata scaduta</Badge>}
                      {l.callbackAt && !due && <div className="text-xs text-slate-500">richiamare {fmtDate(l.callbackAt)}</div>}
                      {l.dedupeResult === "POSSIBLE_DUPLICATE" && <Badge className="ml-1 bg-amber-100 text-amber-800">possibile duplicato</Badge>}
                    </td>
                    <td>{l.attempts}</td>
                    <td className="whitespace-nowrap text-slate-500">{fmtDate(l.createdAt)}</td>
                    <td><Link href={`/operator/${l.id}`} className="btn-primary">Chiama</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
