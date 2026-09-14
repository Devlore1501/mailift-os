"use client";

import Link from "next/link";
import { Badge, Empty, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { TERRITORY_LEVEL_LABELS } from "@/lib/labels";

interface Terr { id: string; clientId: string; clientName: string; level: string; value: string; province: string | null; region: string | null; exclusive: boolean }

export default function TerritoriesPage() {
  const { data, error, reload } = useApi<Terr[]>("/territories");
  return (
    <div>
      <PageTitle title="Territori" subtitle="Chi serve cosa. I territori si aggiungono dalla scheda cliente; il sistema rifiuta i conflitti con le esclusive." />
      <ErrorBox error={error} />
      {data && data.length === 0 && <Empty text="Nessun territorio configurato." />}
      {data && data.length > 0 && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Livello</th><th>Valore</th><th>Provincia</th><th>Regione</th><th>Cliente</th><th>Esclusiva</th><th></th></tr></thead>
            <tbody>
              {data.map((t) => (
                <tr key={t.id}>
                  <td>{TERRITORY_LEVEL_LABELS[t.level]}</td><td className="font-medium">{t.value}</td><td>{t.province}</td><td>{t.region}</td>
                  <td><Link className="text-brand-600 hover:underline" href={`/admin/clients/${t.clientId}`}>{t.clientName}</Link></td>
                  <td>{t.exclusive ? <Badge className="bg-violet-100 text-violet-800">esclusivo</Badge> : <span className="text-slate-500">condiviso</span>}</td>
                  <td><button className="text-xs text-red-600 hover:underline" onClick={async () => { await api(`/territories/${t.id}`, { method: "DELETE" }); reload(); }}>Rimuovi</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
