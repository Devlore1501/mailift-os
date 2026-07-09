# Lead Research (Pre-Discovery)

## Obiettivo
Dato nome, e almeno uno tra telefono / email / sito di un **lead nuovo**,
produrre un mini-dossier pre-call: piattaforma eCommerce, ESP già in uso,
prodotti/prezzi, presenza social, segnali pubblici rilevanti, e se il lead
è già conosciuto (GHL o knowledge graph interno).

Obiettivo pratico: che Lorenzo arrivi alla discovery call sapendo già cosa
chiedere, invece di scoprire tutto in call.

Questo workflow copre il **prima** della call. Il **dopo** (classificazione
HOT/WARM/COLD, briefing, sync GHL) resta su
[workflows/discovery_call_processing.md](discovery_call_processing.md), che
usa questo dossier come input se disponibile.

## Quando usarlo
- Trigger manuale: Lorenzo fornisce nome lead + almeno un contatto (sito,
  email o telefono), prima di una discovery call in agenda.
- Va eseguito **prima** della call, non dopo (a differenza di
  `discovery_call_processing.md`).

## Input richiesti

### Da Lorenzo
- Nome azienda o persona (obbligatorio)
- Almeno uno tra: sito web, email, telefono
- (opzionale) settore, se già noto da dove è arrivato il lead

### Tool richiesti
- `WebFetch` — lettura sito
- `WebSearch` — ricerca pubblica
- [tools/ghl_client.py](../tools/ghl_client.py) — `search_contacts_by_email`,
  `search_contacts_by_phone`, `search_contacts_by_name` (solo ricerca,
  nessuna scrittura in questo workflow)
- `graphify query "<nome lead>"` — solo se `graphify-out/graph.json` esiste
  (vedi skill `graphify`); se manca, salta questo controllo senza bloccare

## Esecuzione (sequenza)

### 1. Check storico interno (prima di tutto)

- `search_contacts_by_email` / `_by_phone` / `_by_name` su GHL → se il
  contatto esiste già, riporta subito tag, note e storico invece di
  ripartire da zero.
- `graphify query "<nome lead>"` → se il grafo lo conosce già (es. citato
  in una call di un altro cliente, in una review interna team, o è un
  ex-prospect con trigger di riapertura), riportalo.
- **Se trovato in uno dei due**: fermati e segnala subito a Lorenzo prima
  di continuare la ricerca esterna — potrebbe essere un cliente attivo,
  ex-cliente, o lead già scartato in passato. Non serve rifare la ricerca
  pubblica se lo storico interno risponde già alle domande principali.

### 2. Analisi sito web (se fornito)

