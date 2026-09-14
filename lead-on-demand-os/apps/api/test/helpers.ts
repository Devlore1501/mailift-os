import type { FastifyInstance } from "fastify";
import { createDb, seedBase, seedDemo, type DbHandle } from "@lod/db";
import { buildApp } from "../src/app.js";
import { loadConfig } from "../src/config.js";
import { FakeGhlClient } from "../src/services/ghlClient.js";
import { buildHandlers, runJobsOnce } from "../src/services/worker.js";

export interface TestEnv {
  app: FastifyInstance;
  handle: DbHandle;
  ghl: FakeGhlClient;
  seed: Awaited<ReturnType<typeof seedDemo>>;
  tokens: { admin: string; manager: string; operator: string; client: string };
  clock: { now: Date };
  runJobs: () => Promise<{ processed: number; failed: number }>;
  api: (token: string | null, method: string, url: string, body?: unknown, headers?: Record<string, string>) => Promise<{ status: number; json: any; text: string }>;
}

export async function makeEnv(): Promise<TestEnv> {
  const handle = await createDb("pglite://memory");
  await handle.migrate();
  await seedBase(handle.db);
  const seed = await seedDemo(handle.db);
  const config = loadConfig({ JWT_SECRET: "test-secret", PUBLIC_LEAD_API_KEY: "landing-key", GHL_API_KEY: "pit-test", GHL_WEBHOOK_SECRET: "whsec" } as NodeJS.ProcessEnv);
  const ghl = new FakeGhlClient();
  const clock = { now: new Date("2026-09-14T09:00:00Z") };
  const app = await buildApp({ db: handle.db, config, ghl, now: () => clock.now });
  const api: TestEnv["api"] = async (token, method, url, body, headers = {}) => {
    const res = await app.inject({ method: method as "GET", url, payload: body === undefined ? undefined : (body as object), headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...headers } });
    let json: unknown = null;
    try {
      json = res.json();
    } catch {
      json = null;
    }
    return { status: res.statusCode, json, text: res.body };
  };
  const login = async (email: string, password: string) => (await api(null, "POST", "/auth/login", { email, password })).json.token as string;
  const tokens = {
    admin: await login("admin@leadondemand.it", "admin12345"),
    manager: await login("manager@leadondemand.it", "manager12345"),
    operator: await login("operatore@leadondemand.it", "operator12345"),
    client: await login("portale@rossiimpianti.it", "cliente12345"),
  };
  const handlers = buildHandlers({ fetchImpl: (async () => new Response("ok", { status: 200 })) as typeof fetch });
  const runJobs = () => runJobsOnce({ db: handle.db, config, ghl, user: null, now: () => clock.now }, handlers, 100);
  return { app, handle, ghl, seed, tokens, clock, runJobs, api };
}

export const QUALIFIED_ANSWERS = {
  interested: "true",
  owner: "true",
  property_type: "villa",
  roof_available: "true",
  monthly_bill: 180,
  annual_kwh: 4200,
  household_size: 4,
  heat_pump: "false",
  electric_car: "false",
  storage: "true",
  motivation: "bill",
  timeline: "lt3m",
  decision_maker: "true",
  quotes_requested: "none",
  phone_verified: "true",
};
