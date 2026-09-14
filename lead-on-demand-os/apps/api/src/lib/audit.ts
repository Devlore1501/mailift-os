import { auditLogs, type DbOrTx } from "@lod/db";
import { SYSTEM_USER, type AuthUser } from "./context.js";

export interface AuditInput {
  action: string;
  entityType: string;
  entityId?: string | null;
  clientId?: string | null;
  leadId?: string | null;
  summary: string;
  details?: unknown;
}

export async function audit(db: DbOrTx, user: AuthUser | null, input: AuditInput, ip?: string): Promise<void> {
  const u = user ?? SYSTEM_USER;
  await db.insert(auditLogs).values({
    userId: u.id === SYSTEM_USER.id ? null : u.id,
    action: input.action,
    entityType: input.entityType,
    entityId: input.entityId ?? null,
    clientId: input.clientId ?? null,
    leadId: input.leadId ?? null,
    summary: input.summary,
    details: input.details === undefined ? null : (input.details as object),
    ip: ip ?? null,
  });
}
