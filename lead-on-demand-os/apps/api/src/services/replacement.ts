import { and, desc, eq, sql } from "drizzle-orm";
import { clients, leads, replacementRequests, type DbOrTx } from "@lod/db";
import { checkReplacementSla, REPLACEMENT_REASON_LABELS, type ReplacementReason } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, forbidden, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { notify } from "../lib/notify.js";
import { applyLedgerMoveTx } from "./packages.js";
import { getLead, setLeadStatusTx } from "./leads.js";

export interface ReplacementInput {
  reason: ReplacementReason;
  note?: string | null;
  attachments?: Array<{ name: string; url: string }>;
}

// PRD sez. 22-24: il cliente (o un admin per suo conto) apre la richiesta entro lo SLA.
export async function requestReplacement(ctx: Ctx, leadId: string, input: ReplacementInput) {
  const id = await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    if (ctx.user?.role === "CLIENT" && lead.clientId !== ctx.user.clientId) throw notFound("Lead");
    if (!lead.clientId || !lead.packageId || !lead.deliveredAt) throw conflict("Il lead non risulta consegnato");
    if (!lead.creditCharged) throw conflict("Il lead non ha scalato credito: nessuna sostituzione necessaria");
    if (lead.replaced) throw conflict("Il lead è già stato sostituito");
    const open = await tx.query.replacementRequests.findFirst({ where: and(eq(replacementRequests.leadId, leadId), eq(replacementRequests.status, "REQUESTED")) });
    if (open) throw conflict("Esiste già una richiesta di sostituzione aperta per questo lead");
    const client = await tx.query.clients.findFirst({ where: eq(clients.id, lead.clientId) });
    const sla = checkReplacementSla(lead.deliveredAt, client?.replacementSlaHours ?? 72, ctx.now());
    if (!sla.allowed && ctx.user?.role === "CLIENT") throw forbidden(sla.message ?? "SLA scaduto");
    const [req] = await tx
      .insert(replacementRequests)
      .values({
        leadId,
        clientId: lead.clientId,
        packageId: lead.packageId,
        reason: input.reason,
        note: input.note ?? null,
        attachments: input.attachments ?? [],
        requestedBy: ctx.user?.id ?? null,
        createdAt: ctx.now(),
      })
      .returning();
    await setLeadStatusTx(ctx, tx, leadId, "REPLACEMENT_REQUESTED", `Sostituzione richiesta: ${REPLACEMENT_REASON_LABELS[input.reason]}${sla.allowed ? "" : " (fuori SLA, apertura manuale)"}`);
    await notify(tx, {
      event: "REPLACEMENT_REQUESTED",
      severity: "warning",
      title: `${client?.tradeName ?? "Cliente"} richiede la sostituzione del lead ${lead.code}`,
      body: `Motivo: ${REPLACEMENT_REASON_LABELS[input.reason]}${input.note ? `. ${input.note}` : ""}`,
      leadId,
      clientId: lead.clientId,
      dedupeKey: `repl-req:${req!.id}`,
    });
    await emitEvent(tx, "lead.replacement_requested", { clientId: lead.clientId, leadId, data: { leadId, code: lead.code, reason: input.reason } });
    return req!.id;
  });
  return getReplacement(ctx, id);
}

export async function getReplacement(ctx: Ctx, id: string) {
  const r = await ctx.db.query.replacementRequests.findFirst({ where: eq(replacementRequests.id, id) });
  if (!r) throw notFound("Richiesta di sostituzione");
  if (ctx.user?.role === "CLIENT" && r.clientId !== ctx.user.clientId) throw notFound("Richiesta di sostituzione");
  return r;
}

export async function listReplacements(ctx: Ctx, filter: { status?: "REQUESTED" | "APPROVED" | "REJECTED"; clientId?: string } = {}) {
  const where = [];
  if (ctx.user?.role === "CLIENT") where.push(eq(replacementRequests.clientId, ctx.user.clientId ?? ""));
  else if (filter.clientId) where.push(eq(replacementRequests.clientId, filter.clientId));
  if (filter.status) where.push(eq(replacementRequests.status, filter.status));
  const rows = await ctx.db
    .select({ req: replacementRequests, leadCode: leads.code, leadName: sql<string>`coalesce(${leads.firstName},'') || ' ' || coalesce(${leads.lastName},'')`, clientName: clients.tradeName })
    .from(replacementRequests)
    .innerJoin(leads, eq(leads.id, replacementRequests.leadId))
    .innerJoin(clients, eq(clients.id, replacementRequests.clientId))
    .where(where.length ? and(...where) : undefined)
    .orderBy(desc(replacementRequests.createdAt));
  return rows.map((r) => ({ ...r.req, leadCode: r.leadCode, leadName: r.leadName.trim(), clientName: r.clientName }));
}

// Approvazione: +1 credito nel ledger, lead marcato REPLACED (resta nello storico).
export async function decideReplacement(ctx: Ctx, id: string, decision: "APPROVED" | "REJECTED", note?: string | null) {
  await ctx.db.transaction(async (tx) => {
    const req = await tx.query.replacementRequests.findFirst({ where: eq(replacementRequests.id, id) });
    if (!req) throw notFound("Richiesta di sostituzione");
    if (req.status !== "REQUESTED") throw conflict(`Richiesta già ${req.status}`);
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, req.leadId) });
    if (!lead) throw notFound("Lead");
    await tx
      .update(replacementRequests)
      .set({ status: decision, decidedBy: ctx.user?.id ?? null, decisionNote: note ?? null, decidedAt: ctx.now() })
      .where(eq(replacementRequests.id, id));
    if (decision === "APPROVED") {
      await applyLedgerMoveTx(ctx, tx, { packageId: req.packageId, leadId: lead.id, type: "REPLACEMENT", quantity: 1, reason: `Sostituzione approvata per lead ${lead.code} (${req.reason})` });
      await setLeadStatusTx(ctx, tx, lead.id, "REPLACEMENT_APPROVED", note ?? "Sostituzione approvata", { replaced: true });
      await emitEvent(tx, "lead.replaced", { clientId: req.clientId, leadId: lead.id, data: { leadId: lead.id, code: lead.code, packageId: req.packageId } });
    } else {
      await setLeadStatusTx(ctx, tx, lead.id, "REPLACEMENT_REJECTED", note ?? "Sostituzione rifiutata");
    }
    await audit(tx, ctx.user, {
      action: `replacement.${decision.toLowerCase()}`,
      entityType: "replacement_request",
      entityId: id,
      leadId: lead.id,
      clientId: req.clientId,
      summary: `Sostituzione lead ${lead.code}: ${decision}${note ? ` (${note})` : ""}`,
    });
  });
  return getReplacement(ctx, id);
}

// Tasso di replacement per cliente nell'ultimo periodo: usato per l'alert "replacement rate anomalo".
export async function replacementRate(db: DbOrTx, clientId: string, days = 30): Promise<{ delivered: number; approved: number; rate: number }> {
  const since = new Date(Date.now() - days * 86400000);
  const d = await db.select({ n: sql<number>`count(*)::int` }).from(leads).where(and(eq(leads.clientId, clientId), sql`${leads.deliveredAt} >= ${since}`));
  const a = await db.select({ n: sql<number>`count(*)::int` }).from(replacementRequests).where(and(eq(replacementRequests.clientId, clientId), eq(replacementRequests.status, "APPROVED"), sql`${replacementRequests.decidedAt} >= ${since}`));
  const delivered = Number(d[0]?.n ?? 0);
  const approved = Number(a[0]?.n ?? 0);
  return { delivered, approved, rate: delivered ? approved / delivered : 0 };
}
