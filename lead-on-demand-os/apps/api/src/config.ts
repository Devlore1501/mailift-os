export interface Config {
  port: number;
  host: string;
  databaseUrl: string;
  jwtSecret: string;
  jwtTtlSeconds: number;
  corsOrigin: string;
  ghl: {
    apiKey: string | null; // token globale (fallback quando il cliente non ha una propria integrazione)
    baseUrl: string;
    apiVersion: string;
    webhookSecret: string | null;
  };
  slackWebhookUrl: string | null;
  workerIntervalMs: number;
  autoDeliverOnAssign: boolean;
  publicLeadApiKey: string | null; // chiave per POST /leads da landing/Make/Zapier
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  return {
    port: Number(env.PORT ?? 4000),
    host: env.HOST ?? "0.0.0.0",
    databaseUrl: env.DATABASE_URL ?? "postgres://postgres:postgres@127.0.0.1:5432/lod_dev",
    jwtSecret: env.JWT_SECRET ?? "dev-secret-change-me",
    jwtTtlSeconds: Number(env.JWT_TTL_SECONDS ?? 60 * 60 * 12),
    corsOrigin: env.CORS_ORIGIN ?? "http://localhost:3000",
    ghl: {
      apiKey: env.GHL_API_KEY ?? null,
      baseUrl: env.GHL_BASE_URL ?? "https://services.leadconnectorhq.com",
      apiVersion: env.GHL_API_VERSION ?? "2021-07-28",
      webhookSecret: env.GHL_WEBHOOK_SECRET ?? null,
    },
    slackWebhookUrl: env.SLACK_WEBHOOK_URL ?? null,
    workerIntervalMs: Number(env.WORKER_INTERVAL_MS ?? 5000),
    autoDeliverOnAssign: (env.AUTO_DELIVER_ON_ASSIGN ?? "true") !== "false",
    publicLeadApiKey: env.PUBLIC_LEAD_API_KEY ?? null,
  };
}
