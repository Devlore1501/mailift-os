# Segretaria Telegram — Sistema 24/7

## Obiettivo
Trasformare la Segretaria Operativa Mailift da assistente **on-demand** (apri
Claude Code, parli, chiudi) a un servizio **always-on** con cui Lorenzo
interagisce da mobile via Telegram, e che lo contatta proattivamente per
reminder, alert e briefing.

L'obiettivo è eliminare il bisogno di "ricordarsi di chiedere": la Segretaria
deve scrivere a Lorenzo prima che lui si renda conto di avere bisogno di lei.

---

## Decisioni di design (defaults — confermare con Lorenzo)

| Decisione | Default scelto | Motivo / da confermare |
|---|---|---|
| **Canale** | Telegram (no Slack) | 1:1 con Lorenzo, app mobile leggera, bot gratuito, niente OAuth complesso. Slack solo se in futuro entrano collaboratori. |
| **Hosting Fase 1** | Mac di Lorenzo (sempre acceso) | Zero costi, accesso diretto a `.env` e `tools/`. Limite: se chiudi il Mac o cade Internet, il bot tace. |
| **Hosting Fase 3** | VPS Hetzner CX22 (€4/mese) o Fly.io free tier | Quando l'MVP è validato e Lorenzo lo usa davvero. |
| **Livello di proattività** | **Moderato** — 1 briefing mattutino + reminder scadenze entro 2h + alert email URGENTE | Configurabile da `.env`, default sensato per non essere invadente. |
| **Lingua** | Italiano | Coerente con CLAUDE.md Segretaria |
| **Multi-utente** | No, solo Lorenzo | Bot accetta messaggi solo da `TELEGRAM_CHAT_ID_LORENZO`, ignora il resto |

---

## Architettura

```
┌──────────────────┐         ┌─────────────────────────────────────────┐
│  Lorenzo mobile  │◄───────►│  Mac/VPS — processo Python sempre on    │
│  (Telegram app)  │         │                                          │
└──────────────────┘         │  ┌──────────────────────────────────┐   │
                             │  │  tools/telegram_bot.py            │   │
                             │  │  python-telegram-bot              │   │
                             │  │  - riceve messaggi                │   │
                             │  │  - filtra by chat_id (solo LB)    │   │
                             │  │  - manda risposte                 │   │
                             │  └──────────────────────────────────┘   │
                             │                  ▲                       │
                             │                  │                       │
                             │  ┌──────────────────────────────────┐   │
                             │  │  tools/agent_runner.py            │   │
                             │  │  Claude Agent SDK (Python)        │   │
                             │  │  - carica CLAUDE.md + workflows/  │   │
                             │  │  - carica memoria persistente     │   │
                             │  │  - tool/MCP existing (Notion,     │   │
                             │  │    Gmail, GCal, Klaviyo, FiC)     │   │
                             │  │  - genera risposta                │   │
                             │  └──────────────────────────────────┘   │
                             │                  ▲                       │
                             │                  │                       │
                             │  ┌──────────────────────────────────┐   │
                             │  │  tools/scheduler.py               │   │
                             │  │  APScheduler                       │   │
                             │  │  - job mattutino                   │   │
                             │  │  - polling Notion ogni 30 min      │   │
                             │  │  - cron lunedì report Klaviyo      │   │
                             │  │  - alert email URGENTE             │   │
                             │  └──────────────────────────────────┘   │
                             │                                          │
                             └─────────────────────────────────────────┘
                                              ▲
                                              │
                             ┌────────────────┴─────────────────┐
                             │  .env, workflows/, memorie       │
                             │  (riusati 1:1 da quelli esistenti)│
                             └──────────────────────────────────┘
```

**Principio chiave**: il bot **non sostituisce** Claude Code. È solo un canale
I/O alternativo. Tutto il lavoro di CLAUDE.md + workflows + tool resta
identico. Cambia solo *come* arriva la richiesta.

---

## Piano di implementazione in 3 fasi

### Fase 1 — MVP base (no proattività)
**Goal**: bot Telegram che risponde a messaggi usando i workflow esistenti.
Lorenzo può chiedere da mobile cose tipo "report Klaviyo EV8", "che task ho
oggi?", "ricordami di...".

**Cosa creare**:
1. **Bot Telegram**: aprire chat con `@BotFather`, eseguire `/newbot`, salvare
   il token. Aprire chat col bot, mandare un messaggio, recuperare
   `chat_id` di Lorenzo via API `getUpdates`.
