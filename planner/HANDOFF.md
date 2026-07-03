# Mailift Planner — Handoff di sessione

> File di stato per riprendere il lavoro in una nuova sessione Claude.
> In una sessione nuova: "Leggi planner/HANDOFF.md e continua da lì".
> Aggiornare questo file a fine sessione se cambia qualcosa di sostanziale.

**Ultimo aggiornamento**: 2026-07-03 (sera) · **Branch**: `claude/saas-email-planning-ecommerce-mf9kls`

## Cos'è

Web app SaaS multi-cliente per un'agenzia email marketing (Mailift, founder Lorenzo):
genera **calendari editoriali email MENSILI** per brand eCommerce DTC su Klaviyo,
con testi scritti da Claude, template Canva abbinati da un DB Notion, e
pubblicazione del calendario approvato su Notion.

- Codice in `planner/` (separato dalla webapp autofatture in `webapp/`)
- Backend FastAPI + SQLAlchemy/SQLite (`planner/backend`, porta 8001)
- Frontend React 18 + Vite + TS + Tailwind + shadcn + react-query (`planner/frontend`, porta 5174)
- Contratto API: `planner/design/api_contract.md` (v1 + aggiornamenti v1.1 in coda)
- Avvio: `./planner/start.sh` (kill automatico istanze zombie; fix bash 3.2 macOS)
- Test: `cd planner/backend && ../../.venv/bin/python tests/smoke_test.py` (~35 check, mock mode)

## Funzionalità completate

1. **Multi-tenant**: ogni brand è un workspace isolato (`brand_id` su tutto), switch da topbar
2. **Profilo brand**: descrizione/tono/mission/positioning, avatar (desideri/obiezioni/linguaggio),
   email a settimana (base ×4 per il mensile), **paese di destinazione** (default IT)
3. **Brand identity da PDF**: upload brand book (PDF/TXT/MD, max 3 file/20MB) →
   `POST /brands/{id}/extract-profile?apply=bool` estrae profilo+avatar+prodotti.
   UI: dialog "Nuovo brand" (upload opzionale) e card nella pagina Profilo
4. **Catalogo**: prodotti (best seller ⭐, stagionalità), offerte con codici, occasioni
5. **Suggerimenti festività**: `POST /brands/{id}/occasions/suggest {month}` → Claude analizza
   festività/ponti/ricorrenze del paese del brand + idee email; card con checkbox nella tab
   Occasioni → inserimento a calendario
6. **Klaviyo per-brand** (chiave nel DB, mai in chiaro): sync segmenti+campagne+metriche
   (client DIFENSIVO: prova varianti di richiesta e degrada su 400 — page[size] max 10,
   additional-fields rifiutati, sort/filtri non supportati, conteggi per-segmento cap 30)
7. **Generazione piano MENSILE** (`month_start` YYYY-MM-01, colonna DB si chiama ancora
   `week_start` per compatibilità): asincrona (thread + polling 2s), structured output.
   **Regola 70/20/10**: ~70% educativo (nurturing/storytelling), ~20% prodotto (vendita),
   ~10% promo. Barra a 3 segmenti nella UI. Claude considera festività del paese
8. **Card email**: giorno+orario, obiettivo (badge), FORMATO (badge grafica/testuale),
   tema/angolo, segmento+rationale, 2-3 oggetti A/B, preview, prodotti/offerta, template
   Canva con link+anteprima. **Formati bilanciati ~60% grafiche / 40% testuali** (prompt),
   mai solo immagini; promo/prodotto grafiche, storytelling/nurturing spesso testuali.
   TESTUALI: body in prosa 1:1, niente template. GRAFICHE: body vuoto e `blocks` = scaletta
   per il designer (banner: headline≤7/sub≤14/CTA/visual; sezioni con micro-copy ≤25 parole
   e campo visual che spinge INFOGRAFICHE per evitare muri di testo; info; cta_finale).
   UI: vista "Scaletta per il designer" + editor per-blocco nel dialog; contatore formati
   sotto la barra 70/20/10; pubblicazione Notion con select Formato e scaletta a sezioni.
   Modifica inline + rigenerazione singola con istruzioni
9. **Template Canva**: due sorgenti (una attiva alla volta, ogni import rimpiazza la libreria):
   a) **set tipi × varianti** — il flusso reale di Lorenzo: elenco Notion "About x3, Flash
   Sale x3, ..." (45 tipi × 3 = 135 template) incollato così com'è nella card della pagina
   Template → `GET/PUT /api/templates/set` (`entries_text` grezzo o `entries` strutturati);
   categorie AUTO-assegnate da mappa keyword in `services/canva_set.py::_CATEGORY_RULES`
   (promo/educativo/prodotto/storytelling/social proof/engagement/...); ogni variante ha una
   pagina globale nel file Canva → deep-link `...edit#N` che apre la pagina giusta;
   b) sync dal DB Notion. **Anteprime**: export PNG del file Canva (immagini numerate o zip)
   → `POST /api/templates/previews`, match per numero di pagina dal nome file, servite da
   `GET /api/templates/previews/{page}` (salvate in data/previews/), mostrate nella griglia
   e nelle card email (Template.preview_url, anche dentro canva_template delle email)
10. **Approvazione → pubblicazione Notion**: database calendario con pagina per email
11. **Mock mode completo** senza ANTHROPIC_API_KEY (demo deterministica di tutto)
12. **UI "studio editoriale"**: sidebar scura a inchiostro + canvas carta, Fraunces (titoli) +
    Plus Jakarta Sans self-hosted via Fontsource, indigo+ambra, dark mode pronta

## Configurazione (stato di Lorenzo)

- Repo clonato in `~/mailift-os` sul suo Mac (bash 3.2, Python 3.13, Node 20)
- Klaviyo: chiave collegata per il brand "bergamo", sync FUNZIONANTE (dopo i fix difensivi)
- `ANTHROPIC_API_KEY`: da verificare se già in `.env` (senza → mock mode, badge giallo)
- Notion: token/DB template/pagina calendari NON ancora configurati (si fa da UI → Impostazioni)
- Env letto da `.env` in root repo o `~/.secrets/mailift/.env`
- `PLANNER_CLAUDE_MODEL` default `claude-opus-4-8`

## Dettagli tecnici da ricordare

- Micro-migrazioni SQLite in `app/main.py::_migrate()` (ALTER TABLE per colonne nuove;
  `create_all` non altera tabelle esistenti)
- `Plan.month_start` è `mapped_column("week_start", ...)` — NON rinominare la colonna DB
- Klaviyo: `_paginate()` in `services/klaviyo.py` ritorna (dati, params usati) e fa fallback
  automatico su 400 — estendere le liste `attempts` per nuovi endpoint
- Estrazione PDF: Claude legge i PDF nativamente (document block base64); mock usa pypdf
- Il frontend agent-generated segue `lib/queries.ts` (hook react-query centralizzati, chiavi
  in `keys`) — mantenere il pattern per nuovi endpoint
- Verifiche fatte con Playwright headless (`/opt/pw-browsers/chromium` nel container di sessione)

## Possibili prossimi passi (non richiesti, da confermare con Lorenzo)

- Autenticazione multi-utente per l'agenzia
- Creazione bozze campagna direttamente su Klaviyo (write API)
- Vista calendario visuale (griglia mese) oltre alla lista card
- Altri canali (SMS/WhatsApp) come nuovi servizi in `app/services/`
- Docker compose per avvio one-command
