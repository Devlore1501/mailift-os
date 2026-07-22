# Verify pipeline — E2E test report

Report di `processes-eng` sulle Fasi 2-4 (test E2E verify-suppliers + smoke test
end-to-end di tutto il backend) del piano `rippling-beaming-bird`.

## Aggiornamento 2026-04-09 — Smoke test E2E completo

Aggiunto [webapp/backend/tests/smoke_test_e2e.py](../backend/tests/smoke_test_e2e.py),
script standalone che esercita TUTTI gli endpoint REST del backend in sequenza
(15 step, 19 assertion). Risultato finale: **19/19 pass**.

### Step coperti

1. `GET /api/health` — verifica campi nuovi `db_ok`, `gmail_tokens_ok`,
   `anthropic_api_ok`, `fic_token_valid`
2. `GET /api/config` — numeration, blacklist_count, payment_method
3. `POST /api/statements/upload` (CSV reale da `inbox/processed/`)
4. `POST /api/statements/{id}/parse` — count transazioni + outflows
5. `POST /api/statements/{id}/classify` async + poll, con fallback seed
   deterministico se Anthropic credit esaurito
6. `POST /api/statements/{id}/preview` — verifica presenza di `vat_id`,
   `vat_rate_percent`, `is_extra_ue`, `supplier_country_iso` per ogni
   autofattura/linea
7. **Test critico extra-UE** (OpenAI) → `vat_id=10`, `vat_rate_percent=0`,
   `is_extra_ue=True`
8. **Test critico UE** (Lovable, SE) → `vat_id=0`, `vat_rate_percent=22`,
   `is_extra_ue=False`
9. **Test critico Google Cloud Italy** → presente in `skipped_italian`,
   assente in `autofatture` (verificato col seed che lo include esplicitamente)
10. `POST /api/statements/{id}/verify-suppliers` async + poll, verifica che
    almeno un fornitore sia non-pending (positivo o non_found)
11. `GET /api/statements/{id}/verify-suppliers/results` — listing dettagliato
12. `POST /api/autofatture/create` con `dry_run=true`, verifica che
    `ok+errors+skipped == len(items)` e che venga scritta `RunHistory`
13. `GET /api/history` + `GET /api/history/{id}` — il run appena fatto compare
    e il detail include `result_json`
14. **CRUD overrides**: POST → GET → DELETE → GET (verifica rimozione)
15. `GET /api/suppliers/verify-rejects` — quarantena PDF

### Bug trovati durante il test e fixati

**Bug 1 — `build_preview` non filtrava fornitori IT (defense-in-depth gap)**

Sintomo (step 9 fail al primo run): inserendo "Google Cloud Italy Srl" tra i
candidates, l'autofattura compariva nel preview con `vat_id=0`, `vat_rate=22%`
(reverse charge), che è **fiscalmente errato**: i fornitori IT vanno in IVA
diretta 22%, mai in autofattura.

Root cause: `tools/classify_transactions.AUTOFATTURA_BLACKLIST` filtra i
fornitori IT a livello di classifier AI, ma `services/workflow.build_preview()`
si fidava completamente del classifier. Qualunque path che bypassasse il
classifier (override custom, candidates seedati a mano, futura regressione AI,
upsert diretto via API) avrebbe lasciato passare un'autofattura IT
fiscalmente invalida.

Fix in [services/workflow.py](../backend/app/services/workflow.py):
defense-in-depth nel loop di `build_preview()`: per ogni fornitore con
`country_iso == "IT"` (post-override), invece di emetterlo come autofattura
viene aggiunto a `extra_skipped` con reason "IT, IVA 22% diretta" e finisce
nella lista `skipped_italian` insieme a quelli filtrati dal classifier. Zero
modifiche al contratto API: il frontend continua a leggere `skipped_italian`
come prima, ora include anche le esclusioni post-classify.

