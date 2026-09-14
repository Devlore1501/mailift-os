import { desc, eq } from "drizzle-orm";
import { leads, salesOutcomes } from "@lod/db";
import type { SalesOutcome } from "@lod/core";
import { audit } from "../lib/audit.js";
import type { Ctx } from "../lib/context.js";
import { conflict, notFound } from "../lib/errors.js";
import { emitEvent } from "../lib/events.js";
import { notify } from "../lib/notify.js";
import { setLeadStatusTx } from "./leads.js";

export interface OutcomeInput {
  outcome: SalesOutcome;
  lostReason?: string | null;
  contractValue?: number | null;
  soldAt?: Date | null;
  margin?: number | null;
  product?: string | null;
}

// Esito commerciale dal cliente (PRD sez. 26): alimenta ROI e chiude il lead su WON/LOST.
export async function recordOutcome(ctx: Ctx, leadId: string, input: OutcomeInput) {
  await ctx.db.transaction(async (tx) => {
    const lead = await tx.query.leads.findFirst({ where: eq(leads.id, leadId) });
    if (!lead) throw notFound("Lead");
    if (ctx.user?.role === "CLIENT" && lead.clientId !== ctx.user.clientId) throw notFound("Lead");
    if (!lead.clientId) throw conflict("Il lead non è assegnato a un cliente");
    await tx.insert(salesOutcomes).values({
      leadId,
      clientId: lead.clientId,
      outcome: input.outcome,
      lostReason: input.lostReason ?? null,
      contractValue: input.contractValue != null ? input.contractValue.toFixed(2) : null,
      soldAt: input.soldAt ?? (input.outcome === "WON" ? ctx.now() : null),
      margin: input.margin != null ? input.margin.toFixed(2) : null,
      product: input.product ?? null,
      reportedBy: ctx.user?.id ?? null,
      createdAt: ctx.now(),
    });
    if (input.outcome === "WON" && (lead.status === "DELIVERED" || lead.status === "REPLACEMENT_REJECTED")) {
      await setLeadStatusTx(ctx, tx, leadId, "CLOSED_WON", `Venduto: ${input.contractValue ?? "-"} euro`);
      await emitEvent(tx, "sale.won", { clientId: lead.clientId, leadId, data: { leadId, contractValue: input.contractValue ?? null } });
      await notify(tx, { event: "SALE_WON", title: `Vendita registrata sul lead ${lead.code}`, body: input.contractValue ? `Valore contratto: ${input.contractValue} euro` : undefined, leadId, clientId: lead.clientId, dedupeKey: `won:${leadId}` });
    } else if (input.outcome === "LOST" && (lead.status === "DELIVERED" || lead.status === "REPLACEMENT_REJECTED")) {
      await setLeadStatusTx(ctx, tx, leadId, "CLOSED_LOST", `Perso: ${input.lostReason ?? "-"}`);
      await emitEvent(tx, "sale.lost", { clientId: lead.clientId, leadId, data: { leadId, reason: input.lostReason ?? null } });
    }
    await audit(tx, ctx.user, { action: "outcome.recorded", entityType: "lead", entityId: leadId, leadId, clientId: lead.clientId, summary: `Esito ${input.outcome} sul lead ${lead.code}` });
  });
  return ctx.db.query.salesOutcomes.findMany({ where: eq(salesOutcomes.leadId, leadId), orderBy: desc(salesOutcomes.createdAt) });
}
