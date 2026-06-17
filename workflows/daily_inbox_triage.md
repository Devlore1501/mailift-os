# Daily Inbox Triage

## Obiettivo
Triage giornaliero delle due caselle Gmail dell'utente (personale + business)
per:

1. Archiviare le email **promozionali / inutili** (newsletter, marketing,
   transazionali impersonali) cosi' che non riempiano l'inbox.
2. Trasformare le email **importanti / actionable** (richiedono risposta,
   decisione, scadenza) in task nel database **Tasks_Mailift** di Notion,
   assegnandole a Lorenzo.
3. Inviare un **report giornaliero** via Gmail sulla casella personale che
   riassuma cosa e' stato fatto, quali task sono stati creati, e quali email
   informative meritano comunque attenzione.

L'esecuzione e' affidata a uno **script Python** in [tools/inbox_triage.py](tools/inbox_triage.py)
che usa direttamente Gmail API e Notion API. L'agente (Claude) si limita a:
- decidere quando lanciarlo (manuale o schedulato),
- leggere il report finale,
- proporre miglioramenti al SOP quando vede pattern ricorrenti.

> Storico: una prima versione del workflow usava i connettori MCP `claude.ai
> Gmail` e `claude.ai Notion`. Il connettore Gmail di claude.ai e' read-only +
> drafts (no `archive`, no `send`), quindi non poteva fare il cleanup. Per
> avere il pieno controllo siamo passati a Google API + Notion API direttamente
> dal Python tool. Il connettore MCP Notion resta utile per discovery
> interattivo (search, get-users, fetch).

## Quando usarlo
- **Schedulato**: ogni mattina alle **09:00** (Europe/Rome). Setup separato
  via cron / launchd / GitHub Actions una volta validato manualmente.
- **Manuale**: `python tools/inbox_triage.py --account business --hours 24`
  oppure l'utente dice "fai il triage di oggi" e l'agente lancia il tool.

## Input richiesti

