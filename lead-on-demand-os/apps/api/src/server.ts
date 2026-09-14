import { createDb } from "@lod/db";
import { loadConfig } from "./config.js";
import { buildApp } from "./app.js";
import { HttpGhlClient } from "./services/ghlClient.js";
import { buildHandlers, startWorker } from "./services/worker.js";

const config = loadConfig();
const handle = await createDb(config.databaseUrl);
await handle.migrate();
const ghl = new HttpGhlClient(config.ghl.baseUrl, config.ghl.apiVersion);
const app = await buildApp({ db: handle.db, config, ghl });

const workerCtx = { db: handle.db, config, ghl, user: null, now: () => new Date() };
const stopWorker = startWorker(workerCtx, buildHandlers({ log: (m, e) => app.log.info({ err: e }, m) }), config.workerIntervalMs, (m, e) => app.log.info({ err: e }, m));

await app.listen({ port: config.port, host: config.host });
app.log.info(`Lead on Demand OS API su http://${config.host}:${config.port} (db: ${handle.kind})`);

const shutdown = async () => {
  stopWorker();
  await app.close();
  await handle.close();
  process.exit(0);
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
