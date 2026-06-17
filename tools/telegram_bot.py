"""
Segretaria Telegram — Bot che riceve messaggi e vocali
e coordina con agent_runner per le risposte.

Uso:
  python tools/telegram_bot.py

Assicurati che .env abbia:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID_LORENZO
  - OPENAI_API_KEY (per vocali)
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Verifica .env
if not os.path.exists(".env"):
    logger.error("❌ File .env non trovato. Crea uno da .env.example")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# Import moduli locali
try:
    from tools.voice_handler import VoiceHandler
    from tools.scheduler import (
        start_scheduler,
        stop_scheduler,
        set_snooze,
        toggle_quiet_mode,
        get_status,
        run_job_now,
        JOBS,
    )
    from tools.agent_runner import run_query
except ImportError as e:
    logger.error(f"❌ Errore import: {e}")
    sys.exit(1)

TZ = ZoneInfo("Europe/Rome")

# Inizializza handler
voice_handler = VoiceHandler()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_LORENZO = int(os.getenv("TELEGRAM_CHAT_ID_LORENZO"))

if not BOT_TOKEN or not CHAT_ID_LORENZO:
    logger.error("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID_LORENZO mancanti")
    sys.exit(1)

TMP_DIR = Path(".tmp")
TMP_DIR.mkdir(exist_ok=True)


async def check_user(update: Update) -> bool:
    """Verifica che il messaggio arrivi da Lorenzo."""
    if update.effective_chat.id != CHAT_ID_LORENZO:
        logger.warning(f"⚠️ Messaggio da chat_id diversa: {update.effective_chat.id}")
        return False
    return True


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /start."""
    if not await check_user(update):
        return

    msg = """Ciao Lorenzo 👋

Sono la tua Segretaria Telegram — Fase 2 attiva (proattività).

• Mandami **testo libero** o **vocali** — rispondo
• Usa i **comandi** sotto

**Calendario**:
/replan — Propone piano time-block 5gg (non crea)
/replan_ok — Crea gli eventi del piano su Google Calendar

**Scheduler**:
/status — Job attivi + prossime esecuzioni
/run <job_id> — Esegui subito un job (morning_briefing, replan_calendar, poll_vip_emails, klaviyo_weekly_report, evening_recap)
/snooze 1h|2h|today — Silenzia notifiche
/quiet — Toggle modalità silenziosa (solo briefing)

Sono sempre in ascolto 🎤.
"""
    await update.message.reply_text(msg)
    logger.info(f"✓ /start da {update.effective_user.first_name}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler messaggi vocali."""
    if not await check_user(update):
        return

    logger.info("🎤 Vocale ricevuto, scarico e trascrivo...")

    # Mostra "typing..."
    await update.message.chat.send_action("typing")

    audio_path = None
    try:
        # Scarica il vocale da Telegram
        voice_file = update.message.voice
        file = await voice_file.get_file()
        audio_path = TMP_DIR / f"voice_{update.message.message_id}.ogg"

        await file.download_to_drive(str(audio_path))
        logger.info(f"✓ File audio scaricato: {audio_path}")

        # Trascrivi con Whisper
        transcription = await voice_handler.transcribe_voice(str(audio_path))
        logger.info(f"✓ Trascritto: {transcription[:100]}...")

        # Invia un feedback della trascrizione
        await update.message.reply_text(
            f"🎤 Trascritto:\n> _{transcription}_",
            parse_mode="Markdown"
        )

        logger.info(f"✓ Vocale elaborato e trascritto")

    except Exception as e:
        logger.error(f"❌ Errore vocale: {e}")
        await update.message.reply_text(
            f"❌ Errore transcription:\n`{str(e)[:200]}`",
            parse_mode="Markdown"
        )

    finally:
        # Cleanup
        if audio_path and Path(audio_path).exists():
            voice_handler.cleanup_audio(str(audio_path))


async def _send_chunked(message, text: str):
    """Invia messaggio spezzato in chunk da 4096 char (limite Telegram)."""
    if not text:
        await message.reply_text("_(risposta vuota)_", parse_mode="Markdown")
        return
    for i in range(0, len(text), 4096):
        await message.reply_text(text[i : i + 4096])


async def handle_command_replan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /replan — propone time-blocking via agent_runner."""
    if not await check_user(update):
        return

    logger.info("📅 /replan richiesto, genero piano calendario...")
    await update.message.chat.send_action("typing")
    await update.message.reply_text(
        "📅 Sto analizzando task e calendario… (~60-90s)"
    )

    try:
        prompt = (
            "Esegui il workflow workflows/replan_calendar.md per i prossimi 5 "
            "giorni lavorativi. Genera SOLO la proposta di piano time-blocked "
            "come definito nello step 7 (tabella markdown per giorno, backlog, "
            "statistiche). NON creare eventi su Google Calendar."
        )
        loop = asyncio.get_event_loop()
        plan = await loop.run_in_executor(None, run_query, prompt, 180.0)

        await _send_chunked(update.message, plan)
        await update.message.reply_text(
            "_Rispondi con /replan_ok per creare gli eventi su Google Calendar._",
            parse_mode="Markdown",
        )
        logger.info("✓ Piano replan inviato (%d char)", len(plan or ""))

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Errore replan: {e}")
        await update.message.reply_text(f"❌ Errore: {str(e)[:200]}")


async def handle_command_replan_ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /replan_ok — crea davvero gli eventi dal piano appena proposto."""
    if not await check_user(update):
        return

    logger.info("✅ /replan_ok — creo eventi su Google Calendar...")
    await update.message.chat.send_action("typing")
    await update.message.reply_text("✅ Creo gli eventi su Google Calendar…")

    try:
        # agent_runner mantiene la sessione conversazionale, quindi il piano
        # proposto da /replan e' ancora nel contesto.
        prompt = (
            "Ok procedi: crea gli eventi del piano calendario che hai appena "
            "proposto. Usa gcal_create_event per ciascun time-block. "
            "Al termine, riporta in markdown la lista degli eventi creati "
            "con giorno, orario, nome task."
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_query, prompt, 180.0)

        await _send_chunked(update.message, result)
        logger.info("✓ Eventi creati, output: %d char", len(result or ""))

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Errore creazione eventi: {e}")
        await update.message.reply_text(f"❌ Errore: {str(e)[:200]}")


async def handle_command_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /snooze 1h|2h|today — silenzia notifiche proattive."""
    if not await check_user(update):
        return

    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Uso: `/snooze 1h` | `/snooze 2h` | `/snooze today`", parse_mode="Markdown")
        return

    arg = args[1].strip().lower()
    try:
        if arg == "today":
            now = datetime.now(TZ)
            tomorrow_8 = (now + timedelta(days=1)).replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            duration = tomorrow_8 - now
        elif arg.endswith("h"):
            hours = int(arg[:-1])
            if hours <= 0 or hours > 24:
                raise ValueError("Durata tra 1h e 24h")
            duration = timedelta(hours=hours)
        else:
            await update.message.reply_text("Formato non valido. Usa `1h`, `2h` o `today`.")
            return
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    until = set_snooze(duration)
    until_local = until.astimezone(TZ)
    await update.message.reply_text(
        f"🔇 Silenziato fino alle {until_local:%H:%M} (del {until_local:%d/%m})"
    )


async def handle_command_quiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /quiet — toggle modalità silenziosa (solo briefing passa)."""
    if not await check_user(update):
        return
    enabled = toggle_quiet_mode()
    status = "ON" if enabled else "OFF"
    desc = "solo briefing mattutino passa" if enabled else "tutte le notifiche attive"
    await update.message.reply_text(f"🤫 Quiet mode: *{status}* ({desc})", parse_mode="Markdown")


async def handle_command_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /status — mostra stato scheduler + job attivi."""
    if not await check_user(update):
        return

    s = get_status()
    lines = ["📊 *Status scheduler*", ""]

    if s["snooze_until"]:
        snooze_dt = datetime.fromisoformat(s["snooze_until"]).astimezone(TZ)
        lines.append(f"🔇 Snooze fino a: {snooze_dt:%d/%m %H:%M}")
    else:
        lines.append("🔇 Snooze: OFF")
    lines.append(f"🤫 Quiet mode: {'ON' if s['quiet_mode'] else 'OFF'}")
    lines.append("")
    lines.append(f"*Job attivi ({len(s['jobs'])})*:")
    for j in s["jobs"]:
        next_run = j["next_run"]
        if next_run:
            next_dt = datetime.fromisoformat(next_run).astimezone(TZ)
            next_str = f"{next_dt:%d/%m %H:%M}"
        else:
            next_str = "—"
        lines.append(f"• {j['label']}\n  _next: {next_str}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_command_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /run <job_id> — esegue subito un job."""
    if not await check_user(update):
        return

    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        available = ", ".join(JOBS.keys())
        await update.message.reply_text(
            f"Uso: `/run <job_id>`\nJob disponibili: {available}",
            parse_mode="Markdown",
        )
        return

    job_id = args[1].strip()
    if job_id not in JOBS:
        available = ", ".join(JOBS.keys())
        await update.message.reply_text(
            f"❌ Job `{job_id}` non trovato.\nDisponibili: {available}",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(f"▶️ Eseguo `{job_id}`…", parse_mode="Markdown")
    logger.info("manual run: %s", job_id)
    ok = await run_job_now(job_id)
    if not ok:
        await update.message.reply_text(f"❌ Job `{job_id}` fallito (vedi log)")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errori."""
    logger.error(f"❌ Errore non gestito: {context.error}")


async def on_post_init(app: Application) -> None:
    """Avvia lo scheduler Fase 2 dopo che Application e' inizializzato."""
    start_scheduler(app.bot, CHAT_ID_LORENZO)
    logger.info("✓ Scheduler Fase 2 avviato (5 job)")


async def on_post_shutdown(app: Application) -> None:
    """Ferma lo scheduler in modo pulito allo shutdown."""
    stop_scheduler()
    logger.info("✓ Scheduler fermato")


def main():
    """Avvia il bot + scheduler nello stesso processo."""
    logger.info("🚀 Avvio Segretaria Telegram (Fase 2 — proattivita')")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_post_init)
        .post_shutdown(on_post_shutdown)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("replan", handle_command_replan))
    app.add_handler(CommandHandler("replan_ok", handle_command_replan_ok))
    app.add_handler(CommandHandler("snooze", handle_command_snooze))
    app.add_handler(CommandHandler("quiet", handle_command_quiet))
    app.add_handler(CommandHandler("status", handle_command_status))
    app.add_handler(CommandHandler("run", handle_command_run))

    # Message handlers (ordine importa: voice prima di text)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info(f"✓ Bot pronto. In ascolto da chat_id {CHAT_ID_LORENZO}")
    logger.info("Premi Ctrl+C per fermare")

    # Start polling (blocca). Lo scheduler parte via on_post_init.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
