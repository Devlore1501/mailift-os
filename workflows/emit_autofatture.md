# Emit Autofatture from Bank Statements

## Obiettivo
Automatizzare l'emissione delle autofatture passive (reverse charge UE / extra-UE,
TD17 / TD18 / TD19) partendo da un estratto conto bancario, creando i documenti
direttamente su Fatture in Cloud.

Per ciascun fornitore identificato dall'AI viene creata **una sola autofattura**
con **una sola riga aggregata** (importo totale del periodo accorpato), data di
emissione = data del run, sezionale `a`, stato pagamento "Stornato", regime
fiscale "Inversione contabile art.7 ter". La fattura resta in stato `not_sent`
(non inviata al SDI) finche' l'utente non clicca "Verifica formale" + "Firma e
invia" sulla UI di FiC.

## Due modi per usarlo

### 1. Webapp v2 (consigliato per uso interattivo)
La webapp locale in [webapp/](../webapp/) wrappa tutto il workflow con UI shadcn/ui:
- Drag&drop dell'estratto conto
- Step "Verifica fornitori" che scarica le fatture PDF reali da Gmail (personal+business) e pre-popola i dati fiscali
- Country-aware vat_id automatico (UE 22% RC vs extra-UE 0% non soggetta)
- Auto-skip dei fornitori italiani con IVA diretta (Google Cloud Italy ecc.) con box trasparenza
- Override fornitori persistenti su SQLite
- Storico run consultabile
- Dry-run switch globale per simulare senza creare

Avvio:
```
# Backend
cd webapp/backend && source ../../.venv/bin/activate && uvicorn app.main:app --port 8000
# Frontend (altro terminale)
cd webapp/frontend && npm run dev
# Apri http://localhost:5173
```

Documentazione interna: [webapp/design/api_contract_v2.md](../webapp/design/api_contract_v2.md), [webapp/design/design_system.md](../webapp/design/design_system.md), [webapp/design/verify_pipeline_test_report.md](../webapp/design/verify_pipeline_test_report.md).

### 2. Automazione mensile via scheduler (consigliato per uso ricorrente)
Il job `monthly_autofatture` nello scheduler ([tools/scheduler.py](../tools/scheduler.py))
esegue la pipeline completa ogni **10 del mese alle 09:00** in automatico:

1. Scarica le transazioni del mese precedente via **Revolut Business API**
   ([tools/revolut_client.py](../tools/revolut_client.py))
2. Classifica con AI, accorpa per fornitore, crea su FiC
3. Manda notifica su Telegram con il riepilogo

**Setup one-time richiesto:**
- `REVOLUT_API_KEY` nel `.env` (Settings > APIs > Add access token, scope: Read Transactions)
- Il bot Telegram deve girare (`python tools/telegram_bot.py`)

Per eseguire manualmente fuori ciclo:
```
python tools/monthly_autofatture.py              # mese scorso
python tools/monthly_autofatture.py --dry-run    # anteprima senza FiC
python tools/monthly_autofatture.py --force      # riesegui se report esiste già
```

Oppure dal bot Telegram: `/run monthly_autofatture`

### 3. CLI (script puro, per un estratto specifico)
Per processare un file specifico (es. estratto carta separato, periodi arretrati).
Vedi sezione "Esecuzione" più sotto.

## Quando usarlo
- Periodicamente (consigliato settimanale / fine mese) per non accumulare arretrato.
- Ogni volta che l'utente carica un nuovo estratto conto in [inbox/](inbox/) (modalità CLI) o lo trascina nella webapp.

## Input richiesti
- File estratto conto: PDF (testuale, non scansionato), CSV, XLS o XLSX.
- `.env` correttamente configurato (vedi `.env.example`):
  - `FIC_CLIENT_ID`, `FIC_CLIENT_SECRET`, `FIC_ACCESS_TOKEN`, `FIC_REFRESH_TOKEN`, `FIC_COMPANY_ID`
  - `FIC_NUMERATION` (default `a`)
  - `FIC_PAYMENT_ACCOUNT_NAME` (default `Revolut`)
  - `ANTHROPIC_API_KEY`

## Setup iniziale (una tantum)

