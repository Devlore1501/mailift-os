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

## Automazione — GHL + Make.com (v3, costruita e testata il 2026-07-31)

Versione automatica di questo workflow. Blueprint pronto all'import:
[tools/make_blueprints/lead_precall_research.json](../tools/make_blueprints/lead_precall_research.json).

**Cosa fa**: quando un lead prenota la call (o entra nello stage "Fissata
call analisi"), GHL manda un webhook a Make; Make scarica il sito del lead,
passa a Claude i dati del form + quello che il CRM sa già + il testo del
sito, e riscrive il dossier come **nota sul contatto GHL**, mette il tag
`precall-research-done` e avvisa Lorenzo su Telegram.

**Perché questa versione e non la v2 (Apify + Perplexity + PDF su Drive)**:
la v2 richiedeva due account nuovi a pagamento (Apify, Perplexity) e un
template Google Docs. La v3 gira con le sole chiavi già in `.env`
(`ANTHROPIC_API_KEY`, `GHL_API_KEY`, `TELEGRAM_BOT_TOKEN`) e produce lo
stesso dossier, come nota GHL invece che come PDF. Apify/Perplexity restano
un upgrade documentato in fondo, non un prerequisito.

### Prerequisiti
- Account Make.com (piano con webhook — tutti tranne il free legacy)
- `ANTHROPIC_API_KEY`, `GHL_API_KEY` (`pit-…`), `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID_LORENZO` — già in `~/.secrets/mailift/.env`
- Nessun altro account nuovo

### Struttura dello scenario (7 moduli)

| # | Modulo | Cosa fa |
|---|---|---|
| 1 | `gateway:CustomWebHook` | riceve il payload da GHL |
| 2 | HTTP GET | scarica la homepage del lead (errore → `Resume`, lo scenario continua senza contenuto sito) |
| 3 | `regexp:HTMLToText` | HTML → testo |
| 4 | HTTP POST Anthropic | genera il dossier (`claude-sonnet-5`, thinking disabilitato) |
| 5 | HTTP POST GHL | scrive la nota sul contatto |
| 6 | HTTP POST GHL | tag `precall-research-done` |
| 7 | HTTP GET Telegram | notifica a Lorenzo con link diretto al contatto (errore → `Ignore`) |

Gestione errori: solo i moduli 2 (sito) e 7 (Telegram) hanno un handler.
Su 4, 5 e 6 gli errori restano **visibili** nella cronologia Make: se Claude
o GHL falliscono voglio accorgermene, non perdere il dossier in silenzio.

### Step 1 — Import in Make
1. Nuovo scenario → `⋯` → **Import Blueprint** → carica il JSON.
2. Modulo 1: crea/seleziona il webhook, **copia l'URL** (serve allo step 2).
3. Modulo 4: header `x-api-key` → sostituisci `INSERISCI_ANTHROPIC_API_KEY`.
4. Moduli 5 e 6: header `Authorization` → `Bearer pit-…` (il `GHL_API_KEY`).
5. Modulo 7: nell'URL sostituisci `INSERISCI_TELEGRAM_BOT_TOKEN` e nel
   query param `chat_id` metti `INSERISCI_TELEGRAM_CHAT_ID`.
6. Attiva lo scenario (scheduling: **Immediately**, è instant).

### Step 2 — GHL: workflow che manda il webhook
1. GHL → Automazioni → **New Workflow**.
2. Trigger (uno o entrambi):
   - *Appointment* → calendario **Consulenza strategica**
     (`3IIFrrczXhMvLYQAL4md`), status `booked`
   - *Opportunity Stage Changed* → pipeline **E-commerce | Offerta Mail
     Marketing** (`TlfwSKfJhZG3B44ZPNBS`), stage **Fissata call analisi**
     (`55478c71-985a-434c-b103-5342d754685a`)
3. Filtro anti-doppione: condizione `Contact Tag` **does not contain**
   `precall-research-done` → altrimenti esci.
4. Azione **Webhook** → POST all'URL del modulo 1 → in **Custom Data**
   aggiungi le chiavi qui sotto (chiave a sinistra, merge field a destra).

| Chiave webhook | Merge field GHL | Compilato (su 17 lead reali) |
|---|---|---|
| `contact_id` | `{{contact.id}}` | 100% |
| `full_name` | `{{contact.name}}` | 100% |
| `company_name` | `{{contact.company_name}}` | raro |
| `email` | `{{contact.email}}` | 100% |
| `phone` | `{{contact.phone}}` | 100% |
| `sito` | `{{contact.website}}` | **53%** |
| `tipo` | `{{contact.sono_un_}}` | 41% |
| `settore` | `{{contact.in_quale_settore_sei}}` | 35% |
| `fatturato` | `{{contact.quale__il_tuo_attuale_fatturato_mensile}}` | 71% |
| `fatturato_ecom` | `{{contact.do_you_have_a_way_of_knowing_your_staff_is_calling_new_leads_within_five_minutes}}` | 35% |
| `lista` | `{{contact.grandezza_lista}}` | 35% |
| `quota_email` | `{{contact.fatturato_da_email_in_}}` | 35% |
| `frequenza` | `{{contact.frequenza_di_invio_email}}` | 29% |
| `flussi` | `{{contact.flussi_automatici_esistenti}}` | 29% |
| `responsabile_email` | `{{contact.chi_e_attualmente_responsabile_del_tuo_email_marketing}}` | 6% |
| `soddisfazione` | `{{contact.can_your_staff_send_text_message_to_leads_from_a_business_number_without_using_a_personal_phone}}` | 24% |
| `agenzia` | `{{contact.sei_gi_seguit_da_unagenzia_in_questo_momento}}` | raro |
| `budget_ads` | `{{contact.radio_2877z}}` | 29% |
| `obiettivo` | `{{contact.qual__il_tuo_obiettivo_al_momento_descrivi_in_maniera_specifica}}` | raro |
| `motivo_calcolatore` | `{{contact.per_quale_motivo_hai_scelto_di_scaricare_il_calcolatore}}` | 12% |
| `note_extra` | `{{contact.altro_che_hai_bisogno_di_dirci}}` | 29% |
| `classificazione_attuale` | `{{contact.classificazione}}` | 35% |
| `motivazione` | `{{contact.motivazione}}` | 35% |
| `azione_consigliata` | `{{contact.azione_consigliata}}` | 35% |
| `spunti_precedenti` | `{{contact.spunti_di_apertura}}` | **88%** |
| `link_report` | `{{contact.link_report_email}}` | 47% |
| `source` | `{{contact.source}}` | 100% |
| `utm_campaign` | `{{contact.utm_campaign}}` | raro |

I nomi dei campi sono brutti perché sono form GHL riciclati da vecchie
nicchie (es. "Fatturato ecommerce 1" vive dentro
`do_you_have_a_way_of_knowing_your_staff_is_calling_new_leads_within_five_minutes`):
**vanno copiati così come sono**, sono le chiavi reali della location.

5. Aggiungi in coda un'azione **Add Tag** → `precall-research-done` solo se
   preferisci l'idempotenza lato GHL invece che lato Make (il modulo 6 lo
   fa già: non serve duplicarla).
