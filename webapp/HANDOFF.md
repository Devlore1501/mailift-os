# Handoff: Autofatture online (webapp v3)

> Scritto il 19/11/2026 a fine sessione. Serve per far partire il progetto in
> una sessione nuova senza ricostruire il contesto. Dettagli tecnici completi in
> [README.md](README.md); logica fiscale in
> [workflows/emit_autofatture.md](../workflows/emit_autofatture.md).

## Obiettivo

Portare online la webapp autofatture: Lorenzo deve poter fare il ciclo mensile dal browser, anche fuori casa. Il ciclo è caricare l'estratto Revolut, rivedere, creare su Fatture in Cloud e inviare al SDI.

**Done quando:**
1. La webapp risponde su un URL HTTPS protetto da password.
2. Il FiC dell'health check è verde e i token restano validi dopo un riavvio.
3. Il prossimo estratto mensile (dicembre 2026) passa da lì fino all'invio SDI, con controllo duplicati verde e totali che quadrano con l'estratto.

## Stato attuale

| Pezzo | Stato |
|---|---|
| Codice webapp v3 (backend + frontend) | Fatto e testato in locale, **non committato** |
| Librerie aggiornate (React 19, Vite 8, Tailwind 4, TS 7, FastAPI 0.162, anthropic 2.6) | Fatto, versioni fissate |
| Dockerfile + `render.yaml` | Scritti, **build Docker mai eseguita** (Docker non installato sul Mac) |
| Deploy online | **Non fatto**: serve account Render di Lorenzo |
| Token FiC dedicato al server | **Da generare** |
| Token Gmail personale | **Scaduto** (`invalid_grant`), da rinnovare |

### Test già passati (19/11)

Il test è sull'estratto ago-nov 2026, che si trova in `inbox/processed/revolut_2026-08_2026-11.pdf`:
- **Lettura estratto:** 241 movimenti, catena dei saldi 239/239.
- **Esclusioni:** 8 giroconti e 7 rimborsi esclusi; rimborso Apple €26,12 segnalato come orfano.
- **Autofatture:** 66 per €9.938,31 netti, divise per mese 14/20/20/12. Corrispondono al batch emesso a mano (74/a–139/a).
- **Duplicati:** tutte e 66 segnalate come possibili duplicati, ed è corretto perché sono già su FiC.
- **Sicurezza:** API protette (401 senza sessione) e invio SDI rifiutato senza la parola "INVIA".
- **Container simulato:** stessa struttura dell'immagine, con i segreti copiati sul disco al primo avvio e FiC che risponde.

Il test si rilancia con:
```bash
cd webapp/backend && ../../.venv/bin/python tests/e2e_real_statement.py /tmp/autofatture-e2e
```
Non usa Anthropic e non scrive su FiC.

## Prossimi passi (in ordine)

1. **Commit** dei soli file della webapp e dei tool autofatture. Nel repo ci sono modifiche di altre sessioni da lasciare fuori: `Claude.md`, `.gitignore`, `requirements.txt`, `landing/`, `quiz-to-customer/`, `.claude/settings.local.json`, `knowledge/`, e la funzione `create_draft` in `tools/gmail_client.py`.
   File da committare:
   - `webapp/` (tutto tranne `frontend/dist`, `node_modules`, `.tmp`)
   - `tools/autofatture_prep.py` (nuovo), `tools/fic_client.py`, `tools/run_autofatture.py`, `tools/send_autofatture_sdi.py`, `tools/classify_transactions.py`, `tools/verify_suppliers_from_email.py`
   - `workflows/emit_autofatture.md`
2. **Push** su `github.com/Devlore1501/mailift-os` (repo privato, Render lo legge da lì).
3. **Token FiC per il server.** Esegui `python tools/fic_device_setup.py` e tieni la coppia di token per Render, senza sovrascrivere quella locale. Così server e computer non si invalidano a vicenda col refresh.
4. **Rinnovo Gmail personale:**
   ```bash
   python3 tools/gmail_oauth_setup.py --account personal
   ```
