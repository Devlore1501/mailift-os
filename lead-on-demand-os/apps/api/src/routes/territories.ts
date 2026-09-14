import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { TERRITORY_LEVELS } from "@lod/core";
import { ADMIN_ROLES, requireRole } from "../app.js";
import * as terrSvc from "../services/territories.js";

export async function registerTerritoryRoutes(app: FastifyInstance) {
  app.get("/territories", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => terrSvc.listTerritories(req.ctx, z.object({ clientId: z.string().uuid().optional() }).parse(req.query)));
  app.post("/territories", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ clientId: z.string().uuid(), level: z.enum(TERRITORY_LEVELS), value: z.string().min(1), region: z.string().nullish(), province: z.string().nullish(), exclusive: z.boolean().optional() }).parse(req.body);
    return reply.status(201).send(await terrSvc.createTerritory(req.ctx, body));
  });
  app.delete("/territories/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => terrSvc.deactivateTerritory(req.ctx, (req.params as { id: string }).id));
}
