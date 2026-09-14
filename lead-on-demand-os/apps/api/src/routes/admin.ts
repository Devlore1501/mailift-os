import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { and, desc, eq, isNull, or, sql } from "drizzle-orm";
import { auditLogs, campaigns, ghlMappings, integrations, leadSources, marketingCosts, notifications, qualificationTemplates, settings, users, webhookEvents } from "@lod/db";
import { ROLES } from "@lod/core";
import { ADMIN_ROLES, STAFF_ROLES, requireRole } from "../app.js";
import { hashPassword } from "../lib/auth.js";
import { audit } from "../lib/audit.js";
import { badRequest, conflict, notFound } from "../lib/errors.js";
import { queueStats } from "../services/worker.js";

export async function registerAdminRoutes(app: FastifyInstance) {
  // Team (PRD sez. 3): utenti interni.
  app.get("/team", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) =>
    req.ctx.db.select({ id: users.id, email: users.email, fullName: users.fullName, role: users.role, active: users.active, lastLoginAt: users.lastLoginAt, createdAt: users.createdAt }).from(users).where(sql`${users.role} <> 'CLIENT'`).orderBy(users.fullName),
  );
  app.post("/team", { preHandler: requireRole("SUPER_ADMIN") }, async (req, reply) => {
    const body = z.object({ email: z.string().email(), fullName: z.string().min(1), password: z.string().min(8), role: z.enum(ROLES).refine((r) => r !== "CLIENT", "Gli utenti cliente si creano dalla scheda cliente") }).parse(req.body);
    const email = body.email.toLowerCase();
    if (await req.ctx.db.query.users.findFirst({ where: eq(users.email, email) })) throw conflict("Email già registrata");
    const [u] = await req.ctx.db.insert(users).values({ email, fullName: body.fullName, role: body.role, passwordHash: await hashPassword(body.password) }).returning({ id: users.id, email: users.email, fullName: users.fullName, role: users.role });
    await audit(req.ctx.db, req.ctx.user, { action: "user.created", entityType: "user", entityId: u!.id, summary: `Utente ${email} creato con ruolo ${body.role}` }, req.ip);
    return reply.status(201).send(u);
  });
  app.patch("/team/:id", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => {
    const body = z.object({ fullName: z.string().optional(), role: z.enum(ROLES).optional(), active: z.boolean().optional(), password: z.string().min(8).optional() }).parse(req.body);
    const id = (req.params as { id: string }).id;
    const set: Partial<typeof users.$inferInsert> = { updatedAt: new Date() };
    if (body.fullName) set.fullName = body.fullName;
    if (body.role) set.role = body.role;
    if (body.active !== undefined) set.active = body.active;
    if (body.password) set.passwordHash = await hashPassword(body.password);
    const [u] = await req.ctx.db.update(users).set(set).where(eq(users.id, id)).returning({ id: users.id, email: users.email, fullName: users.fullName, role: users.role, active: users.active });
    if (!u) throw notFound("Utente");
    await audit(req.ctx.db, req.ctx.user, { action: "user.updated", entityType: "user", entityId: id, summary: `Utente ${u.email} aggiornato`, details: Object.keys(body) }, req.ip);
    return u;
  });

  // Notifiche in-app.
  app.get("/notifications", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const q = z.object({ unread: z.enum(["true", "false"]).optional(), limit: z.coerce.number().optional() }).parse(req.query);
    const where = [or(isNull(notifications.userId), eq(notifications.userId, req.ctx.user!.id))!];
    if (q.unread === "true") where.push(isNull(notifications.readAt));
    return req.ctx.db.select().from(notifications).where(and(...where)).orderBy(desc(notifications.createdAt)).limit(q.limit ?? 50);
  });
  app.post("/notifications/:id/read", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    await req.ctx.db.update(notifications).set({ readAt: new Date() }).where(eq(notifications.id, (req.params as { id: string }).id));
    return { ok: true };
  });
  app.post("/notifications/read-all", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    await req.ctx.db.update(notifications).set({ readAt: new Date() }).where(and(isNull(notifications.readAt), or(isNull(notifications.userId), eq(notifications.userId, req.ctx.user!.id))!));
    return { ok: true };
  });

  // Audit log (PRD sez. 36).
  app.get("/audit", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const q = z.object({ leadId: z.string().uuid().optional(), clientId: z.string().uuid().optional(), entityType: z.string().optional(), limit: z.coerce.number().max(500).optional() }).parse(req.query);
    const where = [];
    if (q.leadId) where.push(eq(auditLogs.leadId, q.leadId));
    if (q.clientId) where.push(eq(auditLogs.clientId, q.clientId));
    if (q.entityType) where.push(eq(auditLogs.entityType, q.entityType));
    return req.ctx.db
      .select({ log: auditLogs, userName: users.fullName })
      .from(auditLogs)
      .leftJoin(users, eq(users.id, auditLogs.userId))
      .where(where.length ? and(...where) : undefined)
      .orderBy(desc(auditLogs.seq))
      .limit(q.limit ?? 100)
      .then((rows) => rows.map((r) => ({ ...r.log, userName: r.userName })));
  });

  // Template di qualifica (PRD sez. 15-16): configurabili senza toccare codice.
  app.get("/qualification-templates", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => req.ctx.db.select().from(qualificationTemplates).orderBy(qualificationTemplates.vertical, qualificationTemplates.leadType));
  app.put("/qualification-templates/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const body = z.object({ name: z.string().optional(), template: z.unknown().optional(), criteria: z.unknown().optional(), scoreConfig: z.unknown().optional(), active: z.boolean().optional() }).parse(req.body);
    const id = (req.params as { id: string }).id;
    const set: Partial<typeof qualificationTemplates.$inferInsert> = { updatedAt: new Date() };
    if (body.name) set.name = body.name;
    if (body.template !== undefined) set.template = body.template as object;
    if (body.criteria !== undefined) set.criteria = body.criteria as object;
    if (body.scoreConfig !== undefined) set.scoreConfig = body.scoreConfig as object;
    if (body.active !== undefined) set.active = body.active;
    const [t] = await req.ctx.db.update(qualificationTemplates).set(set).where(eq(qualificationTemplates.id, id)).returning();
    if (!t) throw notFound("Template");
    await audit(req.ctx.db, req.ctx.user, { action: "qualification_template.updated", entityType: "qualification_template", entityId: id, summary: `Template ${t.name} aggiornato` }, req.ip);
    return t;
  });
  app.post("/qualification-templates", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ name: z.string(), vertical: z.string(), leadType: z.enum(["RESIDENTIAL", "BUSINESS"]), template: z.unknown(), criteria: z.unknown().optional(), scoreConfig: z.unknown() }).parse(req.body);
    const [t] = await req.ctx.db.insert(qualificationTemplates).values({ name: body.name, vertical: body.vertical, leadType: body.leadType, template: body.template as object, criteria: (body.criteria ?? []) as object, scoreConfig: body.scoreConfig as object }).returning();
    return reply.status(201).send(t);
  });

  // Integrazioni e mapping GHL (PRD sez. 17-18).
  app.get("/integrations", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => {
    const rows = await req.ctx.db.select().from(integrations);
    return rows.map((r) => ({ ...r, config: maskConfig(r.config as Record<string, unknown>) }));
  });
  app.post("/integrations", { preHandler: requireRole("SUPER_ADMIN") }, async (req, reply) => {
    const body = z.object({ clientId: z.string().uuid().nullish(), provider: z.string().default("ghl"), config: z.record(z.unknown()), active: z.boolean().optional() }).parse(req.body);
    const [r] = await req.ctx.db.insert(integrations).values({ clientId: body.clientId ?? null, provider: body.provider, config: body.config, active: body.active ?? true }).returning();
    await audit(req.ctx.db, req.ctx.user, { action: "integration.created", entityType: "integration", entityId: r!.id, clientId: body.clientId ?? null, summary: `Integrazione ${body.provider} configurata` }, req.ip);
    return reply.status(201).send({ ...r, config: maskConfig(r!.config as Record<string, unknown>) });
  });
  app.get("/ghl-mappings", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    const q = z.object({ clientId: z.string().uuid().optional() }).parse(req.query);
    return req.ctx.db.select().from(ghlMappings).where(q.clientId ? or(eq(ghlMappings.clientId, q.clientId), isNull(ghlMappings.clientId)) : undefined).orderBy(ghlMappings.lodField);
  });
  app.post("/ghl-mappings", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ clientId: z.string().uuid().nullish(), lodField: z.string().min(1), ghlField: z.string().min(1), kind: z.enum(["custom_field", "standard", "tag"]).optional() }).parse(req.body);
    const [m] = await req.ctx.db.insert(ghlMappings).values({ clientId: body.clientId ?? null, lodField: body.lodField, ghlField: body.ghlField, kind: body.kind ?? "custom_field" }).returning();
    return reply.status(201).send(m);
  });
  app.delete("/ghl-mappings/:id", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => {
    await req.ctx.db.delete(ghlMappings).where(eq(ghlMappings.id, (req.params as { id: string }).id));
    return { ok: true };
  });
  app.get("/webhook-events", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => req.ctx.db.select().from(webhookEvents).orderBy(desc(webhookEvents.receivedAt)).limit(100));
  app.get("/system/queue", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => queueStats(req.ctx));

  // Campagne, fonti, costi marketing.
  app.get("/campaigns", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => req.ctx.db.select().from(campaigns).orderBy(campaigns.name));
  app.post("/campaigns", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ name: z.string().min(1), platform: z.string().nullish(), externalId: z.string().nullish(), vertical: z.string().optional() }).parse(req.body);
    const [c] = await req.ctx.db.insert(campaigns).values({ name: body.name, platform: body.platform ?? null, externalId: body.externalId ?? null, vertical: body.vertical ?? "photovoltaic" }).returning();
    return reply.status(201).send(c);
  });
  app.post("/campaigns/:id/costs", { preHandler: requireRole("SUPER_ADMIN") }, async (req, reply) => {
    const body = z.object({ periodStart: z.coerce.date(), periodEnd: z.coerce.date(), amount: z.number().nonnegative(), note: z.string().nullish() }).parse(req.body);
    if (body.periodEnd < body.periodStart) throw badRequest("Periodo non valido");
    const [m] = await req.ctx.db.insert(marketingCosts).values({ campaignId: (req.params as { id: string }).id, periodStart: body.periodStart, periodEnd: body.periodEnd, amount: body.amount.toFixed(2), note: body.note ?? null }).returning();
    return reply.status(201).send(m);
  });
  app.get("/lead-sources", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => req.ctx.db.select({ id: leadSources.id, name: leadSources.name, kind: leadSources.kind, active: leadSources.active }).from(leadSources).orderBy(leadSources.name));
  app.post("/lead-sources", { preHandler: requireRole(...ADMIN_ROLES) }, async (req, reply) => {
    const body = z.object({ name: z.string().min(1), kind: z.string().min(1) }).parse(req.body);
    const [s] = await req.ctx.db.insert(leadSources).values(body).returning();
    return reply.status(201).send(s);
  });

  // Impostazioni globali (finestra duplicati, soglie di default, ...).
  app.get("/settings", { preHandler: requireRole(...ADMIN_ROLES) }, async (req) => req.ctx.db.select().from(settings));
  app.put("/settings/:key", { preHandler: requireRole("SUPER_ADMIN") }, async (req) => {
    const key = (req.params as { key: string }).key;
    const body = z.object({ value: z.unknown() }).parse(req.body);
    await req.ctx.db.insert(settings).values({ key, value: body.value as object }).onConflictDoUpdate({ target: settings.key, set: { value: body.value as object, updatedAt: new Date() } });
    await audit(req.ctx.db, req.ctx.user, { action: "settings.updated", entityType: "settings", entityId: key, summary: `Impostazione ${key} aggiornata`, details: body.value }, req.ip);
    return { key, value: body.value };
  });
}

function maskConfig(cfg: Record<string, unknown>) {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(cfg)) out[k] = /key|secret|token/i.test(k) && typeof v === "string" ? `${v.slice(0, 4)}…` : v;
  return out;
}