5. **Render** (lo fa Lorenzo: crea l'account e sceglie il piano Starter, circa $7/mese, che serve per il disco):
   - New → Blueprint → repo `mailift-os` → Blueprint path `webapp/render.yaml`
   - Compila i segreti:
     - `WEBAPP_PASSWORD`
     - `ANTHROPIC_API_KEY`
     - `FIC_CLIENT_ID`, `FIC_CLIENT_SECRET`, `FIC_ACCESS_TOKEN`, `FIC_REFRESH_TOKEN`
     - `GMAIL_TOKEN_PERSONAL_JSON`, `GMAIL_TOKEN_BUSINESS_JSON` (contenuto dei file in `tokens/`)
   - Deploy manuale (`autoDeploy: false`)
6. **Verifica online:**
   - login, health tutto verde
   - pagina Invio SDI con data 22/08/2026: 16 documenti, tutti "Inviata"
   - riavvio del servizio e nuovo controllo dell'health, per verificare che il token FiC sopravviva
7. **Primo run reale**: estratto di dicembre, all'inizio di gennaio. Usa prima la modalità dry-run e passa a Live solo con totali e duplicati verificati.

## Decisioni già prese (non ridiscuterle)

- **Hosting:** Render con un solo processo e SQLite su disco persistente (`/data`). Non serve un database esterno: l'app ha un solo utente.
- **Login:** password unica in `WEBAPP_PASSWORD` e cookie firmato. Niente multi-utente.
- **Token FiC e Gmail:** si copiano sul disco al primo avvio, poi i file sul disco sono la fonte di verità (il server li aggiorna da solo). Per sostituire un token si cancella il file sul disco e si riavvia.
- **Invio SDI:** solo con "INVIA" digitato. Prima di ogni invio si rifà la verifica formale e i documenti già inviati vengono saltati.
- **Errori di classificazione:** se la classificazione AI fallisce, il run si ferma. Non ci sono candidati di riserva.
- **Accorpamento:** un'autofattura per fornitore per mese.
- **Mese nell'oggetto interno:** è scritto nell'oggetto interno FiC (`subject`, non quello visibile) ed è la chiave del controllo duplicati certo.
- **Versioni delle librerie:** solo versioni pubblicate da almeno due settimane. React Router resta alla 7 finché il Mac ha Node 20.
- **`.venv` del progetto non aggiornato:** lo usano altri script (anthropic 0.91 → 2.x è una major). La webapp funziona con entrambe le versioni.

## Rischi aperti

- **Dockerfile mai buildato.** Il primo deploy Render è anche il primo build. Se fallisce, controlla prima che `Dockerfile.dockerignore` lasci entrare tutti i file necessari: il contesto di build è la root del repo.
- **Duplicati sulle autofatture vecchie.** Quelle emesse prima del 19/11 non hanno il mese nell'oggetto, quindi su di loro il controllo dà solo "possibile duplicato" e gli abbonamenti a prezzo fisso generano falsi allarmi. È preciso solo da ora in poi.
- **Nomi fornitori.** I nomi del classificatore possono differire dall'anagrafica FiC ("Dropbox Ireland" vs "Dropbox International"). Il paese si corregge con un override, il nome no.
- **Punti da girare al commercialista** (srlsemplice@gmail.com):
  - nota di variazione per il rimborso Apple €26,12
  - registrazione nel IV trimestre delle autofatture di agosto e settembre
  - trattamento di Paddle (GB) a 0%

## Per partire nella nuova sessione

Leggi in quest'ordine:
1. questo file
2. [README.md](README.md)
3. la sezione "Aggiornamento 2026-11-19" in fondo a [workflows/emit_autofatture.md](../workflows/emit_autofatture.md)

Poi parti dal passo 1 qui sopra.

Avvio in locale per provare:
```bash
./webapp/start.sh
```
Poi apri http://localhost:5173. Senza `WEBAPP_PASSWORD` il login è disattivato.
