import { createHash } from "node:crypto";
import { and, eq, or } from "drizzle-orm";
import { appointments, leads, webhookEvents } from "@lod/db";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { bookAppointment, updateAppointmentStatus } from "./appointments.js";
import { recordOutcome } from "./outcomes.js";

// Payload atteso dal webhook GHL (azione "Webhook" in un workflow, con custom data):
// {
//   "event_id": "...",                 opzionale: se assente si usa l'hash del payload
//   "type": "appointment.created" | "appointment.cancelled" | "appointment.show" | "appointment.no_show"
//         | "contact.updated" | "opportunity.updated" | "sale.won" | "sale.lost",
//   "contact_id": "...", "lead_code": "LD-000123",           uno dei due per identificare il lead
//   "appointment": { "id": "...", "start_time": "...", "end_time": "...", "title": "..." },
//   "opportunity": { "id": "...", "status": "open|won|lost", "monetary_value": 11500, "stage_name": "..." },
//   "reason": "..."
// }
export interface GhlInboundPayload {
  event_id?: string;
  id?: string;
  type?: string;
  event?: string;
  contact_id?: string;
  contactId?: string;
  lead_code?: string;
  appointment?: { id?: string; start_time?: string; startTime?: string; end_time?: string; endTime?: string; title?: string; status?: string };
  opportunity?: { id?: string; status?: string; monetary_value?: number; monetaryValue?: number; stage_name?: string; pipelineStageName?: string };
  reason?: string;
  [k: string]: unknown;
}