### 1. App OAuth2 su Fatture in Cloud
Vai su <https://developers.fattureincloud.it/> e crea una nuova app:
- Tipo: **OAuth 2.0**
- Redirect URI: `http://localhost:8765/callback` (formalita', non lo useremo)
- Scope da spuntare:
  - Anagrafica fornitori (lettura + tutto)
  - Documenti emessi - Autofatture (lettura + tutto)
  - Impostazioni (lettura)

Copia `client_id` e `client_secret` in `.env`.

### 2. Aliquote IVA e conti di saldo
- Verifica che esista in FiC l'aliquota **"Inversione contabile, art.7 ter"**
  (Impostazioni > Aliquote IVA). Sull'account Mailift è id `11`. Lo script la
  cerca per descrizione e ne usa l'id automaticamente.
- Verifica che esista almeno un conto di saldo (Impostazioni > Conti di saldo).
  Lo script preferisce un conto chiamato "Revolut", o usa il primo disponibile.
  Override via `FIC_PAYMENT_ACCOUNT_NAME` nel `.env`.
- Verifica che esista un **sezionale dedicato** per le autofatture (default `a`).
  Override via `FIC_NUMERATION` nel `.env`.

### 3. Venv e dipendenze
```
cd "/Users/lorenzobaretta/workflow ai"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Authentication via Device Code flow
```
python tools/fic_device_setup.py
```
Lo script stampa un URL (`https://fattureincloud.it/connetti`) e un codice
tipo `XXXX-YYYY`. Vai sull'URL nel browser, incolla il codice, autorizza. Lo
script polla finche' non sei a posto e salva da solo `FIC_ACCESS_TOKEN`,
`FIC_REFRESH_TOKEN`, `FIC_COMPANY_ID` nel `.env`.

**Importante**: il flow Authorization Code (con browser callback) e' risultato
inutilizzabile su FiC per via di una grant "stuck" lato server (errore
`invalid_grant - token expired` anche con code freschi). Usare SOLO il device
code flow.

## Esecuzione

### Modo manuale
```
python tools/run_autofatture.py inbox/estratto.csv --dry-run    # anteprima senza FiC
python tools/run_autofatture.py inbox/estratto.csv              # crea su FiC
```
Flag utili:
- `--dry-run` -> nessuna chiamata a FiC, salva il piano in `.tmp/autofatture_plan.json`
- `--min-confidence high` -> processa solo righe con alta confidenza dal classificatore (default `medium`)

### Modo schedulato (settimanale)
1. Carichi gli estratti conto in [inbox/](inbox/)
2. Cron lancia [tools/process_inbox.sh](tools/process_inbox.sh) che processa tutti i file e li sposta in `inbox/processed/`.
3. Crontab esempio (lunedì ore 9:00):
   ```
   0 9 * * 1 /Users/lorenzobaretta/workflow\ ai/tools/process_inbox.sh >> /Users/lorenzobaretta/workflow\ ai/.tmp/cron.log 2>&1
   ```
4. Risultato: ogni lunedì trovi le autofatture pronte da rivedere su FiC.

## Cosa fa lo script (sequenza)
1. **`tools/parse_bank_statement.py`** estrae le transazioni dal file in formato uniforme.
2. **`tools/classify_transactions.py`** chiede a Claude di identificare le righe che richiedono
   autofattura (tool use). Per ognuna restituisce: `type_doc`, `supplier_name`, `supplier_country`,
   `supplier_vat_number`, `description`, `vat_rate`, `confidence`, `reason`.
3. L'orchestratore **accorpa** per `(fornitore_normalizzato, type_doc, valuta)` e crea una sola
   `AutofatturaInput` per gruppo, con UNA SOLA riga aggregata e descrizione neutra (no date dei
   movimenti, no conteggio addebiti).
4. **`tools/fic_client.py`** per ogni gruppo:
   - cerca il fornitore esistente con matching robusto (per `vat_number` esatto, poi per nome
     normalizzato senza suffissi societari, poi per "kernel" del nome). Se non lo trova lo crea.
   - per fornitori extra-UE senza P.IVA applica i fix CAP `00000`, provincia `EE`,
     `vat_number=OO99999999999` come da guida ufficiale FiC.
   - crea la self_supplier_invoice con `e_invoice=true`, sezionale `a`, payment status `reversed`.
5. Scrive `.tmp/autofatture_report.json` con id, numero documento, totale per ogni gruppo.

## ⚠ Invio al SDI — passaggio separato e deliberato
`run_autofatture.py` **non invia nulla al SDI**: lascia tutte le autofatture in stato
`not_sent`, modificabili. Il controllo umano va fatto QUI, perché dopo l'invio l'unico
rimedio è una nota di variazione. Rivedi aliquota, fornitore, importo, indirizzo.

Poi hai due strade equivalenti:

**A. UI di Fatture in Cloud** — FiC > Fatture e Documenti > Autofatture, per ognuna
"Verifica formale" → "Firma e invia".

**B. In batch da CLI** ([tools/send_autofatture_sdi.py](../tools/send_autofatture_sdi.py),
aggiunto 2026-08-22):
```
python tools/send_autofatture_sdi.py --date 2026-08-22             # SOLO verifica formale
python tools/send_autofatture_sdi.py --date 2026-08-22 --confirm   # verifica + invio
python tools/send_autofatture_sdi.py --date 2026-08-22 --status    # stato SDI del batch
```
Senza `--confirm` fa solo la verifica formale (read-only) e si ferma; i documenti che non
la superano non vengono mai inviati; quelli già inviati vengono saltati.

Endpoint usati (non erano documentati in questo workflow):
- `GET  /c/{company}/issued_documents/{id}/e_invoice/xml_verify` → verifica formale
- `POST /c/{company}/issued_documents/{id}/e_invoice/send` (body `{"data":{}}`) → firma e invia
- `GET  /c/{company}/issued_documents/{id}/e_invoice/xml` → XML SDI generato (risposta **non JSON**:
  va letta con `requests.get(...).text`, non con `_request()`)
- `GET  /c/{company}/issued_documents/{id}/e_invoice/error_reason` → motivo dello scarto

Progressione degli stati: `not_sent` → `pending`/`processing` → `sent` → `delivered` (o
`rejected`). L'esito definitivo arriva entro qualche ora: **ricontrolla sempre con `--status`**
il giorno dopo, uno scarto SDI non notificato resta un adempimento non assolto.

## Edge case noti
- **PDF scansionati**: il parser usa `pdfplumber`, non OCR. Se il PDF è un'immagine
  va prima passato a un OCR (non incluso). Meglio chiedere l'export CSV/XLSX dal portale.
- **P.IVA fornitori esteri**: il classificatore prova a fornirla per i fornitori notori.
  Per fornitori sconosciuti `vat_number` arriverà vuoto → rivedere a mano.
- **Movimenti aggregati su carta**: se la banca aggrega più addebiti, una singola riga
  PDF può non bastare. Usare l'export movimenti carta separato.
- **Doppi pagamenti**: lo script NON deduplica contro autofatture già emesse. Per ogni
  periodo nuovo esegui sempre `--dry-run` PRIMA per controllare.
- **CSV Revolut con date in formato ISO YYYY-MM-DD**: pandas con `dayfirst=True`
  swappava giorno/mese; il parser ora rileva il formato ISO e lo usa esplicitamente.
- **Float `-275.0` da pandas**: la regex per gli importi pretendeva 2 decimali e
  scartava `-275.0`. Il parser ora accetta float direttamente.
- **Il classificatore può confondere il paese del fornitore**: capita su nomi simili
  (es. Mailsupply marcato come DE quando è US). Verificare sulla UI di FiC dopo creazione.
- **Fornitori "finti esteri" che in realtà fatturano con IVA italiana**: Google Workspace
  per i clienti italiani è fatturato da **Google Cloud Italy S.r.l.** (P.IVA IT11256580967)
  con IVA 22% italiana già addebitata. Il classificatore lo vede come Google Ireland (per
  il nome del dominio) e propone un'autofattura, ma è sbagliato: va in Fatture ricevute
  come TD01. Aggiungere una lista di fornitori "blacklist per autofattura" in
  `classify_transactions.py` se il caso si ripete.

## ⚠ Pre-check CRITICO prima di emettere (lezioni sessione 2026-04-08 serale)

Prima di lanciare `run_autofatture.py`, **devi** aver verificato queste cose per i fornitori
che appaiono sull'estratto conto. Se salti questo passaggio, rischi di emettere
autofatture errate che vanno poi cancellate a mano, con costi fiscali reali.

### 1. L'operazione richiede davvero un'autofattura?
Non tutti i pagamenti con la carta Revolut aziendale generano un'autofattura passiva.
Le eccezioni ricorrenti:

- **Fornitore italiano con P.IVA IT**: emette una normale fattura passiva italiana
  (TD01) con IVA 22% già addebitata. Non è reverse charge. Va in "Fatture ricevute",
  non in autofatture. Esempi scoperti sul campo:
    - **Google Workspace** → fatturato da **Google Cloud Italy S.r.l.** (P.IVA
      IT11256580967) con IVA italiana diretta. NON autofattura. Sessione 2026-04-08:
      ho emesso 20/a Google e ho dovuto cancellarla.
- **Servizio B2C (consumatore)**: se il fornitore ti fattura come privato (nessuna
  P.IVA sul Bill to, nome tipo "Tuo Nome Personale" o "Workspace"), allora non c'è
  reverse charge e quindi non c'è autofattura per Mailift. Tecnicamente è una spesa
  personale pagata con la carta aziendale → nota spese / rimborso / fringe benefit.
  Esempi: **Gamma Tech**, **Klaviyo** (admin di account clienti), **ElevenLabs** —
  scoperti via email scraping (vedi "Verifica via email scraping" sotto).

### 2. Il fornitore è UE o extra-UE?
Determina la scelta di `vat_id` nell'autofattura (vedi regola sotto). Verificato via
lettura fatture reali + confronto con autofatture 2025 del commercialista:

| Tipo fornitore  | vat_id | Descrizione             | RegimeFiscale | Esempi                     |
|-----------------|--------|-------------------------|---------------|----------------------------|
| UE              | 0      | 22% reverse charge      | RF01          | Meta IE, Apify CZ, DKV DE  |
| extra-UE        | 10     | Oper. non soggetta art.7-ter (0%) | RF18 | Lovable US, Myleadfox AE, OpenAI US |

Questa distinzione è implementata country-aware in `FicClient.get_vat_id_for_autofattura`
e viene applicata automaticamente a partire dal country_iso del fornitore.

**IMPORTANTE**: sia fornitori UE che extra-UE arrivano con "0% reverse charge" SULLA
LORO fattura. La differenza tra id=0 (22%) e id=10 (0%) è nell'autofattura italiana,
non nella fattura del fornitore — lato italiano i servizi intra-UE si riportano con
IVA 22% neutralizzata, quelli extra-UE come "non soggetta".

### 3. Il Bill to è davvero Mailift?
Molti SaaS tengono una billing address vecchia o personale (Gmail personale, vecchia
P.IVA). Se paghi col Revolut aziendale ma il billing è ancora sul tuo account privato,
la fattura non è tecnicamente intestata a Mailift. Casi veri:

- Gamma, ElevenLabs → billed to "Lorenzo Baretta's Workspace" + gmail personale
- Google Workspace → P.IVA vecchia IT03058670591 invece di IT18160081008
- Klaviyo → billed a entità cliente diversa

**Cosa fare**: decisione operativa presa con l'utente — per semplicità, se il
pagamento è stato fatto con la carta Mailift si emette comunque l'autofattura
(con vat_id country-aware), ma vanno corretti progressivamente i billing data sui
portali dei fornitori (pannello Billing di ognuno → inserire nome Mailift Srl,
P.IVA IT18160081008, indirizzo Via Casilina 1940, 00132 Roma).

## Verifica via email scraping (`tools/verify_suppliers_from_email.py`)

Per ridurre gli errori del pre-check, il workflow include un tool che scarica le
fatture PDF reali dalle caselle Gmail (personal + business) e le classifica:

```
python tools/verify_suppliers_from_email.py --skip-analysis --max-per-supplier 2
python tools/verify_suppliers_from_email.py --supplier openai
```

Caratteristiche:
- Ricerca in ordine: business account → personal account (fallback)
- Query multiple per fornitore: `from:dominio`, `subject:invoice + keyword`, fallback
  keyword-only
- Pre-filtro locale via `pdfplumber`: scarta PDF il cui Bill to **non** contiene la
  P.IVA `18160081008` o il nome "mailift". I PDF scartati finiscono in
  `.tmp/invoices_rejected/<supplier>/` per ispezione manuale.
- `--skip-analysis` scarica i PDF senza analizzarli (utile quando vuoi leggerli
  direttamente). Senza flag, ogni PDF viene passato a Claude Opus 4.6 con
  `document` block + tool use per estrarre i campi fiscali strutturati.

Richiede: token Gmail per i due account (vedi `tools/gmail_oauth_setup.py`) + credit
Anthropic API per l'analisi automatica.

## Note sui payload FiC scoperte sul campo (sessioni 2026-04-07/08)
Per creare una `self_supplier_invoice` valida via API serve il payload completo:

1. **`type=self_supplier_invoice` + `e_invoice=true`** — il campo `ei_data` (incluso il
   sotto-tipo TD17/18/19) viene **ignorato** dal server FiC se `e_invoice=false`. Verificato
   nel SDK: `IssuedDocumentEiData` ha il commento `[Only if e_invoice=true]`.

2. **TipoDocumento TD17/18/19 va in `ei_raw`, NON in `ei_data`** ⚡ FIX CRITICO sessione 2026-04-08.
   Il SDK `IssuedDocumentEiData` non espone `document_type`. Il TipoDocumento SDI si imposta
   nel campo "raw" `ei_raw`, che è un dump JSON dei tag XML della fattura elettronica:

   ```json
   "ei_raw": {
     "FatturaElettronicaBody": {
       "DatiGenerali": {
         "DatiGeneraliDocumento": {
           "TipoDocumento": "TD17"
         }
       }
     },
     "FatturaElettronicaHeader": {
       "CedentePrestatore": {
         "DatiAnagrafici": {
           "RegimeFiscale": "RF18"
         }
       }
     }
   }
   ```

   **Senza questo campo, FiC genera un XML invalido e la verifica formale SDI fallisce.**
   Verificato leggendo le autofatture vere create a mano dal commercialista (Anthropic, Notion,
   Meta) — tutte hanno questo blob in `ei_raw`. RegimeFiscale = RF01 per fornitori UE,
   RF18 per fornitori extra-UE.

3. **`entity.country` va in italiano**, non come ISO. Es. "Stati Uniti", "Irlanda", "Germania".
   Mappa ISO→italiano gestita in `_COUNTRY_NAMES_IT` di `fic_client.py`. country_iso può
   essere passato in parallelo ma FiC usa il nome italiano nel rendering.

4. **`entity.ei_code` = codice destinatario del COMMITTENTE** (M5UXCR1 per Mailift Srl), NON del
   fornitore. È contro-intuitivo ma è così perché in autofattura passiva tu sei sia
   l'emittente sia il destinatario del documento elettronico. Configurabile via env
   `FIC_DESTINATARIO_CODE`.

5. **Aliquota IVA: country-aware UE vs extra-UE** (fix definitivo sessione 2026-04-08 serale).
   Le autofatture 2025 del commercialista mostrano chiaramente il pattern:
   - Fornitori UE (Meta IE, Apify CZ, Miro NL, Paddle UK pre-brexit, UAB Holo LT, DKV DE) →
     **vat_id=0** (22% standard, reverse charge con IVA neutralizzata input/output)
   - Fornitori extra-UE (Notion US, Lovable US, Antifragile UAE, Anthropic US, OpenAI US,
     Higgsfield US, Myleadfox AE, ElevenLabs US, Gamma US) → **vat_id=10**
     ("Oper. non soggetta, art.7 ter", 0%)

   Il metodo `FicClient.get_vat_id_for_autofattura(country_iso)` implementa questa logica:
   se `country_iso` è nel set `_EU_COUNTRIES` restituisce 0, altrimenti 10. GB/UK sono
   trattati come extra-UE post-Brexit. L'env `FIC_VAT_ID` resta come escape hatch manuale.

   **Calcolo gross**: per vat_id=0 (22%), `gross_price = net * 1.22` e `payment.amount = gross`.
   Per vat_id=10 (0%), `gross_price = net = payment.amount` (nessuna IVA aggiunta).
   Calcolato dinamicamente leggendo `value` dell'aliquota da `/info/vat_types`.

   Errore scoperto sul campo (stesso sessione): avevo inizialmente hard-coded vat_id=0 per
   tutti (con env `FIC_VAT_ID=0`). Ha funzionato per i fornitori UE ma ha prodotto autofatture
   sbagliate per 7 fornitori extra-UE (14/a, 18/a, 21/a, 22/a, 24/a, 25/a, 28/a) — tutte
   corrette a posteriori via PUT con `tools/fix_autofatture_vat.py`.

6. **`vat: {id: <id>}`** — passare l'id, NON `{value: 22}` → errore `vat.id field is required`.

7. **Number**: omettere completamente il campo, NON passare 0 → errore `must be at least 1`.
   FiC assegna automaticamente il progressivo del sezionale.

8. **Numeration**: passare `numeration: "a"` (o env `FIC_NUMERATION`) per usare il sezionale
   dedicato delle autofatture, separato dalla numerazione delle fatture attive.

9. **Payments_list**: obbligatorio. `payments_sum` deve coincidere con `amount_due` (il LORDO),
   `status: "reversed"` (= "Stornato" sulla UI, default per autofatture come da guida FiC),
   `payment_account.id` valorizzato.

10. **Entity inline**: passare `{id, name, country, country_iso, vat_number, ei_code}`. Solo id
    non basta → errore `entity.name field must not be empty`.

11. **Fornitori esteri — pattern SDI-valido** (scoperto analizzando le autofatture
    effettivamente inviate e accettate dal SDI dal commercialista, sessione 2026-04-08):
    - `address_province`: **`"ee"` LOWERCASE** (non `"EE"` uppercase come dice la guida FiC pubblica)
    - `address_postal_code`: sempre `"00000"`
    - `vat_number`: **VUOTO** per fornitori esteri (la guida suggerisce `OO99999999999`
      ma SDI lo accetta vuoto quando `country` e `country_iso` sono valorizzati correttamente)
    - `address_street`: **obbligatorio**, non può essere vuoto (errore SDI:
      "Nei dati del Cedente Prestatore, il campo Indirizzo non e' nel formato valido").
      Placeholder `"Estero"` se non noto.
    - `address_city`: nome del paese lowercase se la citta' non e' nota
      (es. `"stati uniti"`, `"germania"`, `"irlanda"`)
    - Sempre impostare `ei_code` al codice destinatario di Mailift (`M5UXCR1`).

12. **Token JWT con prefisso `c/...`**: i code OAuth restituiti da FiC sono JWT prefissati
    da `c/`. Il prefisso va MANTENUTO quando si scambia per il token (rimuoverlo causa
    `error decoding the token`).

## Lezioni sessione 2026-08-22 (estratto luglio 2026)

### 1. Il classificatore SALTA fornitori ricorrenti di importo piccolo
Nel primo dry-run di luglio mancavano **Myleadfox (16,67)** e **Digital Media LLC (20,00)**,
entrambi già autofatturati nei mesi precedenti (21/a, 30/a e 32/a, 50/a). Il modello li aveva
scartati perché ambigui/di importo basso.
**Fix applicato**: sezione "FORNITORI RICORRENTI GIA' AUTOFATTURATI" nel `SYSTEM_PROMPT` di
`classify_transactions.py` con la lista dei fornitori noti + la regola "l'obbligo di autofattura
non ha soglia di importo".
**Regola operativa**: dopo ogni dry-run, riconcilia SEMPRE i movimenti in uscita del CSV con il
piano e verifica che ogni esclusione sia motivata (fornitore IT, giroconto, stipendio, F24).

### 2. Le P.IVA estere venivano allucinate dal classificatore
Su tre run diversi Revolut Payments UAB ha ricevuto tre P.IVA diverse (LT100013740611 su 17/a,
LT100013710611 su 38/a, LT100013613010 su 51/a): **tutte e tre INVALID su VIES**. Su 35/a a
Dropbox era finita `IE3668997OH`, che su VIES risulta essere **Google Cloud EMEA Limited**.
Causa: in `create_self_supplier_invoice` l'entity usava `af.supplier_vat_number or supplier.vat_number`,
cioè il valore inventato dall'AI vinceva su quello in anagrafica.
**Fix applicato** in `fic_client.py`:
- nuova funzione `vies_check(vat)` → `True` / `False` / `None` (non verificabile) via
  `https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{cc}/vat/{num}`
- l'entity ora preferisce la P.IVA in anagrafica FiC e, se VIES risponde INVALID, **la svuota**
  (SDI accetta la P.IVA estera vuota — vedi nota 11 — mentre una P.IVA sbagliata rende il
  documento errato). Stessa validazione anche in `find_or_create_supplier`.
- il prompt del classificatore ora vieta esplicitamente di indovinare la P.IVA.

P.IVA verificate VALID su VIES (usabili con fiducia): Apple `IE9700053D`, Meta `IE9692928F`,
Dropbox `IE9852817J`. Da trovare sulla fattura vera: Revolut Payments UAB, Hostinger International.

### 3. Verifica via email scraping non disponibile
Il token Gmail dell'account **personal** è scaduto (`invalid_grant`) e la maggior parte delle
ricevute SaaS arriva lì. Rifare `python tools/gmail_oauth_setup.py --account personal` per
riabilitare il pre-check sulle fatture reali.

### 4. Lovable è statunitense — CHIUSO sulla fattura vera
Fattura **0LNAHU2R-0019 del 24/07/2026**: emittente **Lovable Labs Incorporated, 1111b South
Governors Avenue, Dover, Delaware 19904, United States**, "Tax to be paid on reverse charge basis",
0%. Bill to corretto: mailift srl, Via Casilina 1940, 00132 Roma, IT VAT IT18160081008 (l'email
sul portale è ancora la gmail personale — da cambiare nel pannello Billing di Lovable).
Quindi Lovable è **extra-UE → vat_id=10, RF18**, e la country "Svezia" in anagrafica FiC era
sbagliata (probabilmente per via di "Lovable AB", entità diversa).

Corretto il 22/08/2026: anagrafica fornitore 50070423 (country Stati Uniti + indirizzo reale) e
autofattura 61/a (vat 0→10, lordo 30,50→25,00, RF01→RF18). Prompt del classificatore aggiornato.

### 5. DatiFattureCollegate: si lasciano vuoti
Tentato di popolare `ei_data.od_number` / `od_date` con il numero della fattura reale: FiC richiede
anche `original_document_type` e rifiuta i valori provati (`invoice`, `TD01`, `supplier_invoice`)
senza documentare l'enum. Verificato che **nessuna** delle 60 autofatture storiche — comprese quelle
del commercialista accettate dal SDI — ha quei campi valorizzati: non servono, lasciarli vuoti.

### 6. Ambiguità ancora aperta
- **Paddle.com Market Ltd (GB)**: 15/a del 2025 usava vat_id=0 (22%), la regola attuale post-Brexit
  lo tratta come extra-UE → vat_id=10 (65/a). Allineare la scelta con il commercialista.

## Suppliers duplicati - cosa fare
Se ti accorgi che FiC ha duplicati (succede se il matching fallisce), usa
[tools/cleanup_suppliers.py](tools/cleanup_suppliers.py): ne contiene una lista hard-coded
per la sessione 2026-04-08, ma puoi modificarla per pulire altri casi futuri.
Lo script chiede conferma e cancella via `DELETE /entities/suppliers/{id}`.

Il matching robusto in `find_or_create_supplier` ora cerca:
1. Match esatto `vat_number` (case-insensitive, trim)
2. Match nome normalizzato (lowercase, senza punteggiatura, senza suffissi societari)
3. Substring "kernel" del nome (es. "google" → "Google Ireland Limited")

## Auto-improvement loop
Quando una classificazione è sbagliata o una creazione fallisce:
1. Aggiorna `SYSTEM_PROMPT` in `tools/classify_transactions.py` con la regola mancante
2. Se il fallimento è un payload FiC, aggiungi il fix in `tools/fic_client.py` e
   nota il caso nelle "Note sui payload FiC" di questo workflow.
3. Rilancia in dry-run sullo stesso estratto per verificare.

---

## Lezioni sessione 2026-11-19 (arretrato agosto-novembre 2026)

### 1. Estratto conto Revolut in PDF italiano: ora supportato

Il parser generico leggeva **0 movimenti** dagli export PDF in italiano. Il
layout e' `23 ago 2026 CAR Manychat.com €14.55 €1 579.06`: mese abbreviato IT,
migliaia separate da spazio, e **tre colonne di importi** (uscita / entrata /
saldo). Dal solo testo la colonna e' ambigua, perche' ogni riga ha sempre due
numeri (movimento + saldo) e l'ordine non dice quale sia l'uscita.

`tools/parse_bank_statement.py` ha ora `parse_revolut_it_pdf()`, attivata in
automatico da `is_revolut_it_pdf()`. La colonna si deduce dalle **coordinate x**
del token finale del numero (uscita x1<=408, entrata <=485, oltre = saldo).

Due trappole trovate:
- **l'intestazione `Data (UTC) Descrizione` appare una volta per sezione-conto,
  non per pagina**: se il footer di pagina chiude la tabella, dalla pagina 2 in
  poi non legge piu' nulla (si passa da 241 a 23 movimenti). Il footer va
  **saltato**, non trattato come fine tabella.
- le continuazioni di descrizione stanno nella colonna descrizione (x0~175);
  footer e riepiloghi stanno a x0<=72 o x0>=190. Senza questo filtro il testo
  legale di Revolut finisce dentro le descrizioni dei fornitori.

**Validazione obbligatoria**: `validate_balance_chain()` verifica che
`saldo[i] - saldo[i+1] == importo[i]` su ogni coppia consecutiva dello stesso
conto. Il parser e' corretto solo se riporta 0 incoerenze. Controlla anche che
i totali per conto combacino col "Riepilogo saldo" e i totali per codice col
box "Tipi di transazione" che Revolut stampa a fine sezione.

### 2. Un export contiene TUTTI i conti

L'export PDF include ogni sotto-conto (Main EUR/GBP/USD, LOD operativo, iva,
tasse varie 30%). Conseguenze:
- i **giroconti interni** (`A LOD operativo` / `Da Main` / `A Main`) compaiono
  due volte, come uscita su un conto e entrata sull'altro. Vanno esclusi prima
  della classificazione, altrimenti generano autofatture inesistenti (in questa
  sessione erano 8 righe per 7.735,00 EUR).
