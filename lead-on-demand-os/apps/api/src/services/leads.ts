import { and, desc, eq, gte, inArray, isNull, or, sql } from "drizzle-orm";
import {
  campaigns,
  clients,
  leadAnswers,
  leadNotes,
  leadSources,
  leadStatusHistory,
  leads,
  qualificationTemplates,
  type DbOrTx,
} from "@lod/db";
import {
  addressLastnameKey,
  assertTransition,
  computeScore,
  evaluateCriteria,
  formatAnswers,
  evaluateDuplicate,
  nextAttemptStatus,
  nextQuestion,
  normalizeEmail,
  normalizePhone,
  normalizeProvince,
  OPERATOR_QUEUE_STATUSES,
  type Answers,
  type Criterion,
  type LeadStatus,
  type LeadType,
  type QualificationTemplate,
  type ScoreConfig,
} from "@lod/core";
import { audit } from "../lib/audit.js";
import { nextLeadCode } from "../lib/codes.js";
import type { Ctx } from "../lib/context.js";
import { badRequest, conflict, forbidden, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { notify } from "../lib/notify.js";

export interface CreateLeadInput {
  vertical?: string;
  leadType?: LeadType;
  firstName?: string | null;
  lastName?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  municipality?: string | null;
  postalCode?: string | null;
  province?: string | null;
  region?: string | null;
  country?: string | null;
  sourceId?: string | null;
  sourceName?: string | null;
  campaignId?: string | null;
  campaignName?: string | null;
  source?: string | null;
  medium?: string | null;
  adSet?: string | null;
  ad?: string | null;
  creative?: string | null;
  landingPage?: string | null;
  utmSource?: string | null;
  utmMedium?: string | null;
  utmCampaign?: string | null;
  utmContent?: string | null;
  utmTerm?: string | null;
  clickIds?: Record<string, string>;
  attributedCost?: number | null;
  consentRecorded?: boolean;
  consentText?: string | null;
  customFields?: Record<string, unknown>;
  answers?: Answers; // risposte già raccolte dal form (prequalifica digitale)
  acquiredAt?: Date;
}

export async function setLeadStatusTx(
  ctx: Ctx,
  tx: DbOrTx,
  leadId: string,
  to: LeadStatus,
  reason?: string | null,
  extra: Partial<typeof leads.$inferInsert> = {},
) {
  const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
  if (!lead) throw notFound("Lead");
  if (lead.status !== to) assertTransition(lead.status, to);
  await tx
    .update(leads)
    .set({ status: to, updatedAt: ctx.now(), ...extra })
    .where(eq(leads.id, leadId));
  await tx.insert(leadStatusHistory).values({
    leadId,
    fromStatus: lead.status,
    toStatus: to,
    reason: reason ?? null,
    userId: ctx.user?.id ?? null,
    createdAt: ctx.now(),
  });
  await audit(tx, ctx.user, {
    action: "lead.status",
    entityType: "lead",
    entityId: leadId,
    leadId,
    clientId: lead.clientId,
    summary: `Lead ${lead.code}: ${lead.status} -> ${to}${reason ? ` (${reason})` : ""}`,
  });
  return lead;
}

async function resolveDedupeWindow(tx: DbOrTx): Promise<number> {
  const row = await tx.query.settings.findFirst({ where: (s, { eq }) => eq(s.key, "dedupe_window_days") });
  const v = row?.value as number | undefined;
  return typeof v === "number" && v > 0 ? v : 90;
}

// Ingresso lead (PRD sez. 8, 14): normalizza, controlla duplicati, assegna codice, entra in VALIDATING.
export async function createLead(ctx: Ctx, input: CreateLeadInput) {
  const phoneNormalized = normalizePhone(input.phone);
  const emailNormalized = normalizeEmail(input.email);
  if (!phoneNormalized && !emailNormalized) throw badRequest("Serve almeno un telefono o una email validi");

  return ctx.db.transaction(async (tx) => {
    const windowDays = await resolveDedupeWindow(tx);
    const cutoff = new Date(ctx.now().getTime() - windowDays * 86400000);
    const addrKey = addressLastnameKey(input.address, input.lastName);
    const conds = [];
    if (phoneNormalized) conds.push(eq(leads.phoneNormalized, phoneNormalized));
    if (emailNormalized) conds.push(eq(leads.emailNormalized, emailNormalized));
    if (addrKey) conds.push(eq(leads.addressLastnameKey, addrKey));
    const existing = conds.length
      ? await tx
          .select({
            id: leads.id,
            phoneNormalized: leads.phoneNormalized,
            emailNormalized: leads.emailNormalized,
            addressLastnameKey: leads.addressLastnameKey,
            createdAt: leads.createdAt,
          })
          .from(leads)
          .where(and(gte(leads.createdAt, cutoff), or(...conds)))
          .orderBy(desc(leads.createdAt))
      : [];
    const dedupe = evaluateDuplicate(
      { phone: input.phone, email: input.email, address: input.address, lastName: input.lastName },
      existing,
      windowDays,
      ctx.now(),
    );

    let sourceId = input.sourceId ?? null;
    if (!sourceId && input.sourceName) {
      const src = await tx.query.leadSources.findFirst({ where: eq(leadSources.name, input.sourceName) });
      if (src) sourceId = src.id;
      else {
        const [created] = await tx.insert(leadSources).values({ name: input.sourceName, kind: "api" }).returning();
        sourceId = created!.id;
      }
    }
    let campaignId = input.campaignId ?? null;
    if (!campaignId && input.campaignName) {
      const c = await tx.query.campaigns.findFirst({ where: eq(campaigns.name, input.campaignName) });
      if (c) campaignId = c.id;
      else {
        const [created] = await tx.insert(campaigns).values({ name: input.campaignName, platform: input.source ?? input.utmSource ?? null, vertical: input.vertical ?? "photovoltaic" }).returning();
        campaignId = created!.id;
      }
    }

    const code = await nextLeadCode(tx);
    const initialStatus: LeadStatus = "NEW";
    const [lead] = await tx
      .insert(leads)
      .values({
        code,
        vertical: input.vertical ?? "photovoltaic",
        leadType: input.leadType ?? "RESIDENTIAL",
        status: initialStatus,
        firstName: input.firstName ?? null,
        lastName: input.lastName ?? null,
        phone: input.phone ?? null,
        phoneNormalized,
        email: input.email ?? null,
        emailNormalized,
        address: input.address ?? null,
        addressLastnameKey: addrKey,
        municipality: input.municipality?.trim() || null,
        postalCode: input.postalCode?.trim() || null,
        province: normalizeProvince(input.province),
        region: input.region?.trim().toUpperCase() || null,
        country: input.country ?? "IT",
        sourceId,
        campaignId,
        source: input.source ?? null,
        medium: input.medium ?? null,
        campaignName: input.campaignName ?? null,
        adSet: input.adSet ?? null,
        ad: input.ad ?? null,
        creative: input.creative ?? null,
        landingPage: input.landingPage ?? null,
        utmSource: input.utmSource ?? null,
        utmMedium: input.utmMedium ?? null,
        utmCampaign: input.utmCampaign ?? null,
        utmContent: input.utmContent ?? null,
        utmTerm: input.utmTerm ?? null,
        clickIds: input.clickIds ?? {},
        acquiredAt: input.acquiredAt ?? ctx.now(),
        attributedCost: input.attributedCost != null ? input.attributedCost.toFixed(2) : null,
        consentRecorded: input.consentRecorded ?? false,
        consentText: input.consentText ?? null,
        customFields: input.customFields ?? {},
        dedupeResult: dedupe.result,
        duplicateOfLeadId: dedupe.matchedLeadId,
        createdAt: ctx.now(),
        updatedAt: ctx.now(),
      })
      .returning();
    await tx.insert(leadStatusHistory).values({ leadId: lead!.id, fromStatus: null, toStatus: "NEW", reason: "Lead acquisito", userId: ctx.user?.id ?? null, createdAt: ctx.now() });

    if (input.answers) {
      for (const [k, v] of Object.entries(input.answers)) {
        await tx.insert(leadAnswers).values({ leadId: lead!.id, questionKey: k, value: v as object, answeredBy: null });
      }
    }

    await audit(tx, ctx.user, {
      action: "lead.created",
      entityType: "lead",
      entityId: lead!.id,
      leadId: lead!.id,
      summary: `Lead ${code} acquisito da ${input.source ?? input.sourceName ?? "api"} (${dedupe.result})`,
      details: { dedupe },
    });

    // Duplicato certo: resta tracciato ma esce dalla pipeline e non scala mai il pacchetto.
    if (dedupe.result === "DUPLICATE") {
      await setLeadStatusTx(ctx, tx, lead!.id, "NOT_QUALIFIED", `Duplicato di lead ${dedupe.matchedLeadId}`, {
        notQualifiedReason: "DUPLICATE",
      });
    } else {
      await setLeadStatusTx(ctx, tx, lead!.id, "VALIDATING", dedupe.result === "POSSIBLE_DUPLICATE" ? "Possibile duplicato: verificare in chiamata" : null);
      await setLeadStatusTx(ctx, tx, lead!.id, "TO_CONTACT", "In coda operatori");
    }
    await emitEvent(tx, "lead.created", { leadId: lead!.id, data: { leadId: lead!.id, code, dedupe: dedupe.result } });
    await notify(tx, {
      event: "NEW_LEAD",
      title: `Nuovo lead ${code}${lead!.province ? ` (${lead!.province})` : ""}`,
      body: dedupe.result === "UNIQUE" ? undefined : `Controllo duplicati: ${dedupe.result}`,
      leadId: lead!.id,
      dedupeKey: `new-lead:${lead!.id}`,
    });
    return getLead(ctx, lead!.id, tx);
  });
}

export async function getLead(ctx: Ctx, id: string, db: DbOrTx = ctx.db) {
  const lead = await db.query.leads.findFirst({ where: eq(leads.id, id) });
  if (!lead) throw notFound("Lead");
  if (ctx.user?.role === "CLIENT" && lead.clientId !== ctx.user.clientId) throw notFound("Lead");
  if (ctx.user?.role === "OPERATOR" && lead.ownerUserId && lead.ownerUserId !== ctx.user.id && !OPERATOR_QUEUE_STATUSES.includes(lead.status)) {
    throw forbidden("Lead assegnato a un altro operatore");
  }
  const answers = await db.query.leadAnswers.findMany({ where: eq(leadAnswers.leadId, id) });
  const history = await db.query.leadStatusHistory.findMany({ where: eq(leadStatusHistory.leadId, id), orderBy: desc(leadStatusHistory.seq) });
  const notes = await db.query.leadNotes.findMany({ where: eq(leadNotes.leadId, id), orderBy: desc(leadNotes.createdAt) });
  const client = lead.clientId ? await db.query.clients.findFirst({ where: eq(clients.id, lead.clientId), columns: { id: true, tradeName: true, code: true } }) : null;
  const answersMap: Answers = {};
  for (const a of answers) answersMap[a.questionKey] = a.value as Answers[string];
  const visibleNotes = ctx.user?.role === "CLIENT" ? notes.filter((n) => n.visibleToClient) : notes;
  const tpl = await resolveTemplate(db, lead.vertical, lead.leadType);
  const answersDisplay = formatAnswers((tpl?.template as QualificationTemplate | undefined) ?? null, answersMap);
  return { ...lead, answers: answersMap, answersDisplay, history, notes: visibleNotes, client };
}

export interface LeadListFilter {
  status?: LeadStatus[];
  clientId?: string;
  province?: string;
  region?: string;
  ownerUserId?: string;
  campaignId?: string;
  sourceId?: string;
  qualificationCategory?: string;
  packageId?: string;
  from?: Date;
  to?: Date;
  search?: string;
  replaced?: boolean;
  limit?: number;
  offset?: number;
}

export async function listLeads(ctx: Ctx, filter: LeadListFilter) {
  const where = [];
  if (ctx.user?.role === "CLIENT") where.push(eq(leads.clientId, ctx.user.clientId ?? "00000000-0000-0000-0000-000000000000"));
  else if (filter.clientId) where.push(eq(leads.clientId, filter.clientId));
  if (filter.status?.length) where.push(inArray(leads.status, filter.status));
  if (filter.province) where.push(eq(leads.province, filter.province.toUpperCase()));
  if (filter.region) where.push(eq(leads.region, filter.region.toUpperCase()));
  if (filter.ownerUserId) where.push(eq(leads.ownerUserId, filter.ownerUserId));
  if (filter.campaignId) where.push(eq(leads.campaignId, filter.campaignId));
  if (filter.sourceId) where.push(eq(leads.sourceId, filter.sourceId));
  if (filter.packageId) where.push(eq(leads.packageId, filter.packageId));
  if (filter.qualificationCategory) where.push(sql`${leads.qualificationCategory} = ${filter.qualificationCategory}`);
  if (filter.replaced !== undefined) where.push(eq(leads.replaced, filter.replaced));
  if (filter.from) where.push(gte(leads.createdAt, filter.from));
  if (filter.to) where.push(sql`${leads.createdAt} <= ${filter.to}`);
  if (filter.search) {
    const s = `%${filter.search.trim()}%`;
    const phone = normalizePhone(filter.search);
    const conds = [
      sql`${leads.code} ilike ${s}`,
      sql`coalesce(${leads.firstName},'') || ' ' || coalesce(${leads.lastName},'') ilike ${s}`,
      sql`${leads.email} ilike ${s}`,
      sql`${leads.municipality} ilike ${s}`,
    ];
    if (phone) conds.push(eq(leads.phoneNormalized, phone));
    else conds.push(sql`${leads.phone} ilike ${s}`);
    where.push(or(...conds)!);
  }
  const limit = Math.min(filter.limit ?? 50, 500);
  const offset = filter.offset ?? 0;
  const rows = await ctx.db
    .select({ lead: leads, clientName: clients.tradeName })
    .from(leads)
    .leftJoin(clients, eq(clients.id, leads.clientId))
    .where(where.length ? and(...where) : undefined)
    .orderBy(desc(leads.createdAt))
    .limit(limit)
    .offset(offset);
  const count = await ctx.db
    .select({ n: sql<number>`count(*)::int` })
    .from(leads)
    .where(where.length ? and(...where) : undefined);
  return { items: rows.map((r) => ({ ...r.lead, clientName: r.clientName })), total: Number(count[0]?.n ?? 0), limit, offset };
}

export async function operatorQueue(ctx: Ctx) {
  const uid = ctx.user?.id ?? "";
  const rows = await ctx.db
    .select()
    .from(leads)
    .where(and(inArray(leads.status, [...OPERATOR_QUEUE_STATUSES]), or(isNull(leads.ownerUserId), eq(leads.ownerUserId, uid))))
    .orderBy(sql`case when ${leads.callbackAt} is not null and ${leads.callbackAt} <= now() then 0 when ${leads.status} = 'TO_CONTACT' then 1 else 2 end`, leads.createdAt)
    .limit(200);
  return rows;
}

export async function claimLead(ctx: Ctx, leadId: string) {
  const lead = await ctx.db.query.leads.findFirst({ where: eq(leads.id, leadId) });
  if (!lead) throw notFound("Lead");
  if (lead.ownerUserId && lead.ownerUserId !== ctx.user?.id && ctx.user?.role === "OPERATOR") throw conflict("Lead già in carico a un altro operatore");
  await ctx.db.update(leads).set({ ownerUserId: ctx.user?.id ?? null, updatedAt: ctx.now() }).where(eq(leads.id, leadId));
  await audit(ctx.db, ctx.user, { action: "lead.claimed", entityType: "lead", entityId: leadId, leadId, summary: `Lead ${lead.code} preso in carico da ${ctx.user?.fullName ?? "?"}` });
  return getLead(ctx, leadId);
}

export async function addNote(ctx: Ctx, leadId: string, body: string, visibleToClient = false) {
  if (!body.trim()) throw badRequest("Nota vuota");
  await getLead(ctx, leadId);
  await ctx.db.insert(leadNotes).values({ leadId, userId: ctx.user?.id ?? null, body, visibleToClient });
  await audit(ctx.db, ctx.user, { action: "lead.note", entityType: "lead", entityId: leadId, leadId, summary: `Nota aggiunta al lead` });
  return getLead(ctx, leadId);
}

// NON RISPONDE: avanza il tentativo. Dopo il terzo tentativo resta in ATTEMPT_3 finché
// l'operatore decide (richiamata o non qualificato).
export async function recordAttempt(ctx: Ctx, leadId: string, note?: string) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    const next = nextAttemptStatus(lead.status);
    await setLeadStatusTx(ctx, tx, leadId, next, note ?? "Nessuna risposta", {
      attempts: lead.attempts + 1,
      lastContactAt: ctx.now(),
      ownerUserId: lead.ownerUserId ?? ctx.user?.id ?? null,
      callbackAt: null,
    });
  });
  return getLead(ctx, leadId);
}

