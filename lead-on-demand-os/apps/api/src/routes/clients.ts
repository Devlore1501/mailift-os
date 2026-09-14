import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { CLIENT_STATUSES, CLIENT_TYPES, OFFER_TYPES } from "@lod/core";
import { ADMIN_ROLES, requireRole } from "../app.js";
import * as clientsSvc from "../services/clients.js";
import * as analytics from "../services/analytics.js";
import { replacementRate } from "../services/replacement.js";

const criterion = z.object({ field: z.string(), op: z.enum(["eq", "neq", "gte", "lte", "in", "truthy", "falsy", "contains"]), value: z.unknown().optional(), kind: z.enum(["MANDATORY", "PREFERRED", "EXCLUSION"]), label: z.string() });

const clientSchema = z.object({
  legalName: z.string().min(1),
  tradeName: z.string().min(1),
  vatNumber: z.string().nullish(),
  contactName: z.string().nullish(),
  phone: z.string().nullish(),
  email: z.string().nullish(),
  address: z.string().nullish(),
  region: z.string().nullish(),
  website: z.string().nullish(),
  vertical: z.string().optional(),
  clientType: z.enum(CLIENT_TYPES).optional(),
  offerType: z.enum(OFFER_TYPES).optional(),
  defaultLeadPrice: z.number().nullish(),
  status: z.enum(CLIENT_STATUSES).optional(),
  startDate: z.coerce.date().nullish(),
  endDate: z.coerce.date().nullish(),
  capDaily: z.number().int().nullish(),
  capWeekly: z.number().int().nullish(),
  capMonthly: z.number().int().nullish(),
  priority: z.number().int().optional(),
  ghlLocationId: z.string().nullish(),
  ghlPipelineId: z.string().nullish(),
  ghlPipelineStageId: z.string().nullish(),
  ghlCalendarId: z.string().nullish(),
  webhookUrl: z.string().nullish(),
  webhookSecret: z.string().nullish(),
  externalCrm: z.string().nullish(),
  notificationEmail: z.string().nullish(),
  notificationPhone: z.string().nullish(),
  accountManagerUserId: z.string().uuid().nullish(),
  replacementSlaHours: z.number().int().optional(),
  dedupeWindowDays: z.number().int().optional(),
  criteria: z.array(criterion).optional(),
  notes: z.string().nullish(),
});

export async function registerClientRoutes(app: FastifyInstance) {
  app.get("/clients", { preHandler: requireRole(...ADMIN_ROLES, "OPERATOR") }, async (req) => {
    const list = await clientsSvc.listClients(req.ctx);
    if (req.ctx.user?.role === "OPERATOR") return list.map((c) => ({ id: c.id, code: c.code, tradeName: c.tradeName, status: c.status, clientType: c.clientType }));
    return list;
  });
  app.post("/clients", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => reply.status(201).send(await clientsSvc.createClient(req.ctx, clientSchema.parse(req.body))));
  app.get("/clients/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => clientsSvc.getClient(req.ctx, (req.params as { id: string }).id));
  app.patch("/clients/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => clientsSvc.updateClient(req.ctx, (req.params as { id: string }).id, clientSchema.partial().parse(req.body)));
  app.post("/clients/:id/portal-users", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ email: z.string().email(), fullName: z.string().min(1), password: z.string().min(8) }).parse(req.body);
    return reply.status(201).send(await clientsSvc.addPortalUser(req.ctx, (req.params as { id: string }).id, body));
  });
  app.get("/clients/:id/analytics", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const q = z.object({ from: z.coerce.date().optional(), to: z.coerce.date().optional() }).parse(req.query);
    const id = (req.params as { id: string }).id;
    const [a, r] = await Promise.all([analytics.clientAnalytics(req.ctx, id, q), replacementRate(req.ctx.db, id)]);
    return { ...a, replacementRate: r };
  });
}
