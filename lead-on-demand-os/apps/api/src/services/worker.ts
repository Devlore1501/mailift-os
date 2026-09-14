import { and, eq, sql } from "drizzle-orm";
import { clients, jobs, outboundEvents } from "@lod/db";
import { createHmac } from "node:crypto";
import type { Ctx } from "../lib/context.js";
import { onGhlDeliveryDead, runGhlDelivery } from "./delivery.js";

export type JobHandler = (ctx: Ctx, payload: Record<string, unknown>) => Promise<void>;

export interface WorkerDeps {
  fetchImpl?: typeof fetch;
  log?: (msg: string, extra?: unknown) => void;
}

export function backoffMs(attempt: number): number {
  return Math.min(30_000 * 2 ** attempt, 30 * 60_000);
}

export function buildHandlers(deps: WorkerDeps = {}): Record<string, JobHandler> {
  const fetchImpl = deps.fetchImpl ?? fetch;
  const log = deps.log ?? (() => {});
  return {
    "ghl.deliver": async (ctx, payload) => {
      await runGhlDelivery(ctx, String(payload.leadId));
    },
    "webhook.dispatch": async (ctx, payload) => {
      const ev = await ctx.db.query.outboundEvents.findFirst({ where: eq(outboundEvents.id, String(payload.eventId)) });
      const client = await ctx.db.query.clients.findFirst({ where: eq(clients.id, String(payload.clientId)) });
      if (!ev || !client?.webhookUrl) return;
      const body = JSON.stringify({ id: ev.id, type: ev.eventType, createdAt: ev.createdAt, data: ev.payload });
      const headers: Record<string, string> = { "Content-Type": "application/json", "X-LOD-Event": ev.eventType, "X-LOD-Event-Id": ev.id };
      if (client.webhookSecret) headers["X-LOD-Signature"] = createHmac("sha256", client.webhookSecret).update(body).digest("hex");
      const res = await fetchImpl(client.webhookUrl, { method: "POST", headers, body });
      if (!res.ok) throw new Error(`Webhook ${client.webhookUrl} -> ${res.status}`);
    },
    "notification.send": async (ctx, payload) => {
      // Canali esterni (PRD sez. 32): Slack se configurato; email demandata a fase successiva.
      if (ctx.config.slackWebhookUrl && (payload.severity === "warning" || payload.severity === "critical")) {
        const res = await fetchImpl(ctx.config.slackWebhookUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: `[${payload.severity}] ${payload.title}${payload.body ? `\n${payload.body}` : ""}` }) });
        if (!res.ok) throw new Error(`Slack -> ${res.status}`);
      } else {
        log(`notifica: ${payload.title}`);
      }
    },
  };
}

// Esegue un giro di coda: prende i job scaduti, li lancia, gestisce retry con backoff e stato DEAD.
export async function runJobsOnce(ctx: Ctx, handlers: Record<string, JobHandler>, limit = 20): Promise<{ processed: number; failed: number }> {
  const due = await ctx.db
    .select()
    .from(jobs)
    .where(and(eq(jobs.status, "PENDING"), sql`${jobs.runAt} <= greatest(now(), ${ctx.now()})`))
    .orderBy(jobs.runAt)
    .limit(limit);
  let processed = 0;
  let failed = 0;
  for (const job of due) {
    // Lock ottimistico: solo chi riesce a passare PENDING -> RUNNING esegue il job.
    const claimed = await ctx.db
      .update(jobs)
      .set({ status: "RUNNING", attempts: job.attempts + 1, updatedAt: ctx.now() })
      .where(and(eq(jobs.id, job.id), eq(jobs.status, "PENDING")))
      .returning({ id: jobs.id });
    if (claimed.length === 0) continue;
    const handler = handlers[job.kind];
    try {
      if (!handler) throw new Error(`Handler mancante per ${job.kind}`);
      await handler(ctx, job.payload as Record<string, unknown>);
      await ctx.db.update(jobs).set({ status: "DONE", updatedAt: ctx.now() }).where(eq(jobs.id, job.id));
      processed += 1;
    } catch (e) {
      failed += 1;
      const attempts = job.attempts + 1;
      const message = (e as Error).message ?? String(e);
      if (attempts >= job.maxAttempts) {
        await ctx.db.update(jobs).set({ status: "DEAD", lastError: message, updatedAt: ctx.now() }).where(eq(jobs.id, job.id));
        if (job.kind === "ghl.deliver") await onGhlDeliveryDead(ctx, String((job.payload as { leadId: string }).leadId), message);
      } else {
        await ctx.db
          .update(jobs)
          .set({ status: "PENDING", lastError: message, runAt: new Date(ctx.now().getTime() + backoffMs(attempts)), updatedAt: ctx.now() })
          .where(eq(jobs.id, job.id));
      }
    }
  }
  return { processed, failed };
}

export async function queueStats(ctx: Ctx) {
  const rows = await ctx.db.select({ status: jobs.status, kind: jobs.kind, n: sql<number>`count(*)::int` }).from(jobs).groupBy(jobs.status, jobs.kind);
  return rows.map((r) => ({ ...r, n: Number(r.n) }));
}

export function startWorker(ctx: Ctx, handlers: Record<string, JobHandler>, intervalMs: number, log: (m: string, e?: unknown) => void) {
  let running = false;
  const timer = setInterval(async () => {
    if (running) return;
    running = true;
    try {
      const r = await runJobsOnce(ctx, handlers);
      if (r.processed || r.failed) log(`worker: ${r.processed} ok, ${r.failed} falliti`);
    } catch (e) {
      log("worker: errore nel ciclo", e);
    } finally {
      running = false;
    }
  }, intervalMs);
  return () => clearInterval(timer);
}
