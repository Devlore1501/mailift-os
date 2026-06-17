# Discovery Call Processing

## Obiettivo
Trasformare una **trascrizione Fathom** di discovery call in:
1. Una **classificazione lead** strutturata (HOT / WARM / COLD)
2. Un **briefing** ben strutturato che Lorenzo possa rivedere prima del
   follow-up
3. **Note sintetiche per il CRM (GHL)** — `[TODO: bloccato finché GHL API non
   è in .env]`
4. Una **proposta di slot follow-up** se il lead è HOT

L'obiettivo finale è ridurre il tempo che Lorenzo spende su post-call admin
da ~15 minuti a ~2 minuti di review.

## Quando usarlo
- **Trigger manuale**: Lorenzo passa una trascrizione Fathom (paste in chat,
  link al file, o path locale).
- **Trigger automatico futuro**: quando Fathom verrà integrato (oggi
  ingestion è manuale).

## Input richiesti

### Da Lorenzo
- Trascrizione completa Fathom (testo)
- Nome lead / azienda (se non è chiaro dalla trascrizione)
- Sito eCommerce del lead (se disponibile, per arricchimento)

### MCP server richiesti
- `mcp__claude_ai_Gamma__generate` (per il briefing)
- `mcp__claude_ai_Google_Calendar__gcal_find_meeting_times` +
  `gcal_create_event` (per follow-up HOT)

### Tool Python richiesti
- [tools/ghl_client.py](../tools/ghl_client.py) — find/create contact, add note,
  add tags. Usa Personal Integration Token GHL scoped a Mailift location.

### Variabili `.env`
- `GHL_API_KEY` (Personal Integration Token, prefisso `pit-`) — ✅ configurato
- `GHL_LOCATION_ID` — ✅ configurato (Mailift)

## Esecuzione (sequenza)

### 1. Estrazione strutturata
Dalla trascrizione, estrai e popola questo schema (interno, non mostrarlo
ancora):

```json
{
  "azienda": "...",
  "contatto": "...",
  "settore": "...",
  "fatturato_mese_eur": "...",
  "canale_principale": "Shopify | WooCommerce | Magento | altro",
  "esp_attuale": "Klaviyo | Mailchimp | Brevo | nessuno | altro",
  "team_marketing": "in-house | agenzia | nessuno",
  "pain_points": ["...", "..."],
  "obiettivi_dichiarati": ["...", "..."],
  "budget_segnali": "...",
  "tempistiche": "...",
  "decision_maker": "sì/no/non chiaro",
  "obiezioni_emerse": ["..."],
  "next_steps_proposti": "..."
}
```

Se un campo non emerge dalla call, mettilo a `null`. Non inventare.

### 2. Classificazione HOT / WARM / COLD

Applica i criteri ICP del CLAUDE.md Segretaria:

| Tipo | Criteri |
|---|---|
| **HOT** | eCommerce DTC italiano + Shopify + Klaviyo (o pronto a usarlo) + fatturato €25k–€300k/mese + pain point chiari + decision maker in call + budget compatibile |
| **WARM** | Settore giusto ma manca **un solo** requisito (es. fatturato €15-25k, oppure usa Mailchimp ma vuole migrare, oppure decision maker non in call) |
| **COLD** | B2B, no Shopify, fatturato troppo basso (<€15k) o troppo alto (€500k+ → di solito ha già agenzia in-house), settore fuori ICP, nessun pain emergente |

**Output classificazione:**
```
Classificazione: HOT
Motivazione: [2-3 righe specifiche sul perché — citare elementi della call]
Red flag: [se ce ne sono, anche per HOT]
```

### 3. Briefing strutturato (Gamma)

Usa `mcp__claude_ai_Gamma__generate` per creare un briefing visuale.
Struttura suggerita:

1. **Slide 1 — Sintesi lead**: azienda, contatto, classificazione, settore
2. **Slide 2 — Numbers**: fatturato, canale, ESP attuale, team
3. **Slide 3 — Pain points** (bullet list, citazioni quasi-letterali)
4. **Slide 4 — Obiettivi del lead** (cosa vuole ottenere)
5. **Slide 5 — Fit con Mailift**: dove possiamo aiutare specificamente
6. **Slide 6 — Obiezioni emerse + come rispondere**
7. **Slide 7 — Next steps proposti + slot follow-up**

