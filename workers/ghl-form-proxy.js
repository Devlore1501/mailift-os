/**
 * ghl-form-proxy — Cloudflare Worker
 *
 * Proxy sicuro tra il form nativo della landing "optin-calcolatore" e l'API GHL.
 * Il form nativo (mailift.com/optin-calcolatore-page) fa una POST JSON qui;
 * il Worker crea/aggiorna il contatto in GHL via Contacts Upsert API usando il
 * token privato — che così NON è mai esposto nel codice pubblico della pagina.
 *
 * Perché esiste:
 * - il form GHL originale era un iframe cross-origin → si rompeva nel browser
 *   in-app di Instagram (25% di errori JS su iOS, fonte Microsoft Clarity).
 * - l'iframe impediva anche di sparare il pixel Meta `Lead` sulla pagina padre
 *   → Meta ottimizzava alla cieca. Col form nativo il Lead parte lato client.
 *
 * Segreti (impostati con `wrangler secret put`, mai committati):
 * - GHL_API_KEY      : Personal Integration Token (pit-...), scope contacts.write
 * - GHL_LOCATION_ID  : ID location GHL Mailift
 * - META_PIXEL_ID    : (opzionale) id del pixel — abilita la Conversions API
 * - META_CAPI_TOKEN  : (opzionale) token CAPI da Events Manager
 *
 * Conversions API: se i due secret Meta NON sono impostati il Worker si comporta
 * esattamente come prima. Nessun rischio a deployare in anticipo.
 *
 * Custom field mappato:
 * - "Per chi stai richiedendo l'analisi?" → id 7vu3LbWcBBphr9Q4LiOE
 *   valori: "Per il mio brand Ecommerce" | "Per i miei clienti"
 */

const GHL_UPSERT_URL = 'https://services.leadconnectorhq.com/contacts/upsert';
const PER_CHI_FIELD_ID = '7vu3LbWcBBphr9Q4LiOE';
// "Quale è il tuo attuale fatturato Mensile? 1" — campo RADIO.
// I valori inviati dalla landing devono combaciare CARATTERE PER CARATTERE con le
// picklistOptions configurate in GHL (en-dash U+2013; "50k –  80k" ha un doppio spazio).
// Se modifichi le option in GHL, aggiorna anche i data-value in landing/optin-calcolatore.html.
const FATTURATO_FIELD_ID = 'bW87MPPTFNr51QBtNZmG';
// Fonte di verità delle fasce: revenueOptions del quiz (EmailMarketingSurvey.tsx).
// Il quiz squalifica sotto i 10k → landing e GHL usano la stessa soglia e le stesse etichette.
const FATTURATO_SOTTO_SOGLIA = 'Meno di 10.000€/mese';

// Attribuzione. NOTA: `attributionSource` NON è scrivibile via API — GHL lo popola
// solo col proprio tracciamento e ignora in silenzio quello che gli mandi (verificato).
// Per questo gli UTM finiscono su custom field dedicati.
const UTM_FIELD_IDS = {
  utm_source: '5APJqEOKW7biksaGeJID',
  utm_medium: 'kV7HlxLjxYACKMcB5hN9',
  utm_campaign: 'HWyRvoBU4nB8SGdjkJJY',   // id campagna Meta
  utm_content: 'FFS9ENqoI2lDezkohCvt',    // id ANNUNCIO Meta
  utm_term: 'Glt7SwgUvNe68F25y55x',       // id ADSET Meta
  landing_url: 'RnarEKtTf2beKZqJBa0L',
};
const MAX_FIELD_LEN = 500;   // gli URL con fbclid sono lunghissimi

const CAPI_VERSION = 'v21.0';