export function eventIdFor(payload: GhlInboundPayload, headerId?: string): string {
  if (headerId) return headerId;
  if (payload.event_id) return String(payload.event_id);
  if (payload.id) return String(payload.id);
  return "sha256:" + createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

// Ricezione idempotente (PRD sez. 54): stesso provider + external_event_id => una sola elaborazione.
export async function ingestGhlEvent(ctx: Ctx, payload: GhlInboundPayload, headerId?: string): Promise<{ status: string; eventId: string; duplicate: boolean }> {
  const externalEventId = eventIdFor(payload, headerId);
  const eventType = String(payload.type ?? payload.event ?? "unknown");
  const inserted = await ctx.db
    .insert(webhookEvents)
    .values({ provider: "ghl", externalEventId, eventType, payload: payload as object })
    .onConflictDoNothing({ target: [webhookEvents.provider, webhookEvents.externalEventId] })
    .returning({ id: webhookEvents.id });
  if (inserted.length === 0) return { status: "DUPLICATE", eventId: externalEventId, duplicate: true };
  const rowId = inserted[0]!.id;
  try {
    const result = await processGhlEvent(ctx, eventType, payload);
    await ctx.db.update(webhookEvents).set({ status: result.status, leadId: result.leadId ?? null, processedAt: ctx.now() }).where(eq(webhookEvents.id, rowId));
    return { status: result.status, eventId: externalEventId, duplicate: false };
  } catch (e) {
    await ctx.db.update(webhookEvents).set({ status: "FAILED", error: (e as Error).message, processedAt: ctx.now() }).where(eq(webhookEvents.id, rowId));
    return { status: "FAILED", eventId: externalEventId, duplicate: false };
  }
}

async function findLead(ctx: Ctx, payload: GhlInboundPayload) {
  const contactId = payload.contact_id ?? payload.contactId;
  const conds = [];
  if (payload.lead_code) conds.push(eq(leads.code, String(payload.lead_code)));
  if (contactId) conds.push(eq(leads.ghlContactId, String(contactId)));
  if (payload.opportunity?.id) conds.push(eq(leads.ghlOpportunityId, String(payload.opportunity.id)));
  if (conds.length === 0) return null;
  return ctx.db.query.leads.findFirst({ where: or(...conds) });
}

async function processGhlEvent(ctx: Ctx, eventType: string, payload: GhlInboundPayload): Promise<{ status: "PROCESSED" | "IGNORED"; leadId?: string }> {
  const lead = await findLead(ctx, payload);
  if (!lead) return { status: "IGNORED" };
  const sys = { ...ctx, user: null };
  switch (eventType) {
    case "appointment.created": {
      const a = payload.appointment ?? {};
      const start = a.start_time ?? a.startTime;
      if (!start) return { status: "IGNORED", leadId: lead.id };
      const existing = a.id ? await ctx.db.query.appointments.findFirst({ where: and(eq(appointments.calendarProvider, "ghl"), eq(appointments.externalId, String(a.id))) }) : null;
      if (existing) return { status: "IGNORED", leadId: lead.id };
      await bookAppointment(sys, { leadId: lead.id, startsAt: new Date(start), endsAt: a.end_time ?? a.endTime ? new Date((a.end_time ?? a.endTime) as string) : null, notes: a.title ?? null, calendarProvider: "ghl", externalId: a.id ? String(a.id) : null });
      return { status: "PROCESSED", leadId: lead.id };
    }
    case "appointment.cancelled":
    case "appointment.show":
    case "appointment.no_show":
    case "appointment.confirmed":
    case "appointment.rescheduled": {
      const a = payload.appointment ?? {};
      const appt = a.id
        ? await ctx.db.query.appointments.findFirst({ where: and(eq(appointments.calendarProvider, "ghl"), eq(appointments.externalId, String(a.id))) })
        : await ctx.db.query.appointments.findFirst({ where: eq(appointments.leadId, lead.id), orderBy: (t, { desc }) => desc(t.createdAt) });
      if (!appt) return { status: "IGNORED", leadId: lead.id };
      const map: Record<string, "CANCELLED" | "SHOW" | "NO_SHOW" | "CONFIRMED" | "RESCHEDULED"> = {
        "appointment.cancelled": "CANCELLED",
        "appointment.show": "SHOW",
        "appointment.no_show": "NO_SHOW",
        "appointment.confirmed": "CONFIRMED",
        "appointment.rescheduled": "RESCHEDULED",
      };
      const start = a.start_time ?? a.startTime;
      await updateAppointmentStatus(sys, appt.id, map[eventType]!, { startsAt: start ? new Date(start) : undefined });
      return { status: "PROCESSED", leadId: lead.id };
    }
    case "sale.won":
    case "sale.lost": {
      const o = payload.opportunity ?? {};
      await recordOutcome(sys, lead.id, {
        outcome: eventType === "sale.won" ? "WON" : "LOST",
        contractValue: o.monetary_value ?? o.monetaryValue ?? null,
        lostReason: payload.reason ?? null,
      });
      return { status: "PROCESSED", leadId: lead.id };
    }
    case "opportunity.updated": {
      const o = payload.opportunity ?? {};
      const status = String(o.status ?? "").toLowerCase();
      if (status === "won" || status === "lost") {
        await recordOutcome(sys, lead.id, { outcome: status === "won" ? "WON" : "LOST", contractValue: o.monetary_value ?? o.monetaryValue ?? null, lostReason: payload.reason ?? null });
        return { status: "PROCESSED", leadId: lead.id };
      }
      await audit(ctx.db, null, { action: "ghl.opportunity_updated", entityType: "lead", entityId: lead.id, leadId: lead.id, clientId: lead.clientId, summary: `GHL: opportunità aggiornata (${o.stage_name ?? o.pipelineStageName ?? (status || "-")})`, details: o });
      return { status: "PROCESSED", leadId: lead.id };
    }
    case "contact.updated": {
      await audit(ctx.db, null, { action: "ghl.contact_updated", entityType: "lead", entityId: lead.id, leadId: lead.id, clientId: lead.clientId, summary: "GHL: contatto aggiornato", details: payload });
      return { status: "PROCESSED", leadId: lead.id };
    }
    default:
      return { status: "IGNORED", leadId: lead.id };
  }
}
