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

## ⚠ Cosa devi fare TU dopo lo script
Il workflow **non invia nulla al SDI**. Lascia tutte le autofatture in stato `not_sent`,
modificabili dalla UI di Fatture in Cloud. Per ognuna:
1. Vai su FiC > Fatture e Documenti > Autofatture
2. Apri la fattura, controlla l'aliquota, il fornitore, l'importo
3. **Compila i DatiFattureCollegate** se vuoi (Attributi avanzati > 2.1.6) — opzionale
4. Clicca "Verifica formale" → "Firma e invia"

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
