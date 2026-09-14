"use client";

import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { fmtDate } from "@/lib/format";
import { OFFER_TYPE_LABELS, PACKAGE_STATUS_LABELS } from "@/lib/labels";

interface Dash { client: { tradeName: string; offerType: string; replacementSlaHours: number }; packages: Array<{ id: string; code: string; productName: string; quantity: number; status: string; balance: number; delivered: number; replacements: number; startsAt: string | null; expiresAt: string | null }> }

export default function PortalPackage() {
  const { data, error } = useApi<Dash>("/portal/dashboard");
  return (
    <div>
      <PageTitle title="Pacchetti" subtitle={data ? `${OFFER_TYPE_LABELS[data.client.offerType]} · sostituzione richiedibile entro ${data.client.replacementSlaHours} ore dalla consegna` : undefined} />
      <ErrorBox error={error} />
      {data && data.packages.length === 0 && <Empty text="Nessun pacchetto." />}
      {data && data.packages.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Codice</th><th>Prodotto</th><th>Acquistati</th><th>Consegnati</th><th>Sostituzioni</th><th>Residui</th><th>Inizio</th><th>Stato</th></tr></thead>
            <tbody>
              {data.packages.map((p) => (
                <tr key={p.id}>
                  <td className="font-mono">{p.code}</td><td>{p.productName}</td><td>{p.quantity}</td><td>{p.delivered}</td><td>{p.replacements}</td><td className="font-semibold">{p.balance}</td><td>{fmtDate(p.startsAt, false)}</td><td><Badge>{PACKAGE_STATUS_LABELS[p.status]}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
