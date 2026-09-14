"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, ErrorBox, Field, Modal, PageTitle, useApi } from "@/components/ui";
import { LeadStatusBadge } from "@/components/LeadTable";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate, fmtMoney, fullName } from "@/lib/format";
import { APPOINTMENT_KIND_LABELS, LEAD_TYPE_LABELS, OUTCOME_LABELS, QUAL_CATEGORY_COLORS, QUAL_CATEGORY_LABELS, REPLACEMENT_REASON_LABELS, ROUTING_REASON_LABELS } from "@/lib/labels";

export interface LeadFull {
  id: string;
  code: string;
  status: string;
  leadType: string;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  municipality: string | null;
  postalCode: string | null;
  province: string | null;
  region: string | null;
  source: string | null;
  campaignName: string | null;
  utmSource: string | null;
  utmCampaign: string | null;
  landingPage: string | null;
  attributedCost: string | null;
  dedupeResult: string | null;
  duplicateOfLeadId: string | null;
  qualificationScore: number | null;
  qualificationCategory: string | null;
  qualificationPassed: boolean | null;
  qualificationNotes: string | null;
  notQualifiedReason: string | null;
  clientId: string | null;
  packageId: string | null;
  assignedAt: string | null;
  deliveredAt: string | null;
  creditCharged: boolean;
  waitingReasons: string[];
  attempts: number;
  callbackAt: string | null;
  ghlContactId: string | null;
  ghlSyncedAt: string | null;
  ghlLastError: string | null;
  replaced: boolean;
  createdAt: string;
  answers: Record<string, unknown>;
  answersDisplay: Array<{ key: string; question: string; label: string }>;
  history: Array<{ id: string; fromStatus: string | null; toStatus: string; reason: string | null; createdAt: string }>;
  notes: Array<{ id: string; body: string; visibleToClient: boolean; createdAt: string }>;
  client: { id: string; tradeName: string; code: string } | null;
}

interface RoutingDecision {
  outcome: string;
  clientName?: string;
  summary?: string[];
  evaluations: Array<{ clientName: string; eligible: boolean; reasons: string[]; matchedTerritory: { level: string; value: string; exclusive: boolean } | null }>;
}