6. Pubblica il workflow, poi in Make fai **Run once** e prenota una call di
   test per far "imparare" a Make la struttura del payload.

### Step 3 (consigliato) — fallback sito dal dominio email

Il campo "Il tuo sito Web?" è compilato solo nel **29%** dei lead: senza
fallback, 7 dossier su 10 nascono ciechi sul sito. Il dominio dell'email
lo recupera quasi sempre (`info@patanegioielli.it` → `patanegioielli.it`).

**Da incollare a mano nel campo URL del modulo 2 dopo l'import** (contiene
virgolette, che l'import di Make distruggerebbe — vedi note tecniche sotto):

```
https://{{if(length(ifempty(1.sito; 1.customData.sito)) > 4; replace(ifempty(1.sito; 1.customData.sito); "/https?:\/\//"; ""); last(split(ifempty(1.email; 1.customData.email); "@")))}}
```

Sui lead con email personale (gmail, libero…) il fallback punta al sito del
provider: **è già gestito nel prompt**, Claude riconosce Gmail/Google/
Facebook/pagine parcheggio e le tratta come "sito non disponibile" invece
di scriverci sopra un'analisi finta. Verificato su un lead reale.

### Costo e performance (misurati)

- ~11k token input + ~1,7k output per lead su `claude-sonnet-5` → **~$0,06
  per lead**
- 6-7 operazioni Make per lead
- Dossier pronto in ~25-40 secondi dalla prenotazione

### Note tecniche (imparate costruendolo, non ripeterle a mano)

