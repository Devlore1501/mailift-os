import type { FastifyInstance } from "fastify";
import { unauthorized } from "../lib/errors.js";
import { ingestGhlEvent, type GhlInboundPayload } from "../services/webhooksIn.js";

export async function registerWebhookRoutes(app: FastifyInstance) {
  // GHL -> Lead on Demand. Protezione: segreto condiviso in header o query string.
  app.post("/webhooks/ghl", async (req, reply) => {
    const secret = req.ctx.config.ghl.webhookSecret;
    const provided = (req.headers["x-webhook-secret"] as string | undefined) ?? (req.query as { secret?: string }).secret;
    if (secret && provided !== secret) throw unauthorized("Segreto webhook non valido");
    const headerId = req.headers["x-event-id"] as string | undefined;
    const result = await ingestGhlEvent(req.ctx, (req.body ?? {}) as GhlInboundPayload, headerId);
    return reply.status(result.duplicate ? 200 : 202).send(result);
  });
}
