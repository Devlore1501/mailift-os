# Deploy in produzione — Railway

Mailift Planner gira come **un solo servizio Docker**: il backend FastAPI serve
sia le API (`/api/...`) sia la build statica del frontend React, quindi un solo
URL, un solo servizio da pagare, zero problemi di CORS tra domini diversi.

## Perché Railway (e non Supabase o Lovable)

- **Supabase** è un Postgres gestito + Auth + Storage: ottimo come database, ma
  non ospita un backend Python custom con thread in background come il nostro
  (generazione asincrona dei piani, client Klaviyo, publish Notion). Va bene
  come *database*, non come *hosting dell'app*.
- **Lovable** è un builder AI che genera e ospita app dentro il proprio editor
  (React + Supabase), non un posto dove fare il deploy di codice già scritto.
- **Railway** invece prende un `Dockerfile` da un repo Git e lo fa girare,
  con un Postgres gestito nello stesso progetto: è la soluzione più semplice
  per l'app così com'è oggi.

## Cosa c'è già pronto nel repo

- `planner/Dockerfile` — build multi-stage: compila il frontend, poi lo
  incolla dentro l'immagine Python che serve tutto insieme (`app/main.py`
  monta `dist/` quando `PLANNER_FRONTEND_DIST` è impostata).
- `planner/railway.json` — dice a Railway di usare quel Dockerfile.
- `app/db.py` — se c'è `DATABASE_URL` nell'ambiente usa Postgres, altrimenti
  SQLite locale (comportamento di sviluppo invariato).
- Le migrazioni (`_migrate()` in `main.py`) funzionano sia su SQLite che su
  Postgres.

## Passi su Railway

1. **Crea account** su railway.com, **New Project → Deploy from GitHub repo**,
   seleziona `Devlore1501/mailift-os`.
2. Nelle **Settings** del servizio creato:
   - **Root Directory**: `planner` (il Dockerfile e railway.json sono lì,
     non nella root del repo che contiene anche `webapp/`).
   - Railway rileva `railway.json` e usa il Dockerfile automaticamente.
3. **Aggiungi un database**: nel progetto, **New → Database → PostgreSQL**.
   Railway crea la variabile `DATABASE_URL` sul servizio Postgres.
4. Nel servizio dell'app (**Variables**), collega il database e imposta le
   chiavi:
   - `DATABASE_URL` → referenzia quella del Postgres (Railway te lo propone
     con l'autocomplete `${{Postgres.DATABASE_URL}}`)
   - `ANTHROPIC_API_KEY` → la tua chiave Claude (senza, l'app parte in
     modalità demo)
   - `PLANNER_CLAUDE_MODEL` → opzionale, default `claude-opus-4-8`
   - Notion e Klaviyo si configurano **dall'interfaccia** (Impostazioni /
     profilo brand), non servono variabili d'ambiente per quelli
5. **Aggiungi un volume**: Settings → Volumes → monta `/data` sul servizio.
   Serve per le anteprime dei template Canva che carichi da UI (immagini
   salvate su disco); senza volume si perdono ad ogni redeploy. Il database
   ormai è su Postgres quindi non serve per quello.
6. **Deploy**: Railway builda l'immagine e la avvia. Al primo avvio crea le
   tabelle automaticamente (`Base.metadata.create_all` + `_migrate()`).
7. Railway assegna un dominio pubblico (`*.up.railway.app`); puoi collegare
   un dominio tuo da Settings → Networking → Custom Domain.

## Verifiche dopo il deploy

- `https://<tuo-dominio>/api/system/status` deve rispondere con
  `"anthropic_configured": true` (se hai messo la chiave) e
  `"mock_mode": false`.
- La UI deve caricare su `https://<tuo-dominio>/` (stessa origine delle API,
  niente configurazione CORS aggiuntiva necessaria).

## Deploy continuo

Ogni push sul branch collegato (di solito `main`, o quello che scegli in
Railway → Settings → Source) triggera automaticamente un nuovo build e
deploy. Se vuoi, aggiungi un branch di staging su Railway prima di puntare a
`main`.
