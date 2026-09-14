import { and, eq, gte, inArray, sql } from "drizzle-orm";
import { clients, leadAssignments, leads, packageTransactions, packages, qualificationRules, territories, type DbOrTx } from "@lod/db";
import {
  evaluateCriteria,
  evaluateRouting,
  ROUTING_REASON_LABELS,
  type Answers,
  type Criterion,
  type RoutingCandidate,
  type RoutingDecision,
  type RoutingLead,
} from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { notify } from "../lib/notify.js";
import { getLead, setLeadStatusTx } from "./leads.js";
import { deliverLeadTx } from "./delivery.js";

// I cap giornalieri/settimanali/mensili si calcolano sul fuso italiano, non su quello del server.
export const BUSINESS_TZ = "Europe/Rome";

function tzParts(d: Date, tz: string) {
  const f = new Intl.DateTimeFormat("en-US", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23", weekday: "short" });
  const p: Record<string, string> = {};
  for (const part of f.formatToParts(d)) p[part.type] = part.value;
  return { y: Number(p.year), m: Number(p.month), d: Number(p.day), h: Number(p.hour), mi: Number(p.minute), s: Number(p.second), weekday: p.weekday! };
}

export function startOfDay(d: Date, tz = BUSINESS_TZ) {
  const p = tzParts(d, tz);
  // Sottrae l'orario locale trascorso: ottiene la mezzanotte locale come istante assoluto.
  return new Date(d.getTime() - ((p.h * 60 + p.mi) * 60 + p.s) * 1000 - d.getMilliseconds());
}
export function startOfWeek(d: Date, tz = BUSINESS_TZ) {
  const sod = startOfDay(d, tz);
  const idx = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(tzParts(d, tz).weekday);
  return new Date(sod.getTime() - Math.max(idx, 0) * 86400000);
}
export function startOfMonth(d: Date, tz = BUSINESS_TZ) {
  const sod = startOfDay(d, tz);
  return new Date(sod.getTime() - (tzParts(d, tz).d - 1) * 86400000);
}

// Fotografia dei candidati per il Routing Engine: clienti dello stesso verticale con
// pacchetti, territori, cap e criteri specifici valutati sulle risposte del lead.
export async function buildCandidates(ctx: Ctx, tx: DbOrTx, lead: RoutingLead, answers: Answers): Promise<RoutingCandidate[]> {
  const rows = await tx.select().from(clients).where(eq(clients.vertical, lead.vertical));
  if (rows.length === 0) return [];
  const ids = rows.map((c) => c.id);
  const pkgs = await tx
    .select({
      pkg: packages,
      balance: sql<number>`coalesce((select sum(q.quantity) from package_transactions q where q.package_id = "packages"."id"), 0)::int`,
    })
    .from(packages)
    .where(and(inArray(packages.clientId, ids), inArray(packages.status, ["ACTIVE", "LOW_BALANCE"])));
  const terr = await tx.select().from(territories).where(and(inArray(territories.clientId, ids), eq(territories.active, true)));
  const rules = await tx.select().from(qualificationRules).where(and(inArray(qualificationRules.clientId, ids), eq(qualificationRules.active, true)));
  const now = ctx.now();
  const counts = await tx
    .select({
      clientId: packageTransactions.clientId,
      day: sql<number>`count(*) filter (where ${packageTransactions.createdAt} >= ${startOfDay(now)})::int`,
      week: sql<number>`count(*) filter (where ${packageTransactions.createdAt} >= ${startOfWeek(now)})::int`,
      month: sql<number>`count(*) filter (where ${packageTransactions.createdAt} >= ${startOfMonth(now)})::int`,
    })
    .from(packageTransactions)
    .where(and(inArray(packageTransactions.clientId, ids), eq(packageTransactions.type, "DELIVERY"), gte(packageTransactions.createdAt, startOfMonth(now))))
    .groupBy(packageTransactions.clientId);
  const lastAssigned = await tx
    .select({ clientId: leadAssignments.clientId, last: sql<Date>`max(${leadAssignments.createdAt})` })
    .from(leadAssignments)
    .where(inArray(leadAssignments.clientId, ids))
    .groupBy(leadAssignments.clientId);

  return rows.map((c) => {
    const clientCriteria: Criterion[] = [
      ...((c.criteria as Criterion[]) ?? []),
      ...rules.filter((r) => r.clientId === c.id).map((r) => ({ field: r.field, op: r.op as Criterion["op"], value: r.value as Criterion["value"], kind: r.kind as Criterion["kind"], label: r.label })),
    ];
    const cnt = counts.find((x) => x.clientId === c.id);
    const la = lastAssigned.find((x) => x.clientId === c.id);
    return {
      clientId: c.id,
      clientName: c.tradeName,
      clientStatus: c.status,
      clientType: c.clientType,
      vertical: c.vertical,
      packages: pkgs
        .filter((p) => p.pkg.clientId === c.id)
        .map((p) => ({ id: p.pkg.id, status: p.pkg.status, balance: Number(p.balance), createdAt: p.pkg.createdAt })),
      territories: terr
        .filter((t) => t.clientId === c.id)
        .map((t) => ({ id: t.id, clientId: t.clientId, level: t.level, value: t.value, exclusive: t.exclusive, region: t.region, province: t.province })),
      caps: { daily: c.capDaily, weekly: c.capWeekly, monthly: c.capMonthly },
      deliveredCounts: { day: Number(cnt?.day ?? 0), week: Number(cnt?.week ?? 0), month: Number(cnt?.month ?? 0) },
      clientCriteriaPassed: clientCriteria.length ? evaluateCriteria(clientCriteria, answers).passed : true,
      lastAssignedAt: la?.last ? new Date(la.last) : null,
      priority: c.priority,
    };
  });
}

export async function toRoutingLead(tx: DbOrTx, leadId: string): Promise<{ lead: typeof leads.$inferSelect; routingLead: RoutingLead; answers: Answers }> {
  const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
  if (!lead) throw notFound("Lead");
  const rows = await tx.query.leadAnswers.findMany({ where: (a, { eq }) => eq(a.leadId, leadId) });
  const answers: Answers = {};
  for (const a of rows) answers[a.questionKey] = a.value as Answers[string];
  return {
    lead,
    answers,
    routingLead: {
      id: lead.id,
      vertical: lead.vertical,
      leadType: lead.leadType,
      location: { country: lead.country, region: lead.region, province: lead.province, municipality: lead.municipality, postalCode: lead.postalCode },
      qualificationPassed: lead.qualificationPassed === true,
    },
  };
}

// Simulazione senza effetti: POST /routing/evaluate
export async function evaluateForLead(ctx: Ctx, leadId: string): Promise<RoutingDecision> {
  const { routingLead, answers } = await toRoutingLead(ctx.db, leadId);
  const candidates = await buildCandidates(ctx, ctx.db, routingLead, answers);
  return evaluateRouting(routingLead, candidates);
}

export interface RouteOptions {
  deliver?: boolean; // default: config.autoDeliverOnAssign
}

// Routing effettivo: assegna il lead e, se previsto, lo consegna subito scalando il credito.
export async function routeLead(ctx: Ctx, leadId: string, opts: RouteOptions = {}) {
  const decision = await ctx.db.transaction(async (tx) => {
    const { lead, routingLead, answers } = await toRoutingLead(tx, leadId);
    if (!["QUALIFIED", "WAITING_ASSIGNMENT"].includes(lead.status)) {
      throw conflict(`Il lead è in stato ${lead.status}: il routing parte da QUALIFIED o WAITING_ASSIGNMENT`);
    }
    const candidates = await buildCandidates(ctx, tx, routingLead, answers);
    const decision = evaluateRouting(routingLead, candidates);
    if (decision.outcome === "ASSIGNED") {
      await persistAssignmentTx(ctx, tx, lead, decision.clientId, decision.packageId, decision.matchedTerritory.id ?? null, decision, false);
      const client = await tx.query.clients.findFirst({ where: eq(clients.id, decision.clientId) });
      const deliverNow = opts.deliver ?? (ctx.config.autoDeliverOnAssign && client?.offerType !== "APPOINTMENT");
      if (deliverNow) await deliverLeadTx(ctx, tx, lead.id);
    } else if (decision.outcome === "WAITING_ASSIGNMENT") {
      const reasons = decision.summary.map((r) => ROUTING_REASON_LABELS[r]);
      if (lead.status !== "WAITING_ASSIGNMENT") {
        await setLeadStatusTx(ctx, tx, lead.id, "WAITING_ASSIGNMENT", `Nessun cliente disponibile: ${reasons.join("; ")}`, { waitingReasons: decision.summary });
        await notify(tx, {
          event: "LEAD_WITHOUT_BUYER",
          severity: "warning",
          title: `Lead ${lead.code} qualificato senza buyer${lead.province ? ` (${lead.province})` : ""}`,
          body: reasons.join("; "),
          leadId: lead.id,
          dedupeKey: `no-buyer:${lead.id}`,
        });
      } else {
        await tx.update(leads).set({ waitingReasons: decision.summary, updatedAt: ctx.now() }).where(eq(leads.id, lead.id));
      }
    }
    return decision;
  });
  return { decision, lead: await getLead(ctx, leadId) };
}

export async function persistAssignmentTx(
  ctx: Ctx,
  tx: DbOrTx,
  lead: typeof leads.$inferSelect,
  clientId: string,
  packageId: string,
  matchedTerritoryId: string | null,
  decision: RoutingDecision | null,
  manual: boolean,
) {
  await tx.update(leadAssignments).set({ active: false }).where(and(eq(leadAssignments.leadId, lead.id), eq(leadAssignments.active, true)));
  await tx.insert(leadAssignments).values({
    leadId: lead.id,
    clientId,
    packageId,
    matchedTerritoryId,
    decision: decision as object | null,
    manual,
    assignedBy: ctx.user?.id ?? null,
  });
  const client = await tx.query.clients.findFirst({ where: eq(clients.id, clientId), columns: { tradeName: true } });
  await setLeadStatusTx(ctx, tx, lead.id, "ASSIGNED", `Assegnato a ${client?.tradeName ?? clientId}${manual ? " (manuale)" : ""}`, {
    clientId,
    packageId,
    assignedAt: ctx.now(),
    waitingReasons: [],
  });
  await emitEvent(tx, "lead.assigned", { clientId, leadId: lead.id, data: { leadId: lead.id, code: lead.code, packageId } });
}

// Assegnazione manuale da Admin/Manager: bypassa il routing ma non il credito.
export async function manualAssign(ctx: Ctx, leadId: string, clientId: string, packageId: string | null, deliver: boolean) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    if (!["QUALIFIED", "WAITING_ASSIGNMENT", "ASSIGNED"].includes(lead.status)) {
      throw conflict(`Il lead è in stato ${lead.status}: assegnazione manuale ammessa solo da QUALIFIED, WAITING_ASSIGNMENT o ASSIGNED`);
    }
    let pkgId = packageId;
    if (!pkgId) {
      const p = await tx
        .select({ pkg: packages, balance: sql<number>`coalesce((select sum(q.quantity) from package_transactions q where q.package_id = "packages"."id"), 0)::int` })
        .from(packages)
        .where(and(eq(packages.clientId, clientId), inArray(packages.status, ["ACTIVE", "LOW_BALANCE"])))
        .orderBy(packages.createdAt);
      const first = p.find((x) => Number(x.balance) > 0);
      if (!first) throw conflict("Il cliente non ha pacchetti attivi con credito");
      pkgId = first.pkg.id;
    }
    if (lead.status === "ASSIGNED") {
      await setLeadStatusTx(ctx, tx, leadId, "WAITING_ASSIGNMENT", "Riassegnazione manuale");
      lead.status = "WAITING_ASSIGNMENT";
    }
    await persistAssignmentTx(ctx, tx, lead, clientId, pkgId, null, null, true);
    await audit(tx, ctx.user, { action: "lead.manual_assign", entityType: "lead", entityId: leadId, leadId, clientId, summary: `Lead ${lead.code} assegnato manualmente` });
    if (deliver) await deliverLeadTx(ctx, tx, leadId);
  });
  return getLead(ctx, leadId);
}

// Riprova il routing per tutti i lead in coda (dopo un rinnovo, un nuovo territorio, ecc.).
export async function retryWaitingQueue(ctx: Ctx, limit = 100) {
  const waiting = await ctx.db.select({ id: leads.id }).from(leads).where(eq(leads.status, "WAITING_ASSIGNMENT")).orderBy(leads.createdAt).limit(limit);
  const results: Array<{ leadId: string; outcome: string }> = [];
  for (const w of waiting) {
    try {
      const r = await routeLead(ctx, w.id);
      results.push({ leadId: w.id, outcome: r.decision.outcome });
    } catch (e) {
      results.push({ leadId: w.id, outcome: `ERROR: ${(e as Error).message}` });
    }
  }
  return results;
}
