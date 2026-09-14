import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { makeEnv, QUALIFIED_ANSWERS, type TestEnv } from "./helpers.js";

let env: TestEnv;
beforeAll(async () => {
  env = await makeEnv();
});
afterAll(async () => {
  await env.app.close();
  await env.handle.close();
});

async function ingest(overrides: Record<string, unknown> = {}) {
  const r = await env.api(null, "POST", "/leads", {
    firstName: "Mario",
    lastName: "Rossi",
    phone: "340 123 4567",
    email: "mario.rossi@example.com",
    address: "Via Roma 1",
    municipality: "Vicenza",
    postalCode: "36100",
    province: "VI",
    region: "Veneto",
    source: "meta",
    campaignName: "PV Veneto settembre",
    utmSource: "facebook",
    attributedCost: 12.5,
    consentRecorded: true,
    ...overrides,
  }, { "x-api-key": "landing-key" });
  return r;
}

describe("flusso MVP (PRD sez. 57-58)", () => {
  let leadId: string;

  it("rifiuta l'ingresso senza API key né utente", async () => {
    const r = await env.api(null, "POST", "/leads", { phone: "3331112222" });
    expect(r.status).toBe(401);
  });

  it("acquisisce il lead, lo mette in coda operatori e registra la storia", async () => {
    const r = await ingest();
    expect(r.status).toBe(201);
    leadId = r.json.id;
    expect(r.json.code).toBe("LD-000001");
    expect(r.json.status).toBe("TO_CONTACT");
    expect(r.json.dedupeResult).toBe("UNIQUE");
    expect(r.json.phoneNormalized).toBe("+393401234567");
    expect(r.json.history.map((h: { toStatus: string }) => h.toStatus)).toEqual(["TO_CONTACT", "VALIDATING", "NEW"]);
  });

  it("scarta il duplicato per telefono senza scalare nulla", async () => {
    const r = await ingest({ phone: "+39 340 1234567", email: "altro@example.com" });
    expect(r.status).toBe(201);
    expect(r.json.dedupeResult).toBe("DUPLICATE");
    expect(r.json.status).toBe("NOT_QUALIFIED");
    expect(r.json.duplicateOfLeadId).toBe(leadId);
  });

  it("l'operatore vede la coda ma non i clienti nel dettaglio", async () => {
    const q = await env.api(env.tokens.operator, "GET", "/leads/queue");
    expect(q.status).toBe(200);
    expect(q.json.map((l: { id: string }) => l.id)).toContain(leadId);
    const pk = await env.api(env.tokens.operator, "GET", "/packages");
    expect(pk.status).toBe(403);
  });

  it("registra un tentativo senza risposta e una richiamata", async () => {
    const a = await env.api(env.tokens.operator, "POST", `/leads/${leadId}/attempt`, {});
    expect(a.json.status).toBe("ATTEMPT_1");
    expect(a.json.attempts).toBe(1);
    const cb = await env.api(env.tokens.operator, "POST", `/leads/${leadId}/callback`, { callbackAt: "2026-09-14T15:00:00Z" });
    expect(cb.json.status).toBe("CALLBACK");
  });

  it("lo script guidato propone la domanda successiva e blocca la qualifica se i criteri obbligatori mancano", async () => {
    const s0 = await env.api(env.tokens.operator, "GET", `/leads/${leadId}/qualification`);
    expect(s0.json.next.key).toBe("interested");
    const s1 = await env.api(env.tokens.operator, "PATCH", `/leads/${leadId}/answers`, { answers: { interested: "true", owner: "false" } });
    expect(s1.json.next.key).toBe("decision_maker");
    expect(s1.json.lead.status).toBe("QUALIFYING");
    const bad = await env.api(env.tokens.operator, "POST", `/leads/${leadId}/qualify`, { outcome: "QUALIFIED" });
    expect(bad.status).toBe(409);
    expect(bad.json.message).toMatch(/Proprietario/);
  });

  it("qualifica, instrada, scala il credito e mette in coda l'invio GHL", async () => {
    const s = await env.api(env.tokens.operator, "PATCH", `/leads/${leadId}/answers`, { answers: QUALIFIED_ANSWERS });
    expect(s.json.next).toBeNull();
    expect(s.json.score.score).toBe(100);
    expect(s.json.score.category).toBe("HOT");
    const q = await env.api(env.tokens.operator, "POST", `/leads/${leadId}/qualify`, { outcome: "QUALIFIED", notes: "Interessato FV + accumulo" });
    expect(q.status).toBe(200);
    expect(q.json.routing.outcome).toBe("ASSIGNED");
    expect(q.json.routing.clientName).toBe("Rossi Impianti");
    expect(q.json.lead.status).toBe("DELIVERED");
    expect(q.json.lead.creditCharged).toBe(true);
    expect(q.json.lead.clientId).toBe(env.seed.clientId);

    const pkg = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`);
    expect(pkg.json.balance).toBe(19);
    expect(pkg.json.deliveredCount).toBe(1);
    const tx = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}/transactions`);
    expect(tx.json.map((t: { type: string; quantity: number }) => [t.type, t.quantity])).toEqual([["DELIVERY", -1], ["PURCHASE", 20]]);
  });

  it("il worker invia il lead a GHL con tag, custom field e nota", async () => {
    await env.api(env.tokens.admin, "PATCH", `/clients/${env.seed.clientId}`, { ghlLocationId: "loc_rossi", ghlPipelineId: "pipe_1", ghlPipelineStageId: "stage_new" });
    await env.api(env.tokens.admin, "POST", "/ghl-mappings", { clientId: env.seed.clientId, lodField: "monthly_bill", ghlField: "cf_bolletta" });
    await env.api(env.tokens.admin, "POST", "/ghl-mappings", { clientId: env.seed.clientId, lodField: "qualification_status", ghlField: "lod-{value}", kind: "tag" });
    const r = await env.runJobs();
    expect(r.failed).toBe(0);
    expect(env.ghl.contacts).toHaveLength(1);
    const c = env.ghl.contacts[0]!;
    expect(c.auth.locationId).toBe("loc_rossi");
    expect(c.input.customFields).toEqual([{ id: "cf_bolletta", value: 180 }]);
    expect(c.input.tags).toContain("lod-HOT");
    expect(env.ghl.opportunities).toHaveLength(1);
    expect(env.ghl.notes[0]!.body).toMatch(/LD-000001/);
    const lead = await env.api(env.tokens.admin, "GET", `/leads/${leadId}`);
    expect(lead.json.ghlContactId).toBe("ghl_c_1");
    expect(lead.json.ghlSyncedAt).not.toBeNull();
  });

  it("il cliente vede il lead nel portale, ma non lead altrui né dati interni", async () => {
    const dash = await env.api(env.tokens.client, "GET", "/portal/dashboard");
    expect(dash.status).toBe(200);
    expect(dash.json.packages[0].balance).toBe(19);
    expect(dash.json.packages[0].delivered).toBe(1);
    const list = await env.api(env.tokens.client, "GET", "/portal/leads");
    expect(list.json.items).toHaveLength(1);
    expect(list.json.items[0].code).toBe("LD-000001");
    expect(list.json.items[0].attributedCost).toBeUndefined();
    const detail = await env.api(env.tokens.client, "GET", `/portal/leads/${leadId}`);
    expect(detail.json.answers.monthly_bill).toBe(180);
    expect(detail.json.replacementSla.allowed).toBe(true);
    // Accessi vietati per il ruolo CLIENT
    expect((await env.api(env.tokens.client, "GET", "/leads")).status).toBe(403);
    expect((await env.api(env.tokens.client, "GET", "/analytics")).status).toBe(403);
    expect((await env.api(env.tokens.client, "GET", `/clients/${env.seed.clientId}`)).status).toBe(403);
  });

  it("webhook GHL idempotente: appuntamento creato una sola volta, poi show e vendita", async () => {
    const payload = { event_id: "evt-1", type: "appointment.created", contact_id: "ghl_c_1", appointment: { id: "appt_1", start_time: "2026-09-16T15:30:00Z", title: "Sopralluogo" } };
    const a1 = await env.api(null, "POST", "/webhooks/ghl", payload, { "x-webhook-secret": "whsec" });
    expect(a1.status).toBe(202);
    expect(a1.json.status).toBe("PROCESSED");
    const a2 = await env.api(null, "POST", "/webhooks/ghl", payload, { "x-webhook-secret": "whsec" });
    expect(a2.status).toBe(200);
    expect(a2.json.duplicate).toBe(true);
    expect((await env.api(null, "POST", "/webhooks/ghl", payload, { "x-webhook-secret": "wrong" })).status).toBe(401);
    const appts = await env.api(env.tokens.admin, "GET", "/appointments");
    expect(appts.json).toHaveLength(1);
    expect(appts.json[0].leadCode).toBe("LD-000001");
    let lead = await env.api(env.tokens.admin, "GET", `/leads/${leadId}`);
    expect(lead.json.status).toBe("APPOINTMENT_BOOKED");

    await env.api(null, "POST", "/webhooks/ghl", { event_id: "evt-2", type: "appointment.show", contact_id: "ghl_c_1", appointment: { id: "appt_1" } }, { "x-webhook-secret": "whsec" });
    const appt = await env.api(env.tokens.admin, "GET", `/appointments/${appts.json[0].id}`);
    expect(appt.json.status).toBe("SHOW");

    // Il cliente registra l'esito dal portale.
    const out = await env.api(env.tokens.client, "POST", `/portal/leads/${leadId}/outcome`, { outcome: "QUOTE_SENT" });
    expect(out.status).toBe(200);
    // Pacchetto ancora a 19: l'appuntamento non scala un secondo credito.
    const pkg = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`);
    expect(pkg.json.balance).toBe(19);
  });

  it("replacement: il cliente richiede, l'admin approva, il credito torna a 20 e il lead resta in storico", async () => {
    // Serve un lead consegnato in stato DELIVERED: ne creiamo un secondo.
    const r = await ingest({ firstName: "Luca", lastName: "Bianchi", phone: "333 222 1111", email: "luca@example.com", address: "Via Verdi 5" });
    const id2 = r.json.id;
    await env.api(env.tokens.operator, "PATCH", `/leads/${id2}/answers`, { answers: QUALIFIED_ANSWERS });
    const q = await env.api(env.tokens.operator, "POST", `/leads/${id2}/qualify`, { outcome: "QUALIFIED" });
    expect(q.json.lead.status).toBe("DELIVERED");
    expect((await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`)).json.balance).toBe(18);

    const req = await env.api(env.tokens.client, "POST", `/portal/leads/${id2}/replacement`, { reason: "NUMBER_NOT_EXISTING", note: "Numero inesistente, provato 3 volte" });
    expect(req.status).toBe(201);
    expect(req.json.status).toBe("REQUESTED");
    const dup = await env.api(env.tokens.client, "POST", `/portal/leads/${id2}/replacement`, { reason: "OTHER" });
    expect(dup.status).toBe(409);

    const pending = await env.api(env.tokens.manager, "GET", "/replacements?status=REQUESTED");
    expect(pending.json).toHaveLength(1);
    const dec = await env.api(env.tokens.manager, "POST", `/replacements/${req.json.id}/decide`, { decision: "APPROVED", note: "Verificato" });
    expect(dec.json.status).toBe("APPROVED");
    const pkg = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`);
    expect(pkg.json.balance).toBe(19);
    expect(pkg.json.replacementCount).toBe(1);
    const lead = await env.api(env.tokens.admin, "GET", `/leads/${id2}`);
    expect(lead.json.status).toBe("REPLACEMENT_APPROVED");
    expect(lead.json.replaced).toBe(true);
  });

  it("blocca la richiesta di replacement oltre lo SLA per il cliente", async () => {
    const r = await ingest({ firstName: "Anna", lastName: "Verdi", phone: "335 999 8888", email: "anna@example.com", address: "Via Po 9" });
    await env.api(env.tokens.operator, "PATCH", `/leads/${r.json.id}/answers`, { answers: QUALIFIED_ANSWERS });
    await env.api(env.tokens.operator, "POST", `/leads/${r.json.id}/qualify`, { outcome: "QUALIFIED" });
    env.clock.now = new Date("2026-09-18T09:00:00Z"); // 4 giorni dopo, SLA 72h
    const late = await env.api(env.tokens.client, "POST", `/portal/leads/${r.json.id}/replacement`, { reason: "OTHER" });
    expect(late.status).toBe(403);
    expect(late.json.message).toMatch(/terminato/);
    // L'admin può comunque aprirla manualmente.
    const manual = await env.api(env.tokens.admin, "POST", `/leads/${r.json.id}/replacement`, { reason: "OTHER", note: "Apertura manuale fuori SLA" });
    expect(manual.status).toBe(201);
    await env.api(env.tokens.admin, "POST", `/replacements/${manual.json.id}/decide`, { decision: "REJECTED", note: "Lead corretto" });
    env.clock.now = new Date("2026-09-14T09:00:00Z");
  });

  it("il cap giornaliero sospende il cliente e il lead finisce in coda con motivazione", async () => {
    // Cap giornaliero = 3: consegnati oggi finora 3 (LD-1, LD-2, LD-3).
    const r = await ingest({ firstName: "Paolo", lastName: "Neri", phone: "347 111 2222", email: "paolo@example.com", address: "Via Dante 2" });
    await env.api(env.tokens.operator, "PATCH", `/leads/${r.json.id}/answers`, { answers: QUALIFIED_ANSWERS });
    const q = await env.api(env.tokens.operator, "POST", `/leads/${r.json.id}/qualify`, { outcome: "QUALIFIED" });
    expect(q.json.routing.outcome).toBe("WAITING_ASSIGNMENT");
    expect(q.json.routing.summary).toContain("CAP_DAILY_REACHED");
    expect(q.json.lead.status).toBe("WAITING_ASSIGNMENT");
    const waiting = await env.api(env.tokens.admin, "GET", "/routing/waiting");
    expect(waiting.json.total).toBe(1);
    expect(waiting.json.byProvince.VI).toBe(1);
    // Il giorno dopo il cap si azzera: retry della coda.
    env.clock.now = new Date("2026-09-15T09:00:00Z");
    const retry = await env.api(env.tokens.admin, "POST", "/routing/retry-queue");
    expect(retry.json[0].outcome).toBe("ASSIGNED");
  });

  it("l'esclusiva di Vicenza impedisce di assegnare la provincia a un altro cliente", async () => {
    const c2 = await env.api(env.tokens.admin, "POST", "/clients", { legalName: "Verdi Solar Srl", tradeName: "Verdi Solar", clientType: "RESIDENTIAL" });
    expect(c2.status).toBe(201);
    const t = await env.api(env.tokens.admin, "POST", "/territories", { clientId: c2.json.id, level: "PROVINCE", value: "VI" });
    expect(t.status).toBe(409);
    expect(t.json.message).toBe("Impossibile assegnare VI a Verdi Solar. Il territorio è attualmente assegnato in esclusiva a Rossi Impianti.");
    const ok = await env.api(env.tokens.admin, "POST", "/territories", { clientId: c2.json.id, level: "PROVINCE", value: "PD", region: "VENETO" });
    expect(ok.status).toBe(201);
  });

  it("a saldo zero il routing verso il pacchetto si blocca e parte l'alert", async () => {
    // Rettifica manuale per portare il saldo a 1, poi consegna un lead e verifica il blocco.
    const pkg = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`);
    const adj = await env.api(env.tokens.admin, "POST", `/packages/${env.seed.packageId}/adjust`, { quantity: -(pkg.json.balance - 1), reason: "Test saldo" });
    expect(adj.json.balance).toBe(1);
    expect(adj.json.status).toBe("LOW_BALANCE");
    env.clock.now = new Date("2026-09-16T09:00:00Z");
    const r = await ingest({ firstName: "Ultimo", lastName: "Lead", phone: "348 000 1111", email: "ultimo@example.com", address: "Via Fine 1" });
    await env.api(env.tokens.operator, "PATCH", `/leads/${r.json.id}/answers`, { answers: QUALIFIED_ANSWERS });
    const q = await env.api(env.tokens.operator, "POST", `/leads/${r.json.id}/qualify`, { outcome: "QUALIFIED" });
    expect(q.json.lead.status).toBe("DELIVERED");
    const after = await env.api(env.tokens.admin, "GET", `/packages/${env.seed.packageId}`);
    expect(after.json.balance).toBe(0);
    expect(after.json.status).toBe("COMPLETED");
    const client = await env.api(env.tokens.admin, "GET", `/clients/${env.seed.clientId}`);
    expect(client.json.status).toBe("OUT_OF_CREDIT");

    const r2 = await ingest({ firstName: "Nessuno", lastName: "Buyer", phone: "349 000 2222", email: "nessuno@example.com", address: "Via Vuota 1" });
    await env.api(env.tokens.operator, "PATCH", `/leads/${r2.json.id}/answers`, { answers: QUALIFIED_ANSWERS });
    const q2 = await env.api(env.tokens.operator, "POST", `/leads/${r2.json.id}/qualify`, { outcome: "QUALIFIED" });
    expect(q2.json.routing.outcome).toBe("WAITING_ASSIGNMENT");
    expect(q2.json.routing.summary).toEqual(expect.arrayContaining(["NO_CREDIT"]));

    const notif = await env.api(env.tokens.admin, "GET", "/notifications");
    const events = notif.json.map((n: { event: string }) => n.event);
    expect(events).toContain("PACKAGE_COMPLETED");
    expect(events).toContain("LEAD_WITHOUT_BUYER");

    // Rinnovo: nuovo pacchetto pagato -> attivazione -> la coda viene riprovata.
    const np = await env.api(env.tokens.admin, "POST", "/packages", { clientId: env.seed.clientId, productName: "Rinnovo 20 lead", quantity: 20, unitPrice: 200, paid: true });
    expect(np.status).toBe(201);
    expect(np.json.status).toBe("ACTIVE");
    expect(np.json.balance).toBe(20);
    const retry = await env.api(env.tokens.admin, "POST", "/routing/retry-queue");
    expect(retry.json.find((x: { leadId: string }) => x.leadId === r2.json.id)?.outcome).toBe("ASSIGNED");
    const c = await env.api(env.tokens.admin, "GET", `/clients/${env.seed.clientId}`);
    expect(c.json.status).toBe("ACTIVE");
  });

  it("errore GHL: retry con backoff e alert admin a tentativi esauriti", async () => {
    env.ghl.failNext = 1000;
    const before = await env.runJobs();
    expect(before.failed).toBeGreaterThan(0);
    // Avanza il tempo oltre i backoff e ripeti finché i job muoiono.
    for (let i = 0; i < 6; i++) {
      env.clock.now = new Date(env.clock.now.getTime() + 60 * 60 * 1000);
      await env.runJobs();
    }
    const queue = await env.api(env.tokens.admin, "GET", "/system/queue");
    expect(queue.json.some((q: { status: string; kind: string }) => q.status === "DEAD" && q.kind === "ghl.deliver")).toBe(true);
    const notif = await env.api(env.tokens.admin, "GET", "/notifications");
    expect(notif.json.map((n: { event: string }) => n.event)).toContain("DELIVERY_FAILED");
    const failed = await env.api(env.tokens.admin, "GET", "/leads?status=DELIVERY_FAILED");
    expect(failed.json.total).toBeGreaterThan(0);
    // Reinvio manuale: GHL torna disponibile.
    env.ghl.failNext = 0;
    const retry = await env.api(env.tokens.admin, "POST", `/leads/${failed.json.items[0].id}/ghl-retry`);
    expect(retry.json.queued).toBe(true);
    await env.runJobs();
    const lead = await env.api(env.tokens.admin, "GET", `/leads/${failed.json.items[0].id}`);
    expect(lead.json.status).toBe("DELIVERED");
  });

  it("audit log e dashboard rispondono alle cinque domande del PRD", async () => {
    const audit = await env.api(env.tokens.admin, "GET", `/audit?leadId=${leadId}`);
    const actions = audit.json.map((a: { action: string }) => a.action);
    expect(actions).toEqual(expect.arrayContaining(["lead.created", "lead.status", "package.credit", "lead.ghl_synced"]));
    const dash = await env.api(env.tokens.admin, "GET", "/analytics?from=2026-09-01T00:00:00Z&to=2026-09-30T00:00:00Z");
    expect(dash.status).toBe(200);
    expect(dash.json.leads.period).toBeGreaterThanOrEqual(7);
    expect(dash.json.leads.delivered).toBeGreaterThanOrEqual(5);
    expect(dash.json.economics.revenueRecognized).toBeGreaterThan(0);
    const mgr = await env.api(env.tokens.manager, "GET", "/analytics");
    expect(mgr.json.economics).toBeNull();
    const csv = await env.api(env.tokens.admin, "GET", "/leads/export.csv");
    expect(csv.status).toBe(200);
    expect(csv.text.split("\n")[0]).toMatch(/^code;createdAt/);
    const portalCsv = await env.api(env.tokens.client, "GET", "/portal/leads/export.csv");
    expect(portalCsv.text).not.toMatch(/attributedCost/);
  });
});
