import { desc, eq, sql } from "drizzle-orm";
import { clientUsers, clients, users } from "@lod/db";
import type { ClientStatus, ClientType, OfferType } from "@lod/core";
import { audit } from "../lib/audit.js";
import { hashPassword } from "../lib/auth.js";
import { nextClientCode } from "../lib/codes.js";
import type { Ctx } from "../lib/context.js";
import { badRequest, conflict, notFound } from "../lib/errors.js";

export interface ClientInput {
  legalName: string;
  tradeName: string;
  vatNumber?: string | null;
  contactName?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  region?: string | null;
  website?: string | null;
  vertical?: string;
  clientType?: ClientType;
  offerType?: OfferType;
  defaultLeadPrice?: number | null;
  status?: ClientStatus;
  startDate?: Date | null;
  endDate?: Date | null;
  capDaily?: number | null;
  capWeekly?: number | null;
  capMonthly?: number | null;
  priority?: number;
  ghlLocationId?: string | null;
  ghlPipelineId?: string | null;
  ghlPipelineStageId?: string | null;
  ghlCalendarId?: string | null;
  webhookUrl?: string | null;
  webhookSecret?: string | null;
  externalCrm?: string | null;
  notificationEmail?: string | null;
  notificationPhone?: string | null;
  accountManagerUserId?: string | null;
  replacementSlaHours?: number;
  dedupeWindowDays?: number;
  criteria?: unknown[];
  notes?: string | null;
}

export async function createClient(ctx: Ctx, input: ClientInput) {
  return ctx.db.transaction(async (tx) => {
    const code = await nextClientCode(tx);
    const [c] = await tx
      .insert(clients)
      .values({ ...toRow(input), legalName: input.legalName, tradeName: input.tradeName, code })
      .returning();
    await audit(tx, ctx.user, { action: "client.created", entityType: "client", entityId: c!.id, clientId: c!.id, summary: `Cliente ${code} ${input.tradeName} creato` });
    return c!;
  });
}

function toRow(input: Partial<ClientInput>) {
  const row: Partial<typeof clients.$inferInsert> = {};
  for (const [k, v] of Object.entries(input)) {
    if (v === undefined) continue;
    if (k === "defaultLeadPrice") row.defaultLeadPrice = v == null ? null : Number(v).toFixed(2);
    else (row as Record<string, unknown>)[k] = v;
  }
  return row;
}

export async function updateClient(ctx: Ctx, id: string, input: Partial<ClientInput>) {
  const existing = await ctx.db.query.clients.findFirst({ where: eq(clients.id, id) });
  if (!existing) throw notFound("Cliente");
  await ctx.db.update(clients).set({ ...toRow(input), updatedAt: ctx.now() }).where(eq(clients.id, id));
  await audit(ctx.db, ctx.user, { action: "client.updated", entityType: "client", entityId: id, clientId: id, summary: `Cliente ${existing.tradeName} aggiornato`, details: Object.keys(input) });
  return getClient(ctx, id);
}

export async function getClient(ctx: Ctx, id: string) {
  const c = await ctx.db.query.clients.findFirst({ where: eq(clients.id, id) });
  if (!c) throw notFound("Cliente");
  const stats = (await ctx.db.execute(sql`
    select
      coalesce((select sum(q.quantity) from package_transactions q join packages p on p.id = q.package_id where p.client_id = ${id} and p.status in ('ACTIVE','LOW_BALANCE')), 0)::int as balance,
      (select count(*) from leads l where l.client_id = ${id} and l.credit_charged = true)::int as delivered,
      (select count(*) from replacement_requests r where r.client_id = ${id} and r.status = 'REQUESTED')::int as open_replacements,
      (select count(*) from packages p where p.client_id = ${id} and p.status in ('ACTIVE','LOW_BALANCE'))::int as active_packages
  `)) as unknown as { rows?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>;
  const s = (Array.isArray(stats) ? stats[0] : stats.rows?.[0]) ?? {};
  const portalUsers = await ctx.db
    .select({ id: users.id, email: users.email, fullName: users.fullName, active: users.active })
    .from(clientUsers)
    .innerJoin(users, eq(users.id, clientUsers.userId))
    .where(eq(clientUsers.clientId, id));
  return { ...c, balance: Number(s.balance ?? 0), deliveredCount: Number(s.delivered ?? 0), openReplacements: Number(s.open_replacements ?? 0), activePackages: Number(s.active_packages ?? 0), portalUsers };
}

export async function listClients(ctx: Ctx) {
  const rows = await ctx.db
    .select({
      client: clients,
      balance: sql<number>`coalesce((select sum(q.quantity) from package_transactions q join packages p on p.id = q.package_id where p.client_id = "clients"."id" and p.status in ('ACTIVE','LOW_BALANCE')), 0)::int`,
      delivered: sql<number>`(select count(*) from leads l where l.client_id = "clients"."id" and l.credit_charged = true)::int`,
    })
    .from(clients)
    .orderBy(desc(clients.createdAt));
  return rows.map((r) => ({ ...r.client, balance: Number(r.balance), deliveredCount: Number(r.delivered) }));
}

// Crea (o collega) l'utente del portale cliente.
export async function addPortalUser(ctx: Ctx, clientId: string, input: { email: string; fullName: string; password: string }) {
  if (input.password.length < 8) throw badRequest("Password di almeno 8 caratteri");
  return ctx.db.transaction(async (tx) => {
    const client = await tx.query.clients.findFirst({ where: eq(clients.id, clientId) });
    if (!client) throw notFound("Cliente");
    const email = input.email.trim().toLowerCase();
    const existing = await tx.query.users.findFirst({ where: eq(users.email, email) });
    if (existing && existing.role !== "CLIENT") throw conflict("Email già usata da un utente interno");
    let userId = existing?.id;
    if (!userId) {
      const [u] = await tx.insert(users).values({ email, fullName: input.fullName, passwordHash: await hashPassword(input.password), role: "CLIENT" }).returning();
      userId = u!.id;
    } else {
      const link = await tx.query.clientUsers.findFirst({ where: eq(clientUsers.userId, userId) });
      if (link && link.clientId !== clientId) throw conflict("Utente già collegato a un altro cliente");
    }
    await tx.insert(clientUsers).values({ clientId, userId }).onConflictDoNothing();
    await audit(tx, ctx.user, { action: "client.portal_user", entityType: "client", entityId: clientId, clientId, summary: `Utente portale ${email} collegato a ${client.tradeName}` });
    return { userId, email };
  });
}
