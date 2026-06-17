# Triage Task Notion — Fai tu vs Delega

## Obiettivo
Analizzare i task aperti del database **Tasks_Mailift** e classificarli in tre
categorie di delega: **Lorenzo**, **Segretaria** o **Team**. L'output è una
tabella sintetica che permette a Lorenzo di vedere subito cosa toccare lui e
cosa può scaricare.

L'analisi è **informativa**, non aggiorna nulla su Notion. Lorenzo riassegna
manualmente (o ti chiede di farlo come azione separata).

## Quando usarlo

Trigger phrases tipiche da chat (Telegram o Claude Code):
- "analizza i task", "che task ho", "cosa devo fare"
- "cosa posso delegare", "fai tu vs delega"
- "triage task", "task aperti", "weekly task review"
- "dammi i task in scaletta"

## Input richiesti
- Database Tasks_Mailift già popolato con i task di Lorenzo
- Variabili `.env`: `NOTION_API_KEY`, `NOTION_TASKS_DATA_SOURCE_ID`,
  `NOTION_USER_ID_LORENZO` (tutte già configurate)
- Tool: [tools/notion_tasks.py](../tools/notion_tasks.py) — funzione
  `list_open_tasks()` aggiunta in questo workflow

## Esecuzione

### 1. Pull dei task aperti
Lancia uno snippet Python via Bash dal root del progetto:

```bash
cd "/Users/lorenzobaretta/workflow ai" && .venv/bin/python -c "
from tools.notion_tasks import list_open_tasks
import json
tasks = list_open_tasks(only_lorenzo=True, include_unassigned=True)
print(json.dumps(tasks, indent=2, ensure_ascii=False))
"
```

Per richieste tipo "tutti i task, anche assegnati ad altri" usa
`only_lorenzo=False`. Per "solo i miei strict" usa `include_unassigned=False`.

L'output è una lista JSON di dict con questi campi:
- `id`, `url`, `name`, `status`, `priorita`, `categoria`, `due_date`,
  `due_overdue`, `assign_ids`, `assigned_to_lorenzo`, `cliente_ids`,
  `created_time`

### 2. Inferenza categoria mancante (importante)
Lorenzo **spesso non popola** i campi `Categoria` e `Priorità` su Notion. La
maggior parte dei task ha `categoria=None` e `priorita=None`. Quando
classifichi, usa la **categoria esplicita se presente**, altrimenti
**deduci dal titolo** secondo questi pattern:

| Pattern nel titolo | Categoria inferita |
|---|---|
| `[STRATEGIA]`, `[STRATEGY]`, "strategia", "segmentazione" | `Strategia` |
| `[COPY]`, "copy", "scrivi", "newsletter", "email per" | `Copy` |
| `[DESIGN]`, "design", "banner", "asset", "popup", "grafica" | `Design` |
| `[TECNICO]`, "setup", "integrazione", "API", "webhook", "make.com", "n8n", "klaviyo flow", "trigger" | `Tecnico` |
| `[REPORT]`, "report", "weekly", "metriche", "analisi" | `Reportistica` |
| `[Personale]`, "rinnovare", "polizza", "pagamento" | `Personale` (vedi nota sotto) |
| "fattura", "autofattura", "estratto conto", "Revolut" | `Amministrazione` |
| "call con", "discovery", "follow up cliente" | `Cliente/Call` |

Se davvero non si capisce, marca come `Da categorizzare` e mettilo in cima al
report tra i "task da chiarire".

**Nota Personale**: i task con `[Personale]` nel titolo restano sempre con
Lorenzo (non delegabili a Segretaria nemmeno se sembrano admin).

### 3. Classificazione delega

Applica queste regole, **in ordine**:

| Categoria | Default delega | Eccezioni / note |
|---|---|---|
| `Strategia` | **Lorenzo** | Decisioni strategiche, posizionamento, segmentazione, partnership |
| `Copy` | **Lorenzo** | La voce è la sua. Eccezione: copy admin/automazione (welcome generico, conferme ordini) → Segretaria può preparare bozze |
| `Cliente/Call` | **Lorenzo** | Le call le fa lui, ma la Segretaria può preparare briefing pre-call |
| `Personale` | **Lorenzo** | Mai delegato |
| `Reportistica` | **Segretaria** | Report Klaviyo, dashboard cliente, weekly recap, briefing |
| `Amministrazione` | **Segretaria** | Fatture, autofatture, estratti conto, scadenze fiscali, follow-up amministrativi |
| `Design` | **Team** | Esecuzione visiva, asset Klaviyo, banner Shopify. Se non c'è team, → Lorenzo + nota "trovare designer" |
| `Tecnico` | **Team** | Setup Klaviyo, integrazioni, debug. Eccezione: fix rapidi via Make/n8n → Segretaria può tentare |
| `Da categorizzare` | **Lorenzo** | Va chiarito prima di poter essere delegato |

**Override per parole chiave** (vincono sulla categoria):
- "approva", "decide", "valutare proposta" → sempre Lorenzo
- "compila", "carica", "scarica", "archivia" → sempre Segretaria
- "configurare", "creare nuovo account" → Team

### 4. Output (template)

