import { clients, outboundEvents, type DbOrTx } from "@lod/db";
import type { OutboundEvent } from "@lod/core";
import { eq } from "drizzle-orm";
import { enqueue } from "./jobs.js";

// Registra un evento in uscita (PRD sez. 40) e, se il cliente ha un webhook configurato,
// accoda la consegna con retry.
export async function emitEvent(
  db: DbOrTx,
  eventType: OutboundEvent,
  payload: { clientId?: string | null; leadId?: string | null; data: Record<string, unknown> },
): Promise<void> {
  const rows = await db
    .insert(outboundEvents)
    .values({ eventType, clientId: payload.clientId ?? null, leadId: payload.leadId ?? null, payload: payload.data })
    .returning({ id: outboundEvents.id });
  const eventId = rows[0]!.id;
  if (!payload.clientId) return;
  const client = await db.query.clients.findFirst({ where: eq(clients.id, payload.clientId), columns: { webhookUrl: true } });
  if (client?.webhookUrl) {
    await enqueue(db, "webhook.dispatch", { eventId, clientId: payload.clientId }, { dedupeKey: `webhook:${eventId}` });
  }
}