- i SaaS stanno sul Main, le ads sul LOD: un estratto del solo LOD non basta.

### 3. Rimborsi integrali: operazione annullata, nessuna autofattura

Le righe `MOR Rimborso da parte di <fornitore>` vanno accoppiate agli addebiti.
Se un addebito e' rimborsato **per intero**, l'operazione e' annullata e non va
autofatturata. In questa sessione: Hyros 401,38 (16/08 -> 02/09), Holo AI
216,55 (19/10 -> 21/10), HeyGen 25,00 (12/10 -> 22/10), OpenAI 66,11 extra
(16/10 -> 23/10), Opus Clip 29,00 x3 (ago/set/ott, tutti rimborsati il 29/10).
Totale escluso 796,04 EUR.

**Attenzione al caso diverso**: un rimborso che si riferisce a un addebito di un
mese **gia' autofatturato** non si risolve con un'esclusione, serve una **nota
di variazione** sul documento gia' trasmesso. Non emetterla di iniziativa: e'
una modifica a un documento depositato, va concordata col commercialista.
Caso aperto: rimborso Apple 26,12 del 23/08, senza addebito corrispondente nel
periodo, quindi relativo a una delle autofatture Apple di giugno/luglio.

### 4. Riconciliazione a quadratura chiusa (fallo sempre)

