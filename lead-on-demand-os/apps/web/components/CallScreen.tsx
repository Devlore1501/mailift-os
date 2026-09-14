"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppointmentModal } from "@/components/LeadDetail";
import { LeadStatusBadge } from "@/components/LeadTable";
import { Badge, ErrorBox, Modal, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/format";
import { LEAD_TYPE_LABELS, QUAL_CATEGORY_COLORS, QUAL_CATEGORY_LABELS, ROUTING_REASON_LABELS } from "@/lib/labels";

interface Question { key: string; text: string; type: "single" | "multi" | "number" | "text" | "boolean"; options?: Array<{ value: string; label: string }>; help?: string; required?: boolean }
interface QualState {
  lead: { id: string; code: string; status: string; leadType: string; firstName: string | null; lastName: string | null; phone: string | null; email: string | null; address: string | null; municipality: string | null; postalCode: string | null; province: string | null; region: string | null; source: string | null; campaignName: string | null; attempts: number; callbackAt: string | null; dedupeResult: string | null; answers: Record<string, unknown>; notes: Array<{ id: string; body: string; createdAt: string }>; history: Array<{ id: string; toStatus: string; reason: string | null; createdAt: string }>; customFields: Record<string, unknown> };
  template: { start: string; questions: Question[] } | null;
  next: Question | null;
  criteria: { passed: boolean; mandatoryFailed: Array<{ label: string }>; exclusionsHit: Array<{ label: string }>; preferredMet: Array<{ label: string }>; preferredMissed: Array<{ label: string }> } | null;
  score: { score: number; maxScore: number; category: string; breakdown: Array<{ label: string; points: number; met: boolean }> } | null;
}

// Schermata chiamata (PRD sez. 42): sinistra dati, centro script dinamico, destra risposte e note, bottom bar azioni.
export function CallScreen({ id, backHref }: { id: string; backHref: string }) {
  const router = useRouter();
  const { data, error, reload } = useApi<QualState>(`/leads/${id}/qualification`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [modal, setModal] = useState<null | "callback" | "notqualified" | "appointment" | "result">(null);
  const [result, setResult] = useState<{ outcome: string; clientName?: string; summary?: string[] } | null>(null);
  const [numberDraft, setNumberDraft] = useState("");
  const [textDraft, setTextDraft] = useState("");

  useEffect(() => {
    if (data && ["TO_CONTACT", "ATTEMPT_1", "ATTEMPT_2", "ATTEMPT_3", "CALLBACK"].includes(data.lead.status)) {
      api(`/leads/${id}/claim`, { method: "POST" }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.lead.id]);

  async function run(fn: () => Promise<unknown>, after?: () => void) {
    setActionError(null);
    try {
      await fn();
      setModal(null);
      reload();
      after?.();
    } catch (e) {
      setActionError((e as Error).message);
    }
  }

  async function answer(key: string, value: unknown) {
    await run(() => api(`/leads/${id}/answers`, { method: "PATCH", json: { answers: { [key]: value } } }));
    setNumberDraft("");
    setTextDraft("");
  }

  async function qualify() {
    setActionError(null);
    try {
      const r = await api<{ lead: { status: string }; routing: { outcome: string; clientName?: string; summary?: string[] } | null }>(`/leads/${id}/qualify`, { method: "POST", json: { outcome: "QUALIFIED", notes: note || null } });
      setResult(r.routing);
      setModal("result");
      reload();
    } catch (e) {
      setActionError((e as Error).message);
    }
  }

  if (error) return <ErrorBox error={error} />;
  if (!data) return <div className="text-sm text-slate-500">Caricamento…</div>;
  const { lead, template, next, criteria, score } = data;
  const finished = !["TO_CONTACT", "ATTEMPT_1", "ATTEMPT_2", "ATTEMPT_3", "CALLBACK", "CONTACTED", "QUALIFYING", "VALIDATING"].includes(lead.status);
  const answered = template ? template.questions.filter((q) => lead.answers[q.key] !== undefined && lead.answers[q.key] !== null) : [];

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col md:h-[calc(100vh-4rem)]">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link href={backHref} className="text-sm text-brand-600 hover:underline">← Coda</Link>
          <h1 className="text-lg font-semibold">{lead.code} · {fullName(lead)} <LeadStatusBadge status={lead.status} /></h1>
        </div>
        {lead.phone && <a href={`tel:${lead.phone}`} className="btn-primary text-base">Chiama {lead.phone}</a>}
      </div>
      <ErrorBox error={actionError} />
      {lead.dedupeResult === "POSSIBLE_DUPLICATE" && <div className="mb-2 rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">Possibile duplicato (stesso cognome e indirizzo di un lead recente): verificare in chiamata.</div>}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto lg:grid-cols-3">
        <section className="card space-y-1 text-sm">
          <h2 className="font-semibold">Dati lead</h2>
          <Row k="Tipo" v={LEAD_TYPE_LABELS[lead.leadType]} />
          <Row k="Email" v={lead.email ?? "–"} />
          <Row k="Indirizzo" v={[lead.address, lead.postalCode, lead.municipality, lead.province ? `(${lead.province})` : null].filter(Boolean).join(" ") || "–"} />
          <Row k="Fonte" v={[lead.source, lead.campaignName].filter(Boolean).join(" · ") || "–"} />
          <Row k="Tentativi" v={String(lead.attempts)} />
          {lead.callbackAt && <Row k="Richiamata" v={fmtDate(lead.callbackAt)} />}
          {Object.keys(lead.customFields ?? {}).length > 0 && (
            <>
              <h3 className="pt-2 font-semibold">Dal form</h3>
              {Object.entries(lead.customFields).map(([k, v]) => <Row key={k} k={k} v={String(v)} />)}
            </>
          )}
          <h3 className="pt-2 font-semibold">Storico</h3>
          <ul className="space-y-1 text-xs text-slate-500">
            {lead.history.slice(0, 8).map((h) => <li key={h.id}>{fmtDate(h.createdAt)} · {h.toStatus}{h.reason ? ` · ${h.reason}` : ""}</li>)}
          </ul>
        </section>

        <section className="card">
          <h2 className="mb-2 font-semibold">Script</h2>
          {!template && <p className="text-sm text-slate-500">Nessun template di qualifica attivo per questo verticale.</p>}
          {template && next && !finished && (
            <div>
              <p className="mb-3 text-lg">{next.text}</p>
              {next.help && <p className="mb-2 text-sm text-slate-500">{next.help}</p>}
              {(next.type === "single" || next.type === "boolean") && (
                <div className="flex flex-wrap gap-2">
                  {next.options?.map((o) => (
                    <button key={o.value} className="btn-secondary text-base" onClick={() => answer(next.key, o.value)}>{o.label}</button>
                  ))}
                </div>
              )}
              {next.type === "number" && (
                <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (numberDraft !== "") answer(next.key, Number(numberDraft)); }}>
                  <input className="input" type="number" autoFocus value={numberDraft} onChange={(e) => setNumberDraft(e.target.value)} />
                  <button className="btn-primary">Avanti</button>
                  {next.required === false && <button type="button" className="btn-secondary" onClick={() => answer(next.key, "")}>Salta</button>}
                </form>
              )}
              {next.type === "text" && (
                <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (textDraft.trim()) answer(next.key, textDraft.trim()); }}>
                  <input className="input" autoFocus value={textDraft} onChange={(e) => setTextDraft(e.target.value)} />
                  <button className="btn-primary">Avanti</button>
                </form>
              )}
              {next.type === "multi" && (
                <MultiSelect options={next.options ?? []} onSubmit={(vals) => answer(next.key, vals)} />
              )}
            </div>
          )}
          {template && !next && !finished && (
            <div className="text-sm">
              <p className="mb-2 font-medium text-emerald-700">Script completato.</p>
              <p className="text-slate-600">Verifica il riepilogo a destra e scegli l'esito nella barra in basso.</p>
            </div>
          )}
          {finished && <p className="text-sm text-slate-600">Lead già lavorato: stato {lead.status}.</p>}
          {score && (
            <div className="mt-3 border-t border-slate-100 pt-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-semibold">Score {score.score}/{score.maxScore}</span>
                <Badge className={QUAL_CATEGORY_COLORS[score.category]}>{QUAL_CATEGORY_LABELS[score.category]}</Badge>
              </div>
              {criteria && !criteria.passed && (
                <p className="mt-1 text-red-700">Blocca la qualifica: {[...criteria.mandatoryFailed, ...criteria.exclusionsHit].map((c) => c.label).join(", ")}</p>
              )}
              {criteria && criteria.passed && <p className="mt-1 text-emerald-700">Criteri obbligatori soddisfatti.</p>}
            </div>
          )}
        </section>

        <section className="card flex flex-col text-sm">
          <h2 className="mb-2 font-semibold">Risposte</h2>
          {answered.length === 0 && <p className="text-slate-500">Nessuna risposta ancora.</p>}
          <dl className="divide-y divide-slate-100">
            {answered.map((q) => {
              const v = lead.answers[q.key];
              const label = q.options?.find((o) => o.value === String(v))?.label ?? (Array.isArray(v) ? v.join(", ") : String(v));
              return (
                <div key={q.key} className="flex items-start justify-between gap-2 py-1">
                  <dt className="text-slate-500">{q.text}</dt>
                  <dd className="shrink-0 font-medium">
                    {!finished && (q.type === "single" || q.type === "boolean") ? (
                      <select className="rounded border border-slate-200 bg-white px-1 py-0.5 text-xs font-medium" value={String(v)} onChange={(e) => answer(q.key, e.target.value)} aria-label={q.text}>
                        {q.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    ) : (
                      label
                    )}
                  </dd>
                </div>
              );
            })}
          </dl>
          {score && score.breakdown.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs">
              {score.breakdown.map((b) => <li key={b.label} className={b.met ? "text-emerald-700" : "text-slate-400"}>{b.met ? "+" : "·"} {b.label} ({b.points})</li>)}
            </ul>
          )}
          <h2 className="mb-1 mt-3 font-semibold">Note</h2>
          <textarea className="input flex-1" rows={4} placeholder="Note di chiamata (salvate con l'esito)" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn-secondary mt-2" disabled={!note.trim()} onClick={() => run(() => api(`/leads/${id}/notes`, { method: "POST", json: { body: note } }), () => setNote(""))}>Salva nota ora</button>
          {lead.notes.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-slate-600">
              {lead.notes.slice(0, 5).map((n) => <li key={n.id}><span className="text-slate-400">{fmtDate(n.createdAt)}</span> {n.body}</li>)}
            </ul>
          )}
        </section>
      </div>

      {!finished && (
        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-200 pt-3 md:grid-cols-5">
          <button className="btn-secondary" onClick={() => run(() => api(`/leads/${id}/attempt`, { method: "POST", json: { note: note || undefined } }), () => router.push(backHref))}>Non risponde</button>
          <button className="btn-secondary" onClick={() => setModal("callback")}>Richiama</button>
          <button className="btn-success" disabled={!!criteria && !criteria.passed} onClick={qualify}>Qualificato</button>
          <button className="btn-danger" onClick={() => setModal("notqualified")}>Non qualificato</button>
          <button className="btn-primary" disabled={!["ASSIGNED", "DELIVERED"].includes(lead.status)} title="Disponibile dopo l'assegnazione a un cliente" onClick={() => setModal("appointment")}>Fissa appuntamento</button>
        </div>
      )}
      {finished && ["ASSIGNED", "DELIVERED"].includes(lead.status) && (
        <div className="mt-3 flex gap-2 border-t border-slate-200 pt-3">
          <button className="btn-primary" onClick={() => setModal("appointment")}>Fissa appuntamento</button>
          <Link href={backHref} className="btn-secondary">Torna alla coda</Link>
        </div>
      )}

      <CallbackModal open={modal === "callback"} onClose={() => setModal(null)} onSubmit={(at) => run(() => api(`/leads/${id}/callback`, { method: "POST", json: { callbackAt: at, note: note || undefined } }), () => router.push(backHref))} />
      <NotQualifiedModal open={modal === "notqualified"} onClose={() => setModal(null)} onSubmit={(reason) => run(() => api(`/leads/${id}/qualify`, { method: "POST", json: { outcome: "NOT_QUALIFIED", reason, notes: note || null } }), () => router.push(backHref))} />
      <AppointmentModal open={modal === "appointment"} onClose={() => setModal(null)} onSubmit={(body) => run(() => api(`/leads/${id}/appointment`, { method: "POST", json: body }))} />
      <Modal open={modal === "result"} onClose={() => setModal(null)} title="Lead qualificato">
        {result?.outcome === "ASSIGNED" && <p className="text-sm">Assegnato a <strong>{result.clientName}</strong>. Il credito è stato scalato e il lead è in invio a GHL.</p>}
        {result?.outcome === "WAITING_ASSIGNMENT" && (
          <p className="text-sm">Nessun cliente disponibile al momento: {result.summary?.map((r) => ROUTING_REASON_LABELS[r] ?? r).join("; ")}. Il lead è in coda di assegnazione.</p>
        )}
        {!result && <p className="text-sm">Qualifica registrata.</p>}
        <div className="mt-3 flex gap-2">
          {result?.outcome === "ASSIGNED" && <button className="btn-primary" onClick={() => setModal("appointment")}>Fissa appuntamento</button>}
          <Link href={backHref} className="btn-secondary">Prossimo lead</Link>
        </div>
      </Modal>
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

