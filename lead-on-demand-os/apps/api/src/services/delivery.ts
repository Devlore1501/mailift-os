import { eq } from "drizzle-orm";
import { clients, ghlMappings, integrations, leads, packages, type DbOrTx } from "@lod/db";
import { DELIVERED_STATUSES } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { enqueue } from "../lib/jobs.js";
import { notify } from "../lib/notify.js";
import { applyLedgerMoveTx } from "./packages.js";
import { getLead, setLeadStatusTx } from "./leads.js";
import type { GhlAuth } from "./ghlClient.js";

// Consegna (PRD sez. 6, 57): è l'unico punto in cui un lead scala il credito.
// Idempotente: un lead già addebitato non viene addebitato due volte.
export async function deliverLeadTx(ctx: Ctx, tx: DbOrTx, leadId: string) {
  const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
  if (!lead) throw notFound("Lead");
  if (!lead.clientId || !lead.packageId) throw conflict("Il lead non è assegnato a nessun cliente/pacchetto");
  if (!["ASSIGNED", "APPOINTMENT_BOOKED", "DELIVERY_FAILED"].includes(lead.status)) {
    throw conflict(`Il lead è in stato ${lead.status}: la consegna parte da ASSIGNED o APPOINTMENT_BOOKED`);
  }
  if (!lead.creditCharged) {
    await applyLedgerMoveTx(ctx, tx, { packageId: lead.packageId, leadId: lead.id, type: "DELIVERY", quantity: 1, reason: `Consegna lead ${lead.code}` });
  }
  if (lead.status !== "DELIVERED") {
    await setLeadStatusTx(ctx, tx, lead.id, "DELIVERED", "Lead consegnato al cliente", { deliveredAt: lead.deliveredAt ?? ctx.now(), creditCharged: true });
  }
  await emitEvent(tx, "lead.delivered", { clientId: lead.clientId, leadId: lead.id, data: { leadId: lead.id, code: lead.code, packageId: lead.packageId } });
  await enqueue(tx, "ghl.deliver", { leadId: lead.id }, { dedupeKey: `ghl-deliver:${lead.id}`, maxAttempts: 5 });
}

export async function deliverLead(ctx: Ctx, leadId: string) {
  await ctx.db.transaction((tx) => deliverLeadTx(ctx, tx, leadId));
  return getLead(ctx, leadId);
}

export function isDeliveredStatus(status: (typeof leads.$inferSelect)["status"]) {
  return DELIVERED_STATUSES.includes(status);
}

// Risolve credenziali GHL del cliente: integrazione per cliente, altrimenti token globale.
export async function resolveGhlAuth(ctx: Ctx, db: DbOrTx, clientId: string): Promise<GhlAuth | null> {
  const client = await db.query.clients.findFirst({ where: eq(clients.id, clientId) });
  if (!client) return null;
  const integ = await db.query.integrations.findFirst({ where: (i, { and, eq }) => and(eq(i.clientId, clientId), eq(i.provider, "ghl"), eq(i.active, true)) });
  const cfg = (integ?.config ?? {}) as { apiKey?: string; locationId?: string };
  const apiKey = cfg.apiKey ?? ctx.config.ghl.apiKey;
  const locationId = cfg.locationId ?? client.ghlLocationId;
  if (!apiKey || !locationId) return null;
  return { apiKey, locationId };
}

