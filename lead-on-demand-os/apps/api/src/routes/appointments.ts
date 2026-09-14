import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { APPOINTMENT_STATUSES } from "@lod/core";
import { STAFF_ROLES, requireRole } from "../app.js";
import * as apptSvc from "../services/appointments.js";

export async function registerAppointmentRoutes(app: FastifyInstance) {
  app.get("/appointments", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const q = z.object({ clientId: z.string().uuid().optional(), from: z.coerce.date().optional(), to: z.coerce.date().optional(), status: z.enum(APPOINTMENT_STATUSES).optional() }).parse(req.query);
    return apptSvc.listAppointments(req.ctx, q);
  });
  app.post("/appointments", { preHandler: requireRole(...STAFF_ROLES) }, async (req, reply) => {
    const body = z.object({ leadId: z.string().uuid(), startsAt: z.coerce.date(), endsAt: z.coerce.date().nullish(), kind: z.string().optional(), notes: z.string().nullish() }).parse(req.body);
    return reply.status(201).send(await apptSvc.bookAppointment(req.ctx, body));
  });
  app.get("/appointments/:id", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => apptSvc.getAppointment(req.ctx, (req.params as { id: string }).id));
  app.post("/appointments/:id/status", { preHandler: requireRole(...STAFF_ROLES) }, async (req) => {
    const body = z.object({ status: z.enum(APPOINTMENT_STATUSES), startsAt: z.coerce.date().optional(), notes: z.string().nullish() }).parse(req.body);
    return apptSvc.updateAppointmentStatus(req.ctx, (req.params as { id: string }).id, body.status, body);
  });
}
