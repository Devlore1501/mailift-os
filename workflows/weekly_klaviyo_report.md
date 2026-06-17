# Weekly Klaviyo Report

## Obiettivo
Generare un **report Klaviyo settimanale** per ciascun cliente attivo Mailift,
confrontando le metriche degli ultimi 7 giorni con la settimana precedente,
evidenziando anomalie e proponendo 3 insight azionabili.

Il report serve a Lorenzo per:
1. Aprire la settimana avendo già il polso di cosa è successo su ogni account
2. Avere materiale pronto per check-in cliente
3. Intercettare cali di deliverability o flussi rotti **prima** che il cliente
   se ne accorga

## Quando usarlo
- **Schedulato**: ogni **lunedì mattina** (priorità giornaliera n°3 nel
  CLAUDE.md Segretaria).
- **Manuale**: Lorenzo dice "fammi il report settimanale Klaviyo di [cliente]"
  o "report Klaviyo della settimana".

## Input richiesti

### Account Klaviyo (uno per cliente)
| Cliente | Account Klaviyo | Note |
|---|---|---|
| EV8 Style | (da identificare via `klaviyo_get_account_details` al primo run) | Segmenti IT/EU separati |
| HCF | (idem) | Setup in corso, primi flussi attivi |
| Bergamo Vini | (idem) | 2 campagne/settimana, sabato 9:30 |

> Al primo run su un cliente nuovo, salva lo `account_id` qui in tabella per
> i run successivi.

### MCP server richiesto
- `claude_ai_Klaviyo` (già configurato, vedi MCP servers nel CLAUDE.md root)

Nessun nuovo tool Python. Tutto tramite MCP.

## Esecuzione (sequenza per ciascun cliente)

### 1. Conferma account
- Usa `mcp__claude_ai_Klaviyo__klaviyo_get_account_details` per verificare di
  essere sull'account giusto. Se ce ne sono più collegati, chiedi a Lorenzo
  quale prima di proseguire.

### 2. Pull dati ultimi 7 giorni + 7 giorni precedenti
**Campagne:**
- `mcp__claude_ai_Klaviyo__klaviyo_get_campaigns` filtrato per `send_time`
  negli ultimi 14 giorni.
- Per ciascuna campagna trovata negli ultimi 7gg: `klaviyo_get_campaign_report`
  per metriche complete (recipients, open rate, CTR, revenue).

**Flussi:**
- `mcp__claude_ai_Klaviyo__klaviyo_get_flows` per la lista dei flussi attivi.
- Per ciascun flusso "live": `klaviyo_get_flow_report` filtrato sugli ultimi
  7 giorni e sui 7 precedenti.

**Metriche aggregate (opzionale, se serve overview):**
- `klaviyo_query_metric_aggregates` per "Placed Order" e "Email Revenue"
  attribuiti a Klaviyo, raggruppati per giorno.

### 3. Confronto e tabella sintetica

Compila una tabella per cliente con questa struttura:

| Metrica | Settimana attuale | Settimana precedente | Δ% | Status |
|---|---|---|---|---|
| Email inviate | … | … | … | 🟢/🟡/🔴 |
| Open rate medio | … | … | … | … |
| CTR medio | … | … | … | … |
| Click-to-open rate | … | … | … | … |
| Revenue attribuita | … | … | … | … |
| Unsubscribe rate | … | … | … | … |
| Bounce rate | … | … | … | … |
| Spam complaint rate | … | … | … | … |

**Soglie status:**
- 🟢 = stabile o migliorato
- 🟡 = peggioramento <10% (osservare)
- 🔴 = peggioramento >10% **oppure** valore assoluto sopra soglia critica:
  - Bounce rate > 2%
  - Spam complaint rate > 0.1%
  - Unsubscribe rate > 0.5% per singola campagna
  - Open rate < 15% (warning Apple MPP a parte)