```markdown
## 📋 Triage task aperti — N task totali

**Capacity check**: di questi N task, solo M sono effettivamente azionabili
(altri sono in attesa o senza scadenza chiara). [opzionale, solo se c'è uno
sbilanciamento]

⚠️ **Da chiarire prima** (se ci sono task `Da categorizzare`):
- [task 1] — proposta categoria: [X]
- [task 2] — proposta categoria: [Y]

---

### 🔴 Fai tu (Lorenzo) — N task

| Task | Cat | Pri | Scadenza |
|---|---|---|---|
| [STRATEGIA] Riformulare segmentazione IT/EU → IT/DACH/EU | Strategia | — | 2026-04-15 |
| ... | ... | ... | ... |

### 🟡 Delega a me (Segretaria) — N task

| Task | Cat | Pri | Scadenza |
|---|---|---|---|
| Caricare estratto conto Revolut per autofatture | Admin | Media | 2026-05-08 |
| ... | ... | ... | ... |

### 🟢 Delega al team — N task

| Task | Cat | Pri | Scadenza |
|---|---|---|---|
| ... | ... | ... | ... |

---

**Quick wins (3 task delegabili subito)**:
1. [task] — perché: [1 riga]
2. [task] — perché: [1 riga]
3. [task] — perché: [1 riga]

**Bloccato in attesa / overdue** (se ce ne sono):
- ⚠️ [task] — scaduto il [data]
- 🐢 [task] — in `In corso` da troppo tempo
```

### 5. Sintesi finale (1-2 righe)
Sempre chiudere con una riga azionabile, tipo:
> "Su 15 task aperti, 8 sono delegabili (5 a me, 3 al team). Se mi dai il via,
> stamattina parto con i 3 quick win. Tu intanto puoi concentrarti sui 4 task
> Strategia con scadenza questa settimana."

## Aggiornare task (chiudere, riassegnare, cambiare priorita)

Per **chiudere task** (Status → Completato), batch o singoli, usa
[tools/notion_tasks.py](../tools/notion_tasks.py):

```bash
.venv/bin/python -c "
from tools.notion_tasks import mark_tasks_done_batch
ids = [
    '33c4a8e8-5355-...',  # Task 1
    'abcd1234-5678-...',  # Task 2
]
report = mark_tasks_done_batch(ids)
print(f'Chiusi: {len(report[\"succeeded\"])}/{report[\"total\"]}')
for f in report['failed']:
    print(f'  ❌ {f[\"id\"]}: {f[\"error\"]}')
"
```

Oppure single-task:
```python
from tools.notion_tasks import mark_task_done
mark_task_done(page_id="33c4a8e8-...")
```

Per cambiare altre proprietà (priorita, categoria, due date, name):
```python
from tools.notion_tasks import update_task_properties
update_task_properties(
    page_id="33c4a8e8-...",
    priorita="Alta",            # Alta/Media/Bassa
    categoria="Strategia",       # vedi CATEGORIE
    due_date="2026-04-30",       # ISO o None per rimuovere
    status="In corso",           # opzionale
)
```

**Workflow tipico "chiudi N task" da chat**:
1. Lorenzo dice "marca come fatte X, Y, Z"
2. Bot esegue `list_open_tasks()`, trova gli ID matching
3. Bot mostra a Lorenzo: "trovati questi N task con quel match: [lista]. Confermi la chiusura?"
4. **Aspetta conferma esplicita di Lorenzo** (mai chiudere senza OK)
5. Bot esegue `mark_tasks_done_batch(ids)`
6. Bot rilancia `list_open_tasks()` per **verificare** lo stato reale e riportare numeri **veri**
7. Bot conferma: "Chiusi N/M task. Restano K aperti."

**Anti-pattern critico (vedi CLAUDE.md "MAI FARE")**:
- ❌ MAI dire "fatto, chiuso N task" senza aver chiamato `mark_tasks_done_batch` davvero
- ❌ MAI saltare la verifica post-update (`list_open_tasks` di nuovo)
- ❌ Se le chiamate falliscono, dirlo subito, non inventare successo

## Edge case noti

- **La maggior parte dei task non ha Categoria/Priorità**: l'inferenza dal
  titolo è la regola, non l'eccezione. Sii esplicito quando inferisci ("ho
  classificato come Strategia perché il titolo inizia con [STRATEGIA]").
- **Task duplicati**: se vedi due task con titolo identico (es. "Check checkout
  flow + sms/whatsapp" comparso 2 volte), segnalalo. Probabilmente uno va
  chiuso.
- **Task senza scadenza**: tienili a parte, suggerisci di assegnare un due date
  per i delegabili.
- **`include_unassigned=True` di default**: i task senza assignee sono
  considerati di Lorenzo. Se non ti torna, prova `only_lorenzo=False` per
  vedere tutto, o filtra in Python.
- **Cliente come ID grezzo**: il campo `cliente_ids` ritorna ID Notion, non
  nomi. Per ora ignoralo nell'output (lookup Clienti_Mailift è future work).
- **Mobile**: il workflow funziona identicamente da Telegram bot — basta che
  Lorenzo dica "analizza i task". Il bot esegue il Bash, legge JSON,
  classifica.

## Apprendimenti

(Vuoto. Popolare quando emergono pattern: titoli ricorrenti che vanno
classificati in modo specifico, eccezioni alla matrice di delega, ecc.)

## Verifica end-to-end

1. `cd "/Users/lorenzobaretta/workflow ai" && .venv/bin/python tools/notion_tasks.py list`
   → vedi tabella riepilogo CLI con totali, breakdown e prime 10 righe.
2. Da Telegram: scrivi a `@mailiftbot` "analizza i miei task aperti su Notion".
   → bot lancia il Python, legge JSON, applica le regole, manda tabella.
3. Verifica edge: chiedi "solo i task amministrativi" → bot deve filtrare lato
   classificazione (categoria=Admin) senza modificare la query Notion.