Usa `WebFetch` sul sito per rilevare (dall'HTML pubblico, senza login):
- **Piattaforma eCommerce**: Shopify (`cdn.shopify.com`, `myshopify.com`
  nei redirect), WooCommerce (`wp-content/plugins/woocommerce`), Magento,
  altro
- **ESP già in uso**: script riconoscibili — `klaviyo.js`/`klaviyo.com`,
  `mailchimp`/`mc.js`, `brevo`/`sendinblue`, `activecampaign`, `omnisend`
- **Popup / exit-intent presente**: segnale di maturità marketing esistente
- **Prodotti/categorie principali** e fascia prezzo indicativa
- **Recensioni**: Judge.me, Trustpilot, Google reviews widget visibili
- **Link social** (Instagram/Facebook/TikTok) da footer/header

### 3. Ricerca pubblica (WebSearch)

- `"<nome azienda>" recensioni` — sentiment pubblico
- `"<nome azienda>" fatturato OR funding OR investimento` — segnali di
  scala, se disponibili (stampa, Registro Imprese)
- `"<nome azienda>" instagram` — stima follower/presenza se non visibile
  dal sito

### 4. Sintesi ICP fit preliminare

Compila (schema interno, non mostrarlo raw a Lorenzo):

```json
{
  "azienda": "...",
  "sito": "...",
  "piattaforma_ecommerce_rilevata": "Shopify | WooCommerce | altro | non rilevato",
  "esp_rilevato": "Klaviyo | Mailchimp | nessuno visibile | non rilevato",
  "settore_stimato": "...",
  "fascia_prezzo_prodotti": "...",
  "social_presenza": "...",
  "segnali_pubblici": ["..."],
  "gia_in_ghl": true,
  "gia_nel_grafo": false,
  "fit_icp_preliminare": "probabile HOT | probabile WARM | probabile COLD | info insufficiente"
}
```

**Importante**: è una stima PRE-call basata su dati pubblici, non una
classificazione ufficiale. La classificazione HOT/WARM/COLD definitiva
avviene solo dopo la call, con dati confermati verbalmente
(`discovery_call_processing.md`). Non promettere nulla al lead basandosi
solo su questa ricerca, e non scrivere nulla su GHL in questo step — è
un workflow di sola lettura.

### 5. Output — mini-dossier pre-call

```markdown
## Pre-call research — [Azienda]

**Contatto**: [nome] · [telefono/email/sito forniti]
**Già in GHL**: sì/no [link o ID contatto se esiste, + tag/storico rilevanti]
**Già nel knowledge graph**: sì/no [dettagli se sì]

### Sito web
- Piattaforma eCommerce: …
- ESP rilevato: …
- Prodotti/prezzo: …
- Popup / social proof: …
- Social: …

### Segnali pubblici
- …

### Fit ICP preliminare
[probabile HOT / WARM / COLD / info insufficiente] — [motivazione 1-2 righe]

### Domande utili per la call
- [2-4 domande mirate sui gap emersi dalla ricerca — es. "chiedere se il
  popup visto sul sito è quello attivo o un test A/B", "confermare se
  usano già Klaviyo o solo il tema Shopify lo suggerisce"]
```

## Edge case noti

- **Sito non raggiungibile o protetto** (Cloudflare challenge, password,
  in costruzione): segnalalo, non bloccare — procedi solo con WebSearch.
- **Nessun sito fornito**: salta lo step 2, fai solo WebSearch sul nome +
  check GHL/grafo.
- **Piattaforma/ESP non rilevabile dall'HTML statico** (sito fortemente
  JS-rendered, contenuto client-side): segnala "non rilevato", **non
  indovinare**.
- **Lead già cliente o ex-cliente** (trovato in GHL o nel grafo): ferma la
  ricerca esterna, riporta subito lo storico interno a Lorenzo prima di
  continuare — la priorità è capire perché è tornato/cosa è già successo.
- **Nome ambiguo** (comune, o coincide con altra azienda nota): segnala
  l'ambiguità invece di riportare dati sulla azienda sbagliata.

## Automazione (Make.com) — trigger su "call fissata"

Versione automatica di questo workflow, limitata ai lead che **fissano
effettivamente una call** (non tutti i lead nuovi). Trigger: stage
**"Fissata call analisi"** nella pipeline *E-commerce | Offerta Mail
Marketing* (`TlfwSKfJhZG3B44ZPNBS`, stage id
`55478c71-985a-434c-b103-5342d754685a`) — è già lo stage che oggi genera
l'evento CAPI "Schedule" verso Meta, quindi è un aggancio esistente, non
uno nuovo da inventare in GHL.

Non è disponibile un trigger istantaneo "vero" senza un server sempre
acceso a ricevere il webhook: questa versione usa **Make.com** come
ricevitore/orchestratore (invece di un webhook self-hosted), che è
comunque reattivo in pochi secondi dal momento della prenotazione.

**Non ho un connector Make in sessione**: questo scenario va costruito
manualmente nell'interfaccia Make da Lorenzo (o da chi gestisce
l'account), seguendo lo schema sotto. Se lo schema cambia, aggiornare
questa sezione per tenerla sincronizzata con lo scenario reale.

