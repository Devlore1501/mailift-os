import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { eq } from "drizzle-orm";
import { clientUsers, users } from "@lod/db";
import { signToken, verifyPassword, hashPassword } from "../lib/auth.js";
import { unauthorized, badRequest } from "../lib/errors.js";
import { audit } from "../lib/audit.js";

export async function registerAuthRoutes(app: FastifyInstance) {
  app.post("/auth/login", async (req) => {
    const body = z.object({ email: z.string().email(), password: z.string().min(1) }).parse(req.body);
    const email = body.email.trim().toLowerCase();
    const user = await req.ctx.db.query.users.findFirst({ where: eq(users.email, email) });
    if (!user || !user.active || !(await verifyPassword(body.password, user.passwordHash))) throw unauthorized("Credenziali non valide");
    let clientId: string | null = null;
    if (user.role === "CLIENT") {
      const link = await req.ctx.db.query.clientUsers.findFirst({ where: eq(clientUsers.userId, user.id) });
      if (!link) throw unauthorized("Utente cliente non collegato a nessun cliente");
      clientId = link.clientId;
    }
    const authUser = { id: user.id, email: user.email, fullName: user.fullName, role: user.role, clientId };
    const token = await signToken(authUser, req.ctx.config.jwtSecret, req.ctx.config.jwtTtlSeconds);
    await req.ctx.db.update(users).set({ lastLoginAt: new Date() }).where(eq(users.id, user.id));
    await audit(req.ctx.db, authUser, { action: "auth.login", entityType: "user", entityId: user.id, summary: `Accesso di ${user.email}` }, req.ip);
    return { token, user: authUser };
  });

  app.get("/auth/me", async (req) => {
    if (!req.ctx.user) throw unauthorized();
    return { user: req.ctx.user };
  });

  app.post("/auth/change-password", async (req) => {
    if (!req.ctx.user) throw unauthorized();
    const body = z.object({ currentPassword: z.string(), newPassword: z.string().min(8) }).parse(req.body);
    const user = await req.ctx.db.query.users.findFirst({ where: eq(users.id, req.ctx.user.id) });
    if (!user || !(await verifyPassword(body.currentPassword, user.passwordHash))) throw badRequest("Password attuale errata");
    await req.ctx.db.update(users).set({ passwordHash: await hashPassword(body.newPassword), updatedAt: new Date() }).where(eq(users.id, user.id));
    await audit(req.ctx.db, req.ctx.user, { action: "auth.password_changed", entityType: "user", entityId: user.id, summary: "Password aggiornata" }, req.ip);
    return { ok: true };
  });
}