export async function scheduleCallback(ctx: Ctx, leadId: string, callbackAt: Date, note?: string) {
  await ctx.db.transaction(async (tx) => {
    await setLeadStatusTx(ctx, tx, leadId, "CALLBACK", note ?? `Richiamare il ${callbackAt.toISOString()}`, {
      callbackAt,
      lastContactAt: ctx.now(),
      ownerUserId: ctx.user?.id ?? null,
    });
  });
  return getLead(ctx, leadId);
}

export async function markContacted(ctx: Ctx, leadId: string) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    if (lead.status !== "CONTACTED" && lead.status !== "QUALIFYING") {
      await setLeadStatusTx(ctx, tx, leadId, "CONTACTED", "Contatto riuscito", { lastContactAt: ctx.now(), ownerUserId: lead.ownerUserId ?? ctx.user?.id ?? null });
      await setLeadStatusTx(ctx, tx, leadId, "QUALIFYING", "Qualifica in corso");
    }
  });
  return getLead(ctx, leadId);
}

export async function resolveTemplate(db: DbOrTx, vertical: string, leadType: LeadType) {
  const t = await db.query.qualificationTemplates.findFirst({
    where: and(eq(qualificationTemplates.vertical, vertical), eq(qualificationTemplates.leadType, leadType), eq(qualificationTemplates.active, true)),
  });
  return t ?? null;
}