Prima di creare, verifica che **ogni euro** delle uscite non-giroconto sia
spiegato da una delle quattro voci:

    autofatturato + rimborsato + in sospeso + italiani/esenti = uscite totali

In questa sessione: 9.938,31 + 796,04 + 0 + 3.338,75 = 14.073,10 EUR, esatto al
centesimo. Se non quadra, c'e' una riga persa dal parser o una classificazione
silenziosamente scartata.

### 5. Canonicalizzazione dei nomi fornitore

Il classificatore inventa varianti del nome tra un mese e l'altro e FiC
creerebbe **anagrafiche duplicate**. Varianti viste: `Dropbox Ireland Ltd` vs
`Dropbox International Unlimited Company`, `Skool Inc.` vs `Skool Inc`,
`Instantly Inc.` vs `Instantly`, `Manus AI` vs `Manus AI Inc.`.
Prima di creare, scarica le anagrafiche esistenti
(`GET /c/{company}/entities/suppliers`) e rimappa sul nome canonico.

Caso piu' insidioso: **conflitti di paese** che cambiano l'aliquota.
`Miro` e' stato classificato come `RealtimeBoard, Inc. dba Miro` (US, 0%) ma
l'anagrafica e la precedente autofattura usano `RealtimeBoard BV dba Miro`
(Paesi Bassi, 22% RC). In caso di conflitto **vince il trattamento gia'
depositato**, salvo fattura reale che dica altro: la coerenza con quanto gia'
trasmesso conta piu' dell'ipotesi del modello.