### Prerequisiti
- Account Make.com
- Account Apify + API token (nuovo — per Website Content Crawler,
  Instagram Scraper, Google Maps Scraper)
- Account Perplexity + API key (nuovo — per la ricerca pubblica
  sintetizzata allo step 7)
- `ANTHROPIC_API_KEY` (già in `.env`, riusabile — stesso usato da
  `tools/process_call.py`)
- `GHL_API_KEY` (Personal Integration Token `pit-...`) e `GHL_LOCATION_ID`
  (già in `.env`) — in Make vanno salvati come Connection/Data store, mai
  hardcoded nei moduli visibili
- Account Google già autenticato (stesso di `gcal_client.py`) per la
  generazione del PDF via Google Docs/Drive (step 9-10)

### Step 0 — GHL: aggiungere il webhook in uscita

1. GHL → Automazioni → Workflows → workflow agganciato alla pipeline
   *E-commerce | Offerta Mail Marketing*
2. Trigger: "Opportunity Stage Changed" → stage "Fissata call analisi"
3. Azione aggiuntiva: **Webhook** → URL = quello generato dal modulo 1 di
   Make (sotto) → metodo POST, payload minimo: `contact_id`, `first_name`,
   `last_name`, `email`, `phone`, `company_name`, e sito web se presente
   in un custom field

### Scenario Make.com — moduli in sequenza (v2, con Apify + PDF)

Verificati su Apify (`search-actors`): nessun Actor dedicato esiste per
**registro imprese/P.IVA italiana** né per **generazione PDF** — quelle
due parti restano fuori da Apify (vedi "Note operative" sotto per come
coprirle). Per il resto, Apify batte HTTP grezzo + Google CSE su
precisione e costo:

1. **Webhooks › Custom webhook** — riceve il payload dello step 0
2. **HTTP › Make a request** (GHL, `GET /contacts/{{1.contact_id}}`) —
   headers `Authorization: Bearer {{GHL_API_KEY}}`,
   `Version: 2021-07-28`, `Accept: application/json` — recupera tag e
   custom field già presenti sul contatto
3. **Filter** — se il contatto ha già il tag `precall-research-done`,
   ferma lo scenario qui (idempotenza: evita di rifare la ricerca se il
   workflow GHL rifira per errore o cambio stage multiplo)
4. **Apify › Run Actor** — `apify/website-content-crawler`
   (**gratuito**) sul sito del lead (da custom field GHL, se presente) →
   restituisce il contenuto del sito già pulito in markdown, non HTML
   grezzo — meno lavoro di interpretazione per il modulo Claude dopo
5. **Apify › Run Actor** — `apify/instagram-scraper`
   (~€0.0027/risultato) sull'handle Instagram, se rilevabile dal sito
   (step 4) o già noto → follower/bio/ultimi post **reali**, non stimati
6. **Apify › Run Actor** — `compass/crawler-google-places`
   (~€0.004/scheda + add-on recensioni) — cerca "nome azienda + città"
   per i lead con negozio fisico → rating, n° recensioni, categoria,
   orari. Salta questo step se il lead è puramente online
7. **HTTP › Make a request** (Perplexity Sonar API,
   `POST https://api.perplexity.ai/chat/completions`) — headers
   `Authorization: Bearer {{PERPLEXITY_API_KEY}}` — sostituisce lo step
   "Apify Google Search Scraper" v1: a differenza di uno scraper grezzo,
   Perplexity fa ricerca **e** sintesi con fonti in una chiamata sola,
   più vicino a come lavoro io con `WebSearch`. Prompt: "Cerca
   informazioni pubbliche su [azienda/nome lead]: recensioni, segnali di
   fatturato/scala, notizie stampa, presenza social — cita le fonti."
   Output: testo sintetizzato + lista fonti, passato come contesto allo
   step 8 invece di risultati SERP grezzi da interpretare
   ⚠️ **Non verificato dal vivo** (a differenza degli Actor Apify sopra,
   qui non ho un connettore per testare schema/pricing attuali — vanno
   confermati sul sito Perplexity al momento della configurazione)
