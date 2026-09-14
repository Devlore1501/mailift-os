import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { and, desc, eq, sql } from "drizzle-orm";
import { clients, packages, replacementRequests } from "@lod/db";
import { REPLACEMENT_REASONS, SALES_OUTCOMES, checkReplacementSla } from "@lod/core";
import { requireRole } from "../app.js";
import { forbidden } from "../lib/errors.js";
import { toCsv } from "../lib/csv.js";
import * as leadsSvc from "../services/leads.js";
import * as replSvc from "../services/replacement.js";
import * as apptSvc from "../services/appointments.js";
import * as outcomeSvc from "../services/outcomes.js";
import * as analytics from "../services/analytics.js";
import { getBalance } from "../services/packages.js";

// Portale cliente (PRD sez. 25, 41, 53): il client_id arriva SEMPRE dal token, mai dalla richiesta.
function clientIdOf(req: { ctx: { user: { clientId: string | null } | null } }): string {
  const id = req.ctx.user?.clientId;
  if (!id) throw forbidden("Utente non collegato a un cliente");
  return id;
}

const PORTAL_LEAD_FIELDS = ["id", "code", "createdAt", "deliveredAt", "status", "firstName", "lastName", "phone", "email", "address", "municipality", "postalCode", "province", "region", "leadType", "qualificationCategory", "qualificationScore", "qualificationNotes", "replaced", "customFields"] as const;

function portalLead<T extends Record<string, unknown>>(lead: T) {
  const out: Record<string, unknown> = {};
  for (const k of PORTAL_LEAD_FIELDS) out[k] = lead[k];
  return out;
}

