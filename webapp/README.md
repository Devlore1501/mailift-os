# Autofatture Webapp v2

Webapp locale per emettere autofatture passive (TD17/TD18/TD19 reverse charge) su Fatture in Cloud da estratti conto Revolut, con **verifica automatica dei fornitori via Gmail** e **logica IVA country-aware**.

Costruita sopra il workflow CLI in [`tools/`](../tools/) — non duplica logica fiscale, riusa `FicClient`, `parse_bank_statement`, `classify_transactions`, `verify_suppliers_from_email` come librerie Python.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite (`.tmp/webapp.db`) |
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui + React Query |
| Persistenza | SQLite (4 tabelle: Statement, Job, SupplierOverride, RunHistory) |
| Auth | Single user Mailift, nessuna autenticazione — pronto a evolvere |

## Avvio rapido

```bash
./webapp/start.sh
```

Apre backend (`:8000`) + frontend (`:5173`) in parallelo, logs affiancati con prefisso `[backend]` / `[frontend]`, Ctrl+C ferma entrambi. Poi vai su [http://localhost:5173](http://localhost:5173).

Solo backend: `./webapp/start.sh backend`. Solo frontend: `./webapp/start.sh frontend`.

## Setup one-time

Già fatto se lavori dal venv del progetto. In caso servisse rifarlo:

```bash
# 1. Python deps (sqlalchemy, fastapi, uvicorn, python-multipart, pdfplumber, anthropic)
.venv/bin/pip install -r webapp/backend/requirements.txt

# 2. Frontend deps (installa tutto: shadcn, tailwind, react-query, ecc.)
cd webapp/frontend && npm install
```

## Flusso utente (wizard 6 step)

1. **Upload** — drag&drop CSV/XLSX/PDF dell'estratto conto Revolut business
2. **Processing** — parser pandas + classificazione via Claude, identifica i fornitori soggetti a reverse charge, filtra automaticamente i fornitori italiani con IVA diretta (blacklist + defense-in-depth)
3. **Verify Suppliers** — step centrale: per ogni fornitore del preview, il backend cerca la fattura reale in Gmail (account personal + business), scarica il PDF, filtra per Bill to Mailift, e se c'è credit Anthropic analizza il PDF con Claude per estrarre paese/P.IVA/bill-to. Questo **corregge gli errori di classificazione** del classifier AI sui paesi fornitori.
4. **Review** — tabella editabile con VatBadge colorati (22% RC blu per UE, 0% viola per extra-UE), warning gialli per fornitori con Bill to non intestato a Mailift, icona PDF per preview delle fatture scaricate, accordion delle "transazioni escluse" (fornitori italiani filtrati). Editing inline descrizione/importo/exclude.
5. **Creating** — job async che crea le autofatture su FiC, progress bar live, lista con icon per ogni riga
6. **Results** — griglia card con numero FiC + link diretto + warning prominente "NON inviate al SDI, firma su FiC manualmente"

## Altre pagine

- **Dashboard** — health card (FiC, DB, Gmail, Anthropic), ultimi 5 run, CTA nuovo run
- **History** — lista run passati con filtri, dettaglio con lista autofatture
- **Settings → Override fornitori** — CRUD di correzioni persistenti per fornitore. Es. "Lovable Labs → country US" — si applica a tutti i run futuri automaticamente.
- **Settings → Sistema** — info backend, path DB, stato health esteso

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

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs). Contratto completo con esempi JSON: [`webapp/design/api_contract_v2.md`](design/api_contract_v2.md).

## Modalità dry-run

Per testare il flusso senza creare autofatture reali su FiC:

- **Per-richiesta**: toggle "Live ↔ Dry-run" nella topbar (stato persistito in localStorage)
- **Globale**: avviare il backend con `WEBAPP_DRY_RUN=true ./webapp/start.sh backend`

In dry-run il backend segue tutto il flusso ma nel create step salta la chiamata a `FicClient` e ritorna status `skipped` per ogni riga.

## Test automatico

Smoke test E2E completo del backend (19 step, no frontend):

```bash
# Terminal 1 — avvia backend su porta 8001 (non collide col dev server)
cd webapp/backend
../../.venv/bin/uvicorn app.main:app --port 8001

# Terminal 2 — esegui test
.venv/bin/python webapp/backend/tests/smoke_test_e2e.py
```

Copre: health, upload, parse, classify (con fallback seed se Anthropic esausto), preview, check critici country-aware, verify suppliers reale Gmail, create dry-run, history, CRUD overrides, verify-rejects.

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
├── start.sh                  # avvio unificato backend + frontend
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

## Cosa NON è incluso (out of scope)

- Auth multi-user (single-user Mailift)
- Deploy cloud (Dockerfile non creato)
- Invio automatico al SDI (firma manuale su FiC)
- OCR PDF scansionati (solo pdfplumber per PDF testuali)
- Test automatici frontend (Playwright) — solo smoke test backend
- Command palette Cmd+K
- Editing inline di country_iso nel Review (usa Settings → Override per correzioni persistenti)
