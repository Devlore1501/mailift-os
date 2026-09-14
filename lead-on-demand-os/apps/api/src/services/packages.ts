import { and, desc, eq, sql } from "drizzle-orm";
import {
  clients,
  packageTransactions,
  packages,
  type DbOrTx,
} from "@lod/db";
import { derivePackageStatus, signedQuantity, type LedgerType, type PackageStatus } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { badRequest, conflict, notFound } from "../lib/errors.js";
import { nextPackageCode } from "../lib/codes.js";
import { notify } from "../lib/notify.js";
import { emitEvent } from "../lib/events.js";

export async function getBalance(db: DbOrTx, packageId: string): Promise<number> {
  const rows = await db
    .select({ total: sql<number>`coalesce(sum(${packageTransactions.quantity}), 0)::int` })
    .from(packageTransactions)
    .where(eq(packageTransactions.packageId, packageId));
  return Number(rows[0]?.total ?? 0);
}

export interface CreatePackageInput {
  clientId: string;
  productName: string;
  offerType?: "DIGITAL_QUALIFIED" | "PHONE_PREQUALIFIED" | "APPOINTMENT";
  quantity: number;
  unitPrice: number;
  paid?: boolean;
  paymentReference?: string | null;
  activate?: boolean; // se true e pagato: attiva subito e registra PURCHASE
  warningThreshold?: number;
  alertThreshold?: number;
  expiresAt?: Date | null;
  notes?: string | null;
}

export async function createPackage(ctx: Ctx, input: CreatePackageInput) {
  if (input.quantity <= 0) throw badRequest("La quantità deve essere positiva");
  return ctx.db.transaction(async (tx) => {
    const client = await tx.query.clients.findFirst({ where: eq(clients.id, input.clientId) });
    if (!client) throw notFound("Cliente");
    const code = await nextPackageCode(tx, client.vertical, ctx.now());
    const total = (input.quantity * input.unitPrice).toFixed(2);
    const paid = input.paid ?? false;
    const [pkg] = await tx
      .insert(packages)
      .values({
        code,
        clientId: client.id,
        productName: input.productName,
        offerType: input.offerType ?? client.offerType,
        quantity: input.quantity,
        unitPrice: input.unitPrice.toFixed(2),
        totalPrice: total,
        paid,
        paidAt: paid ? ctx.now() : null,
        paymentReference: input.paymentReference ?? null,
        status: paid ? "AWAITING_PAYMENT" : "DRAFT",
        warningThreshold: input.warningThreshold ?? 5,
        alertThreshold: input.alertThreshold ?? 3,
        expiresAt: input.expiresAt ?? null,
        notes: input.notes ?? null,
      })
      .returning();
    await audit(tx, ctx.user, {
      action: "package.created",
      entityType: "package",
      entityId: pkg!.id,
      clientId: client.id,
      summary: `Pacchetto ${code} creato per ${client.tradeName}: ${input.quantity} lead a ${input.unitPrice} euro`,
    });
    if (paid && (input.activate ?? true)) {
      await activatePackageTx(ctx, tx, pkg!.id, "Pagamento registrato alla creazione");
    }
    return loadPackageTx(tx, pkg!.id);
  });
}

async function loadPackageTx(tx: DbOrTx, id: string) {
  const pkg = await tx.query.packages.findFirst({ where: eq(packages.id, id) });
  if (!pkg) throw notFound("Pacchetto");
  const balance = await getBalance(tx, id);
  const delivered = await tx
    .select({ n: sql<number>`count(*)::int` })
    .from(packageTransactions)
    .where(and(eq(packageTransactions.packageId, id), eq(packageTransactions.type, "DELIVERY")));
  const replacements = await tx
    .select({ n: sql<number>`count(*)::int` })
    .from(packageTransactions)
    .where(and(eq(packageTransactions.packageId, id), eq(packageTransactions.type, "REPLACEMENT")));
  return { ...pkg, balance, deliveredCount: Number(delivered[0]?.n ?? 0), replacementCount: Number(replacements[0]?.n ?? 0) };
}