Test rilanciato dopo il fix → **19/19 pass**, Google Cloud Italy correttamente
in `skipped_italian` e fuori da `autofatture`.

### Output del run finale

```
[OK]   step 1: GET /api/health
[OK]   step 2: GET /api/config
[OK]   step 3: POST /api/statements/upload — id=0233d225fa29
[OK]   step 4: POST /api/statements/{id}/parse — 66 tx, outflows=60
[WARN] classify fallito per Anthropic credit/rate, seeding candidates
[OK]   step 5: POST /api/statements/{id}/classify (seeded fallback) 7 candidates
[OK]   step 6: POST /api/statements/{id}/preview — 6 autofatture, 1 skipped IT
[OK]   step 7: extra-UE country-aware — OpenAI → vat_id=10, 0%, extra-UE
[OK]   step 8: UE country-aware — Lovable Labs → vat_id=0, 22% RC
[OK]   step 9: skipped_italian — 1 esclusi: Google Cloud Italy Srl
[OK]   step 10: POST /api/statements/{id}/verify-suppliers — job done, 6 fornitori
[OK]   step 11: GET verify-suppliers/results — 4 positivi (verified|pdf_only|bill_to_mismatch)
[OK]   step 12: POST /api/autofatture/create (dry-run) — items=6, skipped=6
[OK]   step 13: GET /api/history — 1 run per questo statement, detail ok
[OK]   step 14a/b/c/d: CRUD overrides
[OK]   step 15: GET /api/suppliers/verify-rejects — 82 PDF in quarantena

Smoke test summary: 19/19 pass, 0 fail, 1 warn
```

(L'unico WARN è il fallback seed perché Anthropic continua a essere senza
credit; il job `classify` AI fallisce ma il test prosegue con i candidates
deterministici. Quando i credit verranno ripristinati, anche il classify
diventerà un OK.)

### Edge case verificati

- **Anthropic API down/credit esauriti**: il classify AI fallisce → fallback
  seed via DB. Il `_anthropic_available()` di `services/suppliers.py` rileva
  il problema con un ping `max_tokens=1` e mette il verify in modalità
  `pdf_only` (scarica PDF, niente parsing Claude). Comportamento già
  validato e ribadito qui.
- **Gmail tokens parziali/mancanti**: il test stampa un WARN ma non
  fallisce; il verify torna `not_found` per tutti.
- **CSV con fornitore IT esplicito**: ora intercettato sia dal classifier
  blacklist che da `build_preview` defense-in-depth.
- **Job polling**: `_poll_job` con timeout configurabile (180s default
  classify, 600s default verify, 120s default create). Nessun timeout in
  questo run, classify fail in <5s, verify completo in ~52s, create in <3s.

### File modificati nel run smoke

- `webapp/backend/tests/smoke_test_e2e.py` — nuovo, 19 assertion
- `webapp/backend/app/services/workflow.py` — fix defense-in-depth IT in
  `build_preview()`

### Limitazioni note (invariate)

Vedi sezione "Limitazioni note" più sotto del report originale.

---

## TL;DR

La pipeline `POST /api/statements/{id}/verify-suppliers` funziona end-to-end
colpendo Gmail reale. 6/6 fornitori processati in 52 s, PDF scaricati dove
presenti, bill-to mismatch rilevati correttamente, nessuna eccezione non gestita
nel job async. Il fallback `pdf_only` su credit Anthropic esauriti è stato
trigger dal vivo ed è andato a buon fine.

## Cosa è stato testato

Script: [webapp/backend/tests/test_verify_e2e.py](../backend/tests/test_verify_e2e.py)

Flow eseguito contro backend reale (`uvicorn app.main:app --port 8001`):

1. `GET /api/health` → ok (fic_token_valid, db_ok, gmail_tokens_ok
   {personal+business}, anthropic_api_ok)
2. `POST /api/statements/upload` con
   `inbox/processed/20260408-042103_account-statement_01-Jan-2026_13-Mar-2026.csv`
   (66 transazioni, 60 outflow)