**Default tema Gamma**: lascia il default (la Segretaria non sceglie temi
salvo richiesta esplicita di Lorenzo). Lingua: **italiano**.

Salva il file ID del Gamma generato per riferimento futuro.

### 4. Sync su GHL (find/create contact + nota + tag)

Sequenza Python via [tools/ghl_client.py](../tools/ghl_client.py):

```python
from tools.ghl_client import find_or_create_contact, add_note, add_tags

# 4.1 — find o crea il contatto
contact, was_created = find_or_create_contact(
    email=lead_email,
    first_name=lead_first_name,
    last_name=lead_last_name,
    company_name=azienda,
    phone=lead_phone,        # se disponibile
    source="discovery_call",
    tags=[],                 # i tag li mettiamo dopo
)
contact_id = contact["id"]

# 4.2 — aggiungi nota briefing strutturato
note_body = f"""## Discovery Call — {data_iso}

**Classificazione:** {classificazione}  ({hot_warm_cold_emoji})
**Motivazione:** {motivazione_2_3_righe}

### Sintesi
- Settore: {settore}
- Fatturato/mese: {fatturato}
- ESP attuale: {esp}
- Decision maker in call: {dm_yes_no}
- Budget signal: {budget}

### Pain points
{bullet_list(pain_points)}

### Next steps
{next_steps_text}

### Briefing Gamma
{gamma_url_or_id}
"""
add_note(contact_id=contact_id, body=note_body)

# 4.3 — applica tag classificazione
add_tags(contact_id=contact_id, tags=[
    f"discovery-{classificazione.lower()}",   # discovery-hot / -warm / -cold
    f"settore-{settore_slug}",
    "discovery-{anno}-{mese}",                # es. discovery-2026-04
])
```

**Convenzioni tag** (mantenere coerenti per filtri GHL):
- `discovery-hot` / `discovery-warm` / `discovery-cold`
- `settore-{slug}` (es. `settore-fashion`, `settore-cosmesi`)
- `discovery-{YYYY}-{MM}` per cohort

**Errori da gestire**:
- Se `find_or_create_contact` fallisce per email duplicata con grafia diversa
  (caso edge): cerca anche per `query=nome+cognome` e segnalalo a Lorenzo
  prima di creare un duplicato
- Se `add_note` fallisce: non bloccare il workflow, mostra il blocco markdown
  in chat come fallback per copia-incolla manuale

### 5. Slot follow-up (solo se HOT)

Se la classificazione è HOT:
1. `mcp__claude_ai_Google_Calendar__gcal_find_my_free_time` per i prossimi
   3 giorni lavorativi (08:00–19:00 Europe/Rome, durata 30min).
2. Proponi a Lorenzo **3 slot** disponibili.
3. **Non creare l'evento direttamente** — Lorenzo conferma quale e poi
   chiama `gcal_create_event` con:
   - Title: `Follow-up [Azienda] — Lorenzo / [Contatto]`
   - Description: link al briefing Gamma + sintesi 3 righe
   - Attendee: email del lead (chiedere a Lorenzo se non in trascrizione)
   - **Bozza email di invito**, MAI inviata: la prepari come draft Gmail
     se Lorenzo lo richiede.

Se WARM: proponi un follow-up più rilassato (1-2 settimane dopo) e suggerisci
un'azione di nurturing (es. inviare un case study).

Se COLD: segnala motivo e archivia in chat senza creare nulla. Niente
follow-up automatico.

## Output finale (template chat)

```markdown
## Discovery Call — [Azienda]

**Classificazione**: 🔥 HOT / 🌡️ WARM / ❄️ COLD
**Motivazione**: [2-3 righe]

### Sintesi
- Settore: …
- Fatturato: …
- ESP attuale: …
- Decision maker in call: sì/no
- Budget signal: …

### Pain points principali
- …
- …

### Briefing Gamma
[link / file ID generato]

### GHL
- Contatto: {contact_id} ({"creato" se nuovo, "aggiornato" se esistente})
- Nota aggiunta: {note_id}
- Tag applicati: discovery-{classificazione}, settore-{slug}, discovery-{cohort}

### Next steps
- [se HOT] Slot follow-up proposti:
  - Opzione A: …
  - Opzione B: …
  - Opzione C: …
- [se WARM] Suggerisco nurturing: …
- [se COLD] Nessuna azione, archivio.
```

