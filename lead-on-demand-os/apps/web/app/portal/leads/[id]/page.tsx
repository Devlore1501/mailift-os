"use client";

import { use, useState } from "react";
import Link from "next/link";
import { OutcomeModal, ReplacementModal } from "@/components/LeadDetail";
import { LeadStatusBadge } from "@/components/LeadTable";
import { Badge, ErrorBox, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate, fmtMoney } from "@/lib/format";
import { APPOINTMENT_STATUS_LABELS, LEAD_TYPE_LABELS, OUTCOME_LABELS, QUAL_CATEGORY_COLORS, QUAL_CATEGORY_LABELS, REPLACEMENT_REASON_LABELS, REPLACEMENT_STATUS_LABELS } from "@/lib/labels";

interface PortalLeadDetail {
  id: string; code: string; deliveredAt: string; status: string; firstName: string | null; lastName: string | null; phone: string | null; email: string | null; address: string | null; municipality: string | null; postalCode: string | null; province: string | null; leadType: string; qualificationCategory: string | null; qualificationScore: number | null; qualificationNotes: string | null; replaced: boolean;
  answers: Record<string, unknown>;
  answersDisplay: Array<{ key: string; question: string; label: string }>;
  notes: Array<{ id: string; body: string; createdAt: string }>;
  timeline: Array<{ id: string; toStatus: string; reason: string | null; createdAt: string }>;
  replacementSla: { allowed: boolean; deadline: string; message: string | null } | null;
  replacements: Array<{ id: string; reason: string; status: string; note: string | null; decisionNote: string | null; createdAt: string }>;
  appointments: Array<{ id: string; startsAt: string; status: string; kind: string }>;
  outcomes: Array<{ id: string; outcome: string; contractValue: string | null; lostReason: string | null; createdAt: string }>;
}

