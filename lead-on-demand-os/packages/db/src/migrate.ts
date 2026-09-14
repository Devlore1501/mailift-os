import { createDb } from "./client.js";

const url = process.env.DATABASE_URL ?? "postgres://postgres:postgres@127.0.0.1:5432/lod_dev";
const handle = await createDb(url);
await handle.migrate();
console.log(`Migrazioni applicate su ${handle.kind} (${url.replace(/:[^:@/]+@/, ":***@")})`);
await handle.close();