### Variabili `.env` (vedi [.env.example](.env.example))
| Chiave | Valore di default |
|---|---|
| `GMAIL_CREDENTIALS_FILE` | `credentials_gmail.json` (OAuth Desktop client) |
| `GMAIL_TOKEN_PERSONAL` | `tokens/gmail_personal.json` (creato da oauth_setup) |
| `GMAIL_TOKEN_BUSINESS` | `tokens/gmail_business.json` (creato da oauth_setup) |
| `GMAIL_PERSONAL_ADDRESS` | `lorenzo.baretta997@gmail.com` |
| `GMAIL_BUSINESS_ADDRESS` | `info@mailift.com` |
| `INBOX_TRIAGE_REPORT_TO` | `lorenzo.baretta997@gmail.com` |
| `NOTION_API_KEY` | Internal Integration Secret |
| `NOTION_TASKS_DB_ID` | `5dfdc59e-16de-4ab3-9846-8f69a433aff7` (Tasks_Mailift) |
| `NOTION_CLIENTI_DB_ID` | `09b69349-30c8-47b2-800c-0334265560da` (Clienti_Mailift) |
| `NOTION_USER_ID_LORENZO` | `f33fe0ac-6358-43f9-93e2-40f54dfed7c5` |
| `ANTHROPIC_API_KEY` | usata da [tools/classify_emails.py](tools/classify_emails.py) |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` |

### Schema property `Tasks_Mailift` (verificato 2026-04-08)
- `Name` (title)
- `Assign` (person)
- `Status` (select) — `To-do` / `In corso` / `In approvazione` / `Completato`
- `Due Date` (date)
- `Categoria` (select) — `Strategia` / `Copy` / `Design` / `Tecnico` / `Reportistica` / `Altro`
- `Priorità` (select) — `Alta` / `Media` / `Bassa`
- `Cliente` (relation → `Clienti_Mailift`)
- `Created by`, `Created time` — auto, read-only
- **Niente campo URL** → il link al thread Gmail va nel **body** della pagina.

## Setup iniziale (una tantum)

### 1. Google Cloud + Gmail API
1. Vai su <https://console.cloud.google.com/> e crea un progetto.
2. Abilita **Gmail API**.
3. OAuth Consent Screen: tipo `External`, in stato `Testing`. Aggiungi
   `lorenzo.baretta997@gmail.com` e `info@mailift.com` come **Test users**.
4. Crea credenziali OAuth client di tipo **Desktop**.
5. Scarica il JSON, rinominalo `credentials_gmail.json`, mettilo nella root
   del progetto. (Gia' gitignorato via `.gitignore` -> `.env` pattern; aggiungi
   `credentials_gmail.json` e `tokens/` se non ci sono.)

### 2. Notion internal integration
1. Vai su <https://www.notion.so/my-integrations> e crea un'integration:
   - Nome: `Workflow AI Inbox Triage`
   - Type: **Internal**
   - Capabilities: Read content + **Insert content** + Update content
2. Copia l'**Internal Integration Secret** in `.env` come `NOTION_API_KEY`.
3. Su Notion, apri il database `Tasks_Mailift` → menu (...) → **Connections**
   → aggiungi `Workflow AI Inbox Triage`. (Solo questo: il database
   `Clienti_Mailift` non e' usato dal workflow.)

### 3. OAuth flow per ciascun account Gmail
Lancia, una volta sola per account:
```bash
python tools/gmail_oauth_setup.py --account personal
python tools/gmail_oauth_setup.py --account business
```
Il browser si apre, accedi con l'account giusto, autorizza. Lo script verifica
che l'email autenticata corrisponda a quella attesa e salva il token in
`tokens/gmail_<account>.json`.

### 4. Dipendenze Python
```bash
pip install -r requirements.txt
```
Aggiunge `google-auth-oauthlib`, `google-api-python-client`, `notion-client`
oltre alle dipendenze gia' presenti.

## Esecuzione

### Manuale (un account)
```bash
# Dry-run, ultime 24h, business — niente scritture
python tools/inbox_triage.py --account business --hours 24 --dry-run

# Run reale, ultime 24h, business — archivia + crea task
python tools/inbox_triage.py --account business --hours 24

# Run reale + invio report via email
python tools/inbox_triage.py --account business --hours 24 --send-report
```

### Manuale (entrambi gli account)
```bash
python tools/inbox_triage.py --account personal --hours 24 --send-report
python tools/inbox_triage.py --account business --hours 24 --send-report
```
Lo script tratta i due account in modo indipendente: due esecuzioni, due
report `.tmp/inbox_triage_<account>_<date>.json`, due email di report.

### Schedulato (cron Mac)
3 run al giorno. Le email dalle 18:00 in poi vengono gestite il giorno dopo alle 09:00.

```
CRON_TZ=Europe/Rome

# 09:00 — copre dalle 18:00 di ieri (15h)
0 9 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account personal --hours 15 --send-report >> ".tmp/cron_triage.log" 2>&1
5 9 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account business --hours 15 --send-report >> ".tmp/cron_triage.log" 2>&1

# 14:00 — copre dalle 09:00 (5h)
0 14 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account personal --hours 5 --send-report >> ".tmp/cron_triage.log" 2>&1
5 14 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account business --hours 5 --send-report >> ".tmp/cron_triage.log" 2>&1

