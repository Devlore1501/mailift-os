# Autofatture Webapp v3

Webapp per emettere autofatture passive (TD17/TD18/TD19 reverse charge) su Fatture in Cloud da estratti conto Revolut, con **verifica dei fornitori via Gmail**, **controllo duplicati su FiC**, **invio al SDI** e **logica IVA country-aware**. Gira in locale o online (Docker, con login).

Costruita sopra il workflow CLI in [`tools/`](../tools/): non duplica logica fiscale, riusa `parse_bank_statement`, `autofatture_prep`, `classify_transactions`, `run_autofatture.group_candidates`, `fic_client`, `send_autofatture_sdi`, `verify_suppliers_from_email` come librerie Python.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13, FastAPI 0.162, SQLAlchemy 2.1, SQLite |
| Frontend | React 19, Vite 8, TypeScript 7, Tailwind 4, shadcn/ui (Radix), React Router 7, TanStack Query 5 |
| Persistenza | SQLite (Statement, Job, SupplierOverride, RunHistory) |
| Auth | Password unica (`WEBAPP_PASSWORD`) + cookie di sessione firmato HttpOnly/SameSite=Strict; disattivata se la variabile e' vuota |

Versioni fissate in `backend/requirements.txt` e `frontend/package.json`, scelte tra quelle pubblicate da almeno due settimane.

## Avvio in locale

```bash
./webapp/start.sh
```

Backend su `:8000` (con `/docs`), frontend Vite su `:5173` che inoltra `/api` al backend. Senza `WEBAPP_PASSWORD` non chiede login.

Per provare la versione "come online" (un solo processo che serve anche il frontend buildato):

```bash
cd webapp/frontend && npm run build
cd ../backend && WEBAPP_PASSWORD=... ../../.venv/bin/uvicorn app.main:app --port 8000
```

## Flusso utente

1. **Upload**: CSV/XLSX/PDF dell'estratto Revolut (anche il PDF italiano multi-conto). Max 20 MB.
2. **Elaborazione**:
   - parsing, con controllo della **catena dei saldi** (se un importo e' letto male il run si ferma prima della classificazione, che e' a pagamento)
   - esclusione deterministica di **giroconti** tra conti propri e **addebiti rimborsati** per intero (`tools/autofatture_prep.py`)
   - classificazione AI degli addebiti restanti. Se fallisce, il run si ferma: niente candidati di riserva.
3. **Verifica fornitori**: cerca le fatture in Gmail, controlla il "Bill to", estrae paese e P.IVA dal PDF.
4. **Revisione**:
   - un'autofattura **per fornitore per mese**, con IVA, paese e mese degli addebiti
   - **duplicati su FiC**: quelli certi partono esclusi, i possibili sono segnalati con il numero del documento esistente
   - elenco degli addebiti non autofatturati, ciascuno con il motivo
   - rimborsi orfani da girare al commercialista (nota di variazione)
   - in modalita' Live, conferma con riepilogo prima di creare
5. **Creazione** su FiC. Lato server si rifa' il controllo duplicati: un duplicato certo non viene creato nemmeno se arriva dal frontend.
6. **Risultati**, con il link alla pagina Invio SDI.