## Edge case noti

- **Trascrizione incompleta o di bassa qualità**: se mancano informazioni
  cruciali (settore, fatturato), elenca cosa manca e chiedi a Lorenzo prima
  di classificare. Una classificazione sbagliata HOT/COLD ha costo alto.
- **Lead non italiano**: ICP è italiano ma se il lead parla inglese e il
  fit è altrimenti perfetto, classificalo HOT con flag "lingua: EN" — sarà
  Lorenzo a decidere se gestirlo.
- **Più persone nella call dal lato lead**: identifica chi è il decision
  maker. Se non emerge, segnalalo come red flag.
- **Lead già cliente o ex-cliente**: skippa la classificazione, fai solo il
  briefing + note GHL.
- **Trascrizione Fathom con timestamp/speaker labels**: estraili pure ma non
  inquinare il briefing finale con timestamps.

## Apprendimenti

### Architettura eventi CAPI → Meta (audit 10/06/2026)

I segnali di conversione verso Meta partono da **un solo workflow GHL**:
`capi stage change positivi` (pipeline "E-commerce | Offerta"), con scala
eventi per profondità funnel:

| Stage GHL | Evento Meta | Valore |
|---|---|---|
| Fissata call analisi | Funnel Event → **Schedule** | — (filtro tag "non qualificato" a monte) |
| Presentazione offerta | **Lead Event** | — |
| Chiuso (contratto) | Funnel Event → **Purchase** | `{{opportunity.lead_value}}` EUR |

Regole emerse dall'audit:
- **Mai trigger CAPI sullo stage "Lead"** (pre-qualifica): manda segnali
  sporchi. Rimosso il 10/06/2026.
- Il flusso `Report personalizzato email - verifica e FU 50 bot` filtra i
  lead a monte (squalifica <10/15k €/mese, budget ads 0-3k, fatturato ecom
  0-25k) e applica tag "non qualificato" + Set Unqualified. La fascia
  15-25k resta dentro **di proposito** (vendibile setup). I campi form sono
  obbligatori, quindi niente leak da risposte vuote.
- ⚠️ Il trigger di quel flusso è "qualsiasi modulo" sulla pagina: **ogni
  form nuovo con campi rinominati bypassa i filtri** → aggiornare i Branch
  quando si crea un form.
- Nei Condition GHL, **mai lasciare azioni CAPI nel ramo ELSE** ("none of
  the conditions met"): ogni trigger futuro ci cadrebbe dentro. Rami sempre
  espliciti per nome trigger.
- ⚠️ Il campo "Codice di prova" (test code) nel nodo CAPI rende gli eventi
  **invisibili all'ottimizzazione Meta** (solo Test Events). Il flusso
  `Schedule call report - CAPI` è rimasto con `TEST9253` attivo da ott 2025
  a giu 2026 senza mandare nulla di reale → eliminato (duplicava lo
  Schedule dello stage change). Controllare sempre che il test code sia
  vuoto in produzione.

### Limiti API GHL (per i tool)
- `GET /workflows/` accetta **solo** `locationId` (param extra → HTTP 422)
  e ritorna solo metadati: trigger/step/azioni NON sono esposti via API,
  servono UI o screenshot.

(Popolare anche con pattern di lead, motivazioni di mis-classificazione, ecc.)

## Verifica end-to-end (prima volta)

1. Lorenzo passa una trascrizione Fathom in chat.
2. Estrai schema strutturato (sezione 1) — chiedi conferma se mancano dati
   critici.
3. Classifica HOT/WARM/COLD con motivazione.
4. Genera briefing Gamma → verifica che il file sia accessibile a Lorenzo.
5. Produci blocco "Note GHL" markdown da copia-incollare manualmente.
6. Se HOT: proponi 3 slot, **non creare l'evento finché Lorenzo non sceglie**.
7. Lorenzo dà feedback su classificazione e briefing → aggiorna gli
   "Apprendimenti" qui se c'è una lezione.
