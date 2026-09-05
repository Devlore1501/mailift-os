/**
 * pv-lead-proxy — Cloudflare Worker per il funnel fotovoltaico B2C
 *
 * Riceve il lead dal quiz statico (landing/fotovoltaico/index.html) e lo smista:
 *   1. GHL  → contatto upsert, tag di qualifica, nota con tutte le risposte + stima
 *   2. Sheet → riga su Google Sheet via Apps Script webhook (nessuna OAuth da gestire)
 *   3. Meta  → evento Lead server-side, deduplicato con il pixel via event_id (opzionale)
 *
 * Stessa filosofia di ghl-form-proxy.js: il token GHL non tocca mai il browser.
 *
 * Segreti (wrangler secret put, mai committati):
 *   GHL_API_KEY       pit-... con scope contacts.write
 *   GHL_LOCATION_ID   id location GHL Mailift
 *   SHEET_WEBHOOK_URL url del web app Apps Script (vedi workers/README-fotovoltaico.md)
 *   META_PIXEL_ID     opzionale
 *   META_CAPI_TOKEN   opzionale
 *
 * Deploy:  cd workers && wrangler deploy --config wrangler-pv.toml
 */

const GHL_UPSERT_URL = 'https://services.leadconnectorhq.com/contacts/upsert';
const GHL_NOTES_URL = (id) => `https://services.leadconnectorhq.com/contacts/${id}/notes`;
const CAPI_VERSION = 'v21.0';
const MAX_LEN = 500;

/* Le risposte del quiz finiscono in una NOTA, non in custom field: la location
 * GHL non ha (ancora) campi fotovoltaico e una nota leggibile è più utile al
 * commerciale di dieci campi vuoti. Quando i campi esisteranno, mapparli qui. */
const CAMPI_NOTA = [
  ['immobile',   'Immobile'],
  ['proprieta',  'Proprietà'],
  ['tetto',      'Tetto'],
  ['bolletta',   'Bolletta/mese'],
  ['consumo',    'Consumi'],
  ['batteria',   'Batteria'],
  ['cap',        'CAP'],
  ['quando',     'Tempistica'],
];
const CAMPI_STIMA = [
  ['kwp',            'Impianto consigliato (kWp)'],
  ['zona',           'Zona irraggiamento'],
  ['consumo_kwh',    'Consumo stimato (kWh/anno)'],
  ['produzione_kwh', 'Produzione stimata (kWh/anno)'],
  ['risparmio_anno', 'Risparmio annuo (€)'],
  ['costo_netto',    'Costo netto post-detrazione (€)'],
  ['payback_anni',   'Rientro (anni)'],
];

const clean = (v) => (v === undefined || v === null ? '' : String(v).trim());

async function hash(v) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(v));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
const norm = (v) => clean(v).toLowerCase();

/** Nota leggibile: è quello che il commerciale apre prima di alzare il telefono. */
function componiNota(d) {
  const righe = [`QUIZ FOTOVOLTAICO — esito ${d.esito || 'qualificato'} · ${d.fascia || '-'} (score ${d.score ?? '-'})`, ''];
  righe.push('RISPOSTE');
  for (const [k, label] of CAMPI_NOTA) if (clean(d[k])) righe.push(`· ${label}: ${d[k]}`);
  const stima = CAMPI_STIMA.filter(([k]) => clean(d[k]) !== '');
  if (stima.length) {
    righe.push('', 'STIMA MOSTRATA AL LEAD');
    for (const [k, label] of stima) righe.push(`· ${label}: ${d[k]}`);
  }
  righe.push('', 'ATTRIBUZIONE');
  righe.push(`· Fonte: ${clean(d.utm_source) || 'diretto'}${d.utm_medium ? ' / ' + d.utm_medium : ''}`);
  if (clean(d.utm_campaign)) righe.push(`· Campagna: ${d.utm_campaign}`);
  if (clean(d.utm_content)) righe.push(`· Annuncio: ${d.utm_content}`);
  if (clean(d.referrer)) righe.push(`· Referrer: ${d.referrer}`);
  righe.push(`· Consenso ricontatto installatore: ${d.contatto_ok ? 'SÌ' : 'no'}`);
  return righe.join('\n');
}