export function LeadDetail({ id, callHref }: { id: string; callHref: string }) {
  const { user } = useAuth();
  const { data: lead, error, reload } = useApi<LeadFull>(`/leads/${id}`);
  const { data: audit } = useApi<Array<{ id: string; summary: string; userName: string | null; createdAt: string }>>(user?.role !== "OPERATOR" ? `/audit?leadId=${id}&limit=100` : null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [modal, setModal] = useState<null | "assign" | "replacement" | "appointment" | "outcome" | "note" | "simulate">(null);
  const [sim, setSim] = useState<RoutingDecision | null>(null);
  const isAdmin = user?.role === "SUPER_ADMIN" || user?.role === "MANAGER";

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

  const inQueue = ["TO_CONTACT", "ATTEMPT_1", "ATTEMPT_2", "ATTEMPT_3", "CALLBACK", "CONTACTED", "QUALIFYING", "VALIDATING"].includes(lead.status);
  const canRoute = ["QUALIFIED", "WAITING_ASSIGNMENT"].includes(lead.status);
  const canDeliver = ["ASSIGNED", "APPOINTMENT_BOOKED"].includes(lead.status) && !lead.creditCharged;
  const canReplacement = lead.creditCharged && !lead.replaced && !["REPLACEMENT_REQUESTED", "REPLACEMENT_APPROVED"].includes(lead.status);

  return (
    <div>
      <PageTitle
        title={`${lead.code} · ${fullName(lead)}`}
        subtitle={`${LEAD_TYPE_LABELS[lead.leadType]} · acquisito il ${fmtDate(lead.createdAt)}${lead.source ? ` da ${lead.source}` : ""}`}
        actions={
          <>
            <LeadStatusBadge status={lead.status} />
            {inQueue && <Link href={callHref} className="btn-primary">Apri schermata chiamata</Link>}
            {canRoute && <button className="btn-primary" onClick={() => run(() => api(`/leads/${id}/route`, { method: "POST" }))}>Esegui routing</button>}
            {canRoute && <button className="btn-secondary" onClick={async () => { setSim(await api<{ decision: RoutingDecision }>("/routing/evaluate", { method: "POST", json: { leadId: id } }).then((r) => r.decision)); setModal("simulate"); }}>Simula routing</button>}
            {isAdmin && (canRoute || lead.status === "ASSIGNED") && <button className="btn-secondary" onClick={() => setModal("assign")}>Assegna manualmente</button>}
            {canDeliver && <button className="btn-success" onClick={() => run(() => api(`/leads/${id}/deliver`, { method: "POST" }))}>Consegna e scala credito</button>}
            {lead.clientId && ["ASSIGNED", "DELIVERED"].includes(lead.status) && <button className="btn-secondary" onClick={() => setModal("appointment")}>Fissa appuntamento</button>}
            {isAdmin && canReplacement && <button className="btn-warn" onClick={() => setModal("replacement")}>Apri sostituzione</button>}
            {lead.clientId && lead.creditCharged && <button className="btn-secondary" onClick={() => setModal("outcome")}>Registra esito</button>}
            {isAdmin && lead.creditCharged && (lead.status === "DELIVERY_FAILED" || lead.ghlLastError) && <button className="btn-danger" onClick={() => run(() => api(`/leads/${id}/ghl-retry`, { method: "POST" }))}>Reinvia a GHL</button>}
            <button className="btn-secondary" onClick={() => setModal("note")}>Nota</button>
          </>
        }
      />
      <ErrorBox error={actionError} />
      {lead.status === "WAITING_ASSIGNMENT" && (
        <div className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          In attesa di buyer: {lead.waitingReasons.map((r) => ROUTING_REASON_LABELS[r] ?? r).join("; ") || "nessun cliente compatibile"}.
        </div>
      )}
      {lead.ghlLastError && <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">GHL: {lead.ghlLastError}</div>}
      {lead.dedupeResult && lead.dedupeResult !== "UNIQUE" && (
        <div className="mb-4 rounded border border-orange-200 bg-orange-50 px-3 py-2 text-sm text-orange-900">
          Controllo duplicati: {lead.dedupeResult === "DUPLICATE" ? "duplicato" : "possibile duplicato"}{lead.duplicateOfLeadId && <> di <Link className="underline" href={`${callHref.replace(/\/call$/, "").replace(/\/[^/]+$/, "")}/${lead.duplicateOfLeadId}`}>questo lead</Link></>}.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card space-y-2 text-sm">
          <h2 className="font-semibold">Dati lead</h2>
          <Row k="Telefono" v={lead.phone ? <a className="text-brand-600" href={`tel:${lead.phone}`}>{lead.phone}</a> : "–"} />
          <Row k="Email" v={lead.email ?? "–"} />
          <Row k="Indirizzo" v={[lead.address, lead.postalCode, lead.municipality, lead.province ? `(${lead.province})` : null, lead.region].filter(Boolean).join(" ") || "–"} />
          <Row k="Tentativi" v={String(lead.attempts)} />
          {lead.callbackAt && <Row k="Richiamare il" v={fmtDate(lead.callbackAt)} />}
          <h2 className="pt-2 font-semibold">Marketing</h2>
          <Row k="Fonte" v={lead.source ?? lead.utmSource ?? "–"} />
          <Row k="Campagna" v={lead.campaignName ?? lead.utmCampaign ?? "–"} />
          <Row k="Landing" v={lead.landingPage ?? "–"} />
          {user?.role === "SUPER_ADMIN" && <Row k="Costo attribuito" v={lead.attributedCost ? fmtMoney(lead.attributedCost) : "–"} />}
          <h2 className="pt-2 font-semibold">Consegna</h2>
          <Row k="Cliente" v={lead.client ? <Link className="text-brand-600 hover:underline" href={`/admin/clients/${lead.client.id}`}>{lead.client.tradeName}</Link> : "–"} />
          <Row k="Assegnato il" v={lead.assignedAt ? fmtDate(lead.assignedAt) : "–"} />
          <Row k="Consegnato il" v={lead.deliveredAt ? fmtDate(lead.deliveredAt) : "–"} />
          <Row k="Credito scalato" v={lead.creditCharged ? "Sì" : "No"} />
          <Row k="GHL" v={lead.ghlContactId ? `contatto ${lead.ghlContactId} · ${fmtDate(lead.ghlSyncedAt)}` : "non inviato"} />
        </section>

        <section className="card text-sm">
          <h2 className="mb-2 font-semibold">Qualifica</h2>
          {lead.qualificationCategory && (
            <div className="mb-2"><Badge className={QUAL_CATEGORY_COLORS[lead.qualificationCategory]}>{QUAL_CATEGORY_LABELS[lead.qualificationCategory]}</Badge> {lead.qualificationScore != null && <span className="ml-1 text-slate-600">{lead.qualificationScore}/100</span>}</div>
          )}
          {lead.notQualifiedReason && <p className="mb-2 text-slate-600">Motivo: {lead.notQualifiedReason}</p>}
          {lead.qualificationNotes && <p className="mb-2 whitespace-pre-wrap text-slate-700">{lead.qualificationNotes}</p>}
          {lead.answersDisplay.length === 0 && <p className="text-slate-500">Nessuna risposta registrata.</p>}
          <dl className="divide-y divide-slate-100">
            {lead.answersDisplay.map((a) => (
              <div key={a.key} className="flex justify-between gap-3 py-1">
                <dt className="text-slate-500">{a.question}</dt>
                <dd className="text-right font-medium">{a.label}</dd>
              </div>
            ))}
          </dl>
          <h2 className="mb-2 mt-4 font-semibold">Note</h2>
          {lead.notes.length === 0 && <p className="text-slate-500">Nessuna nota.</p>}
          <ul className="space-y-2">
            {lead.notes.map((n) => (
              <li key={n.id} className="rounded bg-slate-50 p-2">
                <div className="whitespace-pre-wrap">{n.body}</div>
                <div className="mt-1 text-xs text-slate-400">{fmtDate(n.createdAt)}{n.visibleToClient ? " · visibile al cliente" : ""}</div>
              </li>
            ))}
          </ul>
        </section>

        <section className="card text-sm">
          <h2 className="mb-2 font-semibold">Timeline stati</h2>
          <ol className="space-y-2">
            {lead.history.map((h) => (
              <li key={h.id} className="border-l-2 border-slate-200 pl-3">
                <div><LeadStatusBadge status={h.toStatus} /></div>
                {h.reason && <div className="text-slate-600">{h.reason}</div>}
                <div className="text-xs text-slate-400">{fmtDate(h.createdAt)}</div>
              </li>
            ))}
          </ol>
          {audit && (
            <>
              <h2 className="mb-2 mt-4 font-semibold">Audit log</h2>
              <ul className="space-y-1 text-xs text-slate-600">
                {audit.map((a) => (
                  <li key={a.id}><span className="text-slate-400">{fmtDate(a.createdAt)}</span> · {a.summary}{a.userName ? ` (${a.userName})` : ""}</li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <AssignModal open={modal === "assign"} onClose={() => setModal(null)} onSubmit={(clientId, deliver) => run(() => api(`/leads/${id}/assign`, { method: "POST", json: { clientId, deliver } }))} />
      <Modal open={modal === "simulate"} onClose={() => setModal(null)} title="Simulazione routing">
        {sim && (
          <div className="space-y-2 text-sm">
            <p>Esito: <strong>{sim.outcome === "ASSIGNED" ? `assegnabile a ${sim.clientName}` : sim.outcome === "WAITING_ASSIGNMENT" ? "nessun cliente disponibile" : "lead non qualificato"}</strong></p>
            <ul className="divide-y divide-slate-100">
              {sim.evaluations.map((e) => (
                <li key={e.clientName} className="py-1">
                  <span className={e.eligible ? "text-emerald-700" : "text-slate-700"}>{e.clientName}</span>
                  {e.matchedTerritory && <span className="ml-1 text-xs text-slate-500">({e.matchedTerritory.level} {e.matchedTerritory.value}{e.matchedTerritory.exclusive ? ", esclusivo" : ""})</span>}
                  {!e.eligible && <div className="text-xs text-slate-500">{e.reasons.map((r) => ROUTING_REASON_LABELS[r] ?? r).join("; ")}</div>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Modal>
      <ReplacementModal open={modal === "replacement"} onClose={() => setModal(null)} onSubmit={(reason, note) => run(() => api(`/leads/${id}/replacement`, { method: "POST", json: { reason, note } }))} />
      <AppointmentModal open={modal === "appointment"} onClose={() => setModal(null)} onSubmit={(body) => run(() => api(`/leads/${id}/appointment`, { method: "POST", json: body }))} />
      <OutcomeModal open={modal === "outcome"} onClose={() => setModal(null)} onSubmit={(body) => run(() => api(`/leads/${id}/outcome`, { method: "POST", json: body }))} />
      <NoteModal open={modal === "note"} onClose={() => setModal(null)} onSubmit={(body, visibleToClient) => run(() => api(`/leads/${id}/notes`, { method: "POST", json: { body, visibleToClient } }))} />
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-slate-500">{k}</span>
      <span className="text-right">{v}</span>
    </div>
  );
}

function AssignModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (clientId: string, deliver: boolean) => void }) {
  const { data: clients } = useApi<Array<{ id: string; tradeName: string; balance: number; status: string }>>(open ? "/clients" : null);
  const [clientId, setClientId] = useState("");
  const [deliver, setDeliver] = useState(true);
  return (
    <Modal open={open} onClose={onClose} title="Assegnazione manuale">
      <div className="space-y-3">
        <Field label="Cliente" hint="Il credito viene comunque verificato e scalato dal pacchetto attivo più vecchio.">
          <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">Seleziona…</option>
            {clients?.map((c) => <option key={c.id} value={c.id}>{c.tradeName} · saldo {c.balance} · {c.status}</option>)}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={deliver} onChange={(e) => setDeliver(e.target.checked)} /> Consegna subito (scala 1 credito e invia a GHL)</label>
        <button className="btn-primary" disabled={!clientId} onClick={() => onSubmit(clientId, deliver)}>Assegna</button>
      </div>
    </Modal>
  );
}

export function ReplacementModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (reason: string, note: string) => void }) {
  const [reason, setReason] = useState("NUMBER_NOT_EXISTING");
  const [note, setNote] = useState("");
  return (
    <Modal open={open} onClose={onClose} title="Richiesta di sostituzione">
      <div className="space-y-3">
        <Field label="Motivo">
          <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
            {Object.entries(REPLACEMENT_REASON_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <Field label="Nota (cosa è successo, quando è stato chiamato)"><textarea className="input" rows={4} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <button className="btn-warn" onClick={() => onSubmit(reason, note)}>Invia richiesta</button>
      </div>
    </Modal>
  );
}

export function AppointmentModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (body: { startsAt: string; kind: string; notes: string }) => void }) {
  const [startsAt, setStartsAt] = useState("");
  const [kind, setKind] = useState("SITE_VISIT");
  const [notes, setNotes] = useState("");
  return (
    <Modal open={open} onClose={onClose} title="Fissa appuntamento">
      <div className="space-y-3">
        <Field label="Data e ora"><input className="input" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} /></Field>
        <Field label="Tipo">
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
            {Object.entries(APPOINTMENT_KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <Field label="Note"><textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <button className="btn-primary" disabled={!startsAt} onClick={() => onSubmit({ startsAt: new Date(startsAt).toISOString(), kind, notes })}>Conferma</button>
      </div>
    </Modal>
  );
}

export function OutcomeModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (body: Record<string, unknown>) => void }) {
  const [outcome, setOutcome] = useState("CONTACTED");
  const [lostReason, setLostReason] = useState("");
  const [contractValue, setContractValue] = useState("");
  const [product, setProduct] = useState("");
  return (
    <Modal open={open} onClose={onClose} title="Esito commerciale">
      <div className="space-y-3">
        <Field label="Esito">
          <select className="input" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {Object.entries(OUTCOME_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        {outcome === "LOST" && <Field label="Motivo perdita"><input className="input" value={lostReason} onChange={(e) => setLostReason(e.target.value)} /></Field>}
        {outcome === "WON" && (
          <>
            <Field label="Valore contratto (euro)"><input className="input" type="number" step="0.01" value={contractValue} onChange={(e) => setContractValue(e.target.value)} /></Field>
            <Field label="Prodotto"><input className="input" value={product} onChange={(e) => setProduct(e.target.value)} /></Field>
          </>
        )}
        <button className="btn-primary" onClick={() => onSubmit({ outcome, lostReason: lostReason || null, contractValue: contractValue ? Number(contractValue) : null, product: product || null })}>Salva</button>
      </div>
    </Modal>
  );
}

function NoteModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (body: string, visibleToClient: boolean) => void }) {
  const [body, setBody] = useState("");
  const [visible, setVisible] = useState(false);
  return (
    <Modal open={open} onClose={onClose} title="Nuova nota">
      <div className="space-y-3">
        <textarea className="input" rows={4} value={body} onChange={(e) => setBody(e.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} /> Visibile al cliente nel portale</label>
        <button className="btn-primary" disabled={!body.trim()} onClick={() => { onSubmit(body, visible); setBody(""); }}>Salva nota</button>
      </div>
    </Modal>
  );
}
