# Mailift Planner

Web app SaaS multi-cliente che genera **piani editoriali email settimanali** per brand
eCommerce DTC su Klaviyo. Pensata per l'agenzia: più brand, un'unica dashboard.

## Cosa fa

- **Multi-cliente**: ogni brand è un workspace isolato (dati, connessioni, piani separati),
  con switch rapido dalla topbar.
- **Input per brand**: descrizione/tono di voce/mission/posizionamento, brand avatar
  (desideri, obiezioni, linguaggio), catalogo prodotti, offerte e codici sconto,
  occasioni del periodo, connessione Klaviyo per-brand.
- **Klaviyo (read-only)**: sincronizza segmenti reali con conteggi, performance campagne
  (open/click/revenue), dimensione lista e salute engagement; produce raccomandazioni.
- **Generazione piano (API Claude)**: per ogni email una card con giorno+orario consigliato,
  tema/angolo + obiettivo (nurturing/promo/storytelling/vendita), segmento Klaviyo consigliato
  con rationale, 2-3 varianti oggetto A/B, preview text, testo email completo (hook, corpo, CTA)
  e prodotti/offerte da includere.
- **Logica intelligente**: regola 80/20 contenuto/promo, segmenti e frequenza adattati ai dati
  Klaviyo (open rate basso → re-engagement), coerenza di tono con il brand avatar.
- **Matching template Canva**: legge il database Notion dei template email categorizzati e
  Claude abbina a ogni email il template più adatto (nome + link Canva diretto).
- **Approvazione + pubblicazione**: rivedi, modifica, rigenera le singole email; una volta
  approvato il piano viene pubblicato su Notion come calendario editoriale (un database con
  una pagina per email: giorno, oggetto, segmento, testo, template, stato).

## Avvio

```bash
# prima volta
python3 -m venv .venv
.venv/bin/pip install -r planner/backend/requirements.txt
(cd planner/frontend && npm install)

# dev mode (backend :8001 + frontend :5174)
./planner/start.sh
```

Apri http://localhost:5174. Le API sono documentate su http://localhost:8001/docs
e il contratto completo è in [design/api_contract.md](design/api_contract.md).

## Configurazione (.env nella root del repo o ~/.secrets/mailift/.env)

| Variabile | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | Generazione piani/email via API Claude. **Senza chiave l'app parte in mock mode**: piani demo deterministici, utile per provare tutto il flusso. |
| `PLANNER_CLAUDE_MODEL` | Modello Claude (default `claude-opus-4-8`). |
| `NOTION_TOKEN` | Token integrazione Notion (lettura template + pubblicazione calendari). Modificabile anche da UI in Impostazioni. |
| `NOTION_TEMPLATES_DB_ID` | ID del database Notion con i ~350 template Canva categorizzati. |
| `NOTION_CALENDAR_PARENT_ID` | ID della pagina Notion sotto cui creare i calendari editoriali. |

Le chiavi **Klaviyo sono per-brand** e si inseriscono dalla UI
(workspace del brand → Integrazioni). Servono permessi read su
Campaigns, Lists, Segments, Metrics, Accounts.

### Database Notion dei template

La sync mappa le proprietà in modo tollerante: la colonna title → nome, una
select/multi-select chiamata `Categoria`/`Category`/`Tipo`/`Type` → categoria,
una colonna URL (idealmente con link Canva) → link al template, una
multi-select `Tag`/`Tags` → tag.

## Architettura

```
planner/
├── design/api_contract.md    # contratto API (fonte di verità FE/BE)
├── backend/                  # FastAPI + SQLAlchemy (SQLite in backend/data/)
│   └── app/
│       ├── api/              # routers: brands, catalog, plans, integrations, templates, system
│       ├── services/         # klaviyo.py, claude_ai.py, notion_api.py, planner.py, mockdata.py
│       └── models/           # db_models.py (multi-tenant per brand_id), schemas.py
└── frontend/                 # React 18 + Vite + TypeScript + Tailwind + shadcn/ui + react-query
```

- **Multi-tenancy**: tutte le risorse (prodotti, offerte, occasioni, piani, snapshot Klaviyo)
  sono scoped su `brand_id`; eliminare un brand elimina l'intero workspace.
- **Generazione asincrona**: `POST /plans/generate` ritorna subito `202 status=generating`;
  un thread di background chiama Claude (structured output JSON) e il frontend fa polling.
- **Estensibilità**: le integrazioni sono servizi isolati in `app/services/`; per aggiungere
  un canale (es. SMS, Meta Ads) si aggiunge un servizio + router senza toccare il core.

## Test

```bash
cd planner/backend && ../../.venv/bin/python tests/smoke_test.py
```

Smoke test end-to-end in mock mode: 29 check su tutto il flusso
(brand → catalogo → sync → generazione → edit → rigenerazione → approvazione → pubblicazione).