# 18:00 — copre dalle 14:00 (4h)
0 18 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account personal --hours 4 --send-report >> ".tmp/cron_triage.log" 2>&1
5 18 * * * cd "/Users/lorenzobaretta/workflow ai" && "/Users/lorenzobaretta/workflow ai/.venv/bin/python" tools/inbox_triage.py --account business --hours 4 --send-report >> ".tmp/cron_triage.log" 2>&1
```

## Cosa fa lo script (sequenza deterministica)

[tools/inbox_triage.py](tools/inbox_triage.py) per ciascuna invocazione:

1. **Carica Gmail service** — `gmail_client.load_service(account)` legge il
   token, fa refresh se serve, costruisce il client API.
2. **Lista messaggi inbox** — `list_recent(service, hours=N)`. Usa
   `in:inbox newer_than:Nh` (o `Nd` se N>24).
3. **Recupera dettagli** — per ogni messaggio: headers, body (text/plain con
   fallback HTML stripped), label, header `List-Unsubscribe`, allegati,
   permalink Gmail.
4. **Classifica via Anthropic** — [tools/classify_emails.py](tools/classify_emails.py)
   manda l'intero batch in UNA chiamata Claude con tool_use, per output
   strutturato. Per ogni email:
   - `category` ∈ {PROMO, INFO, ACTION, VIP}
   - `actionable_title` (solo per ACTION/VIP)
   - `due_date` (ISO YYYY-MM-DD o null)
   - `categoria_notion`, `priorita_notion`
   - `context_summary`
   - `suggested_cliente_query` (per la lookup nel DB Clienti)
5. **Per ogni email classificata ACTION/VIP**:
   - Crea pagina in `Tasks_Mailift` con `notion_tasks.create_task`. Nome:
     `[Business] <titolo>` o `[Personale] <titolo>`. Body: header con link
     Gmail + mittente + account + data + contesto. Il campo `Cliente`
     resta sempre vuoto (lo popoli tu manualmente in Notion se serve).
   - Se la create fallisce, l'errore va nel report e l'email NON viene
     archiviata.
6. **Per ogni email classificata PROMO**: archive (rimuove label `INBOX`)
   tramite `gmail_client.archive_message`. **Mai delete, mai trash.**
7. **Per ogni INFO**: nessuna azione, viene solo elencata nel report.
8. **Salva report** in `.tmp/inbox_triage_<account>_<date>.json` con tutti
   i dettagli (totali, task creati, archiviati, info, errori).
9. **Stampa riepilogo** human-readable su stdout.
10. **Se `--send-report`**: invia il riepilogo via Gmail al
    `INBOX_TRIAGE_REPORT_TO`.

## Regole di classificazione (decision rules)

Le regole vere e proprie vivono nel **system prompt** di
[tools/classify_emails.py](tools/classify_emails.py). Sintesi (in ordine, prima
che fa match vince):

1. **VIP** se mittente in whitelist (sezione "Whitelist VIP" sotto).
2. **PROMO** se header `List-Unsubscribe` presente E mittente non e' un
   cliente Mailift.
3. **PROMO** per mittenti tipici di mass mailing (mailchimp, sendgrid,
   hubspot, klaviyo, mailerlite, instagram updates, learnn, plaud,
   newsletter italiani noti, `no-reply@klaviyo.com` notifiche sistema account
   clienti, `notifications@stripe.com` per account clienti, dropship,
   windsor.ai, `*@xwf.google.com` Google sales outreach).
4. **PROMO** per subject con pattern marketing ("offerta", "% sconto",
   "ultimo giorno", "saldi", emoji marketing).
5. **ACTION** se domanda diretta, richiesta approvazione/firma, allegato
   fattura/contratto/preventivo.
6. **ACTION** se scadenza esplicita ("entro il", "by", "deadline", date).
7. **ACTION** per appuntamenti da confermare.
8. **INFO** altrimenti.

**Tie-break:**
- In dubbio tra PROMO e INFO → **INFO** (mai archiviare per errore).
- In dubbio tra INFO e ACTION → **ACTION con `confidence: low`**. Il task viene
  creato con prefisso `[DA CONTROLLARE]` invece di `[Personale]`/`[Business]`,
  cosi' Lorenzo puo' ignorarlo o promuoverlo senza rumore. Se il dubbio e'
  perche' Lorenzo e' solo admin delegato su account cliente → **INFO** direttamente.

Se cambi le regole, **modifica il system prompt nello script** e poi
documenta il cambio qui sotto in "Apprendimenti".

## Edge case noti
- **Calendar invites** (`calendar-notification@google.com`): `INFO`, mai task.
- **OTP / verifiche / 2FA**: `INFO`, mai task, mai archiviare.
- **Email di sistema** (GitHub, CI, status pages): default `INFO`. Solo
  fallimenti che richiedono intervento → `ACTION`.
- **Thread gia' attivi**: la prima versione crea sempre un nuovo task. Se
  diventa fastidioso, evolvere `notion_tasks.create_task` per cercare task
  esistenti con lo stesso permalink Gmail nel body.
- **Auth Google scaduta**: il token si auto-refresha. Se serve un re-consent,
  rilancia `gmail_oauth_setup.py --account X --force`.
- **Property mismatch su Notion**: se `create_task` solleva, l'errore va nel
  report e l'email NON viene archiviata. Lo script continua col prossimo
  messaggio.
- **Allegati**: lo script legge solo testo. Per email con allegato critico,
  il classificatore li flagga via `has_attachments` ma non li scarica.

## Whitelist VIP
Vuota all'inizio. Per popolarla, modifica direttamente la lista VIP nel
parametro `vip_list` di `classify_emails()` (o estendi `inbox_triage.py` per
leggerla da `.env`/file separato).

```
# Email VIP (sempre ACTION)
- (vuoto)

