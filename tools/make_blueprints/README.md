# Make blueprints

## outreach_personalization.json

Scenario Make (5 moduli, HTTP `http:MakeRequest` v4): legge le righe del foglio contatti →
scrape della homepage → HTML a testo → Claude genera la prima riga personalizzata →
scrive in colonna K.

ID moduli: `41` trigger · `42` GET · `3` HTML to text · `45` Claude · `5` update row.

Mappato sul foglio **installatoriromaoutreach** (Google Sheets):

| Col | Header            | Indice Make | Uso                                  |
|-----|-------------------|-------------|--------------------------------------|
| A   | Priorita          | `0`         | —                                    |
| B   | Azienda           | `1`         | input prompt                         |
| F   | Website           | `5`         | input scraping                       |
| H   | Citta             | `7`         | input prompt                         |
| K   | Personalizzazione | `10`        | **output** (scritto dallo scenario)  |

Trigger = `watchRows`: tiene il cursore sull'ultima riga letta, quindi non riprocessa
le righe già fatte. Se aggiungi righe in fondo le prende al run successivo; se vuoi
rilanciare tutto, resetta il trigger ("Choose where to start").

### Stato reale del foglio (letto il 2026-07-23)

- 256 righe dati, colonna Personalizzazione **tutta vuota**
- 209 righe con Website — **138 sono `http://`**, 71 `https://`, nessuna senza schema
- 187 righe hanno Website **e** Email → sono quelle che lo scenario processa
- 22 righe hanno il sito ma non l'email: escluse dal filtro per non spendere token
  su contatti non raggiungibili via email. Togli la condizione `Email exist` sul
  modulo 2 se vuoi personalizzare anche per l'outreach WhatsApp.
- 5 siti sono `*.business.site` (schede Google Business): contenuto minimo, quasi
  certamente `NO_DATA`
- Colonna Citta inaffidabile (163 "Roma", 73 "Rome", alcune righe con indirizzi o
  numeri) → **non viene passata al prompt**, la città si ricava dal sito

Costo stimato del run completo: ~$1,1 (187 righe, `claude-sonnet-5`), ~935 operazioni Make.

### Import in Make

