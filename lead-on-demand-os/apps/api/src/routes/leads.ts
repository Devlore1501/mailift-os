import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { LEAD_STATUSES, LEAD_TYPES, REPLACEMENT_REASONS, SALES_OUTCOMES } from "@lod/core";
import { ADMIN_ROLES, STAFF_ROLES, requireRole } from "../app.js";
import { unauthorized } from "../lib/errors.js";
import * as leadsSvc from "../services/leads.js";
import * as routingSvc from "../services/routing.js";
import * as deliverySvc from "../services/delivery.js";
import * as replSvc from "../services/replacement.js";
import * as apptSvc from "../services/appointments.js";
import * as outcomeSvc from "../services/outcomes.js";
import { toCsv } from "../lib/csv.js";

const answerValue = z.union([z.string(), z.number(), z.boolean(), z.array(z.string()), z.null()]);

export const createLeadSchema = z.object({
  vertical: z.string().optional(),
  leadType: z.enum(LEAD_TYPES).optional(),
  firstName: z.string().nullish(),
  lastName: z.string().nullish(),
  phone: z.string().nullish(),
  email: z.string().nullish(),
  address: z.string().nullish(),
  municipality: z.string().nullish(),
  postalCode: z.string().nullish(),
  province: z.string().nullish(),
  region: z.string().nullish(),
  country: z.string().nullish(),
  sourceId: z.string().uuid().nullish(),
  sourceName: z.string().nullish(),
  campaignId: z.string().uuid().nullish(),
  campaignName: z.string().nullish(),
  source: z.string().nullish(),
  medium: z.string().nullish(),
  adSet: z.string().nullish(),
  ad: z.string().nullish(),
  creative: z.string().nullish(),
  landingPage: z.string().nullish(),
  utmSource: z.string().nullish(),
  utmMedium: z.string().nullish(),
  utmCampaign: z.string().nullish(),
  utmContent: z.string().nullish(),
  utmTerm: z.string().nullish(),
  clickIds: z.record(z.string()).optional(),
  attributedCost: z.number().nullish(),
  consentRecorded: z.boolean().optional(),
  consentText: z.string().nullish(),
  customFields: z.record(z.unknown()).optional(),
  answers: z.record(answerValue).optional(),
  acquiredAt: z.coerce.date().optional(),
});

const listSchema = z.object({
  status: z.string().optional(),
  clientId: z.string().uuid().optional(),
  province: z.string().optional(),
  region: z.string().optional(),
  ownerUserId: z.string().uuid().optional(),
  campaignId: z.string().uuid().optional(),
  sourceId: z.string().uuid().optional(),
  qualificationCategory: z.string().optional(),
  packageId: z.string().uuid().optional(),
  from: z.coerce.date().optional(),
  to: z.coerce.date().optional(),
  search: z.string().optional(),
  replaced: z.enum(["true", "false"]).optional(),
  limit: z.coerce.number().int().min(1).max(500).optional(),
  offset: z.coerce.number().int().min(0).optional(),
});

function parseFilter(q: unknown) {
  const p = listSchema.parse(q);
  const statuses = p.status ? p.status.split(",").filter((s): s is (typeof LEAD_STATUSES)[number] => (LEAD_STATUSES as readonly string[]).includes(s)) : undefined;
  return { ...p, status: statuses, replaced: p.replaced === undefined ? undefined : p.replaced === "true" };
}