- **`claude-sonnet-5` ha il thinking attivo di default.** Con `max_tokens:
  2000` la risposta conteneva **solo** un blocco `thinking` e zero testo:
  `content[1]` in Make sarebbe stato il thinking, non il dossier. Nel body
  c'è `"thinking": {"type": "disabled"}` — **non toglierlo**.
- **Claude incapsula il JSON in ```json anche se glielo vieti.** Per questo
  il modulo 4 **non** restituisce JSON: restituisce il dossier markdown su
  una riga sola, con `\n` letterali al posto degli a capo e senza virgolette
  doppie. Il modulo 5 lo inserisce in `{"body": "{{4.data.content[1].text}}"}`,
  che resta JSON valido. Se un giorno il modello ci mette dentro una
  virgoletta doppia, il modulo 5 dà 400: si vede subito nella cronologia.
- **Mai virgolette dentro `{{ }}` nel body raw di un modulo HTTP.** All'import
  Make ri-parsa il body e distrugge le espressioni IML che contengono
  literal fra virgolette. Tutte le espressioni del blueprint ne sono prive
  di proposito; le due che ne hanno bisogno (fallback sito) vanno digitate
  a mano nell'interfaccia dopo l'import.
- **`ifempty(1.x; 1.customData.x)` ovunque**: GHL a seconda della versione
  mette le Custom Data del webhook al primo livello o dentro `customData`.
  Così funziona in entrambi i casi senza dover indovinare.
- **La risposta di Claude è `{{4.data.content[1].text}}`**, non `{{4.data}}`:
  gli array in Make partono da 1.
- **Il modulo HTTP v4 rifiuta gli URL senza schema o `http://`** con
  `InvalidConfigurationError: Invalid URL`. Il gestore errori `Resume` sul
  modulo 2 fa proseguire lo scenario a mani vuote invece di far saltare il
  dossier: meglio un dossier solo-form che nessun dossier.
- **Il dossier non sostituisce la classificazione ufficiale**: resta una
  stima PRE-call. HOT/WARM/COLD definitivo solo dopo la call
  (`discovery_call_processing.md`).

### Upgrade possibili (non fatti, in ordine di resa)

1. **Scrittura su custom field** (`Spunti di apertura`, `Azione Consigliata`)
   oltre alla nota: serve una seconda chiamata Claude corta che restituisca
   solo quei due valori, o un modulo Parse JSON.
2. **Instagram reale**: Actor Apify `apify/instagram-scraper`
   (~€0,003/risultato) per follower/bio/ultimi post invece di stime.
3. **PDF su Drive** (era la v2): utile solo se il dossier va condiviso fuori
   da GHL.

---

## Automazione v4 — deep research (ricerca online vera)

Blueprint: [tools/make_blueprints/lead_precall_research_deep.json](../tools/make_blueprints/lead_precall_research_deep.json).
**Non sostituisce la v3**: è uno scenario separato, più costoso e più
completo. La v3 resta la versione economica.

### Cosa aggiunge rispetto alla v3

| | v3 (base) | v4 (deep) |
|---|---|---|
| Fonti | form GHL + sito | + ricerca web + fetch di pagine |
| Titolari / soci | ✗ | ✓ nome, ruolo, da quanto |
| LinkedIn | ✗ | ✓ se pubblico |
| Premi, stampa, anniversari | ✗ | ✓ |
| Dati camerali (P.IVA, ragione sociale, sede, anno, ATECO) | ✗ | ✓ |
| Fatturato e utile pubblici | ✗ | ✓ quando disponibili |
| A cosa tengono (storia, valori, community) | ✗ | ✓ |
| Dinamiche di settore + concorrenti | ✗ | ✓ |
| Costo per lead | ~$0,06 | **~$0,45** |
| Moduli Make | 7 | 10 |

Misurato su Patanè Gioielli (lead reale in pipeline): la v4 ha tirato fuori
i **tre fratelli soci** con nome — che conferma il red flag "decisione a più
teste" già accennato nel CRM — la P.IVA con ragione sociale e sede, e il
**bilancio 2022: 600.449 € di fatturato con 4.964 € di utile netto**, cioè
margine sotto l'1%. Roba che in call scopriresti solo dopo mesi, o mai.

### ⚠️ I campi GHL arrivano con l'ETICHETTA, non con nomi tecnici