/** SHA-256 esadecimale: Meta vuole i dati personali hashati, mai in chiaro. */
async function hash(valore) {
  const dati = new TextEncoder().encode(valore);
  const buf = await crypto.subtle.digest('SHA-256', dati);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** Normalizza prima di hashare: Meta confronta hash, quindi "Mario " e "mario" devono coincidere. */
const norm = (v) => (v || '').toString().trim().toLowerCase();

/**
 * Conversions API — stesso evento del pixel browser, ma dal server.
 *
 * Perché serve: il pixel lato client viene mangiato da ad blocker, ITP e dalle
 * restrizioni dei webview in-app. Con l'89% del traffico dentro Instagram e
 * Facebook è il caso peggiore. Qui l'evento parte nell'istante esatto
 * dell'opt-in, senza passare dal browser dell'utente.
 *
 * Niente doppi conteggi: `event_id` è lo stesso che la landing passa a
 * fbq(..., {eventID}), e Meta deduplica. Se il browser è bloccato resta questo;
 * se passano entrambi ne conta uno.
 */
async function inviaCapi(env, req, d, qualificato) {
  // Non configurato → no-op silenzioso: il Worker resta identico a prima.
  if (!env.META_PIXEL_ID || !env.META_CAPI_TOKEN) return;

  const user = {
    em: [await hash(norm(d.email))],
    client_user_agent: req.headers.get('User-Agent') || undefined,
    client_ip_address: req.headers.get('CF-Connecting-IP') || undefined,
  };

  const parti = (d.full_name || '').trim().split(/\s+/).filter(Boolean);
  if (parti[0]) user.fn = [await hash(norm(parti[0]))];
  if (parti.length > 1) user.ln = [await hash(norm(parti.slice(1).join(' ')))];

  if (d.fbp) user.fbp = d.fbp;
  // `_fbc` spesso NON viene scritto nei webview in-app: in quel caso lo
  // ricostruiamo dal fbclid presente nell'URL, altrimenti proprio sul traffico
  // Instagram — il grosso del nostro — l'attribuzione resterebbe debole.
  if (d.fbc) user.fbc = d.fbc;
  else if (d.fbclid) user.fbc = `fb.1.${Date.now()}.${d.fbclid}`;

  const evento = {
    event_name: 'Lead',
    event_time: Math.floor(Date.now() / 1000),
    event_id: d.event_id || undefined,      // chiave della deduplicazione
    action_source: 'website',
    event_source_url: d.landing_url || undefined,
    user_data: user,
    // Stesso valore del pixel browser: qualificato=10, sotto soglia=1.
    // Serve alla value optimization quando il volume la reggerà.
    custom_data: { currency: 'EUR', value: qualificato ? 10 : 1 },
  };

  const r = await fetch(
    `https://graph.facebook.com/${CAPI_VERSION}/${env.META_PIXEL_ID}/events`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: [evento],
        access_token: env.META_CAPI_TOKEN,
        ...(env.META_TEST_CODE ? { test_event_code: env.META_TEST_CODE } : {}),
      }),
    },
  );
  // Log SEMPRE, non solo in errore: senza, un CAPI che non parte e' invisibile
  // in `wrangler tail` e non si distingue da uno che ha funzionato.
  const risposta = (await r.text()).slice(0, 300);
  console.log(r.ok ? 'CAPI ok' : 'CAPI ko', r.status, 'event_id:', d.event_id || '(assente)', risposta);
}