### 4. Sezione "Top campagne della settimana"
Le 3 campagne con miglior **revenue per recipient** della settimana, con:
nome, data invio, recipients, open rate, CTR, revenue.

### 5. Sezione "Flussi attivi — performance"
Tabella con: nome flusso, trigger, recipients ultimi 7gg, conversion rate,
revenue, delta vs settimana precedente. Evidenzia in rosso i flussi con calo
di conversion >20%.

### 6. Sezione "Anomalie & alert"
Liste segnaletiche, vuote se va tutto bene:
- Cali di deliverability (bounce/spam sopra soglia)
- Flussi che hanno smesso di triggherare (recipients = 0 settimana attuale,
  >0 settimana precedente)
- Segmenti con drop improvviso
- Campagne pianificate ma non inviate

### 7. Tre insight azionabili
Sempre **esattamente 3**. Devono essere concreti e prescrittivi, non generici.
Esempi:
- ❌ "Migliorare gli open rate" (vago)
- ✅ "Il flusso Welcome Series ha CR 8.2% vs 12.4% della scorsa settimana —
  controllare se il codice sconto WELCOME10 è scaduto"
- ✅ "Campagna 'Pasqua10' ha 2.1× revenue/destinatario rispetto alla media —
  replicare segmento 'high engagement IT' su prossima campagna"
- ✅ "Bounce rate al 2.4% (sopra soglia 2%): pulire segmento 'inattivi 90gg'
  prima del prossimo invio massivo"

### 8. Salvataggio del report
**Default**: incolla il report in chat come tabelle markdown + sezioni.

**Se Lorenzo lo richiede esplicitamente**: salva in Notion creando una pagina
nel database appropriato (TBD: per ora `Tasks_Mailift` come task di tipo
`Reportistica`, oppure documento Drive nella cartella cliente). **Non
inventare strutture**: chiedi conferma sulla destinazione la prima volta.

## Output atteso (template)

```markdown
# Report Klaviyo — [Cliente] — Settimana [data inizio] → [data fine]

## Sintesi
[2-3 righe: andamento generale, fatto saliente]

## Metriche chiave
[tabella sezione 3]

## Top campagne
[tabella sezione 4]

## Flussi attivi
[tabella sezione 5]

## Anomalie & alert
[liste sezione 6, oppure "Nessuna anomalia rilevata 🟢"]

## Azioni consigliate (3)
1. [insight 1]
2. [insight 2]
3. [insight 3]
```

## Edge case noti

- **Account multipli sullo stesso MCP**: chiedere a Lorenzo prima di assumere
  quale sia il cliente target.
- **Cliente senza campagne nella settimana**: se sono solo flussi, salta la
  sezione "Top campagne" e concentrati su flow report.
- **Apple MPP inflation**: gli open rate da iOS Mail sono gonfiati dalle
  privacy protection. Quando segnali un open rate alto, contestualizza
  guardando il CTR, che è più affidabile.
- **Periodo con festività**: se la settimana precedente conteneva una festa
  (Black Friday, Pasqua, Natale), il delta % sarà fuorviante. Aggiungi una
  nota in sintesi.
- **Cliente nuovo (HCF setup)**: se non ci sono ancora 7gg di storico, fai
  un report "best effort" con i dati disponibili e segnalalo.

## Apprendimenti

(Vuoto. Popolare man mano che emergono pattern/quirks dei singoli account.)

## Verifica end-to-end (prima volta)
1. Lorenzo chiede: "fammi il report settimanale Klaviyo per EV8".
2. Conferma account via `klaviyo_get_account_details`.
3. Pull campagne + flussi 14 giorni.
4. Compila tabella sezione 3 — verifica che le metriche tornino con
   l'interfaccia Klaviyo.
5. Genera 3 insight azionabili (no platitudini).
6. Riporta in chat.
7. Lorenzo conferma se vuole salvarlo in Notion/Drive: solo allora persisti.