Scoperto leggendo l'export reale dello scenario (31/07/2026). Il webhook GHL
manda i custom field usando **il nome del campo per esteso**, al primo
livello del payload, e `customData` resta vuoto. Quindi si scrive:

```
{{encodeURL(1.`Quale è il tuo attuale fatturato Mensile? 1`)}}
```

non `{{1.fatturato}}`. I backtick servono per i nomi con spazi e punti
interrogativi, e sono **sicuri all'import** (a differenza delle virgolette).

Nel primo scenario in produzione **21 riferimenti su 27 puntavano a nomi
inventati** e risolvevano vuoti: il dossier veniva generato su 5 campi invece
che su 25, e il sito non veniva mai scaricato (`1.website` non esiste nel
payload: il campo si chiama `Il tuo sito Web?`). Da qui in avanti i
riferimenti vanno presi **dall'`interface` del modulo webhook** dopo un run
di test, non inventati.

Attenzione ai nomi con lo spazio finale: `Dimensione lista email ` ce l'ha.

### La nota la scrive il modulo nativo GoHighLevel, non HTTP

Nello scenario reale il modulo `highlevel:addNotetoContact` (connessione
OAuth GHL + userId Lorenzo) ha sostituito la POST HTTP. È meglio: Make
costruisce lui la richiesta, quindi **tutto il problema dell'escaping JSON
sparisce**. Conseguenze pratiche:

- niente più dossier «su una riga sola con \n al posto degli a capo»
- niente più prefill e `stop_sequences`
- il modulo 7 può stare su `claude-sonnet-5` e produrre markdown normale,
  che nella nota GHL si legge molto meglio
- il corpo della nota è `{{7.data.content[].text}}`

La versione con prefill descritta più sotto resta valida **solo** se un
giorno si torna a scrivere la nota via HTTP grezzo.

### Architettura: due chiamate Claude, non una

1. **Modulo 4 — ricerca** (`claude-sonnet-5` + `web_search` + `web_fetch`):
   fa 5 ricerche e 2 fetch, restituisce materiale grezzo con fonti. Nessun
   vincolo di formato.
2. **Moduli 5-6 — iterator + text aggregator**: ricompongono la risposta.
3. **Modulo 7 — scrittura** (`claude-sonnet-4-5`, nessun tool): trasforma il
   materiale nel dossier, in un blocco solo e già JSON-safe.

Perché separate: con la ricerca web attiva la risposta arriva **spezzata in
~47 blocchi** (le citazioni frammentano il testo) e il modello commenta tra
una ricerca e l'altra. Impossibile prendere il dossier con un riferimento
fisso. La seconda chiamata riporta l'output a un blocco unico, prevedibile.

### Il trucco che rende il JSON indistruttibile

Il modulo 7 usa il **prefill**: l'ultimo messaggio è un turno `assistant`
che vale `{"body": "` e la richiesta ha `stop_sequences: ["\"}"]`. Il
modello riprende **da dentro una stringa JSON**, quindi escapa gli a capo
come `\n` da solo, senza doverglielo chiedere a parole. Misurato: 5.176
caratteri di dossier, **zero a capo reali**, payload valido al primo colpo.

Nella v3 l'istruzione a parole («scrivi tutto su una riga») reggeva su
dossier corti ma **saltava su quelli lunghi**: 35 a capo reali → il modulo
nota andava in 400.

⚠️ **Il prefill non è supportato da `claude-sonnet-5` né da `claude-opus-4-6`**
(errore 400: *This model does not support assistant message prefill*).
Funziona su `claude-sonnet-4-5` e `claude-haiku-4-5`. Per questo il modulo 7
è su sonnet-4-5: **non cambiare il modello del modulo 7** senza ritestare.

### Import (differenze rispetto alla v3)

Stessi segnaposto (`INSERISCI_ANTHROPIC_API_KEY` sui moduli 4 e 7,
`Bearer INSERISCI_GHL_API_KEY` sui moduli 8 e 9, token e chat_id Telegram
sul 10), più due controlli:

1. **Modulo 4** deve avere l'header `anthropic-beta: web-fetch-2025-09-10`
   (senza, il fetch delle pagine non parte).
2. **Modulo 6** (Text aggregator): verifica che *Source Module* punti al
   modulo 5 e che il separatore sia vuoto. Se l'import non lo aggancia, si
   risistema dal menu a tendina in 5 secondi.

Poi sposta l'URL del webhook nel workflow GHL dallo scenario v3 al v4, o
tieni entrambi attivi e cambia trigger.