export default {
  async fetch(req, env, ctx) {
    // Riflette l'Origin del chiamante: funziona su mailift.com, www.mailift.com,
    // e sui domini di preview GHL. Il CORS non protegge un form pubblico (bypassabile
    // via curl); la difesa reale è l'honeypot + upsert idempotente.
    const origin = req.headers.get('Origin') || '*';
    const cors = {
      'Access-Control-Allow-Origin': origin,
      'Vary': 'Origin',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (req.method !== 'POST') return json({ error: 'method' }, 405, cors);

    let d;
    try {
      d = await req.json();
    } catch (_) {
      return json({ error: 'bad_json' }, 400, cors);
    }

    // honeypot: campo invisibile compilato solo dai bot → scarto silenzioso (finge ok)
    if (d.website) return json({ ok: true }, 200, cors);
    if (!d.email) return json({ error: 'email_required' }, 400, cors);

    const parts = (d.full_name || '').trim().split(/\s+/).filter(Boolean);

    const customFields = [];
    if (d.per_chi) customFields.push({ id: PER_CHI_FIELD_ID, value: d.per_chi });
    if (d.fatturato) customFields.push({ id: FATTURATO_FIELD_ID, value: d.fatturato });
    for (const [chiave, id] of Object.entries(UTM_FIELD_IDS)) {
      const v = (d[chiave] || '').toString().trim();
      if (v) customFields.push({ id, value: v.slice(0, MAX_FIELD_LEN) });
    }

    // Tag di qualifica: permette di segmentare in GHL senza leggere il custom field.
    // Sotto soglia = lead reale ma non adatto al quiz (dati non attendibili sotto i 15k).
    const tags = ['calcolatore-optin'];
    if (d.fatturato) {
      tags.push(d.fatturato === FATTURATO_SOTTO_SOGLIA ? 'sotto-soglia' : 'qualificato');
    }
    if (d.ab_variant) tags.push(`ab-${d.ab_variant}`);

    // Stessa definizione della landing: agenzie mai qualificate, e senza il dato
    // sul fatturato (variante A) si assume qualificato. Se le due logiche
    // divergono, il `value` del pixel browser e quello del CAPI si contraddicono.
    const qualificato =
      d.per_chi !== 'Per i miei clienti' &&
      (d.fatturato ? d.fatturato !== FATTURATO_SOTTO_SOGLIA : true);

    // waitUntil: l'evento parte in parallelo alla scrittura su GHL e la risposta
    // non lo aspetta. L'utente viene rediretto al quiz senza un millisecondo in
    // più, e il CAPI non può comunque far fallire l'opt-in.
    if (ctx && typeof ctx.waitUntil === 'function') {
      // Il catch resta — il CAPI non deve MAI far fallire l'opt-in — ma ora
      // l'errore viene stampato: prima veniva inghiottito e in `wrangler tail`
      // un CAPI esploso era indistinguibile da uno riuscito.
      ctx.waitUntil(
        inviaCapi(env, req, d, qualificato).catch((e) =>
          console.log('CAPI eccezione:', (e && e.message) || String(e)),
        ),
      );
    } else {
      console.log('CAPI saltato: ctx.waitUntil non disponibile');
    }
    if (!env.META_PIXEL_ID || !env.META_CAPI_TOKEN) {
      console.log('CAPI non configurato: META_PIXEL_ID o META_CAPI_TOKEN mancanti');
    }

    const payload = {
      locationId: env.GHL_LOCATION_ID,
      name: d.full_name || undefined,
      firstName: parts[0] || undefined,
      lastName: parts.slice(1).join(' ') || undefined,
      email: d.email,
      phone: d.phone || undefined,
      // `source` è visibile subito sulla scheda contatto e filtrabile: ci mettiamo
      // un riassunto leggibile dell'attribuzione, così si capisce da dove arriva
      // il lead senza aprire i custom field.
      source: [
        'optin-calcolatore',
        [d.utm_source, d.utm_medium].filter(Boolean).join('/') || (d.referrer ? 'ref' : 'diretto'),
        d.utm_campaign ? `camp:${d.utm_campaign}` : '',
      ].filter(Boolean).join(' · ').slice(0, MAX_FIELD_LEN),
      tags,
      customFields,
    };

    const upsert = (p) =>
      fetch(GHL_UPSERT_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.GHL_API_KEY}`,
          Version: '2021-07-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(p),
      });

    let r;
    try {
      r = await upsert(payload);
      // Rete di sicurezza: se GHL rifiuta il payload (es. un id di custom field
      // non più valido dopo una modifica in GHL), NON perdiamo il lead — riproviamo
      // col contatto essenziale. Meglio un lead senza fatturato che nessun lead.
      if (!r.ok && customFields.length) {
        const { customFields: _drop, ...core } = payload;
        const retry = await upsert({ ...core, tags: [...tags, 'campi-custom-falliti'] });
        if (retry.ok) {
          return json({ ok: true, degraded: true }, 200, cors);
        }
      }
    } catch (_) {
      return json({ error: 'upstream_unreachable' }, 502, cors);
    }

    const body = await r.text();
    // rimando ok/ko al client; il body GHL è utile in debug ma non necessario in prod
    return new Response(r.ok ? JSON.stringify({ ok: true }) : body, {
      status: r.ok ? 200 : 502,
      headers: { ...cors, 'Content-Type': 'application/json' },
    });
  },
};

function json(body, status, cors) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  });
}