2. **`.env`** — aggiungere:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID_LORENZO=...
   ```
3. **`tools/telegram_bot.py`** — script principale:
   - Usa `python-telegram-bot` (`pip install python-telegram-bot`)
   - Handler `MessageHandler` filtrato per `chat_id == TELEGRAM_CHAT_ID_LORENZO`
   - Per ciascun messaggio: chiama `agent_runner.run(message_text)` → manda
     la risposta su Telegram con `reply_text` (o `send_document` per
     allegati)
   - Limite messaggio Telegram: 4096 char. Se la risposta è più lunga,
     spezzare in più messaggi o creare un file `.md` allegato.
4. **`tools/agent_runner.py`** — wrapper Claude Agent SDK:
   - Inizializza un'istanza dell'Agent SDK con:
     - System prompt = contenuto di `Claude.md`
     - Working dir = root del progetto
     - Tool/MCP abilitati: gli stessi che hai oggi (Notion, Gmail, GCal,
       Klaviyo, Gamma, ecc.)
     - Modello: `claude-opus-4-6` per task complessi, `claude-haiku-4-5` per
       quelli semplici (decide il bot a runtime in base alla lunghezza/parole
       chiave)
   - Gestione stato conversazione: per Fase 1, **stateless** — ogni messaggio
     è una nuova "sessione". Memoria persistente sopravvive comunque tramite
     il sistema memorie esistente.
5. **Avvio manuale**: `python tools/telegram_bot.py` da terminale, lo lasci
   girare in background o sotto `tmux`/`screen`. Non automatizzare ancora.

**Verifica Fase 1**:
- Mandi "ciao" da mobile → ricevi risposta in italiano nello stile della
  Segretaria.
- Mandi "che task ho aperti su Notion?" → risponde con la lista corretta.
- Mandi "report Klaviyo EV8" → segue il workflow `weekly_klaviyo_report.md`.

---

### Fase 2 — Proattività (reminder + briefing)
**Goal**: la Segretaria scrive a Lorenzo senza essere chiamata.

**Cosa aggiungere**:

1. **`tools/scheduler.py`** — gestisce i job ricorrenti con APScheduler
   (`pip install APScheduler`). Job iniziali (default moderato):

   | Cron | Job | Cosa fa |
   |---|---|---|
   | `0 8 * * 1-5` | **Briefing mattutino** | Pull task Notion del giorno + eventi GCal di oggi + email URGENTE arrivate dalla notte → manda riepilogo Telegram |
   | `0 8:30 * * 1-5` | **Replan calendario** | Lancia `replan_calendar.md`: analizza task aperti, propone time-blocking per i prossimi 5gg, invia piano Telegram (senza creare eventi, in attesa approvazione) |
   | `*/30 8-19 * * 1-5` | **Polling scadenze** | Ogni 30 min controlla `Tasks_Mailift` per task con `due_date` ≤ ora+2h e non già notificati → manda alert Telegram |
   | `*/15 8-19 * * 1-5` | **Polling email URGENTE** | Lancia inbox triage su entrambi gli account; se trova email URGENTE notifica Telegram con sender + oggetto + bozza preparata in drafts Gmail |
   | `0 9 * * 1` | **Report Klaviyo settimanale** | Lunedì alle 9: lancia `weekly_klaviyo_report.md` per ciascun cliente attivo → invia in Telegram |
   | `0 18 * * 1-5` | **Recap fine giornata** | Pull task chiusi oggi + nuovi task creati + email gestite → riepilogo |

   Tutti i job sono configurabili da `.env`:
   ```
   PROACTIVITY_LEVEL=moderate  # off | minimal | moderate | high
   BRIEFING_MORNING=08:00
   POLLING_DEADLINES_INTERVAL=30
   ```

2. **Tracking notifiche già inviate**: serve un piccolo storage locale
   (`.tmp/notifications_log.json`) per non spammare Lorenzo con lo stesso
   reminder ogni 30 min. Schema: `{task_id: last_notified_at}`.

3. **Anti-spam**: max 1 alert Telegram ogni 5 minuti (debounce). Se ne
   accumulano, batchali in un singolo messaggio.

4. **Ore silenziose**: nessun messaggio proattivo prima delle 8:00 e dopo le
   19:00. Weekend: solo emergenze (definire "emergenza" = email URGENTE da
   cliente attivo, `Cliente` ∈ {EV8, HCF, Bergamo Vini}).

5. **Handler Telegram nuovi**:
   - `/replan` → lancia `replan_calendar.md`, propone time-blocking per i prossimi 5gg (mostra il piano senza creare eventi)
   - `/replan_ok` → crea gli eventi approvati su Google Calendar
   - `/snooze 1h` → silenzia tutte le notifiche per 1h
   - `/snooze today` → silenzia fino a domani 8:00
   - `/status` → mostra job attivi e ultima esecuzione
   - `/quiet` → toggle modalità silenziosa (solo briefing mattutino)

**Flow dettagliato — Replan Calendar in Fase 2**:

1. **Ore 8:00** — Briefing mattutino: "Hai 5 task, 2 eventi, 1 email urgente"
2. **Ore 8:30** — Replan automatico:
   - Bot scarica i task aperti da Notion
   - Scarica gli eventi del calendario
   - Applica la filosofia di `replan_calendar.md` (deep work AM, reattivo PM, buffer 20%)
   - Genera il piano time-blocked
   - **Invia il piano in Telegram** (mostra tabella con slot, categoria, durata, cliente)
   - **NON crea gli eventi** — in attesa della tua approvazione

3. Tu rivedi il piano e:
   - Se va bene: mandi `/replan_ok` → il bot crea gli N eventi su Google Calendar
   - Se vuoi correggere: mandi "modifica X" o "sposta questo task a domani" → ricalcola
   - Se ignori: il piano rimane una proposta, nulla si crea

4. **Durante la giornata**:
   - Ogni 30 min: reminder per task con scadenza ≤ 2h
   - Ogni 15 min: alert per email URGENTE con bozza in drafts Gmail

5. **Ore 18:00** — Recap fine giornata: "Hai chiuso 3 task, creato 2 task nuovi"

**Verifica Fase 2**:
- Domani mattina alle 8:00 ricevi un briefing Telegram non richiesto.
- Alle 8:30 ricevi un piano calendario proposto (tabella time-block).
- Mandi `/replan_ok` → gli eventi vengono creati su Google Calendar.
- Crei un task in Notion con due_date oggi 14:00, alle 12:00 ricevi reminder
  Telegram.
- Ricevi email "urgente bug sito EV8", entro 15 min ti arriva alert Telegram
  con bozza già pronta in Gmail drafts.
- Mandi `/snooze 2h`, per 2 ore non ricevi nulla, poi i job ripartono.

---

### Fase 3 — Sempre online (deploy su VPS)
**Goal**: la Segretaria non dipende più dal Mac di Lorenzo.

**Cosa fare**:

1. **Scelta hosting** (in ordine di preferenza):
   - **Hetzner CX22** Helsinki — €4.59/mese, 2 vCPU, 4GB RAM, Ubuntu 24.04.
     Più che sufficiente.
   - **Fly.io** free tier — gratis fino a soglie generose, ma ha cold start.
   - **Railway** — €5/mese, deploy via git push, comodo.
   - **Raspberry Pi a casa** — €0/mese ma dipende da Internet di casa.

2. **Setup**:
   - Provisioning: SSH al VPS, `apt install python3.13 git`, clone del
     progetto (o `rsync` da locale, vista la sensibilità di `.env`)
   - Trasferire `.env`, `credentials_gmail.json`, `tokens/` in modo sicuro
     (`scp` con permessi 600, **MAI** committare in git)
   - `python -m venv .venv && pip install -r requirements.txt`
   - Test manuale: `python tools/telegram_bot.py` → verifica che risponda
   - **Servizio systemd**: creare `/etc/systemd/system/segretaria.service`
     che esegue `tools/telegram_bot.py` come daemon, `Restart=always`,
     `User=segretaria` (utente dedicato non-root)
   - `systemctl enable segretaria && systemctl start segretaria`

3. **Logging**:
   - Stdout/stderr → `journalctl -u segretaria -f`
   - Errori critici (eccezioni unhandled) → notifica Telegram a Lorenzo con
     traceback truncated

4. **Backup**:
   - `tokens/`, `.env`, `.tmp/notifications_log.json` → backup giornaliero
     in storage cifrato (Backblaze B2 o iCloud Drive via rsync)

5. **Aggiornamenti**:
   - Workflow di deploy: locale → `git push` (se decidi di committare) o
     `rsync` mirato → `systemctl restart segretaria` sul VPS
   - Niente CI/CD per ora, è overkill

**Verifica Fase 3**:
- Spegni il Mac per 24h, la Segretaria continua a rispondere e a mandare
  reminder.
- Riavvio del VPS: il servizio riparte automaticamente entro 30 secondi.

---

## Comandi Telegram (cheat sheet finale)

| Comando | Cosa fa |
|---|---|
| `/start` | Saluta e mostra cosa può fare |
| `/today` | Riepilogo task + eventi + email del giorno |
| `/tasks` | Lista task aperti Notion |
| `/replan` | Esegue `replan_calendar.md` e ti propone il time-blocking per i prossimi 5gg (senza creare eventi, in attesa OK) |
| `/replan ok` | Crea gli eventi su Google Calendar (solo dopo aver approvato il piano con `/replan`) |
| `/replan [cliente]` | Replanning solo per task cliente specifico |
| `/klaviyo [cliente]` | Report Klaviyo settimanale per il cliente |
| `/triage` | Lancia inbox triage manuale |
| `/snooze 1h` | Silenzia notifiche per N (1h, 2h, today) |
| `/quiet` | Modalità silenziosa toggle |
| `/status` | Job attivi, ultimo run |
| Qualsiasi testo libero | Conversazione libera con la Segretaria |
| **Vocale** | Trascritto con Whisper, elaborato come testo |

---

## Costi stimati (Fase 3, regime)

| Voce | €/mese |
|---|---|
| VPS Hetzner CX22 | 4.59 |
| Claude API (Opus + Haiku, ~50 messaggi/giorno + scheduler) | 15–40 |
| Telegram bot | 0 |
| Backup B2 | 1 |
| **Totale** | **~20–45/mese** |

Consumo Claude dipende molto da quanto chatti e dalla lunghezza dei workflow.
Per tenerlo basso: il bot decide a runtime se usare Haiku (default per 80%
dei task) o Opus (solo per workflow complessi tipo `discovery_call_processing`
o `weekly_klaviyo_report`).

---

## Vocali (Fase 1+)

### Come funziona
1. Lorenzo manda un vocale Telegram
2. Il bot scarica il file audio da Telegram
3. Passa a OpenAI Whisper (via API) per trascrizione
4. La trascrizione entra nel flusso normale (come se fosse testo)
5. La risposta torna come **testo** (no TTS per ora)

### Setup
**`.env` — aggiungere**:
```
OPENAI_API_KEY=sk-...  # per Whisper
```

**`tools/telegram_bot.py` — aggiungere handler**:
```python
from telegram import Update
from telegram.ext import MessageHandler, filters

