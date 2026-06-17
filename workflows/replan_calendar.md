# Replan Calendar — Time-Blocking dai Task Notion

## Obiettivo
Analizzare i task aperti di Lorenzo nel database **Tasks_Mailift** di Notion e
proporre un **piano time-blocked** sul Google Calendar che massimizzi
l'efficienza, rispettando vincoli di orario e gli eventi già esistenti.

L'output è **sempre una proposta da rivedere**, mai una scrittura diretta sul
calendario. Coerente con la regola CLAUDE.md "mai modifiche esterne senza OK".

## Quando usarlo
- **Manuale**: Lorenzo dice "ri-organizza il calendario", "fammi il piano",
  "time-block i task", oppure all'inizio della giornata/settimana.
- **Schedulato (futuro)**: lunedì 08:30 come parte della routine settimanale.

## Filosofia di pianificazione

1. **Batch per categoria** → minimizza context switching. Tutti i `Copy`
   insieme, tutti i `Tecnico` insieme.
2. **Deep work al mattino** (09:00–12:00) → riservato a task di alta
   concentrazione: `Strategia`, `Copy`. Niente meeting, niente task
   amministrativi.
3. **Lavoro reattivo nel pomeriggio** → `Design`, `Tecnico`, `Reportistica`,
   `Altro`. Categorie che tollerano interruzioni.
4. **Buffer del 20%** → non riempire al 100%. Se la giornata ha 8h utili,
   pianifica al massimo 6h30 di task. Il resto è buffer per imprevisti,
   email, follow-up.
5. **Priorità Alta prima** → all'interno di ciascuna fascia, ordina per
   `Priorità` (Alta > Media > Bassa) e poi per `Due Date` (più vicina prima).
6. **Overdue first** → i task scaduti vanno in cima, ma **mai più di 2 al
   giorno** per non bruciare l'energia recuperando arretrati.

## Vincoli fissi (NON toccare mai)

| Vincolo | Regola |
|---|---|
| **Eventi esistenti** | Tutto ciò che è già su Google Calendar è intoccabile. Mai proporre di spostare o cancellare. |
| **Pausa pranzo** | 13:00–14:00 sempre libera. |
| **Deep work AM** | 09:00–12:00 solo task `Strategia` / `Copy`. |
| **Stop serale** | Nessun task dopo le **19:00**. |
| **Weekend** | Sabato e domenica off. Se Lorenzo chiede esplicitamente di pianificare nel weekend, fai un'eccezione e segnalalo. |
| **Slot < 25 min** | I gap minori di 25 minuti restano vuoti (non vale la pena context-switch). |

## Input richiesti

### MCP server
- `mcp__claude_ai_Notion__notion-fetch` (per leggere il DB Tasks_Mailift)
- `mcp__claude_ai_Google_Calendar__gcal_list_events` (per gli eventi
  esistenti)
- `mcp__claude_ai_Google_Calendar__gcal_create_event` — **solo dopo
  approvazione esplicita** di Lorenzo

### Riferimenti DB
- `Tasks_Mailift` ID: `5dfdc59e-16de-4ab3-9846-8f69a433aff7`
- Schema: vedi [workflows/daily_inbox_triage.md](daily_inbox_triage.md)
  sezione "Schema property Tasks_Mailift"

### Calendar
- Calendario: `primary` di Lorenzo (Europe/Rome)

## Esecuzione (sequenza)

### 1. Pull task aperti
- Query Notion `Tasks_Mailift` filtrato per:
  - `Status` ∈ {`To-do`, `In corso`}
  - `Assign` = Lorenzo (`f33fe0ac-6358-43f9-93e2-40f54dfed7c5`)
- Per ciascun task estrai: `Name`, `Categoria`, `Priorità`, `Due Date`,
  `Cliente` (relation, se popolata).

**Nota**: nessun filtro su data. Prendiamo tutti i task aperti.

### 2. Stima durata per ciascun task
Notion non ha campo `durata`. Stima sulla base di `Categoria` + titolo:

| Categoria | Default | Note |
|---|---|---|
| `Strategia` | 90 min | Range 60–180 a seconda del titolo |
| `Copy` | 60 min | Range 30–120, dipende da quante email/asset |
| `Design` | 60 min | Range 30–120 |
| `Tecnico` | 45 min | Range 15–120 |
| `Reportistica` | 45 min | Range 30–90 |
| `Altro` | 30 min | Default conservativo |

Se il titolo contiene segnali tipo "veloce", "5 minuti", "rapido" → 15 min.
Se contiene "completo", "draft + revisione", "tutta la settimana" → estremo
alto del range.

**Mostra le stime nel piano** così Lorenzo può correggerle.

### 3. Pull eventi calendario
- `gcal_list_events` per i prossimi **5 giorni lavorativi** (oggi + 4) sul
  calendario `primary`. Time zone Europe/Rome.
- Estrai per ogni evento: `start`, `end`, `summary`, `attendees` (per capire
  se è interno/cliente).

### 4. Calcola gli slot disponibili
Per ciascun giorno lavorativo nei prossimi 5gg (lun-ven):
1. Parti dalla finestra `09:00–19:00` Europe/Rome.
2. Sottrai `13:00–14:00` (pranzo).
3. Sottrai tutti gli eventi esistenti.
4. Spezza la fascia AM (09–12) dalla PM (14–19).
5. Risultato: una lista di gap `[start, end, slot_type=AM|PM]` per giorno.
6. Scarta i gap < 25 min.

### 5. Allocazione