3. `POST /api/statements/{id}/parse`
4. `POST /api/statements/{id}/classify` (async, poll)
5. Fallback: quando classify fallisce per credit Anthropic esauriti, il test
   seeda 6 candidates deterministici via SQLAlchemy (Lovable, Apify, OpenAI,
   ElevenLabs, Hostinger, Gamma) e prosegue. Il seeding passa dal DB SQLite,
   quindi è letto dal processo backend come se provenisse dal classifier reale.
6. `POST /api/statements/{id}/preview` → 6 autofatture con `vat_id`/country
   corretti (SE/CZ/LT UE, US extra-UE)
7. `POST /api/statements/{id}/verify-suppliers` → job async
8. Poll `/api/jobs/{verify_job_id}` ogni 2 s fino a `done`
9. `GET /api/statements/{id}/verify-suppliers/results` → lista risultati

## Risultato E2E

```
[verify] job_id=48574ee54195
  [1/6] Lovable Labs            -> pdf_only           (pdfs=2, 2.1s)
  [2/6] Apify Technologies      -> pdf_only           (pdfs=2, 1.8s)
  [3/6] OpenAI                  -> not_found          (7.0s)
  [4/6] ElevenLabs              -> bill_to_mismatch   (quarantine hit, 12s)
  [5/6] Hostinger               -> not_found          (2.0s)
  [6/6] Gamma Tech              -> bill_to_mismatch   (quarantine hit, 27s)
Totale: 52.2s
Positives (verified|pdf_only|bill_to_mismatch): 4/6 → PASS
```

**Nota chiave**: il job ha continuato a girare senza mai fallire nonostante il
ping Anthropic iniziale fosse negativo (credit esauriti). Il service ha rilevato
il fallback e processato tutto in modalità `pdf_only` (scarica PDF, niente
parsing Claude). Il frontend potrà comunque mostrare il PDF scaricato, senza i
campi estratti. Esattamente il comportamento richiesto in Fase 4 del mandato.

## Cosa ha funzionato subito

- `suppliers_svc.run_verify_for_preview` itera correttamente sul preview dal DB
- `BackgroundTasks` + `JobManager` write-through a SQLite: nessuna race, nessun
  `progress_cb` perso, polling `/api/jobs/{id}` risponde in modo coerente
- Cache `_anthropic_ping_cache` per-processo: il ping viene fatto una volta sola
  all'inizio del job invece di N volte per-fornitore
- `vsfe.find_invoices_for_supplier` con cwd del backend diverso da root
  progetto: nessun issue, perché il tool usa `ROOT = Path(__file__).parent.parent`
  internamente — path-safe
- Gmail OAuth via `load_service()` in thread background: funziona, token riusabili
- La quarantena `.tmp/invoices_rejected/<key>/` viene correttamente riconosciuta
  come `bill_to_mismatch` (ElevenLabs, Gamma)

## Cosa è stato fixato

1. **Logging strutturato** configurato in [webapp/backend/app/main.py](../backend/app/main.py):
   root logger a livello INFO, formatter
   `%(asctime)s %(name)s %(levelname)s %(message)s`, handler stdout + rotating
   file `webapp/backend/.tmp/backend.log` (2 MB × 3 backups). I logger
   `uvicorn.*` sono ricablati sul root per non duplicare.

2. **Robustezza `services/suppliers.py`**
   - `_anthropic_available()` ora fa un vero ping (`max_tokens=1` messaggio
     banale) invece di guardare solo l'ENV, e cacha il risultato per processo.
     Se il ping fallisce, il job non si blocca: setta `status=pdf_only`.
   - Nuovo stato `pdf_only` aggiunto a `VerifyStatus` in
     [models/schemas.py](../backend/app/models/schemas.py) così il frontend
     può mostrare il PDF senza i dati strutturati.
   - Logging dettagliato per-fornitore (name, pdf_count, status, latency) + stack
     trace su errori Gmail / `analyze_pdf`.
   - Soft cap per-fornitore `PER_SUPPLIER_TIMEOUT_S = 30.0` (warning a log se
     superato). La processazione resta seriale: 16 fornitori stanno sotto 8 min.
   - `progress_cb` avvolto in try/except per non bloccare il loop se il manager
     è in stato inconsistente.

