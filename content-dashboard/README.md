# Mailift Content Dashboard

Web app interna per il piano editoriale organico (TikTok / IG Reels, Caroselli, Stories): pianificazione con controllo qualità, misurazione sui segnali che contano (retention, save, share, composizione buyer, DM→FHS) e flusso continuo di idee da fonti reali. Implementa il PRD v1.0 (MVP / Fase 1).

**Prodotto opinionato** — i principi del PRD sono vincoli nel codice, non opzioni:

- **Gate Critico ≥ 38/50**: il backend blocca il passaggio a "Programmato" sotto soglia (soglia configurabile da Impostazioni).
- **Qualità > vanity**: KPI primari dominanti in UI; views/likes relegati in sezione secondaria etichettata "non guidano le decisioni".
- **Mix pillar forzato**: Revenue Leak 30 · Proof 25 · Educational 25 · Contrarian 10 · Backstage 10, alert oltre ±7pp.
- **Idea madre → repurposing**: 1 idea → N output figli (surface + format), raggruppati nella repurposing view.
- **Test per format**: giudizio su 3-5 post; kill flag se retention media <40% dopo ≥5 post; winner se retention >65% o save rate top-decile.
- **Human-in-the-loop**: l'AI propone (coda review), l'umano approva/edita/scarta.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite (`backend/.tmp/content_dashboard.db`) |
| Frontend | React 18 + Vite + TypeScript + Tailwind + Recharts (porta 5174) |
| Auth | Email+password, sessioni Bearer, ruoli Admin / Editor / Contributor applicati a livello API |
| AI | Anthropic API server-side (sintesi proposte Idea Engine) |
| Job | Scheduler in-process (default giornaliero) per fetch fonti + sintesi |

Il PRD proponeva Next.js+Supabase come stack indicativo ("sostituibile purché rispetti moduli e modello dati"): qui si riusa il pattern già validato nel repo (webapp Autofatture) — zero servizi esterni, gira in locale.

## Avvio rapido

```bash
# setup one-time
python3 -m venv .venv
.venv/bin/pip install -r content-dashboard/backend/requirements.txt
cd content-dashboard/frontend && npm install && cd ../..

# dev mode: backend :8010 + frontend :5174
./content-dashboard/start.sh
```

Login default: `lorenzo@mailift.it` / `mailift-admin` (override con env `CONTENT_DASHBOARD_ADMIN_PASSWORD` al primo avvio; cambiarla comunque subito).

Dati demo per vedere la dashboard piena:

```bash
cd content-dashboard/backend && ../../.venv/bin/python seed_demo.py
```

## Moduli

**M1 Piano editoriale** — idee madri con generazione output figli (repurposing view), board Kanban drag-and-drop `Idea → Script → In produzione → Critico → Programmato → Pubblicato → Archiviato` con gate qualità, calendario settimana/mese, filtri pillar/format/surface, widget mix pillar reale vs target con alert.

**M2 Performance & KPI** — inserimento metriche manuale per contenuto (snapshot multipli = andamento), import CSV con mapping colonne (aggancio per URL/ID/titolo), dashboard KPI con primari in alto e vanity in secondaria, trend settimanale, breakdown per format/pillar/surface con winner detection e kill flag, composizione buyer (`icp_ratio`) e funnel DM→FHS per contenuto e per format.

**M3 Idea Engine** — CRUD fonti (rss/reddit/news/trend/blog/twitter/competitor) con **catalogo di 15 fonti consigliate** installate al primo avvio (subreddit eCom/email, query Google News IT, Google Trends Italia, blog di settore — vedi [`backend/app/source_catalog.py`](backend/app/source_catalog.py)); job schedulato giornaliero + trigger manuale che fetch-a item deduplicati (una fonte down non blocca le altre); sintesi AI Anthropic → proposte `{angolo, pillar, format, hook, rilevanza 1-10}` in coda review; in più **brainstorm evergreen** ("Spunti evergreen" nella pagina Idee): argomenti interessanti da trattare non legati alle notizie, bilanciati sul mix pillar e deduplicati contro le idee recenti. Proposta approvata → idea madre in M1. Senza `ANTHROPIC_API_KEY` il fetch funziona e la sintesi/brainstorm restano in attesa (item preservati). X/Twitter non espone RSS pubblici: si aggiunge via bridge Nitter/RSSHub con tipo `twitter`.

**Bozza script AI** — nella card contenuto, "Genera bozza script" produce uno script su misura per surface/format (Reel parlato, carosello slide-per-slide, sequenza story) a partire da idea madre, angolo, hook e pillar; propone hook e CTA keyword se mancano. La bozza non viene salvata da sola: l'umano rifinisce e preme Salva (human-in-the-loop). Endpoint: `POST /api/contents/{id}/generate-script`, accessibile anche ai Contributor.

**Trasversali** — auth con ruoli (Contributor: script/hook/note e stati fino a Critico; Editor: tutto il piano e le metriche; Admin: + fonti, soglie, target, utenti), Impostazioni per tutte le soglie, activity log basilare.

## REST API

Swagger su [http://localhost:8010/docs](http://localhost:8010/docs). Prefisso `/api`: `auth/*`, `users`, `ideas` (+`/children`), `contents` (+`/status` con gate, `/metrics`), `metrics/import` (CSV), `kpi/overview|pillar-mix|breakdown`, `sources` (+`/catalog`, `/catalog/add`), `source-items`, `idea-engine/run|fetch|synthesize|brainstorm`, `config` (+`/settings`, `/pillar-targets`), `activity`, `health`.

## Test

Smoke test E2E del backend (43 check: auth/ruoli, gate Critico, repurposing, metriche+CSV, KPI/winner/kill, mix pillar, fonti+dedup, coda review, impostazioni):

```bash
cd content-dashboard/backend && ../../.venv/bin/python tests/smoke_test_e2e.py
```

Build frontend con type-check: `cd content-dashboard/frontend && npm run build`.

## Note e decisioni aperte (dal PRD §17)

- **Enum 12 format**: tassonomia provvisoria in [`backend/app/enums.py`](backend/app/enums.py) — da confermare con la lista definitiva; si modifica in un punto solo.
- **Multi-piattaforma**: campo `platform` (instagram default, tiktok disponibile) — si parte IG-first senza bloccare TikTok.
- **GHL / DM→FHS**: inserimento manuale/CSV in MVP come da PRD; webhook GHL è P1.
- **Composizione buyer**: tagging manuale (commenti ICP vs non-ICP) in MVP.
- **Password admin**: il seed crea l'admin solo se il DB è vuoto; cambiare subito la password di default.
- In sandbox/CI il fetch di fonti esterne può essere bloccato dalla network policy (403 dal proxy): non è un bug dell'app, in locale funziona. Il fetch usa `requests` con User-Agent identificabile e rispetta i rate limit impliciti (max 25 item/fonte/run).

## Fuori scope MVP (Fase 2/3 del PRD)

Instagram Graph API, TikTok API, webhook GHL, libreria/swipe file (M4), score Critico automatico pre-calcolato, pubblicazione automatica, app mobile.
