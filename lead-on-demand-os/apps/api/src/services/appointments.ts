import { and, desc, eq, gte, lte } from "drizzle-orm";
import { appointments, clients, leads } from "@lod/db";
import type { AppointmentStatus } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { notify } from "../lib/notify.js";
import { setLeadStatusTx } from "./leads.js";
import { deliverLeadTx } from "./delivery.js";

export interface BookInput {
  leadId: string;
  startsAt: Date;
  endsAt?: Date | null;
  kind?: string;
  notes?: string | null;
  calendarProvider?: string | null;
  calendarId?: string | null;
  externalId?: string | null;
}

// Fissa appuntamento (PRD sez. 20). Per l'offerta "lead + appuntamento" la consegna
// e l'addebito del credito avvengono qui.
export async function bookAppointment(ctx: Ctx, input: BookInput) {
  const id = await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, input.leadId) });
    if (!lead) throw notFound("Lead");
    if (!lead.clientId) throw conflict("Il lead non è assegnato a un cliente: assegnarlo prima di fissare l'appuntamento");
    const client = await tx.query.clients.findFirst({ where: eq(clients.id, lead.clientId) });
    const [appt] = await tx
      .insert(appointments)
      .values({
        leadId: lead.id,
        clientId: lead.clientId,
        packageId: lead.packageId,
        operatorUserId: ctx.user?.id ?? null,
        kind: input.kind ?? "SITE_VISIT",
        startsAt: input.startsAt,
        endsAt: input.endsAt ?? null,
        notes: input.notes ?? null,
        calendarProvider: input.calendarProvider ?? null,
        calendarId: input.calendarId ?? client?.ghlCalendarId ?? null,
        externalId: input.externalId ?? null,
        createdAt: ctx.now(),
        updatedAt: ctx.now(),
      })
      .returning();
    if (lead.status === "ASSIGNED" || lead.status === "DELIVERED") {
      await setLeadStatusTx(ctx, tx, lead.id, "APPOINTMENT_BOOKED", `Appuntamento fissato per ${input.startsAt.toISOString()}`);
      if (!lead.creditCharged) await deliverLeadTx(ctx, tx, lead.id);
    }
    await emitEvent(tx, "appointment.booked", { clientId: lead.clientId, leadId: lead.id, data: { appointmentId: appt!.id, leadId: lead.id, startsAt: input.startsAt.toISOString() } });
    await notify(tx, { event: "APPOINTMENT_BOOKED", title: `Appuntamento fissato per il lead ${lead.code}`, leadId: lead.id, clientId: lead.clientId, dedupeKey: `appt:${appt!.id}` });
    await audit(tx, ctx.user, { action: "appointment.booked", entityType: "appointment", entityId: appt!.id, leadId: lead.id, clientId: lead.clientId, summary: `Appuntamento ${appt!.kind} il ${input.startsAt.toISOString()} per lead ${lead.code}` });
    return appt!.id;
  });
  return getAppointment(ctx, id);
}

export async function getAppointment(ctx: Ctx, id: string) {
  const a = await ctx.db.query.appointments.findFirst({ where: eq(appointments.id, id) });
  if (!a) throw notFound("Appuntamento");
  if (ctx.user?.role === "CLIENT" && a.clientId !== ctx.user.clientId) throw notFound("Appuntamento");
  return a;
}

export async function updateAppointmentStatus(ctx: Ctx, id: string, status: AppointmentStatus, opts: { startsAt?: Date; notes?: string | null } = {}) {
  await ctx.db.transaction(async (tx) => {
    const a = await tx.query.appointments.findFirst({ where: eq(appointments.id, id) });
    if (!a) throw notFound("Appuntamento");
    if (ctx.user?.role === "CLIENT" && a.clientId !== ctx.user.clientId) throw notFound("Appuntamento");
    await tx
      .update(appointments)
      .set({ status, startsAt: opts.startsAt ?? a.startsAt, notes: opts.notes ?? a.notes, updatedAt: ctx.now() })
      .where(eq(appointments.id, id));
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, a.leadId) });
    if (status === "SHOW") await emitEvent(tx, "appointment.show", { clientId: a.clientId, leadId: a.leadId, data: { appointmentId: id } });
    if (status === "NO_SHOW") {
      await emitEvent(tx, "appointment.no_show", { clientId: a.clientId, leadId: a.leadId, data: { appointmentId: id } });
      await notify(tx, { event: "NO_SHOW", severity: "warning", title: `No-show per il lead ${lead?.code ?? a.leadId}`, leadId: a.leadId, clientId: a.clientId, dedupeKey: `noshow:${id}` });
    }
    await audit(tx, ctx.user, { action: "appointment.status", entityType: "appointment", entityId: id, leadId: a.leadId, clientId: a.clientId, summary: `Appuntamento: ${a.status} -> ${status}` });
  });
  return getAppointment(ctx, id);
}

export async function listAppointments(ctx: Ctx, filter: { clientId?: string; from?: Date; to?: Date; status?: AppointmentStatus } = {}) {
  const where = [];
  if (ctx.user?.role === "CLIENT") where.push(eq(appointments.clientId, ctx.user.clientId ?? ""));
  else if (filter.clientId) where.push(eq(appointments.clientId, filter.clientId));
  if (filter.from) where.push(gte(appointments.startsAt, filter.from));
  if (filter.to) where.push(lte(appointments.startsAt, filter.to));
  if (filter.status) where.push(eq(appointments.status, filter.status));
  const rows = await ctx.db
    .select({ appt: appointments, leadCode: leads.code, leadFirstName: leads.firstName, leadLastName: leads.lastName, leadPhone: leads.phone, clientName: clients.tradeName })
    .from(appointments)
    .innerJoin(leads, eq(leads.id, appointments.leadId))
    .innerJoin(clients, eq(clients.id, appointments.clientId))
    .where(where.length ? and(...where) : undefined)
    .orderBy(desc(appointments.startsAt));
  return rows.map((r) => ({ ...r.appt, leadCode: r.leadCode, leadName: `${r.leadFirstName ?? ""} ${r.leadLastName ?? ""}`.trim(), leadPhone: r.leadPhone, clientName: r.clientName }));
}