export async function getPackage(ctx: Ctx, id: string) {
  return loadPackageTx(ctx.db, id);
}

// Attivazione: registra il PURCHASE nel ledger e porta il pacchetto ad ACTIVE.
// Il routing verso il pacchetto parte da qui (PRD sez. 35).
export async function activatePackageTx(ctx: Ctx, tx: DbOrTx, packageId: string, reason: string) {
  const pkg = await tx.query.packages.findFirst({ where: eq(packages.id, packageId) });
  if (!pkg) throw notFound("Pacchetto");
  if (pkg.status === "ACTIVE" || pkg.status === "LOW_BALANCE" || pkg.status === "COMPLETED") {
    throw conflict("Pacchetto già attivato");
  }
  const existing = await tx
    .select({ n: sql<number>`count(*)::int` })
    .from(packageTransactions)
    .where(and(eq(packageTransactions.packageId, packageId), eq(packageTransactions.type, "PURCHASE")));
  if (Number(existing[0]?.n ?? 0) === 0) {
    await tx.insert(packageTransactions).values({
      clientId: pkg.clientId,
      packageId,
      type: "PURCHASE",
      quantity: signedQuantity("PURCHASE", pkg.quantity),
      reason,
      createdBy: ctx.user?.id ?? null,
      createdAt: ctx.now(),
    });
  }
  const balance = await getBalance(tx, packageId);
  const status = derivePackageStatus("ACTIVE", balance, { warningAt: pkg.warningThreshold, alertAt: pkg.alertThreshold });
  await tx
    .update(packages)
    .set({ status, paid: true, paidAt: pkg.paidAt ?? ctx.now(), startsAt: pkg.startsAt ?? ctx.now(), updatedAt: ctx.now() })
    .where(eq(packages.id, packageId));
  await tx.update(clients).set({ status: "ACTIVE", updatedAt: ctx.now() }).where(and(eq(clients.id, pkg.clientId), eq(clients.status, "OUT_OF_CREDIT")));
  await audit(tx, ctx.user, {
    action: "package.activated",
    entityType: "package",
    entityId: packageId,
    clientId: pkg.clientId,
    summary: `Pacchetto ${pkg.code} attivato. Credito: +${pkg.quantity} (${reason})`,
  });
}

export async function activatePackage(ctx: Ctx, packageId: string, reason = "Pagamento confermato") {
  await ctx.db.transaction((tx) => activatePackageTx(ctx, tx, packageId, reason));
  return getPackage(ctx, packageId);
}

export async function setPackageStatus(ctx: Ctx, packageId: string, status: PackageStatus, reason?: string) {
  const allowed: PackageStatus[] = ["PAUSED", "ACTIVE", "CANCELLED", "EXPIRED"];
  if (!allowed.includes(status)) throw badRequest("Stato non impostabile manualmente");
  await ctx.db.transaction(async (tx) => {
    const pkg = await tx.query.packages.findFirst({ where: eq(packages.id, packageId) });
    if (!pkg) throw notFound("Pacchetto");
    let next = status;
    if (status === "ACTIVE") {
      const purchases = await tx
        .select({ n: sql<number>`count(*)::int` })
        .from(packageTransactions)
        .where(and(eq(packageTransactions.packageId, packageId), eq(packageTransactions.type, "PURCHASE")));
      if (Number(purchases[0]?.n ?? 0) === 0) throw conflict("Il pacchetto va attivato con la registrazione del pagamento");
      const balance = await getBalance(tx, packageId);
      next = derivePackageStatus("ACTIVE", balance, { warningAt: pkg.warningThreshold, alertAt: pkg.alertThreshold });
    }
    await tx.update(packages).set({ status: next, updatedAt: ctx.now() }).where(eq(packages.id, packageId));
    await audit(tx, ctx.user, {
      action: "package.status",
      entityType: "package",
      entityId: packageId,
      clientId: pkg.clientId,
      summary: `Pacchetto ${pkg.code}: ${pkg.status} -> ${next}${reason ? ` (${reason})` : ""}`,
    });
  });
  return getPackage(ctx, packageId);
}

