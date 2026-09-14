import { sql } from "drizzle-orm";
import { counters, type DbOrTx } from "@lod/db";

// Progressivi leggibili (LD-000123, CLI-0004, PV-2026-00031) tramite tabella counters con upsert atomico.
export async function nextSequence(db: DbOrTx, name: string): Promise<number> {
  const rows = await db
    .insert(counters)
    .values({ name, value: 1 })
    .onConflictDoUpdate({ target: counters.name, set: { value: sql`${counters.value} + 1` } })
    .returning({ value: counters.value });
  return rows[0]!.value;
}

export async function nextLeadCode(db: DbOrTx): Promise<string> {
  const n = await nextSequence(db, "lead");
  return `LD-${String(n).padStart(6, "0")}`;
}

export async function nextClientCode(db: DbOrTx): Promise<string> {
  const n = await nextSequence(db, "client");
  return `CLI-${String(n).padStart(4, "0")}`;
}

export async function nextPackageCode(db: DbOrTx, vertical: string, now: Date): Promise<string> {
  const prefix = vertical === "photovoltaic" ? "PV" : vertical.slice(0, 3).toUpperCase();
  const year = now.getFullYear();
  const n = await nextSequence(db, `package:${prefix}:${year}`);
  return `${prefix}-${year}-${String(n).padStart(5, "0")}`;
}