export async function registerLeadRoutes(app: FastifyInstance) {
  // Ingresso lead: staff autenticato oppure API key pubblica (landing, Make, Zapier, form).
  app.post("/leads", async (req, reply) => {
    const apiKey = req.headers["x-api-key"];
    const cfgKey = req.ctx.config.publicLeadApiKey;
    const viaKey = typeof apiKey === "string" && cfgKey && apiKey === cfgKey;
    if (!viaKey && !(req.ctx.user && STAFF_ROLES.includes(req.ctx.user.role))) throw unauthorized("Serve un utente staff o una API key valida");
    const body = createLeadSchema.parse(req.body);
    const lead = await leadsSvc.createLead(req.ctx, body);
    return reply.status(201).send(lead);
  });

  app.get("/leads", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.listLeads(req.ctx, parseFilter(req.query)));

  app.get("/leads/export.csv", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const r = await leadsSvc.listLeads(req.ctx, { ...parseFilter(req.query), limit: 500 });
    reply.header("Content-Type", "text/csv; charset=utf-8").header("Content-Disposition", "attachment; filename=leads.csv");
    return toCsv(r.items, ["code", "createdAt", "status", "firstName", "lastName", "phone", "email", "municipality", "province", "region", "leadType", "qualificationCategory", "qualificationScore", "clientName", "deliveredAt", "campaignName", "source", "dedupeResult", "replaced"]);
  });

  app.get("/leads/queue", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.operatorQueue(req.ctx));
  app.get("/leads/:id", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.getLead(req.ctx, (req.params as { id: string }).id));
  app.patch("/leads/:id", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.updateLead(req.ctx, (req.params as { id: string }).id, createLeadSchema.partial().parse(req.body)));
  app.post("/leads/:id/claim", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.claimLead(req.ctx, (req.params as { id: string }).id));
  app.post("/leads/:id/notes", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ body: z.string().min(1), visibleToClient: z.boolean().optional() }).parse(req.body);
    return leadsSvc.addNote(req.ctx, (req.params as { id: string }).id, body.body, body.visibleToClient ?? false);
  });
  app.post("/leads/:id/attempt", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ note: z.string().optional() }).parse(req.body ?? {});
    return leadsSvc.recordAttempt(req.ctx, (req.params as { id: string }).id, body.note);
  });
  app.post("/leads/:id/callback", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ callbackAt: z.coerce.date(), note: z.string().optional() }).parse(req.body);
    return leadsSvc.scheduleCallback(req.ctx, (req.params as { id: string }).id, body.callbackAt, body.note);
  });
  app.post("/leads/:id/contacted", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.markContacted(req.ctx, (req.params as { id: string }).id));
  app.get("/leads/:id/qualification", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => leadsSvc.qualificationState(req.ctx, (req.params as { id: string }).id));
  app.patch("/leads/:id/answers", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ answers: z.record(answerValue) }).parse(req.body);
    return leadsSvc.saveAnswers(req.ctx, (req.params as { id: string }).id, body.answers);
  });
  app.post("/leads/:id/qualify", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ outcome: z.enum(["QUALIFIED", "NOT_QUALIFIED"]), reason: z.string().nullish(), notes: z.string().nullish(), route: z.boolean().optional() }).parse(req.body);
    const lead = await leadsSvc.qualifyLead(req.ctx, (req.params as { id: string }).id, body);
    if (body.outcome === "QUALIFIED" && (body.route ?? true)) {
      const r = await routingSvc.routeLead(req.ctx, lead.id);
      return { lead: r.lead, routing: r.decision };
    }
    return { lead, routing: null };
  });
  app.post("/leads/:id/route", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => routingSvc.routeLead(req.ctx, (req.params as { id: string }).id));
  app.post("/leads/:id/assign", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const body = z.object({ clientId: z.string().uuid(), packageId: z.string().uuid().nullish(), deliver: z.boolean().optional() }).parse(req.body);
    return routingSvc.manualAssign(req.ctx, (req.params as { id: string }).id, body.clientId, body.packageId ?? null, body.deliver ?? true);
  });
  app.post("/leads/:id/deliver", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => deliverySvc.deliverLead(req.ctx, (req.params as { id: string }).id));
  app.post("/leads/:id/ghl-retry", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => deliverySvc.retryGhlDelivery(req.ctx, (req.params as { id: string }).id));
  app.post("/leads/:id/replacement", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ reason: z.enum(REPLACEMENT_REASONS), note: z.string().nullish(), attachments: z.array(z.object({ name: z.string(), url: z.string() })).optional() }).parse(req.body);
    return reply.status(201).send(await replSvc.requestReplacement(req.ctx, (req.params as { id: string }).id, body));
  });
  app.post("/leads/:id/appointment", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ startsAt: z.coerce.date(), endsAt: z.coerce.date().nullish(), kind: z.string().optional(), notes: z.string().nullish() }).parse(req.body);
    return apptSvc.bookAppointment(req.ctx, { leadId: (req.params as { id: string }).id, ...body });
  });
  app.post("/leads/:id/outcome", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ outcome: z.enum(SALES_OUTCOMES), lostReason: z.string().nullish(), contractValue: z.number().nullish(), soldAt: z.coerce.date().nullish(), margin: z.number().nullish(), product: z.string().nullish() }).parse(req.body);
    return outcomeSvc.recordOutcome(req.ctx, (req.params as { id: string }).id, body);
  });
  app.post("/leads/:id/anonymize", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => leadsSvc.anonymizeLead(req.ctx, (req.params as { id: string }).id));
}
