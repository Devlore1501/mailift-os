# Voice Integration Setup — Guida Rapida

## Cosa è stato aggiunto

- `tools/voice_handler.py` — modulo per trascrizione Whisper
- `tools/telegram_bot.py` — bot Telegram che riceve vocali e testo
- `.env.example` — template con nuove chiavi

## Setup (5 minuti)

### 1. OpenAI API Key
```bash
# Vai su https://platform.openai.com/api/keys
# Copia una key (o creane una nuova)
# Mettila nel .env:
OPENAI_API_KEY=sk-...
```

### 2. Telegram Bot Token
Se non l'hai ancora:
```
1. Apri Telegram
2. Cerca @BotFather
3. /newbot → scegli nome (@MiaSegretariaLorenzo_bot)
4. Copia il TOKEN
5. Mettilo in .env: TELEGRAM_BOT_TOKEN=...
```

### 3. Chat ID di Lorenzo
```bash
1. Apri una chat con il bot
2. Mandagli un messaggio
3. Esegui (da terminale):
   curl "https://api.telegram.org/botTUO_TOKEN/getUpdates"
4. Cerca "chat":{"id": XXX in risposta
5. Mettilo in .env: TELEGRAM_CHAT_ID_LORENZO=XXX
```

### 4. Requirements
```bash
pip install python-telegram-bot openai python-dotenv
```

## Test Vocali

```bash
# Avvia il bot
python tools/telegram_bot.py
```

Poi da mobile Telegram:
1. Manda `/start` → ricevi messaggio di benvenuto
2. Manda un **vocale** (tieni premuto il microfono)
3. Attendi 3-5 secondi (trascrizione Whisper)
4. Ricevi indietro il testo trascritto

## Come funziona

```
Tu mandi vocale
    ↓
Bot scarica .ogg da Telegram
    ↓
Passa a OpenAI Whisper (API)
    ↓
Whisper restituisce testo italiano
    ↓
Bot ti invia indietro il testo
```

## Costi

- Whisper: ~€0.03 per minuto di audio
- Es.: 10 vocali da 30 sec = €0.15/giorno

## Troubleshooting

**"OPENAI_API_KEY non trovata"**
→ Aggiungi `OPENAI_API_KEY=sk-...` al `.env` reale

**"TELEGRAM_BOT_TOKEN manca"**
→ Vedi step 2 sopra

**"Chat ID sbagliato"**
→ Rivedi step 3, assicurati di mandare un messaggio al bot prima

**Whisper timeout**
→ File audio > 25MB non sono supportati. Prova con vocali ≤ 1 minuto

## Prossimi step

Quando sei pronto:
1. Aggiungere risposta tramite `agent_runner.py` (non solo trascrizione)
2. Aggiungere handler per altri comandi (`/today`, `/tasks`, etc.)
3. Aggiungere scheduler per briefing mattutino (Fase 2)
