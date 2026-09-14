import { and, eq } from "drizzle-orm";
import { clients, territories } from "@lod/db";
import { detectTerritoryConflict, type TerritoryLevel } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, notFound } from "../lib/errors.js";

export interface TerritoryInput {
  clientId: string;
  level: TerritoryLevel;
  value: string;
  region?: string | null;
  province?: string | null;
  exclusive?: boolean;
}

export async function createTerritory(ctx: Ctx, input: TerritoryInput) {
  const value = input.value.trim().toUpperCase();
  return ctx.db.transaction(async (tx) => {
    const client = await tx.query.clients.findFirst({ where: eq(clients.id, input.clientId) });
    if (!client) throw notFound("Cliente");
    const existing = await tx.select().from(territories).where(eq(territories.active, true));
    const names: Record<string, string> = {};
    for (const c of await tx.select({ id: clients.id, name: clients.tradeName }).from(clients)) names[c.id] = c.name;
    const candidate = { clientId: input.clientId, level: input.level, value, region: input.region?.toUpperCase() ?? null, province: input.province?.toUpperCase() ?? null, exclusive: input.exclusive ?? false };
    const c = detectTerritoryConflict(candidate, existing, names);
    if (c) throw conflict(c.message, { conflictingTerritoryId: c.conflictingTerritory.id });
    const [t] = await tx.insert(territories).values(candidate).returning();
    await audit(tx, ctx.user, { action: "territory.created", entityType: "territory", entityId: t!.id, clientId: input.clientId, summary: `Territorio ${input.level} ${value}${candidate.exclusive ? " (esclusivo)" : ""} assegnato a ${client.tradeName}` });
    return t!;
  });
}

export async function deactivateTerritory(ctx: Ctx, id: string) {
  const t = await ctx.db.query.territories.findFirst({ where: eq(territories.id, id) });
  if (!t) throw notFound("Territorio");
  await ctx.db.update(territories).set({ active: false }).where(eq(territories.id, id));
  await audit(ctx.db, ctx.user, { action: "territory.deactivated", entityType: "territory", entityId: id, clientId: t.clientId, summary: `Territorio ${t.level} ${t.value} disattivato` });
  return { ...t, active: false };
}

export async function listTerritories(ctx: Ctx, filter: { clientId?: string } = {}) {
  const where = [eq(territories.active, true)];
  if (filter.clientId) where.push(eq(territories.clientId, filter.clientId));
  const rows = await ctx.db
    .select({ t: territories, clientName: clients.tradeName })
    .from(territories)
    .innerJoin(clients, eq(clients.id, territories.clientId))
    .where(and(...where))
    .orderBy(territories.level, territories.value);
  return rows.map((r) => ({ ...r.t, clientName: r.clientName }));
}