// Salva risposte allo script e restituisce la prossima domanda (script guidato, PRD sez. 15).
export async function saveAnswers(ctx: Ctx, leadId: string, answers: Answers) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    for (const [k, v] of Object.entries(answers)) {
      await tx
        .insert(leadAnswers)
        .values({ leadId, questionKey: k, value: v as object, answeredBy: ctx.user?.id ?? null })
        .onConflictDoUpdate({ target: [leadAnswers.leadId, leadAnswers.questionKey], set: { value: v as object, answeredBy: ctx.user?.id ?? null, updatedAt: ctx.now() } });
    }
    if (lead.status === "TO_CONTACT" || lead.status.startsWith("ATTEMPT") || lead.status === "CALLBACK") {
      await setLeadStatusTx(ctx, tx, leadId, "CONTACTED", "Contatto riuscito", { lastContactAt: ctx.now(), ownerUserId: lead.ownerUserId ?? ctx.user?.id ?? null });
      await setLeadStatusTx(ctx, tx, leadId, "QUALIFYING", "Qualifica in corso");
    } else if (lead.status === "CONTACTED") {
      await setLeadStatusTx(ctx, tx, leadId, "QUALIFYING", "Qualifica in corso");
    }
  });
  return qualificationState(ctx, leadId);
}