export async function registerPortalRoutes(app: FastifyInstance) {
  const guard = requireRole("CLIENT");

  app.get("/portal/dashboard", { preHandler: guard }, async (req) => {
    const clientId = clientIdOf(req);
    const client = await req.ctx.db.query.clients.findFirst({ where: eq(clients.id, clientId), columns: { id: true, tradeName: true, offerType: true, replacementSlaHours: true, status: true } });
    const pkgs = await req.ctx.db.select().from(packages).where(and(eq(packages.clientId, clientId), sql`${packages.status} in ('ACTIVE','LOW_BALANCE','COMPLETED')`)).orderBy(desc(packages.createdAt));
    const withBalance = [];
    for (const p of pkgs) {
      const balance = await getBalance(req.ctx.db, p.id);
      const delivered = await req.ctx.db.execute(sql`select count(*)::int as n from package_transactions where package_id = ${p.id} and type = 'DELIVERY'`);
      const repl = await req.ctx.db.execute(sql`select count(*)::int as n from package_transactions where package_id = ${p.id} and type = 'REPLACEMENT'`);
      const d = ((delivered as { rows?: Array<{ n: number }> }).rows ?? (delivered as unknown as Array<{ n: number }>))[0];
      const r = ((repl as { rows?: Array<{ n: number }> }).rows ?? (repl as unknown as Array<{ n: number }>))[0];
      withBalance.push({ id: p.id, code: p.code, productName: p.productName, quantity: p.quantity, status: p.status, balance, delivered: Number(d?.n ?? 0), replacements: Number(r?.n ?? 0), startsAt: p.startsAt, expiresAt: p.expiresAt });
    }
    const stats = await analytics.clientAnalytics(req.ctx, clientId);
    return { client, packages: withBalance, stats };
  });

  app.get("/portal/leads", { preHandler: guard }, async (req) => {
    const q = z.object({ search: z.string().optional(), status: z.string().optional(), limit: z.coerce.number().optional(), offset: z.coerce.number().optional() }).parse(req.query);
    const r = await leadsSvc.listLeads(req.ctx, { search: q.search, limit: q.limit, offset: q.offset });
    return { ...r, items: r.items.filter((l) => l.creditCharged).map(portalLead) };
  });

  app.get("/portal/leads/export.csv", { preHandler: guard }, async (req, reply) => {
    const r = await leadsSvc.listLeads(req.ctx, { limit: 500 });
    reply.header("Content-Type", "text/csv; charset=utf-8").header("Content-Disposition", "attachment; filename=lead.csv");
    return toCsv(r.items.filter((l) => l.creditCharged).map(portalLead), [...PORTAL_LEAD_FIELDS]);
  });

  app.get("/portal/leads/:id", { preHandler: guard }, async (req) => {
    const clientId = clientIdOf(req);
    const lead = await leadsSvc.getLead(req.ctx, (req.params as { id: string }).id);
    if (!lead.creditCharged) throw forbidden("Lead non ancora consegnato");
    const client = await req.ctx.db.query.clients.findFirst({ where: eq(clients.id, clientId), columns: { replacementSlaHours: true } });
    const sla = lead.deliveredAt ? checkReplacementSla(lead.deliveredAt, client?.replacementSlaHours ?? 72, req.ctx.now()) : null;
    const replacements = await req.ctx.db.query.replacementRequests.findMany({ where: eq(replacementRequests.leadId, lead.id), orderBy: desc(replacementRequests.createdAt) });
    const appts = (await apptSvc.listAppointments(req.ctx)).filter((a) => a.leadId === lead.id);
    const outcomes = await req.ctx.db.query.salesOutcomes.findMany({ where: (o, { eq }) => eq(o.leadId, lead.id), orderBy: (o, { desc }) => desc(o.createdAt) });
    const timeline = lead.history.filter((h) => ["ASSIGNED", "DELIVERED", "APPOINTMENT_BOOKED", "REPLACEMENT_REQUESTED", "REPLACEMENT_APPROVED", "REPLACEMENT_REJECTED", "CLOSED_WON", "CLOSED_LOST"].includes(h.toStatus));
    return { ...portalLead(lead), answers: lead.answers, answersDisplay: lead.answersDisplay, notes: lead.notes, timeline, replacementSla: sla, replacements, appointments: appts, outcomes };
  });

  app.post("/portal/leads/:id/replacement", { preHandler: guard }, async (req, reply) => {
    const body = z.object({ reason: z.enum(REPLACEMENT_REASONS), note: z.string().nullish(), attachments: z.array(z.object({ name: z.string(), url: z.string() })).optional() }).parse(req.body);
    return reply.status(201).send(await replSvc.requestReplacement(req.ctx, (req.params as { id: string }).id, body));
  });

  app.post("/portal/leads/:id/outcome", { preHandler: guard }, async (req) => {
    const body = z.object({ outcome: z.enum(SALES_OUTCOMES), lostReason: z.string().nullish(), contractValue: z.number().nullish(), soldAt: z.coerce.date().nullish(), margin: z.number().nullish(), product: z.string().nullish() }).parse(req.body);
    return outcomeSvc.recordOutcome(req.ctx, (req.params as { id: string }).id, body);
  });

  app.get("/portal/appointments", { preHandler: guard }, async (req) => apptSvc.listAppointments(req.ctx));
  app.post("/portal/appointments/:id/status", { preHandler: guard }, async (req) => {
    const body = z.object({ status: z.enum(["CONFIRMED", "CANCELLED", "SHOW", "NO_SHOW", "COMPLETED"]), notes: z.string().nullish() }).parse(req.body);
    return apptSvc.updateAppointmentStatus(req.ctx, (req.params as { id: string }).id, body.status, body);
  });
  app.get("/portal/replacements", { preHandler: guard }, async (req) => replSvc.listReplacements(req.ctx));
  app.get("/portal/stats", { preHandler: guard }, async (req) => {
    const q = z.object({ from: z.coerce.date().optional(), to: z.coerce.date().optional() }).parse(req.query);
    return analytics.clientAnalytics(req.ctx, clientIdOf(req), q);
  });
}