### Dati camerali ufficiali via openapi.it (moduli 11-12)

Risolve il limite dei bilanci vecchi: invece di leggere portali gratuiti che
si fermano al 2022, interroga il Registro Imprese.

**Endpoint**: `GET https://company.openapi.com/IT-advanced/{partita_iva}`
**Auth**: header `Authorization: Bearer <token>` (token creato nella console
openapi.com, scope sul servizio *company*)
**Prezzo**: **30 chiamate gratuite al mese**, poi €0,10 + IVA a chiamata
(€0,028-0,07 con piano annuale). Con ~20 call fissate al mese siamo dentro
il gratuito.

**Cosa restituisce** (40+ campi): ragione sociale, forma giuridica, sede,
ATECO, capitale sociale, PEC, codice SdI, numero dipendenti, stipendio medio,
**storico di ricavi e utili fino a 7 esercizi**, e **i soci con quota ≥10%**.

Gli ultimi due sono quelli che cambiano la call: lo storico dà la direzione
(in crescita/stabile/in calo) invece di una fotografia vecchia, e l'elenco
soci risponde in modo deterministico alla domanda «la decisione è a una testa
sola?», che è il primo anti-pattern ICP.

#### Come arriva la partita IVA (il punto delicato)

`openapi` vuole la P.IVA, e il form GHL ce l'ha quasi mai (1 lead su 17).
Due sorgenti, in cascata:

1. **Il campo GHL `Partita iva`**, se compilato.
2. **Un modulo Text parser** (id 11) che la estrae con regex dal testo del
   sito **più** dal materiale di ricerca del modulo 4.

Perché entrambi: su 5 siti clienti reali testati, **3 avevano la P.IVA
nell'HTML della homepage** (kalishoes, lerive, partylandia) e 2 no
(patanegioielli, bergamovini — footer renderizzato via JS o pagina legale
separata). Per quei due la P.IVA arriva dalla ricerca online, che la trova
sui portali camerali. Per questo il modulo 11 sta **dopo** la ricerca, non
prima: verificato su Patanè, la ricerca stampa `P.IVA 02780290835` e il
regex la estrae.

Il prompt del modulo 4 contiene un'istruzione di formato vincolante:
*scrivila come `P.IVA 12345678901`, undici cifre attaccate*. **Se cambi quel
pezzo di prompt, si rompe l'estrazione** e il modulo 12 non parte più.

#### Se la P.IVA non si trova

Il modulo 11 ha attivo *Continue the execution of the route even if the
module returns no results*, e il modulo 12 ha `stopOnHttpError: false` più un
handler `Resume`: URL vuoto → nessun dato camerale → il dossier esce lo
stesso, con scritto «dati camerali non recuperati». Nessun lead va perso.

#### Cosa NON è stato testato