function MultiSelect({ options, onSubmit }: { options: Array<{ value: string; label: string }>; onSubmit: (vals: string[]) => void }) {
  const [vals, setVals] = useState<string[]>([]);
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.value} className="flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-sm">
            <input type="checkbox" checked={vals.includes(o.value)} onChange={(e) => setVals(e.target.checked ? [...vals, o.value] : vals.filter((v) => v !== o.value))} /> {o.label}
          </label>
        ))}
      </div>
      <button className="btn-primary mt-2" onClick={() => onSubmit(vals)}>Avanti</button>
    </div>
  );
}

function CallbackModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (at: string) => void }) {
  const [at, setAt] = useState("");
  return (
    <Modal open={open} onClose={onClose} title="Programma richiamata">
      <input className="input" type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} />
      <button className="btn-primary mt-3" disabled={!at} onClick={() => onSubmit(new Date(at).toISOString())}>Conferma</button>
    </Modal>
  );
}

function NotQualifiedModal({ open, onClose, onSubmit }: { open: boolean; onClose: () => void; onSubmit: (reason: string) => void }) {
  const [reason, setReason] = useState("Non interessato");
  const reasons = ["Non interessato", "Non proprietario", "Fuori territorio", "Numero errato o inesistente", "Dati falsi", "Duplicato", "Solo curiosità / nessuna tempistica", "Altro"];
  return (
    <Modal open={open} onClose={onClose} title="Lead non qualificato">
      <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
        {reasons.map((r) => <option key={r}>{r}</option>)}
      </select>
      <button className="btn-danger mt-3" onClick={() => onSubmit(reason)}>Conferma</button>
    </Modal>
  );
}