/** Meta CAPI: stesso evento del pixel browser, dedup su event_id. No-op se non configurato. */
async function inviaCapi(env, req, d) {
  if (!env.META_PIXEL_ID || !env.META_CAPI_TOKEN || !d.email) return;
  const user = {
    em: [await hash(norm(d.email))],
    client_user_agent: req.headers.get('User-Agent') || undefined,
    client_ip_address: req.headers.get('CF-Connecting-IP') || undefined,
  };
  if (clean(d.phone)) user.ph = [await hash(clean(d.phone).replace(/\D/g, ''))];
  const parti = clean(d.full_name).split(/\s+/).filter(Boolean);
  if (parti[0]) user.fn = [await hash(norm(parti[0]))];
  if (parti.length > 1) user.ln = [await hash(norm(parti.slice(1).join(' ')))];
  if (d.fbc) user.fbc = d.fbc;
  else if (d.fbclid) user.fbc = `fb.1.${Date.now()}.${d.fbclid}`;

  const valore = d.fascia === 'HOT' ? 10 : d.fascia === 'WARM' ? 5 : 1;
  const r = await fetch(`https://graph.facebook.com/${CAPI_VERSION}/${env.META_PIXEL_ID}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      data: [{
        event_name: 'Lead',
        event_time: Math.floor(Date.now() / 1000),
        event_id: d.event_id || undefined,
        action_source: 'website',
        event_source_url: d.landing_url || undefined,
        user_data: user,
        custom_data: { currency: 'EUR', value: valore },
      }],
      access_token: env.META_CAPI_TOKEN,
      ...(env.META_TEST_CODE ? { test_event_code: env.META_TEST_CODE } : {}),
    }),
  });
  console.log(r.ok ? 'CAPI ok' : 'CAPI ko', r.status, (await r.text()).slice(0, 200));
}

/** Google Sheet via Apps Script: una riga per lead, colonne fisse. */
async function inviaSheet(env, d) {
  if (!env.SHEET_WEBHOOK_URL) { console.log('Sheet non configurato'); return; }
  const r = await fetch(env.SHEET_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ts: d.ts || new Date().toISOString(),
      nome: clean(d.full_name), email: clean(d.email), telefono: clean(d.phone),
      cap: clean(d.cap), fascia: clean(d.fascia), score: d.score ?? '',
      esito: clean(d.esito),
      immobile: clean(d.immobile), proprieta: clean(d.proprieta), tetto: clean(d.tetto),
      bolletta: clean(d.bolletta), consumo: clean(d.consumo), batteria: clean(d.batteria),
      quando: clean(d.quando),
      kwp: clean(d.kwp), risparmio_anno: clean(d.risparmio_anno),
      costo_netto: clean(d.costo_netto), payback_anni: clean(d.payback_anni),
      utm_source: clean(d.utm_source), utm_campaign: clean(d.utm_campaign),
      utm_content: clean(d.utm_content), landing_url: clean(d.landing_url),
      contatto_ok: d.contatto_ok ? 'sì' : 'no',
    }),
  });
  console.log('Sheet', r.status);
}

/** GHL: upsert contatto + nota. La nota è best-effort, non deve far fallire il lead. */
async function inviaGhl(env, d) {
  const parti = clean(d.full_name).split(/\s+/).filter(Boolean);

  const tags = ['fotovoltaico-quiz'];
  if (d.fascia) tags.push(`fv-${String(d.fascia).toLowerCase()}`);
  if (d.esito === 'non-idoneo') tags.push('fv-non-idoneo');
  if (d.esito === 'richiesta-preventivi') tags.push('fv-vuole-preventivi');
  if (clean(d.cap)) tags.push(`cap-${clean(d.cap)}`);
  if (clean(d.quando).startsWith('Il prima')) tags.push('fv-urgente');

  const payload = {
    locationId: env.GHL_LOCATION_ID,
    email: clean(d.email) || undefined,
    phone: clean(d.phone) || undefined,
    name: clean(d.full_name) || undefined,
    firstName: parti[0] || undefined,
    lastName: parti.slice(1).join(' ') || undefined,
    postalCode: clean(d.cap) || undefined,
    source: ['quiz-fotovoltaico', clean(d.utm_source) || 'diretto',
             d.utm_campaign ? `camp:${d.utm_campaign}` : '']
            .filter(Boolean).join(' · ').slice(0, MAX_LEN),
    tags,
  };

  const r = await fetch(GHL_UPSERT_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GHL_API_KEY}`,
      Version: '2021-07-28',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  const body = await r.text();
  if (!r.ok) { console.log('GHL ko', r.status, body.slice(0, 300)); return { ok: false }; }

  let contactId;
  try { contactId = JSON.parse(body)?.contact?.id; } catch (_) {}
  if (contactId) {
    const n = await fetch(GHL_NOTES_URL(contactId), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GHL_API_KEY}`,
        Version: '2021-07-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ body: componiNota(d) }),
    });
    if (!n.ok) console.log('GHL nota ko', n.status, (await n.text()).slice(0, 200));
  }
  return { ok: true, contactId };
}

export default {
  async fetch(req, env, ctx) {
    const origin = req.headers.get('Origin') || '*';
    const cors = {
      'Access-Control-Allow-Origin': origin,
      Vary: 'Origin',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (req.method !== 'POST') return json({ error: 'method' }, 405, cors);

    let d;
    try { d = await req.json(); } catch (_) { return json({ error: 'bad_json' }, 400, cors); }

    // honeypot: compilato solo dai bot → fingo ok e scarto
    if (clean(d.website)) return json({ ok: true }, 200, cors);
    if (!clean(d.email) && !clean(d.phone)) return json({ error: 'contatto_richiesto' }, 400, cors);

    // Sheet e CAPI in background: il quiz non deve aspettarli per mostrare il risultato.
    const bg = Promise.all([
      inviaSheet(env, d).catch((e) => console.log('Sheet errore:', e.message)),
      inviaCapi(env, req, d).catch((e) => console.log('CAPI errore:', e.message)),
    ]);
    if (ctx?.waitUntil) ctx.waitUntil(bg);

    let esito;
    try { esito = await inviaGhl(env, d); }
    catch (e) { console.log('GHL eccezione', e.message); return json({ error: 'upstream' }, 502, cors); }

    return json({ ok: !!esito.ok }, esito.ok ? 200 : 502, cors);
  },
};

function json(body, status, cors) {
  return new Response(JSON.stringify(body), {
    status, headers: { ...cors, 'Content-Type': 'application/json' },
  });
}