8. **HTTP › Make a request** (Anthropic, `POST /v1/messages`) — headers
   `x-api-key: {{ANTHROPIC_API_KEY}}`, `anthropic-version: 2023-06-01` —
   prompt basato sulle sezioni 2-5 di questo file (analisi sito + sintesi
   ICP fit), con nome/email/telefono + output degli step 4-7
   (Apify + Perplexity) come contesto. Output: **due formati** dallo
   stesso contenuto —
   (a) markdown breve per la nota GHL, (b) blocco strutturato
   (JSON o markdown esteso) per il PDF allo step 9
9. **Google Docs › Create a document from a template** — compila un
   template Google Doc con l'output 8b (sezioni: sito, social, segnali
   pubblici, fit ICP, domande per la call — stesso schema del dossier
   manuale). Riusa l'OAuth Google già attivo nello stack Mailift (stesso
   account di `gcal_client.py`), non serve una nuova connessione
10. **Google Docs › Export to PDF** → **Google Drive › Upload/move file**
    in una cartella dedicata (es. `Lead Research/`)
11. **HTTP › Make a request** (GHL, `POST /contacts/{{1.contact_id}}/notes`)
    — body: markdown breve (step 8a) + link al PDF su Drive (step 10)
12. **HTTP › Make a request** (GHL,
    `POST /contacts/{{1.contact_id}}/tags`) — body
    `{"tags": ["precall-research-done"]}`
13. *(opzionale)* notifica (Slack/Email/Telegram) a Lorenzo quando il
    dossier è pronto, con link diretto al PDF

### Note operative

- **P.IVA/dati societari**: non coperti da Apify. Se serve automatizzare
  anche questo, va aggiunto un modulo HTTP verso un fornitore dati a
  pagamento (es. OpenAPI.it "Company Search") come step tra il 6 e il 7 —
  al momento non deciso, resta manuale (chiesta in call) finché non si
  sceglie un fornitore.
- **Il prompt Claude allo step 8 va tenuto allineato a questo file**: se
  si aggiorna la logica di ricerca/sintesi qui (sezioni 2-5), va
  aggiornato anche il prompt nello scenario Make — rischio di drift tra i
  due se non si sincronizzano insieme.
- **Nessun checkpoint umano prima della scrittura su GHL**: a differenza
  della versione manuale (dove verifico duplicati/ambiguità con Lorenzo
  prima di scrivere, come nel caso Bergamo Vini), questa versione scrive
  la nota in automatico. Il filtro allo step 3 previene solo le
  ri-esecuzioni, non i contatti duplicati/ambigui — se emerge un pattern
  di duplicati frequenti, va aggiunto un controllo esplicito
  (es. `search_contacts_by_email`/`_by_phone` prima di scrivere, invece
  di fidarsi solo del `contact_id` ricevuto dal webhook).
- **Costo stimato per esecuzione**: Website Content Crawler (gratis) +
  Instagram Scraper (pochi centesimi) + Google Maps Scraper (pochi
  centesimi, solo se negozio fisico) + 1 chiamata Perplexity (da
  confermare, generalmente centesimi/richiesta) + 1 chiamata Anthropic
  (pochi centesimi) + esecuzioni Make (dentro il piano mensile) — totale
  indicativo sotto i €0,30 per lead, da verificare con i prezzi reali
  Perplexity al momento del setup.
- **Apify in Make**: esiste un'app nativa Apify nel marketplace Make
  (oltre alla via HTTP diretta su `api.apify.com`) — usare quella se
  disponibile, semplifica l'auth (basta l'Apify API token come
  Connection, niente headers manuali).

## Apprendimenti

(Popolare con pattern ricorrenti di rilevamento tech-stack, falsi positivi
frequenti, fonti che si rivelano poco affidabili, ecc.)
