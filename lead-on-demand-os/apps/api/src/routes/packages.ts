import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { OFFER_TYPES, PACKAGE_STATUSES } from "@lod/core";
import { ADMIN_ROLES, requireRole } from "../app.js";
import * as pkgSvc from "../services/packages.js";
import { retryWaitingQueue } from "../services/routing.js";

export async function registerPackageRoutes(app: FastifyInstance) {
  app.get("/packages", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const q = z.object({ clientId: z.string().uuid().optional(), status: z.enum(PACKAGE_STATUSES).optional() }).parse(req.query);
    return pkgSvc.listPackages(req.ctx, q);
  });
  app.post("/packages", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z
      .object({
        clientId: z.string().uuid(),
        productName: z.string().min(1),
        offerType: z.enum(OFFER_TYPES).optional(),
        quantity: z.number().int().positive(),
        unitPrice: z.number().nonnegative(),
        paid: z.boolean().optional(),
        paymentReference: z.string().nullish(),
        activate: z.boolean().optional(),
        warningThreshold: z.number().int().optional(),
        alertThreshold: z.number().int().optional(),
        expiresAt: z.coerce.date().nullish(),
        notes: z.string().nullish(),
      })
      .parse(req.body);
    return reply.status(201).send(await pkgSvc.createPackage(req.ctx, body));
  });
  app.get("/packages/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => pkgSvc.getPackage(req.ctx, (req.params as { id: string }).id));
  app.get("/packages/:id/transactions", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => pkgSvc.listTransactions(req.ctx, (req.params as { id: string }).id));
  // Registrazione manuale del pagamento (MVP billing, PRD sez. 35): attiva il pacchetto e riprova la coda.
  app.post("/packages/:id/activate", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const body = z.object({ reason: z.string().optional(), retryQueue: z.boolean().optional() }).parse(req.body ?? {});
    const pkg = await pkgSvc.activatePackage(req.ctx, (req.params as { id: string }).id, body.reason ?? "Pagamento registrato manualmente");
    const retried = body.retryQueue === false ? [] : await retryWaitingQueue(req.ctx);
    return { package: pkg, retriedQueue: retried };
  });
  app.post("/packages/:id/status", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const body = z.object({ status: z.enum(PACKAGE_STATUSES), reason: z.string().optional() }).parse(req.body);
    return pkgSvc.setPackageStatus(req.ctx, (req.params as { id: string }).id, body.status, body.reason);
  });
  app.post("/packages/:id/adjust", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => {
    const body = z.object({ quantity: z.number().int(), reason: z.string().min(3) }).parse(req.body);
    return pkgSvc.manualAdjustment(req.ctx, (req.params as { id: string }).id, body.quantity, body.reason);
  });
}