3. **Error reporting job in `api/suppliers._run_verify_job`**: ora salva nel
   campo `error` del Job la stringa `<ExcType>: <msg>\n<traceback>` completa,
   invece del solo `str(e)`. Il frontend vede lo stack quando apre il dettaglio
   job fallito.

4. **Log path**: `main._setup_logging` scrive in `webapp/backend/.tmp/backend.log`
   (non in `webapp/.tmp/`, che è riservato al DB + statements), come da mandato.

## Limitazioni note

- **Credit Anthropic esauriti** (al momento del test: `invalid_request_error,
  credit balance is too low`). Questo ha bloccato sia il classify AI sia
  l'`analyze_pdf` del verify. Per il test il classify è stato bypassato con un
  seed deterministico, e il verify è stato dimostrato funzionare in modalità
  `pdf_only`. Quando i crediti saranno ripristinati, un rerun del test colpirà
  il path `status=verified` con `extracted` popolato da Claude.
- **OpenAI / Hostinger not_found**: normale. Non ci sono fatture degli ultimi
  2 anni in Gmail per quei fornitori dal punto di vista dell'utente Mailift.
- **ElevenLabs / Gamma bill_to_mismatch**: atteso. PDF presenti ma intestati al
  nominativo personale dell'utente, non a Mailift Srl. La quarantena
  `.tmp/invoices_rejected/` viene intercettata correttamente.
- **Higgsfield non testato**: nessuna transazione per quel fornitore nel CSV
  del periodo.
- **Parallelismo**: i fornitori vengono processati in serie. Con 16 fornitori
  tipici, ~2-3 min a fine pipeline è accettabile. Parallelismo controllato
  (es. `asyncio.Semaphore`) può essere aggiunto in una fase successiva se si
  vuole scendere sotto il minuto, ma comporta rischi sul token Gmail condiviso.
- **Cancel del verify job**: non ancora supportato. Un job in flight non può
  essere interrotto dall'esterno — finisce la sua iterazione o va in error.
  Marcato come opzionale dal mandato.

## Come rilanciare il test

```bash
# terminal 1: backend
cd "/Users/lorenzobaretta/workflow ai/webapp/backend"
source ../../.venv/bin/activate
uvicorn app.main:app --port 8001 --host 127.0.0.1

# terminal 2: test
cd "/Users/lorenzobaretta/workflow ai"
source .venv/bin/activate
python webapp/backend/tests/test_verify_e2e.py
```

Opzioni:

```bash
python webapp/backend/tests/test_verify_e2e.py --base-url http://127.0.0.1:8001
python webapp/backend/tests/test_verify_e2e.py --csv /path/to/file.csv
python webapp/backend/tests/test_verify_e2e.py --verify-timeout 900
```

Quando i crediti Anthropic saranno ripristinati, togliere il seed fallback
è banale: il classify job andrà a buon fine da solo.

## File toccati

- `webapp/backend/app/main.py` — setup logging root + rotating file handler
- `webapp/backend/app/services/suppliers.py` — Anthropic ping, logging,
  pdf_only fallback, soft timeout, error paths
- `webapp/backend/app/api/suppliers.py` — stack trace in job.error, logging
- `webapp/backend/app/models/schemas.py` — `VerifyStatus` + `"pdf_only"`
- `webapp/backend/tests/test_verify_e2e.py` — nuovo test integration
- `webapp/backend/.tmp/backend.log` — output log (runtime, gitignorable)
