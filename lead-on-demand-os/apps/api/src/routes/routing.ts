import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { eq } from "drizzle-orm";
import { leads } from "@lod/db";
import { ROUTING_REASON_LABELS } from "@lod/core";
import { ADMIN_ROLES, STAFF_ROLES, requireRole } from "../app.js";
import * as routingSvc from "../services/routing.js";

export async function registerRoutingRoutes(app: FastifyInstance) {
  // Simulazione: quale cliente riceverebbe il lead e perché gli altri no.
  app.post("/routing/evaluate", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ leadId: z.string().uuid() }).parse(req.body);
    const decision = await routingSvc.evaluateForLead(req.ctx, body.leadId);
    return { decision, labels: ROUTING_REASON_LABELS };
  });
  app.post("/routing/retry-queue", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => routingSvc.retryWaitingQueue(req.ctx));
  // Coda di assegnazione (PRD sez. 13) con motivi aggregati: mostra i territori con domanda e senza buyer.
  app.get("/routing/waiting", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const rows = await req.ctx.db.select().from(leads).where(eq(leads.status, "WAITING_ASSIGNMENT")).orderBy(leads.createdAt);
    const byProvince: Record<string, number> = {};
    const byReason: Record<string, number> = {};
    for (const l of rows) {
      byProvince[l.province ?? "?"] = (byProvince[l.province ?? "?"] ?? 0) + 1;
      for (const r of (l.waitingReasons as string[]) ?? []) byReason[r] = (byReason[r] ?? 0) + 1;
    }
    return { total: rows.length, byProvince, byReason, labels: ROUTING_REASON_LABELS, leads: rows };
  });
}