export default function PortalLeadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: lead, error, reload } = useApi<PortalLeadDetail>(`/portal/leads/${id}`);
  const [modal, setModal] = useState<null | "replacement" | "outcome">(null);
  const [actionError, setActionError] = useState<string | null>(null);
  async function run(fn: () => Promise<unknown>) {
    setActionError(null);
    try {
      await fn();
      setModal(null);
      reload();
    } catch (e) {
      setActionError((e as Error).message);
    }
  }
  if (error) return <ErrorBox error={error} />;
  if (!lead) return <div className="text-sm text-slate-500">Caricamento…</div>;
  const openReplacement = lead.replacements.some((r) => r.status === "REQUESTED");
  const canRequest = !lead.replaced && !openReplacement && lead.replacementSla?.allowed;
  return (
    <div>
      <Link href="/portal/leads" className="text-sm text-brand-600 hover:underline">← Lead</Link>
      <PageTitle
        title={`${lead.firstName ?? ""} ${lead.lastName ?? ""}`}
        subtitle={`${lead.code} · consegnato il ${fmtDate(lead.deliveredAt)} · ${LEAD_TYPE_LABELS[lead.leadType]}`}
        actions={
          <>
            <LeadStatusBadge status={lead.status} />
            <button className="btn-primary" onClick={() => setModal("outcome")}>Registra esito</button>
            {canRequest && <button className="btn-warn" onClick={() => setModal("replacement")}>Richiedi sostituzione</button>}
          </>
        }
      />
      <ErrorBox error={actionError} />
      {lead.replacementSla && !lead.replacementSla.allowed && !lead.replaced && <p className="mb-3 text-sm text-slate-500">{lead.replacementSla.message} (scaduto il {fmtDate(lead.replacementSla.deadline)}). Per casi particolari contatta il supporto.</p>}
      {lead.replacementSla?.allowed && !lead.replaced && !openReplacement && <p className="mb-3 text-sm text-slate-500">Sostituzione richiedibile entro il {fmtDate(lead.replacementSla.deadline)}.</p>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card space-y-1 text-sm">
          <h2 className="font-semibold">Contatto</h2>
          <Row k="Telefono" v={lead.phone ? <a className="text-brand-600" href={`tel:${lead.phone}`}>{lead.phone}</a> : "–"} />
          <Row k="Email" v={lead.email ?? "–"} />
          <Row k="Indirizzo" v={[lead.address, lead.postalCode, lead.municipality, lead.province ? `(${lead.province})` : null].filter(Boolean).join(" ") || "–"} />
          <h2 className="pt-2 font-semibold">Qualifica</h2>
          {lead.qualificationCategory && <div><Badge className={QUAL_CATEGORY_COLORS[lead.qualificationCategory]}>{QUAL_CATEGORY_LABELS[lead.qualificationCategory]}</Badge> {lead.qualificationScore != null && <span className="text-slate-600">{lead.qualificationScore}/100</span>}</div>}
          {lead.qualificationNotes && <p className="whitespace-pre-wrap text-slate-700">{lead.qualificationNotes}</p>}
          <dl className="divide-y divide-slate-100">
            {lead.answersDisplay.map((a) => (
              <div key={a.key} className="flex justify-between gap-3 py-1"><dt className="text-slate-500">{a.question}</dt><dd className="text-right font-medium">{a.label}</dd></div>
            ))}
          </dl>
          {lead.notes.length > 0 && (
            <>
              <h2 className="pt-2 font-semibold">Note dell'operatore</h2>
              {lead.notes.map((n) => <p key={n.id} className="rounded bg-slate-50 p-2">{n.body}</p>)}
            </>
          )}
        </section>
        <section className="card text-sm">
          <h2 className="mb-2 font-semibold">Appuntamenti</h2>
          {lead.appointments.length === 0 && <p className="text-slate-500">Nessun appuntamento.</p>}
          <ul className="space-y-1">{lead.appointments.map((a) => <li key={a.id}>{fmtDate(a.startsAt)} · {APPOINTMENT_STATUS_LABELS[a.status]}</li>)}</ul>
          <h2 className="mb-2 mt-4 font-semibold">Esiti registrati</h2>
          {lead.outcomes.length === 0 && <p className="text-slate-500">Nessun esito. Registrarlo aiuta a misurare il ritorno dei lead.</p>}
          <ul className="space-y-1">{lead.outcomes.map((o) => <li key={o.id}>{fmtDate(o.createdAt)} · {OUTCOME_LABELS[o.outcome]}{o.contractValue ? ` · ${fmtMoney(o.contractValue)}` : ""}{o.lostReason ? ` · ${o.lostReason}` : ""}</li>)}</ul>
          <h2 className="mb-2 mt-4 font-semibold">Sostituzioni</h2>
          {lead.replacements.length === 0 && <p className="text-slate-500">Nessuna richiesta.</p>}
          <ul className="space-y-1">{lead.replacements.map((r) => <li key={r.id}>{fmtDate(r.createdAt)} · {REPLACEMENT_REASON_LABELS[r.reason]} · <Badge>{REPLACEMENT_STATUS_LABELS[r.status]}</Badge>{r.decisionNote ? <div className="text-xs text-slate-500">{r.decisionNote}</div> : null}</li>)}</ul>
        </section>
        <section className="card text-sm">
          <h2 className="mb-2 font-semibold">Timeline</h2>
          <ol className="space-y-2">
            {lead.timeline.map((h) => (
              <li key={h.id} className="border-l-2 border-slate-200 pl-3"><LeadStatusBadge status={h.toStatus} /><div className="text-xs text-slate-400">{fmtDate(h.createdAt)}</div></li>
            ))}
          </ol>
        </section>
      </div>
      <ReplacementModal open={modal === "replacement"} onClose={() => setModal(null)} onSubmit={(reason, note) => run(() => api(`/portal/leads/${id}/replacement`, { method: "POST", json: { reason, note } }))} />
      <OutcomeModal open={modal === "outcome"} onClose={() => setModal(null)} onSubmit={(body) => run(() => api(`/portal/leads/${id}/outcome`, { method: "POST", json: body }))} />
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex justify-between gap-3"><span className="text-slate-500">{k}</span><span className="text-right">{v}</span></div>;
}