# Domini VIP (sempre ACTION)
- (vuoto)
```

## Auto-improvement loop
Dopo ogni run reale:

1. **Mittenti ricorrenti ACTION** — Se vedi che lo stesso mittente compare
   come ACTION in piu' run, valuta di aggiungerlo ai VIP (per essere sicuro
   di non perderlo mai).
2. **Errori di classificazione** — Se l'utente segnala "questa era
   importante" o "questa era promo", aggiorna il system prompt di
   `classify_emails.py` con la regola/eccezione, **e** documenta la lezione
   qui sotto in "Apprendimenti".
3. **Edge case nuovi** — Aggiungi una riga alla sezione "Edge case noti".

## Apprendimenti

### 2026-04-08 — Fatture Klaviyo non sono di Mailift
**Cosa e' successo**: il primo run reale ha creato 2 task per email Klaviyo
("Scaricare fattura Klaviyo aprile", "Scaricare ricevuta Stripe Klaviyo
#2850-0011") perche' il classificatore ha visto fattura/ricevuta → ACTION.

**Realta'**: Lorenzo e' admin degli account Klaviyo dei clienti Mailift, ma
le fatture Klaviyo le pagano i clienti, non lui. Quindi quei task erano
spazzatura.

**Fix applicato**:
- Aggiunta regola esplicita nel system prompt di [tools/classify_emails.py](tools/classify_emails.py)
  → fatture/ricevute Klaviyo (anche tramite Stripe `invoice+statements@stripe.com`)
  sono **sempre PROMO**.
- Generalizzazione: stessa logica per altre piattaforme SaaS dove Lorenzo
  e' admin del cliente — se l'oggetto e' una fattura/ricevuta NON destinata
  a Mailift Srl come pagante, e' PROMO.

**Da osservare**: se in futuro arrivano fatture di altre piattaforme con
lo stesso pattern (Shopify, Meta, Google Ads, ecc.) e generano falsi
task, estendere la regola al SaaS specifico.

### 2026-04-15 — Falsi ACTION da notifiche admin account clienti

**Cosa e' successo**: il triage ha creato 7 task su 9 che erano tutti falsi
positivi. Pattern: Lorenzo e' admin di account clienti (Klaviyo, Stripe) e
viene notificato come tale, ma l'azione non spetta a lui. Stessa cosa per
vendor SaaS che fanno outreach commerciale (Dropship, Windsor.ai) e Google
sales (`xwf.google.com`). Il tie-break "in dubbio INFO→ACTION" ha amplificato
il problema trasformando in task email con linguaggio "azionabile" ma non
indirizzate a Lorenzo come decision-maker.

**Fix applicato**:
- `no-reply@klaviyo.com` → sempre PROMO (alert sistema account clienti)
- `notifications@stripe.com` → PROMO se riguarda account cliente; ACTION solo
  se e' Mailift Srl il soggetto pagante/ricevente
- Vendor SaaS outreach/trial (Dropship, Windsor.ai) → PROMO
- Google sales outreach (`*@xwf.google.com`) → PROMO
- Vendor tecnici per setup account cliente (es. Littledata) → INFO, non ACTION
- Tie-break INFO→ACTION affinato: solo se Lorenzo e' il destinatario reale,
  non admin delegato

**Email che DEVONO restare ACTION**:
- Spedizioni fisiche (DHL, corrieri): ACTION
- Conferme eventi/partecipazione personale: ACTION
- Email dirette da clienti Mailift che richiedono risposta/approvazione: ACTION

## Roadmap — Dimensione "urgenza" (TODO, non ancora implementata)

Estensione richiesta dal CLAUDE.md Segretaria: oltre alla **categoria**
(PROMO/INFO/ACTION/VIP), assegnare anche un livello di **urgenza** così che
Lorenzo possa filtrare visivamente cosa serve toccare per primo.

Schema target:
- **URGENTE** → flag immediato in cima al report; bozza di risposta preparata
  in `drafts/` di Gmail (mai inviata). Esempi: cliente bloccato, call di oggi
  da confermare, scadenza fiscale entro 24h.
- **DA RISPONDERE** → bozza preparata entro 2h; finisce nella sezione
  "Pending replies" del report. Esempi: domanda diretta da cliente, lead da
  qualificare.
- **FYI** → solo elencata nel report, nessuna azione. Equivale all'attuale
  `INFO`.
- **SPAM** → archiviata come l'attuale `PROMO`.

Mappatura sulle categorie esistenti:

| Urgenza nuova | Tipicamente coincide con |
|---|---|
| URGENTE | ACTION + (`due_date` ≤ oggi+1 OR mittente VIP) |
| DA RISPONDERE | ACTION restante + VIP non urgenti |
| FYI | INFO |
| SPAM | PROMO |

**Cosa serve per implementarla** (non fatto in questa fase):
1. Estendere lo schema di output di [tools/classify_emails.py](tools/classify_emails.py)
   aggiungendo un campo `urgency` ∈ {URGENTE, DA_RISPONDERE, FYI, SPAM} al
   tool_use schema, e aggiornare il system prompt con i criteri sopra.
2. Estendere [tools/inbox_triage.py](tools/inbox_triage.py) per: (a) ordinare
   il report con URGENTE in cima, (b) creare draft Gmail per URGENTE/DA
   RISPONDERE via `gmail_client.create_draft` (metodo da aggiungere se non
   esiste).
3. Aggiungere `Priorità` al task Notion mappando URGENTE→Alta, DA RISPONDERE→Media.
4. Testare con `--dry-run` su un giorno noto prima di abilitare draft creation.

Finché non implementato: la classificazione resta a 4 categorie. Lorenzo
filtra manualmente leggendo il report.

## Verifica end-to-end (prima volta)
1. `pip install -r requirements.txt`
2. Setup Google Cloud + Notion integration come da sezioni 1-2 sopra.
3. `python tools/gmail_oauth_setup.py --account personal`
4. `python tools/gmail_oauth_setup.py --account business`
5. `python tools/inbox_triage.py --account business --hours 24 --dry-run`
   - Verifica la classificazione nel print/JSON. Niente azioni eseguite.
6. `python tools/inbox_triage.py --account business --hours 24`
   - Controlla che le PROMO siano sparite dall'inbox (cercabili con `in:all`)
     e che i task siano comparsi in `Tasks_Mailift` con assignee Lorenzo.
7. Ripeti per `--account personal`.
8. Quando tutto funziona, abilita lo `--send-report` e poi schedula via cron.