La chiamata a openapi.it **non è mai stata eseguita davvero**: serve un
token, che non ho. Verificato solo che l'endpoint risponde **403** senza
auth (quindi l'URL è giusto, non un 404). Al primo run controlla l'output
del modulo 12: deve essere 200 con un JSON, non un 401.

Non usare `POST /bilancio-ottico` (€4,50 a chiamata, restituisce lo ZIP con
XBRL e verbale): serve per la documentazione ufficiale, non per preparare
una call.

### Scrittura dei dati fiscali sui campi GHL (moduli 13-14)

I dati camerali non restano solo nel dossier: finiscono nei campi del
contatto, così quando il lead chiude **i contratti sono già precompilati**
e non c'è da richiedere P.IVA, PEC e sede.

**Campi scritti** (i primi tre esistevano, gli altri cinque creati il
31/07/2026 via API):

| Campo | fieldKey | id | Fonte openapi |
|---|---|---|---|
| Partita iva | `contact.partita_iva` | `XFYCqGHXHkdL1ktCrdG2` | `vatCode` |
| Ragione sociale | `contact.ragione_sociale` | `L3O4mX5GZ3GGg4Hc2KxO` | `companyName` |
| Codice SDI | `contact.codice_sdi` | `jdxxW9O3MlXY3hqgt9sx` | `sdiCode` |
| PEC | `contact.pec` | `YkYL4kGVFVxqXkcQuk5B` | `pec` |
| Sede legale | `contact.sede_legale` | `BPx4u5COUnJycDG97IdB` | `address.registeredOffice` |
| Soci e quote | `contact.soci_e_quote` | `xTsbqXw3s1jvXQw3pS81` | `shareHolders[]` |
| Fatturato camerale | `contact.fatturato_camerale` | `wI9sRvNbUyeGw9StkM8V` | `balanceSheets.all[]`, anno più recente |
| Dati camerali | `contact.dati_camerali` | `54SM8YT53PkDr5PH7pqq` | forma giuridica, ATECO, capitale, dipendenti, storico 3 anni |

**Come funziona**: il modulo 13 (`claude-haiku-4-5`, ~$0,002) legge il JSON
openapi e produce gli elementi dell'array `customFields`; il modulo 14 fa
`PUT /contacts/{id}` con `{"customFields": [...]}`. GHL fa **merge per id**:
gli altri campi del contatto non vengono toccati — verificato con una
scrittura reale su un contatto in pipeline.

#### Struttura reale della risposta openapi (verificata in sandbox 31/07/2026)

I dati stanno in `data[0]`. Attenzione a due cose che avevo sbagliato a
ipotizzare:

- **`employees` e `shareCapital` non stanno al primo livello** ma dentro
  `balanceSheets.last` e dentro ogni esercizio di `balanceSheets.all[]`.
- ⚠️ **Negli esercizi più recenti di `balanceSheets.all` il `turnover` è
  `null`**: il bilancio non è ancora depositato e c'è solo il numero di
  dipendenti e il capitale. Nel test, `all` aveva 8 esercizi con 2024 e 2023
  a `turnover: null` e i dati veri fermi al 2022. La regola ingenua «usa
  sempre l'anno più recente» avrebbe scritto *fatturato: null (2024)* nel
  campo che finisce nei contratti. Il prompt ora impone di prendere
  **l'esercizio più recente con `turnover` realmente valorizzato** e di
  dichiararne l'anno.

Campi utili oltre ai soliti: `reaCode`, `cciaa`, `activityStatus`,
`startDate`, `totalStaffCost`, e `employees` per anno (dice più del fatturato
sulla struttura reale).

**Sandbox**: host `https://test.company.openapi.com` (la produzione risponde
`401 Wrong Token` alle chiavi di test). Restituisce sempre OPENAPI S.P.A.
qualunque partita IVA si interroghi: serve a provare l'impianto, non i
contenuti.

Il modulo 13 usa il **prefill** (`{"customFields": [` + `stop_sequences:
["]}"]`), quindi il JSON esce già escapato. Gira su haiku-4-5 perché
sonnet-5 e opus-4-6 rifiutano il prefill.

**Regola nel prompt da non togliere**: un campo senza dato va *omesso*, mai
riempito con «non disponibile». Un placeholder che finisce in un contratto è
peggio di un campo vuoto.

**Vale la pena il modulo nativo GHL «Update a contact»?** Non qui. Quel
modulo mappa i custom field uno per uno, quindi servirebbe un ulteriore
passaggio di parsing per esplodere l'output del modulo 13 in campi separati:
più moduli e più cose che si rompono. La `PUT` HTTP fa lo stesso lavoro in un
modulo solo e usa lo stesso endpoint di `tools/ghl_client.py`. Per la **nota**
invece il modulo nativo è la scelta giusta, ed è quella in uso.

### PDF brandizzato allegato al contatto (moduli 16-19)

La nota GHL resta (è cercabile e si legge inline), ma il documento vero è un
**PDF impaginato allegato al profilo del contatto**.

**La nota non renderizza il markdown**: `#` e `**` comparivano letterali. Il
modulo 7 ora produce testo pulito — titoli in MAIUSCOLO, elenchi con trattino,
righe di separazione — invece di markdown.

**Catena PDF**: modulo 16 (`claude-haiku-4-5`) converte il dossier in HTML
semantico con le classi del foglio di stile → modulo 17 apre un job
CloudConvert (`import/raw` + `convert` con engine Chrome + `export/url`) →
modulo 18 attende su `sync.api.cloudconvert.com` → modulo 19 scrive l'URL nel
campo file del contatto.

**CloudConvert**: 25 conversioni al giorno gratis, rendering con Chrome quindi
CSS completo. Il foglio di stile (colori Mailift `#ff8a3d` / `#06101c`, Inter,
intestazione con wordmark, sezioni con barra arancio, box per Fit ICP e red
flag) sta **nel modulo 17**, non nel prompt: la grafica si cambia lì senza
toccare l'AI.

#### Come si allega un file a un contatto GHL (non documentato)

1. Serve un custom field di tipo `FILE_UPLOAD`. Creato: **Dossier pre-call**
   (`contact.dossier_precall`, id `wNyNDjq2ApPGAR4Z08sw`, accetta `.pdf`).
   Attenzione: alla creazione **non passare `maxFileLimit`** → 422.
2. `PUT /contacts/{id}` con `{"customFields":[{"id":"...","value":"<url>"}]}`
   dove il valore è **l'URL come stringa semplice**.
3. **GHL scarica il file e lo copia nel proprio storage**: genera un
   `documentId` e lo serve da `services.leadconnectorhq.com/documents/download/{id}`,
   tenendo l'URL originale in `meta.originalUrl`. Verificato con un PDF di test.

Conseguenza pratica: l'URL temporaneo di CloudConvert (che scade) va benissimo,
perché GHL ne fa una copia permanente. **Non serve scaricare il PDF e
ricaricarlo** sulla media library — due moduli risparmiati.

Nota: i file scritti sul campo si **accumulano** invece di sostituirsi. Con un
dossier per lead non è un problema; se rigeneri più volte lo stesso lead,
troverai più allegati.

#### Il prefill qui NON funziona

Sul modulo 16 il prefill `{"html": "` + `stop_sequences: ["\"}"]` fa emettere
al modello **la sequenza di stop come primo token**: risposta vuota,
`content: []`. Confligge con la regola «non usare virgolette doppie».
Soluzione adottata: niente prefill, e si chiede HTML **su una riga sola, senza
virgolette doppie** (gli attributi HTML5 senza virgolette sono validi). Così il
frammento si incolla dentro il JSON di CloudConvert senza escaping. Misurato:
6.225 caratteri, zero a capo, zero virgolette.

### Versione agenti AI Make (alternativa, 31/07/2026)

Blueprint: [tools/make_blueprints/lead_precall_research_agenti.json](../tools/make_blueprints/lead_precall_research_agenti.json).
Stessa logica, ma le 6 chiamate HTTP ad Anthropic diventano **4 moduli
`ai-local-agent:RunLocalAIAgent`**. Da 17 moduli a 13.

Cosa cambia:
- **Nessuna chiave API nel blueprint**: il modulo usa una connessione Make
  (`makeConnectionId`), come già fa GoHighLevel. I token restano comunque a
  carico dell'account Anthropic: la connessione usa la stessa chiave.
- **Output strutturato** (`outputType: make-schema`): i campi si leggono come
  `{{4.jsonResponse.partita_iva}}`. Spariscono iterator, text aggregator e la
  chiamata dedicata all'estrazione P.IVA.
- **Niente più percent-encoding**: `systemPrompt` e `message` sono campi
  normali, quindi i riferimenti vanno diretti (`{{1.\`Ragione sociale\`}}`) e i
  prompt non devono più spiegare al modello come decodificare.
- **Dossier e HTML dallo stesso agente**, due campi dello schema: una chiamata
  in meno.
- La ricerca web non è più quella di Anthropic ma il tool nativo
  `make-ai-web-search:generateAResponse`, passato all'agente in `tools`.

Agenti e schemi:

| # | Agente | Modello | Output |
|---|---|---|---|
| 15 | Trova il sito | haiku-4-5 | `sito_url` |
| 4 | Ricerca online | sonnet-5 + tool ricerca web | `ricerca`, `partita_iva` |
| 7 | Scrivi il dossier | sonnet-5 | `dossier_testo`, `dossier_html` |
| 13 | Mappa i dati fiscali | haiku-4-5 | `campi` |

⚠️ **Provata e scartata (31/07/2026): i dossier escono peggiori.** Il collo di
bottiglia è il tool `make-ai-web-search`, che raccoglie meno e peggio del web
search nativo di Anthropic (5 ricerche + 2 fetch di pagine). È da lì che
venivano i pezzi che cambiano la call — i tre fratelli soci di Patanè, il
bilancio con l'utile sotto l'1%, il dominio sbagliato di ewooow.

**La versione buona è quella HTTP** (`lead_precall_research_deep.json`): la
comodità dell'output strutturato non compensa la perdita di qualità della
ricerca. Il file agenti resta solo come riferimento della struttura del modulo
`ai-local-agent:RunLocalAIAgent`, che è comunque utile per automazioni dove la
ricerca web non serve.

### Identificatori dei moduli Make: quelli veri

Sbagliarli produce «Module Not Found» all'import, con il modulo grigio e il
punto esclamativo. Presi dalla documentazione ufficiale Integromat
([make-skills](https://github.com/integromat/make-skills/blob/main/skills/make-scenario-building/blueprint-construction.md)):

| Funzione | Identificatore |
|---|---|
| Iterator | `builtin:BasicFeeder` |
| Array aggregator | `builtin:BasicAggregator` |
| **Text aggregator** | **`util:TextAggregator`** (non `builtin:`) |
| Router | `builtin:BasicRouter` |
| Set variable | `util:SetVariable` |
| Sleep | `util:FunctionSleep` |
| Parse JSON | `json:ParseJSON` |
| HTML → testo | `regexp:HTMLToText` |

Il Text aggregator vuole `feeder` dentro `parameters` (id del modulo
iterator) e `metadata.restore.extra.feeder.label` per farsi disegnare bene.

⚠️ **Per il Text parser «Match pattern» non esiste un identificatore
documentato**: `regexp:Matcher` non esiste e fallisce l'import. Se serve
estrarre qualcosa da un testo, o si aggiunge il modulo a mano
nell'interfaccia, o — come qui per la P.IVA — si usa una chiamata haiku, che
costa 0,2 centesimi e vive dentro un `http:MakeRequest` che sappiamo
funzionare.

### Limiti noti

- **La verifica VIES non parte**: `web_fetch` rifiuta gli URL che non
  provengono da una ricerca precedente, e l'endpoint VIES è costruito al
  volo con la P.IVA trovata. Il modello ripiega su fonti camerali terze
  (fatturatoitalia.it e simili): il dato è buono ma va trattato come **da
  confermare**, non come verifica ufficiale. Per una verifica deterministica
  serve un modulo HTTP dedicato dopo aver estratto la P.IVA dal sito.
- **I bilanci gratuiti sono vecchi, e non è un bug del prompt.** Verificato
  su Patanè: 2022 è davvero il dato più recente indicizzato pubblicamente;
  fatturatoitalia.it mostra un solo anno e mette gli altri dietro
  registrazione, reportaziende/ufficiocamerale non pubblicano cifre in
  chiaro, registroimprese e Cribis vendono la visura. Due conseguenze:
  1. **Vincolo di calendario**: una SRL deposita il bilancio ~7 mesi dopo la
     chiusura, quindi anche pagando, oggi il massimo ottenibile è l'esercizio
     **2024** (o il 2025 appena depositato). "Dati 2025 in tempo reale" non
     esistono per nessuna fonte, gratuita o a pagamento.
  2. **Il prompt lo gestisce**: ogni cifra esce con l'anno attaccato e, se ha
     più di due anni, con l'avviso *dato vecchio di N anni, non è la
     fotografia di oggi*. In più fa il **controllo incrociato** tra fatturato
     dichiarato nel form (×12) e fatturato camerale: se divergono di oltre il
     30%, diventa una domanda per la call invece di una conclusione (può
     essere eCommerce-only vs totale col negozio fisico, o crescita/calo).
  Se in futuro serve il dato certificato e fresco, la via è un modulo HTTP
  verso un fornitore a pagamento (openapi.it è il più semplice da mettere in
  Make, pochi centesimi a lookup; Cribis/Atoka sono abbonamenti). Serve la
  P.IVA prima della chiamata: si estrae dal footer del sito con un modulo
  Text parser, oppure si prende dal modulo 4 che già la trova.
- **Omonimie**: il prompt impone di segnalare l'ambiguità invece di
  attribuire dati all'azienda sbagliata. Verificato che lo fa, ma su nomi
  molto comuni vale la pena rileggere il blocco "Azienda (dati verificati)".
- **Costo per lead 7x la v3**: con ~20 call fissate al mese sono ~€8/mese.
  Se il volume cresce, il primo knob è `max_uses` del `web_search` nel
  modulo 4 (5 → 3): i risultati di ricerca si accumulano nel contesto a ogni
  giro, quindi è quello a far salire i token (97k input sul modulo 4).

## Apprendimenti

(Popolare con pattern ricorrenti di rilevamento tech-stack, falsi positivi
frequenti, fonti che si rivelano poco affidabili, ecc.)
