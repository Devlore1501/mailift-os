import { drizzle as drizzlePg } from "drizzle-orm/node-postgres";
import { drizzle as drizzlePglite } from "drizzle-orm/pglite";
import type { PgDatabase, PgQueryResultHKT, PgTransaction } from "drizzle-orm/pg-core";
import type { ExtractTablesWithRelations } from "drizzle-orm";
import { migrate as migratePg } from "drizzle-orm/node-postgres/migrator";
import { migrate as migratePglite } from "drizzle-orm/pglite/migrator";
import { PGlite } from "@electric-sql/pglite";
import pg from "pg";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as schema from "./schema.js";

export type Schema = typeof schema;
export type Database = PgDatabase<PgQueryResultHKT, Schema, ExtractTablesWithRelations<Schema>>;
export type Transaction = PgTransaction<PgQueryResultHKT, Schema, ExtractTablesWithRelations<Schema>>;
export type DbOrTx = Database | Transaction;

export interface DbHandle {
  db: Database;
  kind: "pg" | "pglite";
  migrate: () => Promise<void>;
  close: () => Promise<void>;
}

const MIGRATIONS_FOLDER = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../migrations");

// DATABASE_URL può essere:
//  - postgres://user:pass@host:5432/db      (produzione / sviluppo con Postgres)
//  - pglite://memory                        (test e demo senza server)
//  - pglite:///percorso/cartella            (file locali, nessun server)
export async function createDb(url: string): Promise<DbHandle> {
  if (url.startsWith("pglite:")) {
    const target = url.replace(/^pglite:\/\//, "");
    const client = target === "memory" || target === "" ? new PGlite() : new PGlite(target);
    const db = drizzlePglite(client, { schema }) as unknown as Database;
    return {
      db,
      kind: "pglite",
      migrate: () => migratePglite(db as any, { migrationsFolder: MIGRATIONS_FOLDER }),
      close: () => client.close(),
    };
  }
  const pool = new pg.Pool({ connectionString: url, max: 10 });
  const db = drizzlePg(pool, { schema }) as unknown as Database;
  return {
    db,
    kind: "pg",
    migrate: () => migratePg(db as any, { migrationsFolder: MIGRATIONS_FOLDER }),
    close: () => pool.end(),
  };
}