**Invio SDI** (pagina a se', anche per batch vecchi):
- elenca le autofatture di una data con lo stato SDI
- fa la verifica formale XML
- invia solo dopo aver digitato `INVIA`. La verifica formale viene rifatta prima di ogni documento e quelli gia' inviati vengono saltati. L'invio e' irreversibile.

## Online (Docker)

L'immagine (`webapp/Dockerfile`, build dalla root del repo) contiene frontend buildato + backend + solo i tools necessari. Estratti, clienti, token e `.env` restano fuori dal contesto di build (`Dockerfile.dockerignore`). Gira con un solo worker su un volume persistente montato in `/data`:

| Path | Contenuto |
|---|---|
| `/data/webapp/` | DB SQLite, estratti caricati, log |
| `/data/mailift.env` | token FiC: il refresh lo riscrive, per questo sta sul volume |
| `/data/tokens/` | token Gmail |
| `/data/tmp/` | PDF fatture fornitori scaricati |

**Deploy su Render** con `webapp/render.yaml`:
1. Dashboard → New → Blueprint, repo `mailift-os`, Blueprint path `webapp/render.yaml`.
2. Compila i valori segreti richiesti:
   - `WEBAPP_PASSWORD`
   - `ANTHROPIC_API_KEY`
   - `FIC_CLIENT_ID`, `FIC_CLIENT_SECRET`, `FIC_ACCESS_TOKEN`, `FIC_REFRESH_TOKEN`
   - `GMAIL_TOKEN_PERSONAL_JSON`, `GMAIL_TOKEN_BUSINESS_JSON` (contenuto dei file in `tokens/`)
3. Deploy. Al primo avvio FiC e Gmail vengono copiati su `/data`. Dopo, la fonte di verita' sono quei file: per sostituire un token si cancella il file sul disco e si riavvia.

Piano Starter (serve per il disco), regione Frankfurt, HTTPS automatico, deploy solo manuale (`autoDeploy: false`).

### Variabili d'ambiente

| Variabile | Default | Note |
|---|---|---|
| `WEBAPP_PASSWORD` | vuota | vuota = nessun login (solo locale) |
| `WEBAPP_SECRET` | casuale per processo | firma il cookie; fissala online o ogni riavvio scollega |
| `WEBAPP_SESSION_HOURS` | 12 | durata sessione |
| `WEBAPP_COOKIE_SECURE` | false (true nell'immagine) | cookie solo su HTTPS |
| `WEBAPP_DATA_DIR` | `backend/.tmp` | DB e upload |
| `MAILIFT_ENV_PATH` | `~/.secrets/mailift/.env` | file credenziali; online sul volume |
| `WEBAPP_DRY_RUN` | false | forza dry-run per tutti |
| `WEBAPP_DEV` | false | CORS per Vite e `/docs` (lo attiva `start.sh`) |

## Logica fiscale (chiave)

### Country-aware vat_id
Il backend calcola automaticamente `vat_id` in base al paese del fornitore:

| Paese | vat_id | Descrizione | RegimeFiscale SDI |
|---|---|---|---|
| UE (IT,AT,BE,BG,HR,CY,CZ,DK,EE,FI,FR,DE,GR,HU,IE,LV,LT,LU,MT,NL,PL,PT,RO,SK,SI,ES,SE) | **0** | 22% reverse charge | RF01 |
| Extra-UE (US, AE, GB, CH, NO, ecc.) | **10** | Oper. non soggetta art.7-ter (0%) | RF18 |

Per vat_id=0 il gross_price = net * 1.22. Per vat_id=10 gross_price = net.

### Defense-in-depth fornitori italiani
Se per qualunque motivo un fornitore con `country_iso==IT` sfugge alla blacklist del classifier (regressione AI, override custom, seed manuale), viene intercettato in `build_preview` e spostato in `skipped_italian` — **non può generare autofatture errate**. Google Cloud Italy, Paddle Italia, eccetera, vengono bloccati automaticamente.

### Verify fornitori via Gmail
Per ogni fornitore nel preview:
1. Backend chiama `verify_suppliers_from_email.find_invoices_for_supplier` che cerca in `personal` + `business` usando query multiple (`from:dominio`, `subject:invoice + keyword`)
2. I PDF scaricati sono pre-filtrati con pdfplumber: se il Bill to non contiene "Mailift" o la P.IVA `18160081008`, il PDF va in quarantena `.tmp/invoices_rejected/`
3. Se ci sono credit Anthropic, ogni PDF valido viene passato a Claude Opus con `document` block + tool use per estrarre `supplier_legal_name`, `country_iso`, `vat_number`, `iva_applied`, `reverse_charge_note`, `invoice_number`, `total_gross`
4. Fallback automatico `pdf_only` se Anthropic non disponibile: scarica solo i PDF senza analizzarli, l'utente può aprirli dal dialog preview

Stati possibili per fornitore: `pending`, `verified`, `pdf_only`, `not_found`, `bill_to_mismatch`, `error`.

## REST API (v2)

| Metodo | Path | Note |
|---|---|---|
| `GET` | `/api/health` | fic_token_valid, db_ok, gmail_tokens_ok {personal, business}, anthropic_api_ok |
| `GET` | `/api/config` | company info, sezionale, payment account, dry-run default |
| `POST` | `/api/statements/upload` | multipart/form-data → statement_id |
| `POST` | `/api/statements/{id}/parse` | sync → lista transazioni + outflows_count |
| `POST` | `/api/statements/{id}/classify` | async → job_id. Result: `{candidates, skipped_italian}` |
| `POST` | `/api/statements/{id}/preview` | aggrega → `{autofatture[], skipped_italian[]}` con vat_id country-aware |
| `POST` | `/api/statements/{id}/verify-suppliers` | **NUOVO async** → lancia verify Gmail su tutti i fornitori |
| `GET` | `/api/statements/{id}/verify-suppliers/results` | stato per ogni fornitore |
| `POST` | `/api/autofatture/create` | async → job_id, salva RunHistory |
| `GET` | `/api/suppliers/verify-rejects` | lista PDF in quarantena |
| `GET` | `/api/suppliers/invoices/{supplier_key}/{file}` | stream PDF per preview |
| `GET\|POST\|DELETE` | `/api/suppliers/overrides` | CRUD override persistenti |
| `GET` | `/api/history` | ultimi 50 run |
| `GET` | `/api/history/{run_id}` | dettagli run |
| `GET` | `/api/jobs/{id}` | polling job async |
| `POST` | `/api/auth/login` · `/logout`, `GET /api/auth/me` | sessione (pubblici) |
| `GET` | `/api/healthz` | liveness, pubblico, non tocca FiC |
| `GET` | `/api/sdi/documents?date=&ids=` | autofatture su FiC con stato SDI |
| `POST` | `/api/sdi/verify` | async, verifica formale |
| `POST` | `/api/sdi/send` | async, richiede `confirm: "INVIA"` |

Tutte le `/api/*` tranne auth e healthz richiedono la sessione. Swagger UI solo in dev: [http://localhost:8000/docs](http://localhost:8000/docs). Contratto completo con esempi JSON: [`webapp/design/api_contract_v2.md`](design/api_contract_v2.md).

## Modalità dry-run

Per testare il flusso senza creare autofatture reali su FiC:

- **Per-richiesta**: toggle "Live ↔ Dry-run" nella topbar (stato persistito in localStorage)
- **Globale**: avviare il backend con `WEBAPP_DRY_RUN=true ./webapp/start.sh backend`

In dry-run il backend segue tutto il flusso ma nel create step salta la chiamata a `FicClient` e ritorna status `skipped` per ogni riga.

## Test automatico

E2E del backend sull'estratto reale, **senza chiamate Anthropic e senza scritture su FiC** (classificazione sostituita dai candidati salvati in `.tmp/cand_*.json`, creazione in dry-run, SDI in sola lettura):

```bash
cd webapp/backend
../../.venv/bin/python tests/e2e_real_statement.py /tmp/autofatture-e2e
```

Verifica login, parse + catena saldi, esclusioni, accorpamento mensile, controllo duplicati, dry-run e blocco dell'invio SDI senza conferma. Atteso sull'estratto ago-nov 2026: 66 autofatture, netto 9.938,31.

Il vecchio `tests/smoke_test_e2e.py` (19 step, server su :8001) resta valido per uso locale senza password.

## Troubleshooting

### `fic_token_valid: false` nell'health
Token FiC scaduto. Rigeneralo dal root del progetto:
```bash
python tools/fic_device_setup.py
```

### `classify` job va in error con `credit_balance too low`
Anthropic credits esausti. Due opzioni:
1. Acquista credits su [console.anthropic.com](https://console.anthropic.com) → Billing (è distinto da claude.ai — i credit Max non si travasano)
2. Passa al modello economico: `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` nel `.env`. Costa ~30x meno di Opus 4.6, sufficiente per classify.

### `verify-suppliers` step non trova fornitori
- Controlla `/api/health` → `gmail_tokens_ok.{personal,business}` devono essere `true`
- Se scaduti, rigenera: `python tools/gmail_oauth_setup.py --account personal` (e `business`)
- Fornitori non trovati potrebbero semplicemente non avere una fattura in Gmail (es. nuovo fornitore del mese corrente). Non è un bug.
- Bill-to mismatch: la fattura è nella mail ma intestata ad un'altra entità — è lo scenario Gamma/ElevenLabs. Regola operativa: autofattura emessa lo stesso, warning visibile in UI, da correggere sul portale del fornitore.

### `sqlalchemy` import error
Dipendenze non installate nel venv. Rilancia: `.venv/bin/pip install -r webapp/backend/requirements.txt`.

### Frontend: errore `Failed to fetch` o CORS
Il backend non è up, oppure è su porta diversa da 8000. Verifica: `curl http://localhost:8000/api/health`. CORS è già abilitato per `localhost:5173`.

### PDF preview non si apre nel Review
Il PDF per quel fornitore non è stato scaricato (verify step saltato o `not_found`). Torna allo step Verify e riesegui.

## File structure

```
webapp/
├── start.sh                  # avvio unificato backend + frontend (dev)
├── Dockerfile                # immagine unica per il deploy
├── Dockerfile.dockerignore   # allowlist del contesto di build
├── render.yaml               # Blueprint Render (servizio + disco)
├── README.md                 # questo file
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI + lifespan init DB
│   │   ├── settings.py       # carica .env root + sys.path tools/
│   │   ├── db.py             # SQLAlchemy engine + SessionLocal
│   │   ├── api/              # router: system, statements, suppliers, autofatture, jobs, history
│   │   ├── services/         # workflow, jobs, suppliers, overrides
│   │   └── models/           # schemas.py (Pydantic), db_models.py (SQLAlchemy)
│   ├── tests/
│   │   └── smoke_test_e2e.py # 19-step E2E test script
│   ├── requirements.txt
│   └── .tmp/                 # webapp.db, backend.log, statement cache
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # QueryClientProvider + Router + Toaster
│   │   ├── App.tsx           # Shell + routes
│   │   ├── lib/              # api.ts, queries.ts (React Query hooks), utils, theme
│   │   ├── types/api.ts      # TypeScript shapes dal contratto v2
│   │   ├── components/
│   │   │   ├── ui/           # 16 shadcn components
│   │   │   ├── layout/       # Shell, Sidebar, TopBar
│   │   │   └── domain/       # 9 componenti specifici: SupplierBadge, VatBadge, BillToWarning, PdfPreviewDialog, HealthIndicator, EnvironmentSwitch, StepProgress, EmptyState, Stat
│   │   └── pages/            # Dashboard, NewRun/{Upload,Processing,VerifySuppliers,Review,Creating,Results}, History, HistoryDetail, Settings
│   ├── tailwind.config.ts
│   ├── components.json       # shadcn config
│   └── package.json
└── design/
    ├── design_system.md
    ├── wireframes.md
    ├── interactions.md
    ├── api_contract_v2.md    # 520 righe, contratto con esempi JSON
    └── verify_pipeline_test_report.md
```

## Cosa NON e' incluso

- Multi-utente (una password, un'azienda)
- Piu' worker / piu' istanze: job e cache sono in memoria del processo
- OCR di PDF scansionati (solo pdfplumber su PDF testuali)
- Test automatici frontend
- Rinomina dei fornitori sull'anagrafica FiC esistente (es. "Dropbox Ireland" vs "Dropbox International"): si usa l'override paese, il nome resta quello del classificatore