**Pass 1 — Deep work (slot AM)**
- Filtra task con `Categoria` ∈ {`Strategia`, `Copy`}.
- Ordina per: `OVERDUE` > `Priorità Alta` > `Due Date asc` > `Priorità Media`.
- Riempi i gap AM batchando per categoria (tutti i Copy consecutivi, poi
  Strategia, ecc.) finché entrano.
- Lascia almeno 20% dello slot AM giornaliero come buffer.

**Pass 2 — Lavoro reattivo (slot PM)**
- Tutti gli altri task: `Design`, `Tecnico`, `Reportistica`, `Altro`.
- Stesso ordinamento del Pass 1.
- Riempi i gap PM batchando per categoria.
- Buffer 20%.

**Pass 3 — Overflow Strategia/Copy in PM**
- Se restano task Strategia/Copy non allocati e ci sono ancora slot PM
  liberi, mettili **in fondo al pomeriggio** (non l'ideale ma meglio che
  niente). Segnalali con un ⚠️ "fuori deep work AM".

**Limite "max 2 overdue al giorno"**: applicato in entrambi i pass.

### 6. Task non allocati
Tutto ciò che non entra nei 5 giorni va in una sezione **"Backlog non
pianificato"** del piano, con motivazione (es. "5 task Strategia eccedono
gli slot AM disponibili"). Lorenzo decide cosa fare: posticipare scadenze,
delegare, droppare.

### 7. Output del piano (in chat)

Formato esatto:

```markdown
# Piano calendario — generato [data ora]

## Vincoli applicati
- Deep work AM (09–12): solo Strategia/Copy
- Pranzo 13–14: libero
- Stop 19:00, no weekend
- Eventi esistenti: intoccabili
- Buffer 20% per giorno

## [Lunedì DD/MM]
**Eventi esistenti** (intoccabili):
- 10:30–11:00 — Call Bergamo Vini
- 15:00–16:00 — Demo HCF

**Time-block proposti**:
| Slot | Categoria | Task | Durata | Priorità | Cliente |
|---|---|---|---|---|---|
| 09:00–10:30 | Copy | [titolo task] | 90' | Alta | EV8 |
| 11:00–12:00 | Strategia | [titolo] | 60' | Alta | — |
| 14:00–14:45 | Tecnico | [titolo] | 45' | Media | HCF |
| 16:00–17:00 | Reportistica | Report Klaviyo EV8 | 60' | Alta | EV8 |
| 17:00–17:30 | Altro | [titolo] | 30' | Bassa | — |

**Buffer**: ~1h30 (riservato a email/follow-up/imprevisti)

## [Martedì DD/MM]
[stessa struttura]

…

## Backlog non pianificato (NON entra nei prossimi 5gg)
- [task 1] — Strategia, 90', Alta — motivazione: slot AM saturi
- [task 2] — Copy, 60', Media — motivazione: scadenza oltre il piano
- …

## Statistiche
- Task aperti totali: N
- Allocati nei 5gg: M (X ore di lavoro pianificato)
- Backlog: K
- Overdue trattati: J / totali Z
- Capacity utilizzata media: Y%
```

### 8. Conferma e creazione eventi (passaggio separato)

**Mai automatico.** Dopo che Lorenzo ha visto il piano:

- Se dice "ok crea tutto" → loop su ogni time-block e chiama
  `gcal_create_event` con:
  - `summary`: `[Categoria] Titolo task`
  - `description`: link al task Notion + cliente + priorità + nota "creato
    automaticamente da workflow replan_calendar"
  - `start`/`end`: come da piano
  - `colorId`: opzionale, per distinguere visivamente le categorie
- Se dice "ok solo lunedì" → crea solo gli eventi del giorno indicato.
- Se dice "modifica X" → ricalcola con il vincolo nuovo, ripresenta il piano.

**Niente attendees** sugli eventi creati: sono blocchi personali di Lorenzo,
non meeting.

## Edge case noti

- **Calendario molto pieno**: se la capacità utilizzata media supera il 90%
  in più di 2 giorni, segnala in cima al piano "settimana sovraccarica,
  considera di delegare/posticipare" con suggerimenti specifici.
- **Task senza categoria**: trattali come `Altro` ma flagga in cima al piano
  così Lorenzo può tornare in Notion e categorizzarli.
- **Task senza priorità**: tratta come `Media`.
- **Task con `Due Date` nel passato (overdue)**: priorità massima ma rispetta
  il limite di 2/giorno per non bruciare la giornata.
- **Eventi all-day**: se ci sono eventi all-day (es. ferie), considera
  l'intera giornata occupata e salta al giorno successivo.
- **Cliente specifico richiesto**: se Lorenzo dice "pianifica solo cose per
  EV8", filtra il pull Notion per `Cliente` = EV8.
- **Replanning a metà giornata**: se chiamato a metà giornata, salta gli slot
  ormai passati e parti dall'ora corrente arrotondata ai 15 min superiori.

## Apprendimenti

(Vuoto. Popolare quando emerge che certi pattern di pianificazione non
funzionano per Lorenzo — es. "i Tecnico in tarda serata non li fa mai".)

## Verifica end-to-end (prima volta)

1. Lorenzo dice "ri-organizza il calendario".
2. Pull task da Notion (`Status` ∈ To-do/In corso, assignee Lorenzo).
3. Pull eventi GCal prossimi 5gg.
4. Calcola gli slot, applica i 3 pass, genera il piano markdown.
5. **Mostra in chat senza creare nulla**.
6. Lorenzo rivede, corregge stime di durata se serve, dice "ok crea" o
   "modifica X".
7. Solo allora chiama `gcal_create_event` per gli slot approvati.
8. Conferma in chat: "Creati N eventi su Google Calendar." con la lista.