export interface LedgerMoveInput {
  packageId: string;
  leadId?: string | null;
  type: Exclude<LedgerType, "PURCHASE">;
  quantity: number; // valore assoluto per DELIVERY/REPLACEMENT, con segno per MANUAL_ADJUSTMENT
  reason: string;
}

// Movimento del ledger dentro una transazione con lock sul pacchetto:
// impedisce la consegna oltre il saldo anche con richieste concorrenti.
export async function applyLedgerMoveTx(ctx: Ctx, tx: DbOrTx, input: LedgerMoveInput) {
  const locked = await tx.select().from(packages).where(eq(packages.id, input.packageId)).for("update");
  const pkg = locked[0];
  if (!pkg) throw notFound("Pacchetto");
  const before = await getBalance(tx, input.packageId);
  const qty = signedQuantity(input.type, input.quantity);
  if (input.type === "DELIVERY") {
    if (!(pkg.status === "ACTIVE" || pkg.status === "LOW_BALANCE")) {
      throw conflict(`Pacchetto ${pkg.code} non attivo (${pkg.status})`);
    }
    if (before + qty < 0) throw conflict(`Pacchetto ${pkg.code} senza credito residuo`);
  }
  await tx.insert(packageTransactions).values({
    clientId: pkg.clientId,
    packageId: pkg.id,
    leadId: input.leadId ?? null,
    type: input.type,
    quantity: qty,
    reason: input.reason,
    createdBy: ctx.user?.id ?? null,
    createdAt: ctx.now(),
  });
  const after = before + qty;
  const status = derivePackageStatus(pkg.status, after, { warningAt: pkg.warningThreshold, alertAt: pkg.alertThreshold });
  await tx.update(packages).set({ status, updatedAt: ctx.now() }).where(eq(packages.id, pkg.id));
  await audit(tx, ctx.user, {
    action: "package.credit",
    entityType: "package",
    entityId: pkg.id,
    clientId: pkg.clientId,
    leadId: input.leadId ?? null,
    summary: `Credito pacchetto ${pkg.code}: ${before} -> ${after} (${input.type} ${qty > 0 ? "+" : ""}${qty}, ${input.reason})`,
    details: { before, after, type: input.type, quantity: qty },
  });
  await checkPackageAlertsTx(ctx, tx, pkg.id, after, status);
  return { before, after, status };
}

