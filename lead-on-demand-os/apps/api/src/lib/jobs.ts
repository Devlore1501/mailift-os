import { jobs, type DbOrTx } from "@lod/db";

export interface EnqueueOptions {
  runAt?: Date;
  maxAttempts?: number;
  dedupeKey?: string;
}

// Inserisce un job nella coda persistente. Con dedupeKey l'inserimento è idempotente.
export async function enqueue(db: DbOrTx, kind: string, payload: unknown, opts: EnqueueOptions = {}): Promise<void> {
  const q = db.insert(jobs).values({
    kind,
    payload: payload as object,
    runAt: opts.runAt ?? new Date(),
    maxAttempts: opts.maxAttempts ?? 5,
    dedupeKey: opts.dedupeKey ?? null,
  });
  if (opts.dedupeKey) await q.onConflictDoNothing({ target: jobs.dedupeKey });
  else await q;
}
