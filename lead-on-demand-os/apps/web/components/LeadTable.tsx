"use client";

import Link from "next/link";
import { Badge } from "./ui";
import { fmtDate, fullName } from "@/lib/format";
import { LEAD_STATUS_COLORS, LEAD_STATUS_LABELS, LEAD_TYPE_LABELS, QUAL_CATEGORY_COLORS, QUAL_CATEGORY_LABELS } from "@/lib/labels";

export interface LeadRow {
  id: string;
  code: string;
  createdAt: string;
  status: string;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
  municipality: string | null;
  province: string | null;
  leadType: string;
  qualificationCategory: string | null;
  qualificationScore: number | null;
  clientName?: string | null;
  campaignName?: string | null;
  dedupeResult?: string | null;
  replaced?: boolean;
  callbackAt?: string | null;
}

export function LeadStatusBadge({ status }: { status: string }) {
  return <Badge className={LEAD_STATUS_COLORS[status]}>{LEAD_STATUS_LABELS[status] ?? status}</Badge>;
}

export function LeadTable({ leads, base }: { leads: LeadRow[]; base: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>Lead</th>
            <th>Data</th>
            <th>Nome</th>
            <th>Comune</th>
            <th>Tipo</th>
            <th>Qualifica</th>
            <th>Cliente</th>
            <th>Stato</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l) => (
            <tr key={l.id}>
              <td><Link href={`${base}/${l.id}`} className="font-mono text-brand-600 hover:underline">{l.code}</Link></td>
              <td className="whitespace-nowrap">{fmtDate(l.createdAt)}</td>
              <td>
                <div>{fullName(l)}</div>
                <div className="text-xs text-slate-500">{l.phone}</div>
              </td>
              <td>{l.municipality}{l.province ? ` (${l.province})` : ""}</td>
              <td>{LEAD_TYPE_LABELS[l.leadType]}</td>
              <td>
                {l.qualificationCategory && <Badge className={QUAL_CATEGORY_COLORS[l.qualificationCategory]}>{QUAL_CATEGORY_LABELS[l.qualificationCategory]}{l.qualificationScore != null ? ` ${l.qualificationScore}` : ""}</Badge>}
                {l.dedupeResult === "POSSIBLE_DUPLICATE" && <Badge className="ml-1 bg-amber-100 text-amber-800">possibile duplicato</Badge>}
              </td>
              <td>{l.clientName ?? <span className="text-slate-400">–</span>}</td>
              <td><LeadStatusBadge status={l.status} />{l.replaced && <Badge className="ml-1 bg-orange-100 text-orange-800">sostituito</Badge>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