### 6. Esclusioni italiane confermate

Oltre a Google Workspace (gia' in blacklist), il classificatore esclude
correttamente: **Hyundai Capital Bank Europe GmbH Italy** (le righe
"PAGAMENTO DELLA RATA N°xxx DELLA PRATICA" sono rate di finanziamento da
succursale italiana: operazione finanziaria, nessuna autofattura),
Tspay/TeamSystem, Eni, Netsons, Nuova Sidap, Sife Arrone, HR Job SI,
Antonino Crivello, Tora Laura, HPI Instant Ink Italy.

### 7. Arretrato e periodo IVA: da segnalare, non da decidere

Le TD17 si registrano entro il 15 del mese successivo all'operazione. Su un
arretrato la prassi di questo workflow e' emetterle con **data odierna**, quindi
finiscono nella liquidazione del trimestre corrente. Ma se il trimestre di
competenza e' **gia' stato liquidato** la cosa va detta al commercialista:
in questa sessione la liquidazione III trimestre 2026 (1.564,41 EUR, cod. 6033)
era stata presentata e pagata il 14/11, mentre agosto e settembre non erano
registrati. Il reverse charge e' neutro (IVA a debito = IVA a credito) quindi
l'importo versato non cambia, ma la valutazione su registri e LIPE spetta a lui.

### 8. `timeout` non esiste su macOS

`timeout 580 python3 ...` esce con **codice 0 senza eseguire nulla**: sembra
riuscito e non crea niente. Non usarlo. Per i batch lunghi usa un comando in
background e verifica sempre lo stato reale su FiC prima di dichiarare fatto.

## Aggiornamento 2026-11-19 (webapp v3): le lezioni diventano codice

Le correzioni fatte a mano nell'arretrato ago-nov ora sono deterministiche e
condivise da CLI e webapp:

- **Giroconti e rimborsi**: `tools/autofatture_prep.py` (`prepare`) toglie i
  giroconti tra conti propri ("A <conto>" / "Da <conto>") e abbina ogni
  "Rimborso da parte di X" all'addebito precedente con stesso importo ed
  esercente. I rimborsi senza addebito nell'estratto finiscono in
  `orphan_refunds`: nota di variazione da far valutare, mai compensati.
  Sull'estratto ago-nov riproduce esattamente le esclusioni manuali
  (8 giroconti, 7 rimborsi, Apple €26,12 orfano).
- **Un'autofattura per fornitore per mese**: `run_autofatture.group_candidates`
  include il mese dell'addebito nella chiave. Prima un estratto di piu' mesi
  dava un solo documento per fornitore.
- **Duplicati**: da ora `fic_client` scrive il mese degli addebiti nell'oggetto
  *interno* del documento (`subject`, non `visible_subject`), es.
  `Autofattura TD17 - Meta ... [2026-08]`. `autofatture_prep.find_duplicates`
  lo usa per riconoscere un duplicato certo. Sui documenti vecchi senza mese
  segnala solo "possibile duplicato" (stesso fornitore e netto, emesso dopo il
  primo addebito). Gli abbonamenti a prezzo fisso danno falsi positivi: guardare
  la data del documento esistente.
- **SDI**: `send_autofatture_sdi.py` espone `verify_doc` / `send_doc` /
  `load_batch` (ora paginato: la lista FiC si fermava ai primi 100 documenti).
  La webapp li usa nella pagina Invio SDI con conferma "INVIA".
- **Token FiC in memoria**: dopo un refresh `FicClient` aggiorna anche
  `os.environ`. Prima un processo lungo (webapp) ricreava i client col token
  vecchio.

La webapp (`webapp/README.md`) ora fa tutto il flusso dal browser, anche online
con login. Per un run normale e' la strada consigliata; la CLI resta per i casi
fuori standard.