1. Scenario → `⋯` → **Import Blueprint**.
2. Modulo 1 e 5 (Google Sheets): seleziona la connessione, poi **ri-seleziona Drive,
   spreadsheet e sheet** dai dropdown (l'export segnalava `Drive: Value must not be empty`).
3. Modulo 4 (HTTP → Anthropic): metti la tua API key nell'header `x-api-key`.
4. Run once con `limit: 10` sul trigger, controlla la colonna K, poi alza il limit.

### Punti tecnici che rompono questo scenario (già risolti nel file)

- **Riferimenti al trigger**: i campi si chiamano `0..25`, si mappano con backtick —
  `{{41.\`5\`}}`, non `{{1.F}}`.
- **Row number**: `{{41.__ROW_NUMBER__}}`, mai una colonna dati.
- **Mai virgolette dentro `{{ }}` nel body raw dell'HTTP.** All'import Make ri-parsa
  il body e distrugge le espressioni IML che contengono literal fra virgolette:
  `{{replace(x; "/regex/g"; ".")}}` diventa `{{\}}{{\}}.`. I riferimenti senza
  virgolette (`{{41.\`5\`}}`, `{{6.testopulito}}`) sopravvivono intatti.
  Per questo la pulizia del testo sta nel **modulo 4 "Pulisci testo (JSON-safe)"**
  (Set variable), dove le espressioni stanno in un campo normale, e il body usa solo
  `{{6.testopulito}}`.
- **Escaping del body JSON con `encodeURL`, non con `replace`.** Il testo scrapato
  contiene virgolette e a-capo che invalidano il JSON della chiamata API
  (`Bad control character in string literal`). Le versioni con `replace` + regex
  whitelist **non reggono**: quel campo contiene literal fra virgolette e Make lo
  mangia anche nel Set variable, lasciando passare il testo grezzo. La variabile vale:

      {{encodeURL(substring(3.text; 0; 4000))}}

  Zero virgolette → niente che il parser possa rompere, quindi l'espressione può stare
  **direttamente nel body**, senza modulo Set variable. `encodeURL` percent-encoda
  tutto ciò che romperebbe il JSON: `"` → `%22`, a capo → `%0A`, tab → `%09`,
  backslash → `%5C`. Il system prompt istruisce Claude a decodificarlo.
  Costo: il testo del sito occupa ~2,5x i token, per questo il taglio è a 4.000
  caratteri invece di 6.000.
- **La risposta di Claude è `{{45.data.content[1].text}}`**, non `{{45.data}}`
  (`data` è l'intero oggetto della risposta API — scriverlo in cella mette
  `[object Object]`). Gli array in Make partono da 1, non da 0.
- **Filtri AND vs OR**: in Make `conditions: [[A, B]]` = AND, `[[A],[B]]` = OR.
- **Il modulo HTTP v4 rifiuta gli URL `http://`** con `InvalidConfigurationError:
  Invalid URL`. Testato su un run reale: 5 URL `http` su 5 rifiutati, 0 rifiuti fra
  gli `https` (che davano invece errori di rete veri: 404, timeout, unreachable).
  Soluzione: **Find & Replace sul foglio**, `http://` → `https://` in colonna F,
  così il campo url resta `{{41.\`5\`}}` senza espressioni. Costo misurato su un
  campione di 40 siti: 27 raggiungibili con l'URL originale, 26 forzando https —
  si perde ~1 sito su 40 (quelli senza certificato).

### Gestione errori

- Sito irraggiungibile / timeout → `Ignore`, riga saltata.
- Status ≠ 200 o HTML < 500 caratteri → filtro blocca.
- Claude risponde `NO_DATA` (sito senza info utili) → non scrive, riga da fare a mano.

### Costi

~6.000 caratteri di sito per riga → ~$0,006 per contatto con `claude-sonnet-5`.
5 operazioni Make per riga.

---

## lead_precall_research.json

Scenario Make (7 moduli): GHL manda un webhook quando un lead prenota la discovery call →
scrape del sito → HTML a testo → Claude genera il dossier pre-call → nota sul contatto GHL
+ tag `precall-research-done` + notifica Telegram a Lorenzo.

ID moduli: `1` webhook · `2` GET sito · `3` HTML→testo · `4` Claude · `5` nota GHL ·
`6` tag GHL · `7` Telegram.

Setup completo (trigger GHL, mappatura delle 28 chiavi Custom Data, fallback sito dal
dominio email, costi): [workflows/lead_research.md](../../workflows/lead_research.md),
sezione "Automazione — GHL + Make.com (v3)".

### Segnaposto da sostituire dopo l'import
`INSERISCI_ANTHROPIC_API_KEY` (mod. 4) · `Bearer INSERISCI_GHL_API_KEY` (mod. 5 e 6) ·
`INSERISCI_TELEGRAM_BOT_TOKEN` e `INSERISCI_TELEGRAM_CHAT_ID` (mod. 7).

### Punti tecnici già risolti nel file
- **Thinking di `claude-sonnet-5` disabilitato esplicitamente** (`"thinking": {"type":
  "disabled"}`). Senza, la risposta è solo un blocco `thinking` e `content[1]` non contiene
  il dossier — testato: 2000 token bruciati, zero testo.
- **Claude non restituisce JSON** ma markdown su una riga con `\n` letterali e senza
  virgolette doppie: incapsulava il JSON in ```json anche con istruzione contraria. Il
  modulo 5 lo inserisce in `{"body": "{{4.data.content[1].text}}"}`.
- **Zero virgolette dentro `{{ }}`** in tutto il blueprint (regola dell'import Make, vedi
  sopra). L'unica espressione che ne ha bisogno — il fallback del sito dal dominio email —
  è documentata come incollata a mano nell'URL del modulo 2.
- **`ifempty(1.x; 1.customData.x)`** su ogni campo: regge sia il payload GHL piatto sia
  quello annidato in `customData`.
- **`Resume` sul modulo 2**: sito irraggiungibile o URL invalido → lo scenario prosegue e
  genera il dossier dai soli dati del form, invece di saltare il lead.

### Costi
~$0,06 per lead (`claude-sonnet-5`, ~11k token input) · 6-7 operazioni Make per lead.

---

## lead_precall_research_deep.json

Variante deep della precedente: **10 moduli**, aggiunge la ricerca online vera (titolari,
LinkedIn, premi, stampa, dati camerali/P.IVA, dinamiche di settore) usando il web search
nativo dell'API Anthropic — nessun account esterno.

ID moduli: `1` webhook · `2` GET sito · `3` HTML→testo · `4` Claude ricerca (web_search +
web_fetch) · `5` iterator sui blocchi · `6` text aggregator · `7` Claude dossier (prefill) ·
`8` nota GHL · `9` tag GHL · `10` Telegram.

Costo misurato: **~$0,45 per lead** (vs ~$0,06 della versione base). Documentazione completa
in [workflows/lead_research.md](../../workflows/lead_research.md), sezione "Automazione v4".

### Due cose da non toccare
- **Modulo 4**: header `anthropic-beta: web-fetch-2025-09-10`, senza il quale il fetch delle
  pagine non parte.
- **Modulo 7**: modello `claude-sonnet-4-5`. Usa il **prefill** (ultimo messaggio `assistant`
  = `{"body": "` + `stop_sequences: ["\"}"]`) per ottenere un dossier già JSON-escapato.
  `claude-sonnet-5` e `claude-opus-4-6` **rifiutano il prefill** con 400.

### Perché due chiamate e non una
Con il web search attivo la risposta arriva spezzata in ~47 blocchi (le citazioni frammentano
il testo) e il modello commenta tra una ricerca e l'altra: nessun riferimento fisso regge.
Iterator + Text aggregator ricompongono, poi una seconda chiamata senza tool produce il
dossier in un blocco unico.