# Handler per vocali
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Scarica il file audio
    file = await update.message.voice.get_file()
    audio_path = f".tmp/voice_{update.message.message_id}.ogg"
    await file.download_to_drive(audio_path)
    
    # Trascrivi con Whisper
    transcription = transcribe_with_whisper(audio_path)
    
    # Processa come testo normale
    response = await agent_runner.run(transcription)
    
    # Risposta
    await update.message.reply_text(response)
    
    # Cleanup
    os.remove(audio_path)

# Helper Whisper
def transcribe_with_whisper(audio_path: str) -> str:
    import openai
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="it"  # forza italiano
        )
    return transcript.text

# Registra l'handler nel main
dispatcher.add_handler(MessageHandler(filters.VOICE, handle_voice))
```

### Limitazioni (per ora)
- **Massimo 25 MB** per vocale (limite Telegram)
- **Massimo 25 MB** per file Whisper (limite OpenAI)
- Linguaggio forzato su italiano
- La risposta è sempre testo (niente TTS)
- Costo: ~€0.03 per vocale da 1 minuto (Whisper)

### Verifica
- Mandi un vocale da mobile: "che task ho oggi?"
- Bot scarica, trascrive, risponde con lista task

---

## Cosa NON fa (per ora)

- **TTS (Text-to-Speech)** — risposte vocali. Possibile (Eleven Labs / Google TTS) ma fuori scope MVP
- **WhatsApp** — hai 360dialog nello stack ma è per le campagne, non per la
  segretaria. Tenerlo separato.
- **Multi-utente / collaboratori** — solo Lorenzo
- **Memoria conversazionale long-term** — usa il sistema memorie esistente,
  niente DB conversazioni
- **Auto-risposta a clienti/lead** — la Segretaria parla **solo con Lorenzo**,
  mai con terzi senza approvazione esplicita (regola CLAUDE.md "mai inviare
  senza OK")

---

## Apprendimenti

(Vuoto. Popolare quando emergono pattern di uso, falsi positivi nei reminder,
job che spammano, ecc.)

---

## Verifica end-to-end (quando implementeremo)

**Fase 1:**
1. Setup `@BotFather`, salva token in `.env`
2. `pip install python-telegram-bot anthropic-agent-sdk`
3. Implementa `tools/telegram_bot.py` + `tools/agent_runner.py`
4. `python tools/telegram_bot.py` da terminale Mac
5. Da iPhone: apri Telegram, scrivi al bot "ciao" → ricevi risposta
6. Test workflow esistenti via chat

**Fase 2:**
1. `pip install APScheduler`
2. Implementa `tools/scheduler.py` con i 5 job iniziali
3. `tools/telegram_bot.py` avvia anche lo scheduler nello stesso processo
4. Aspetta domani 8:00 → verifica briefing
5. Crea task Notion con due_date imminente → verifica reminder

**Fase 3:**
1. Provisioning VPS Hetzner
2. `rsync` del progetto + `.env`
3. systemd service + start
4. Spegni Mac, verifica che continui a funzionare
