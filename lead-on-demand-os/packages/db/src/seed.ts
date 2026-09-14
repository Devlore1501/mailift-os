import bcrypt from "bcryptjs";
import { eq } from "drizzle-orm";
import {
  PV_BUSINESS_CRITERIA,
  PV_BUSINESS_SCORE,
  PV_BUSINESS_TEMPLATE,
  PV_RESIDENTIAL_CRITERIA,
  PV_RESIDENTIAL_SCORE,
  PV_RESIDENTIAL_TEMPLATE,
} from "@lod/core";
import { createDb, type Database } from "./client.js";
import { clientUsers, clients, counters, leadSources, packageTransactions, packages, qualificationTemplates, settings, territories, users } from "./schema.js";

// Seed di base: template di qualifica del verticale fotovoltaico + impostazioni. Idempotente.
export async function seedBase(db: Database) {
  const existing = await db.select().from(qualificationTemplates);
  if (!existing.some((t) => t.vertical === "photovoltaic" && t.leadType === "RESIDENTIAL")) {
    await db.insert(qualificationTemplates).values({
      name: "Fotovoltaico residenziale",
      vertical: "photovoltaic",
      leadType: "RESIDENTIAL",
      template: PV_RESIDENTIAL_TEMPLATE,
      criteria: PV_RESIDENTIAL_CRITERIA,
      scoreConfig: PV_RESIDENTIAL_SCORE,
    });
  }
  if (!existing.some((t) => t.vertical === "photovoltaic" && t.leadType === "BUSINESS")) {
    await db.insert(qualificationTemplates).values({
      name: "Fotovoltaico aziende",
      vertical: "photovoltaic",
      leadType: "BUSINESS",
      template: PV_BUSINESS_TEMPLATE,
      criteria: PV_BUSINESS_CRITERIA,
      scoreConfig: PV_BUSINESS_SCORE,
    });
  }
  await db.insert(settings).values({ key: "dedupe_window_days", value: 90 }).onConflictDoNothing();
  await db.insert(leadSources).values([{ name: "Landing page", kind: "landing" }, { name: "Meta Lead Ads", kind: "meta_form" }, { name: "Inserimento manuale", kind: "manual" }]).onConflictDoNothing();
}

export interface DemoSeedResult {
  adminId: string;
  managerId: string;
  operatorId: string;
  clientId: string;
  packageId: string;
  portalUserId: string;
}

// Seed demo (PRD sez. 58): Rossi Impianti, 20 lead a 200 euro, Vicenza in esclusiva.
export async function seedDemo(db: Database, passwords = { admin: "admin12345", manager: "manager12345", operator: "operator12345", client: "cliente12345" }): Promise<DemoSeedResult> {
  const existing = await db.query.users.findFirst({ where: eq(users.email, "admin@leadondemand.it") });
  if (existing) {
    const client = await db.query.clients.findFirst({ where: eq(clients.code, "CLI-0001") });
    const pkg = client ? await db.query.packages.findFirst({ where: eq(packages.clientId, client.id) }) : null;
    const manager = await db.query.users.findFirst({ where: eq(users.email, "manager@leadondemand.it") });
    const operator = await db.query.users.findFirst({ where: eq(users.email, "operatore@leadondemand.it") });
    const portal = await db.query.users.findFirst({ where: eq(users.email, "portale@rossiimpianti.it") });
    return { adminId: existing.id, managerId: manager!.id, operatorId: operator!.id, clientId: client!.id, packageId: pkg!.id, portalUserId: portal!.id };
  }
  const [admin] = await db.insert(users).values({ email: "admin@leadondemand.it", fullName: "Lorenzo (Super Admin)", role: "SUPER_ADMIN", passwordHash: await bcrypt.hash(passwords.admin, 10) }).returning();
  const [manager] = await db.insert(users).values({ email: "manager@leadondemand.it", fullName: "Fabio (Manager)", role: "MANAGER", passwordHash: await bcrypt.hash(passwords.manager, 10) }).returning();
  const [operator] = await db.insert(users).values({ email: "operatore@leadondemand.it", fullName: "Marco (Operatore)", role: "OPERATOR", passwordHash: await bcrypt.hash(passwords.operator, 10) }).returning();

  await db.insert(counters).values([{ name: "client", value: 1 }, { name: "package:PV:" + new Date().getFullYear(), value: 1 }]).onConflictDoNothing();
  const [client] = await db
    .insert(clients)
    .values({
      code: "CLI-0001",
      legalName: "Rossi Impianti Srl",
      tradeName: "Rossi Impianti",
      vatNumber: "IT01234567890",
      contactName: "Giovanni Rossi",
      phone: "+39 0444 000000",
      email: "info@rossiimpianti.it",
      address: "Via dell'Industria 12, Vicenza",
      region: "VENETO",
      vertical: "photovoltaic",
      clientType: "RESIDENTIAL",
      offerType: "PHONE_PREQUALIFIED",
      defaultLeadPrice: "200.00",
      status: "ACTIVE",
      startDate: new Date(),
      capDaily: 3,
      capWeekly: 15,
      capMonthly: 40,
      replacementSlaHours: 72,
      notificationEmail: "info@rossiimpianti.it",
    })
    .returning();
  await db.insert(territories).values([
    { clientId: client!.id, level: "PROVINCE", value: "VI", region: "VENETO", exclusive: true },
  ]);
  const [pkg] = await db
    .insert(packages)
    .values({
      code: `PV-${new Date().getFullYear()}-00001`,
      clientId: client!.id,
      productName: "Lead + prequalifica commerciale",
      offerType: "PHONE_PREQUALIFIED",
      quantity: 20,
      unitPrice: "200.00",
      totalPrice: "4000.00",
      paid: true,
      paidAt: new Date(),
      status: "ACTIVE",
      startsAt: new Date(),
    })
    .returning();
  await db.insert(packageTransactions).values({ clientId: client!.id, packageId: pkg!.id, type: "PURCHASE", quantity: 20, reason: "Acquisto pacchetto iniziale (seed)", createdBy: admin!.id });
  const [portal] = await db.insert(users).values({ email: "portale@rossiimpianti.it", fullName: "Giovanni Rossi", role: "CLIENT", passwordHash: await bcrypt.hash(passwords.client, 10) }).returning();
  await db.insert(clientUsers).values({ clientId: client!.id, userId: portal!.id });
  return { adminId: admin!.id, managerId: manager!.id, operatorId: operator!.id, clientId: client!.id, packageId: pkg!.id, portalUserId: portal!.id };
}

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop() ?? "__none__");
if (isMain) {
  const url = process.env.DATABASE_URL ?? "postgres://postgres:postgres@127.0.0.1:5432/lod_dev";
  const handle = await createDb(url);
  await handle.migrate();
  await seedBase(handle.db);
  const withDemo = process.argv.includes("--demo") || process.env.SEED_DEMO === "true";
  if (withDemo) {
    const r = await seedDemo(handle.db);
    console.log("Seed demo completato:", r);
    console.log("Accessi: admin@leadondemand.it / admin12345, manager@leadondemand.it / manager12345, operatore@leadondemand.it / operator12345, portale@rossiimpianti.it / cliente12345");
  } else {
    console.log("Seed base completato (template fotovoltaico, impostazioni, fonti). Aggiungi --demo per il cliente di esempio.");
  }
  await handle.close();
}
