import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { ADMIN_ROLES, requireRole } from "../app.js";
import * as analytics from "../services/analytics.js";

const filterSchema = z.object({
  from: z.coerce.date().optional(),
  to: z.coerce.date().optional(),
  clientId: z.string().uuid().optional(),
  province: z.string().optional(),
  region: z.string().optional(),
  campaignId: z.string().uuid().optional(),
  sourceId: z.string().uuid().optional(),
  ownerUserId: z.string().uuid().optional(),
  leadType: z.string().optional(),
});

export async function registerAnalyticsRoutes(app: FastifyInstance) {
  app.get("/analytics", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const f = filterSchema.parse(req.query);
    const data = await analytics.adminDashboard(req.ctx, f);
    // Il Manager non vede necessariamente i dati finanziari (PRD sez. 3.2).
    if (req.ctx.user?.role === "MANAGER") return { ...data, economics: null };
    return data;
  });
  app.get("/analytics/campaigns", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => analytics.campaignEconomics(req.ctx, filterSchema.parse(req.query)));
}
