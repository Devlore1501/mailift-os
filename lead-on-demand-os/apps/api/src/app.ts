import Fastify, { type FastifyInstance, type FastifyReply, type FastifyRequest } from "fastify";
import cors from "@fastify/cors";
import { ZodError } from "zod";
import type { Database } from "@lod/db";
import type { Role } from "@lod/core";
import { InvalidTransitionError } from "@lod/core";
import type { Config } from "./config.js";
import { AppError, forbidden, unauthorized } from "./lib/errors.js";
import type { AuthUser, Ctx } from "./lib/context.js";
import { verifyToken } from "./lib/auth.js";
import type { GhlClient } from "./services/ghlClient.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerLeadRoutes } from "./routes/leads.js";
import { registerClientRoutes } from "./routes/clients.js";
import { registerPackageRoutes } from "./routes/packages.js";
import { registerTerritoryRoutes } from "./routes/territories.js";
import { registerRoutingRoutes } from "./routes/routing.js";
import { registerAppointmentRoutes } from "./routes/appointments.js";
import { registerReplacementRoutes } from "./routes/replacements.js";
import { registerAnalyticsRoutes } from "./routes/analytics.js";
import { registerWebhookRoutes } from "./routes/webhooks.js";
import { registerPortalRoutes } from "./routes/portal.js";
import { registerAdminRoutes } from "./routes/admin.js";

export interface AppDeps {
  db: Database;
  config: Config;
  ghl: GhlClient;
  now?: () => Date;
}

declare module "fastify" {
  interface FastifyRequest {
    ctx: Ctx;
  }
}

export function requireRole(...roles: Role[]) {
  return async (req: FastifyRequest) => {
    if (!req.ctx.user) throw unauthorized();
    if (!roles.includes(req.ctx.user.role)) throw forbidden();
  };
}

export const ADMIN_ROLES: Role[] = ["SUPER_ADMIN", "MANAGER"];
export const STAFF_ROLES: Role[] = ["SUPER_ADMIN", "MANAGER", "OPERATOR"];

export async function buildApp(deps: AppDeps): Promise<FastifyInstance> {
  const app = Fastify({ logger: process.env.NODE_ENV !== "test" && process.env.LOG !== "silent" ? { level: process.env.LOG_LEVEL ?? "info" } : false });
  await app.register(cors, { origin: deps.config.corsOrigin.split(",").map((s) => s.trim()), credentials: true });

  app.decorateRequest("ctx", null as unknown as Ctx);
  app.addHook("onRequest", async (req) => {
    let user: AuthUser | null = null;
    const auth = req.headers.authorization;
    if (auth?.startsWith("Bearer ")) user = await verifyToken(auth.slice(7), deps.config.jwtSecret);
    req.ctx = { db: deps.db, config: deps.config, ghl: deps.ghl, user, ip: req.ip, now: deps.now ?? (() => new Date()) };
  });

  app.setErrorHandler((err: unknown, req: FastifyRequest, reply: FastifyReply) => {
    if (err instanceof AppError) {
      return reply.status(err.statusCode).send({ error: err.code, message: err.message, details: err.details ?? null });
    }
    if (err instanceof ZodError) {
      return reply.status(400).send({ error: "VALIDATION", message: "Dati non validi", details: err.flatten() });
    }
    if (err instanceof InvalidTransitionError) {
      return reply.status(409).send({ error: "INVALID_TRANSITION", message: err.message, details: { from: err.from, to: err.to } });
    }
    const e = err as { statusCode?: number; message?: string; validation?: unknown };
    if (e.statusCode && e.statusCode < 500) return reply.status(e.statusCode).send({ error: "REQUEST", message: e.message, details: e.validation ?? null });
    req.log.error(err);
    return reply.status(500).send({ error: "INTERNAL", message: "Errore interno" });
  });

  app.get("/health", async () => ({ ok: true, time: new Date().toISOString() }));

  await registerAuthRoutes(app);
  await registerLeadRoutes(app);
  await registerClientRoutes(app);
  await registerPackageRoutes(app);
  await registerTerritoryRoutes(app);
  await registerRoutingRoutes(app);
  await registerAppointmentRoutes(app);
  await registerReplacementRoutes(app);
  await registerAnalyticsRoutes(app);
  await registerWebhookRoutes(app);
  await registerPortalRoutes(app);
  await registerAdminRoutes(app);
  return app;
}