// Stato della qualifica: prossima domanda, criteri, score calcolati in tempo reale.
export async function qualificationState(ctx: Ctx, leadId: string) {
  const lead = await getLead(ctx, leadId);
  const tpl = await resolveTemplate(ctx.db, lead.vertical, lead.leadType);
  if (!tpl) return { lead, template: null, next: null, criteria: null, score: null, clientCriteria: [] };
  const template = tpl.template as QualificationTemplate;
  const baseCriteria = tpl.criteria as Criterion[];
  const scoreConfig = tpl.scoreConfig as ScoreConfig;
  const next = nextQuestion(template, lead.answers);
  const criteria = evaluateCriteria(baseCriteria, lead.answers);
  const score = computeScore(scoreConfig, lead.answers, criteria.passed);
  return { lead, template, next, criteria, score, templateId: tpl.id };
}

export interface QualifyInput {
  outcome: "QUALIFIED" | "NOT_QUALIFIED";
  reason?: string | null;
  notes?: string | null;
}

export async function qualifyLead(ctx: Ctx, leadId: string, input: QualifyInput) {
  const state = await qualificationState(ctx, leadId);
  const lead = state.lead;
  await ctx.db.transaction(async (tx) => {
    if (input.outcome === "QUALIFIED") {
      if (state.criteria && !state.criteria.passed) {
        const failed = [...state.criteria.mandatoryFailed, ...state.criteria.exclusionsHit].map((c) => c.label).join(", ");
        throw conflict(`Criteri obbligatori non soddisfatti: ${failed}`);
      }
      if (lead.status === "TO_CONTACT" || lead.status.startsWith("ATTEMPT") || lead.status === "CALLBACK") {
        await setLeadStatusTx(ctx, tx, leadId, "CONTACTED", "Contatto riuscito");
        await setLeadStatusTx(ctx, tx, leadId, "QUALIFYING", "Qualifica");
      } else if (lead.status === "CONTACTED" || lead.status === "VALIDATING") {
        await setLeadStatusTx(ctx, tx, leadId, "QUALIFYING", "Qualifica");
      }
      await setLeadStatusTx(ctx, tx, leadId, "QUALIFIED", input.reason ?? `Qualificato da ${ctx.user?.fullName ?? "operatore"}`, {
        qualificationPassed: true,
        qualificationScore: state.score?.score ?? null,
        qualificationCategory: state.score?.category ?? "QUALIFIED",
        qualificationTemplateId: state.templateId ?? null,
        qualificationNotes: input.notes ?? null,
        qualifiedAt: ctx.now(),
        qualifiedBy: ctx.user?.id ?? null,
        ownerUserId: lead.ownerUserId ?? ctx.user?.id ?? null,
        lastContactAt: ctx.now(),
      });
      await emitEvent(tx, "lead.qualified", { leadId, data: { leadId, code: lead.code, score: state.score?.score ?? null, category: state.score?.category ?? null } });
      await notify(tx, { event: "LEAD_QUALIFIED", title: `Lead ${lead.code} qualificato`, leadId, dedupeKey: `lead-qualified:${leadId}` });
    } else {
      await setLeadStatusTx(ctx, tx, leadId, "NOT_QUALIFIED", input.reason ?? "Non qualificato", {
        qualificationPassed: false,
        qualificationScore: state.score?.score ?? null,
        qualificationCategory: "NOT_QUALIFIED",
        qualificationNotes: input.notes ?? null,
        notQualifiedReason: input.reason ?? null,
        qualifiedAt: ctx.now(),
        qualifiedBy: ctx.user?.id ?? null,
        lastContactAt: ctx.now(),
      });
      await emitEvent(tx, "lead.rejected", { leadId, data: { leadId, code: lead.code, reason: input.reason ?? null } });
    }
  });
  return getLead(ctx, leadId);
}