// Alert pacchetto (PRD sez. 33): warning a 5, alert commerciale a 3, stop routing a 0.
async function checkPackageAlertsTx(ctx: Ctx, tx: DbOrTx, packageId: string, balance: number, status: PackageStatus) {
  const pkg = await tx.query.packages.findFirst({ where: eq(packages.id, packageId) });
  if (!pkg) return;
  const client = await tx.query.clients.findFirst({ where: eq(clients.id, pkg.clientId) });
  const name = client?.tradeName ?? pkg.clientId;
  if (balance <= 0 && status === "COMPLETED" && !pkg.completedNotifiedAt) {
    await tx.update(packages).set({ completedNotifiedAt: ctx.now() }).where(eq(packages.id, packageId));
    await notify(tx, {
      event: "PACKAGE_COMPLETED",
      severity: "critical",
      title: `${name}: pacchetto ${pkg.code} terminato`,
      body: `Tutti i ${pkg.quantity} lead sono stati consegnati. Il routing verso questo pacchetto è bloccato. Aprire il rinnovo.`,
      clientId: pkg.clientId,
      dedupeKey: `pkg-completed:${pkg.id}`,
    });
    await emitEvent(tx, "package.completed", { clientId: pkg.clientId, data: { packageId: pkg.id, code: pkg.code } });
    // Se il cliente non ha altri pacchetti attivi, passa a OUT_OF_CREDIT.
    const others = await tx
      .select({ n: sql<number>`count(*)::int` })
      .from(packages)
      .where(and(eq(packages.clientId, pkg.clientId), sql`${packages.status} in ('ACTIVE','LOW_BALANCE')`));
    if (Number(others[0]?.n ?? 0) === 0) {
      await tx.update(clients).set({ status: "OUT_OF_CREDIT", updatedAt: ctx.now() }).where(and(eq(clients.id, pkg.clientId), eq(clients.status, "ACTIVE")));
    }
    return;
  }
  if (balance > 0 && balance <= pkg.alertThreshold && !pkg.lowBalanceNotifiedAt) {
    await tx.update(packages).set({ lowBalanceNotifiedAt: ctx.now() }).where(eq(packages.id, packageId));
    await notify(tx, {
      event: "PACKAGE_LOW_BALANCE",
      severity: "warning",
      title: `${name} ha ${balance} lead residui. Contattare per rinnovo.`,
      body: `Pacchetto ${pkg.code}: ${balance} lead residui su ${pkg.quantity}.`,
      clientId: pkg.clientId,
      dedupeKey: `pkg-low:${pkg.id}`,
    });
    await emitEvent(tx, "package.low_balance", { clientId: pkg.clientId, data: { packageId: pkg.id, code: pkg.code, balance } });
  } else if (balance > pkg.alertThreshold && balance <= pkg.warningThreshold && status === "LOW_BALANCE") {
    await notify(tx, {
      event: "PACKAGE_LOW_BALANCE",
      severity: "info",
      title: `${name}: pacchetto ${pkg.code} sotto soglia (${balance} residui)`,
      clientId: pkg.clientId,
      dedupeKey: `pkg-warn:${pkg.id}:${balance}`,
    });
  }
}

export async function manualAdjustment(ctx: Ctx, packageId: string, quantity: number, reason: string) {
  if (!Number.isInteger(quantity) || quantity === 0) throw badRequest("Quantità non valida");
  if (!reason.trim()) throw badRequest("La motivazione è obbligatoria per una rettifica manuale");
  await ctx.db.transaction((tx) => applyLedgerMoveTx(ctx, tx, { packageId, type: "MANUAL_ADJUSTMENT", quantity, reason }));
  return getPackage(ctx, packageId);
}

export async function listPackages(ctx: Ctx, filter: { clientId?: string; status?: PackageStatus } = {}) {
  const where = [];
  if (filter.clientId) where.push(eq(packages.clientId, filter.clientId));
  if (filter.status) where.push(eq(packages.status, filter.status));
  const rows = await ctx.db
    .select({
      pkg: packages,
      clientName: clients.tradeName,
      balance: sql<number>`coalesce((select sum(q.quantity) from package_transactions q where q.package_id = "packages"."id"), 0)::int`,
      deliveredCount: sql<number>`(select count(*) from package_transactions q where q.package_id = "packages"."id" and q.type = 'DELIVERY')::int`,
      replacementCount: sql<number>`(select count(*) from package_transactions q where q.package_id = "packages"."id" and q.type = 'REPLACEMENT')::int`,
    })
    .from(packages)
    .innerJoin(clients, eq(clients.id, packages.clientId))
    .where(where.length ? and(...where) : undefined)
    .orderBy(desc(packages.createdAt));
  return rows.map((r) => ({ ...r.pkg, clientName: r.clientName, balance: Number(r.balance), deliveredCount: Number(r.deliveredCount), replacementCount: Number(r.replacementCount) }));
}

export async function listTransactions(ctx: Ctx, packageId: string) {
  return ctx.db.query.packageTransactions.findMany({
    where: eq(packageTransactions.packageId, packageId),
    orderBy: desc(packageTransactions.seq),
  });
}
