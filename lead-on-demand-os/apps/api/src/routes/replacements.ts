import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { ADMIN_ROLES, requireRole } from "../app.js";
import * as replSvc from "../services/replacement.js";

export async function registerReplacementRoutes(app: FastifyInstance) {
  app.get("/replacements", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const q = z.object({ status: z.enum(["REQUESTED", "APPROVED", "REJECTED"]).optional(), clientId: z.string().uuid().optional() }).parse(req.query);
    return replSvc.listReplacements(req.ctx, q);
  });
  app.get("/replacements/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => replSvc.getReplacement(req.ctx, (req.params as { id: string }).id));
  app.post("/replacements/:id/decide", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const body = z.object({ decision: z.enum(["APPROVED", "REJECTED"]), note: z.string().nullish() }).parse(req.body);
    return replSvc.decideReplacement(req.ctx, (req.params as { id: string }).id, body.decision, body.note);
  });
}