export async function updateLead(ctx: Ctx, leadId: string, patch: Partial<CreateLeadInput>) {
  const lead = await getLead(ctx, leadId);
  const set: Partial<typeof leads.$inferInsert> = { updatedAt: ctx.now() };
  const fields = ["firstName", "lastName", "address", "municipality", "postalCode", "region", "customFields"] as const;
  for (const f of fields) if (patch[f] !== undefined) (set as Record<string, unknown>)[f] = patch[f];
  if (patch.province !== undefined) set.province = normalizeProvince(patch.province);
  if (patch.phone !== undefined) {
    set.phone = patch.phone;
    set.phoneNormalized = normalizePhone(patch.phone);
  }
  if (patch.email !== undefined) {
    set.email = patch.email;
    set.emailNormalized = normalizeEmail(patch.email);
  }
  if (patch.leadType !== undefined) set.leadType = patch.leadType;
  if (patch.address !== undefined || patch.lastName !== undefined) {
    set.addressLastnameKey = addressLastnameKey(patch.address ?? lead.address, patch.lastName ?? lead.lastName);
  }
  await ctx.db.update(leads).set(set).where(eq(leads.id, leadId));
  await audit(ctx.db, ctx.user, { action: "lead.updated", entityType: "lead", entityId: leadId, leadId, summary: `Lead ${lead.code} aggiornato`, details: Object.keys(patch) });
  return getLead(ctx, leadId);
}

// Anonimizzazione GDPR: cancella i dati personali mantenendo la traccia contabile.
export async function anonymizeLead(ctx: Ctx, leadId: string) {
  const lead = await getLead(ctx, leadId);
  await ctx.db.transaction(async (tx) => {
    await tx
      .update(leads)
      .set({
        firstName: null,
        lastName: null,
        phone: null,
        phoneNormalized: null,
        email: null,
        emailNormalized: null,
        address: null,
        addressLastnameKey: null,
        customFields: {},
        anonymizedAt: ctx.now(),
        updatedAt: ctx.now(),
      })
      .where(eq(leads.id, leadId));
    await tx.delete(leadAnswers).where(eq(leadAnswers.leadId, leadId));
    await tx.delete(leadNotes).where(eq(leadNotes.leadId, leadId));
    await audit(tx, ctx.user, { action: "lead.anonymized", entityType: "lead", entityId: leadId, leadId, summary: `Lead ${lead.code} anonimizzato (GDPR)` });
  });
  return getLead(ctx, leadId);
}
