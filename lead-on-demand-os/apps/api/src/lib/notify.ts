import { notifications, type DbOrTx } from "@lod/db";
import type { NotificationEvent } from "@lod/core";
import { enqueue } from "./jobs.js";

export interface NotifyInput {
  event: NotificationEvent;
  title: string;
  body?: string;
  severity?: "info" | "warning" | "critical";
  userId?: string | null;
  clientId?: string | null;
  leadId?: string | null;
  dedupeKey?: string;
}

// Notifica in-app sempre; email/Slack via job (PRD sez. 32).
export async function notify(db: DbOrTx, input: NotifyInput): Promise<void> {
  await db.insert(notifications).values({
    event: input.event,
    title: input.title,
    body: input.body ?? null,
    severity: input.severity ?? "info",
    userId: input.userId ?? null,
    clientId: input.clientId ?? null,
    leadId: input.leadId ?? null,
  });
  await enqueue(
    db,
    "notification.send",
    { event: input.event, title: input.title, body: input.body ?? null, severity: input.severity ?? "info", clientId: input.clientId ?? null, leadId: input.leadId ?? null },
    { maxAttempts: 3, dedupeKey: input.dedupeKey },
  );
}