// Handler del job ghl.deliver: crea/aggiorna contatto, tag, custom field, opportunità, nota di qualifica.
export async function runGhlDelivery(ctx: Ctx, leadId: string): Promise<{ skipped: boolean }> {
  const lead = await getLead({ ...ctx, user: null }, leadId);
  if (!lead.clientId) return { skipped: true };
  const auth = await resolveGhlAuth(ctx, ctx.db, lead.clientId);
  const client = await ctx.db.query.clients.findFirst({ where: eq(clients.id, lead.clientId) });
  if (!auth || !client) {
    await ctx.db.update(leads).set({ ghlLastError: "GHL non configurato per il cliente", updatedAt: ctx.now() }).where(eq(leads.id, leadId));
    return { skipped: true };
  }
  const mappings = await ctx.db.select().from(ghlMappings).where(eq(ghlMappings.clientId, lead.clientId));
  const defaults = await ctx.db.select().from(ghlMappings).where(eq(ghlMappings.clientId, null as unknown as string));
  const allMappings = [...defaults, ...mappings];
  const values: Record<string, unknown> = {
    ...lead.answers,
    lead_code: lead.code,
    qualification_status: lead.qualificationCategory,
    qualification_score: lead.qualificationScore,
    province: lead.province,
    municipality: lead.municipality,
    postal_code: lead.postalCode,
    campaign: lead.campaignName,
    source: lead.source,
  };
  const customFields: Array<{ id: string; value: unknown }> = [];
  const tags = new Set<string>(["lead-on-demand", `lod:${lead.code.toLowerCase()}`]);
  if (lead.qualificationCategory) tags.add(`lod:${lead.qualificationCategory.toLowerCase()}`);
  for (const m of allMappings) {
    const v = values[m.lodField];
    if (v === undefined || v === null || v === "") continue;
    if (m.kind === "tag") tags.add(m.ghlField.replace("{value}", String(v)));
    else customFields.push({ id: m.ghlField, value: v });
  }
  const { contactId } = await ctx.ghl.upsertContact(auth, {
    firstName: lead.firstName,
    lastName: lead.lastName,
    phone: lead.phoneNormalized ?? lead.phone,
    email: lead.emailNormalized ?? lead.email,
    address1: lead.address,
    city: lead.municipality,
    postalCode: lead.postalCode,
    state: lead.province,
    source: "Lead on Demand",
    tags: Array.from(tags),
    customFields,
  });
  let opportunityId = lead.ghlOpportunityId;
  if (client.ghlPipelineId && !opportunityId) {
    const r = await ctx.ghl.createOpportunity(auth, {
      pipelineId: client.ghlPipelineId,
      pipelineStageId: client.ghlPipelineStageId,
      name: `${lead.firstName ?? ""} ${lead.lastName ?? ""} (${lead.code})`.trim(),
      contactId,
      monetaryValue: null,
    });
    opportunityId = r.opportunityId;
  }
  const answerLines = Object.entries(lead.answers).map(([k, v]) => `- ${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`);
  await ctx.ghl.addNote(
    auth,
    contactId,
    [`Lead on Demand ${lead.code}`, `Qualifica: ${lead.qualificationCategory ?? "-"} (${lead.qualificationScore ?? "-"}/100)`, ...answerLines, lead.qualificationNotes ? `Note: ${lead.qualificationNotes}` : ""].filter(Boolean).join("\n"),
  );
  await ctx.db.transaction(async (tx) => {
    await tx.update(leads).set({ ghlContactId: contactId, ghlOpportunityId: opportunityId ?? null, ghlSyncedAt: ctx.now(), ghlLastError: null, updatedAt: ctx.now() }).where(eq(leads.id, leadId));
    if (lead.status === "DELIVERY_FAILED") await setLeadStatusTx(ctx, tx, leadId, "DELIVERED", "Invio a GHL riuscito dopo retry");
    await audit(tx, null, { action: "lead.ghl_synced", entityType: "lead", entityId: leadId, leadId, clientId: lead.clientId, summary: `Lead ${lead.code} inviato a GHL (contatto ${contactId})` });
  });
  return { skipped: false };
}

// Chiamato dal worker quando i tentativi sono esauriti (PRD sez. 55).
export async function onGhlDeliveryDead(ctx: Ctx, leadId: string, error: string) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) return;
    await tx.update(leads).set({ ghlLastError: error, updatedAt: ctx.now() }).where(eq(leads.id, leadId));
    if (lead.status === "DELIVERED") await setLeadStatusTx(ctx, tx, leadId, "DELIVERY_FAILED", `Invio a GHL fallito: ${error}`);
    const pkg = lead.packageId ? await tx.query.packages.findFirst({ where: eq(packages.id, lead.packageId), columns: { code: true } }) : null;
    await notify(tx, {
      event: "DELIVERY_FAILED",
      severity: "critical",
      title: `Invio a GHL fallito per il lead ${lead.code}`,
      body: `${error}. Il credito del pacchetto ${pkg?.code ?? ""} resta addebitato; riprovare l'invio dalla scheda lead.`,
      leadId,
      clientId: lead.clientId,
      dedupeKey: `ghl-dead:${leadId}:${lead.attempts}`,
    });
  });
}

export async function retryGhlDelivery(ctx: Ctx, leadId: string) {
  const lead = await getLead(ctx, leadId);
  if (!isDeliveredStatus(lead.status) && lead.status !== "DELIVERY_FAILED") throw conflict("Il lead non è ancora stato consegnato");
  await ctx.db.transaction(async (tx) => {
    await enqueue(tx, "ghl.deliver", { leadId }, { dedupeKey: `ghl-deliver:${leadId}:retry:${Date.now()}`, maxAttempts: 3 });
    await audit(tx, ctx.user, { action: "lead.ghl_retry", entityType: "lead", entityId: leadId, leadId, summary: `Reinvio a GHL richiesto per ${lead.code}` });
  });
  return { queued: true };
}
