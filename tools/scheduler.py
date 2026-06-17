"""APScheduler della Segretaria Mailift — proattività integrata nel bot Telegram.

Gira nello stesso processo del bot (`tools/telegram_bot.py`) come AsyncIOScheduler,
condividendo l'event loop di python-telegram-bot. I job sono deterministici:
pullano dati dai client esistenti (Notion, GCal, Gmail, Klaviyo), formattano un
messaggio, lo mandano via bot.send_message. Niente LLM nei job — affidabilita'
prima di tutto.

Job attivi (5) — cadenze low-noise:
1. Briefing mattutino       → 08:00 lun-ven (include scadenze prossime)
2. Replan calendario        → 08:30 lun-ven (via agent_runner + replan_calendar.md)
3. Check email VIP          → 09:00 / 13:00 / 17:00 lun-ven (3 check fissi)
4. Report Klaviyo           → 09:00 lunedi'
5. Recap fine giornata      → 19:00 lun-ven

Nota: job_poll_deadlines esiste ancora nel file ma NON e' piu' nel registro JOBS
(le scadenze passano nel briefing mattutino). Resta disponibile per ripristino
manuale o /run poll_deadlines → ma non viene schedulato.

Anti-spam:
- Notifications log su disco (.tmp/notifications_log.json)
- Snooze in-memory (perso al restart bot)
- Quiet mode toggle
- Ore silenziose: 8-19 weekday only (gia' nel cron)

API esposta a telegram_bot.py:
- start_scheduler(bot, chat_id) → avvia tutti i job
- stop_scheduler() → ferma graceful
- set_snooze(timedelta) → pausa proattivita'
- toggle_quiet_mode() → on/off briefing only mode
- get_status() → dict con job attivi, prossime esecuzioni, stato snooze/quiet
- run_job_now(job_id) → esegue subito un job (per /run command)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Aggiungi PROJECT_ROOT al sys.path cosi' `from tools.X import ...` funziona
# anche quando lo scheduler gira come parte del bot Telegram (cwd potrebbe
# essere altro).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

NOTIFICATIONS_LOG = PROJECT_ROOT / ".tmp" / "notifications_log.json"
NOTIFICATIONS_LOG.parent.mkdir(parents=True, exist_ok=True)

TZ = ZoneInfo("Europe/Rome")

logger = logging.getLogger("scheduler")

# ─── Stato in-memory ─────────────────────────────────────────────────────────

_scheduler: AsyncIOScheduler | None = None
_bot: Bot | None = None
_chat_id: int | None = None
_snooze_until: datetime | None = None
_quiet_mode: bool = False
_last_message_at: datetime | None = None
DEBOUNCE_SECONDS = 60  # Min 60s tra messaggi proattivi consecutivi

# Mailifeders cliente per polling email — mittenti che innescano alert
VIP_KEYWORDS = (
    "ev8style",
    "ev8 style",
    "hcf",
    "bergamo vini",
    "paolo bergamo",
)


# ─── Notifications log (JSON su disco) ───────────────────────────────────────


def _load_log() -> dict[str, str]:
    if not NOTIFICATIONS_LOG.exists():
        return {}
    try:
        return json.loads(NOTIFICATIONS_LOG.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_log(data: dict[str, str]) -> None:
    try:
        NOTIFICATIONS_LOG.write_text(json.dumps(data, indent=2))
    except OSError as exc:
        logger.warning("Cannot save notifications log: %s", exc)


def _was_notified(key: str, within_hours: int = 24) -> bool:
    """True se la chiave e' stata notificata negli ultimi N ore."""
    log = _load_log()
    ts = log.get(key)
    if not ts:
        return False
    try:
        when = datetime.fromisoformat(ts)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - when) < timedelta(hours=within_hours)


def _mark_notified(key: str) -> None:
    log = _load_log()
    log[key] = datetime.now(timezone.utc).isoformat()
    _save_log(log)


def _gc_log(max_age_days: int = 30) -> None:
    """Pulizia notifiche vecchie (chiama una volta al giorno)."""
    log = _load_log()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cleaned = {}
    for k, ts in log.items():
        try:
            when = datetime.fromisoformat(ts)
            if when >= cutoff:
                cleaned[k] = ts
        except ValueError:
            continue
    if len(cleaned) != len(log):
        _save_log(cleaned)
        logger.info("notifications log gc: %d → %d", len(log), len(cleaned))


# ─── Send con anti-spam + snooze + quiet mode ────────────────────────────────


async def _send(text: str, *, force: bool = False, briefing: bool = False) -> bool:
    """Manda un messaggio Telegram rispettando snooze/quiet/debounce.

    Args:
        text: messaggio markdown
        force: bypassa snooze e debounce (ma non quiet mode salvo briefing)
        briefing: il messaggio e' un briefing — passa anche in quiet mode

    Returns:
        True se inviato, False se filtrato.
    """
    global _last_message_at

    if _bot is None or _chat_id is None:
        logger.error("scheduler._send chiamato senza bot/chat_id")
        return False

    now = datetime.now(timezone.utc)

    # Snooze: blocca tutto tranne force
    if _snooze_until and now < _snooze_until and not force:
        logger.info("snooze attivo fino a %s, messaggio droppato", _snooze_until)
        return False

    # Quiet mode: blocca tutto tranne briefing e force
    if _quiet_mode and not briefing and not force:
        logger.info("quiet mode attivo, messaggio droppato")
        return False

    # Debounce: max 1 msg ogni DEBOUNCE_SECONDS (salvo force)
    if (
        _last_message_at
        and (now - _last_message_at) < timedelta(seconds=DEBOUNCE_SECONDS)
        and not force
    ):
        logger.info(
            "debounce attivo (ultimo msg %ds fa), droppato",
            (now - _last_message_at).total_seconds(),
        )
        return False

    try:
        await _bot.send_message(
            chat_id=_chat_id, text=text, parse_mode=ParseMode.MARKDOWN
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("send markdown fallito (%s), retry plain", exc)
        try:
            await _bot.send_message(chat_id=_chat_id, text=text)
        except Exception as exc2:  # noqa: BLE001
            logger.error("send plain fallito: %s", exc2)
            return False

    _last_message_at = now
    return True


# ─── Helpers di formattazione ────────────────────────────────────────────────


def _fmt_task_line(t: dict) -> str:
    """Una riga compatta per un task Notion."""
    name = t.get("name") or "(no title)"
    pri = t.get("priorita") or "—"
    cat = t.get("categoria") or "—"
    due = t.get("due_date") or ""
    overdue = " ⚠️" if t.get("due_overdue") else ""
    bits = [f"• *{name[:80]}*"]
    meta = f"  _{cat} · {pri}"
    if due:
        meta += f" · {due}{overdue}"
    meta += "_"
    return bits[0] + "\n" + meta


def _fmt_event_line(ev: dict) -> str:
    """Una riga compatta per un evento GCal."""
    s = ev.get("start", {})
    if "dateTime" in s:
        dt = datetime.fromisoformat(s["dateTime"]).astimezone(TZ)
        time_str = dt.strftime("%H:%M")
    elif "date" in s:
        time_str = "(all-day)"
    else:
        time_str = "?"
    title = ev.get("summary", "(no title)")[:60]
    return f"• `{time_str}` {title}"


# ─── Job 1: Briefing mattutino ───────────────────────────────────────────────


async def job_morning_briefing() -> None:
    """08:00 lun-ven. Riepilogo task del giorno + eventi GCal + email business non lette."""
    logger.info("running: morning_briefing")
    _gc_log()  # pulizia log vecchio

    sections: list[str] = []
    today_str = date.today().strftime("%A %d/%m")
    sections.append(f"☀️ *Buongiorno Lorenzo* — {today_str}\n")

    # Task Notion
    try:
        from tools.notion_tasks import list_open_tasks

        tasks = list_open_tasks(only_lorenzo=True)
        # Priorita Alta o due date oggi/domani
        today_iso = date.today().isoformat()
        tomorrow_iso = (date.today() + timedelta(days=1)).isoformat()
        priority = [
            t
            for t in tasks
            if t.get("priorita") == "Alta"
            or (t.get("due_date") and t["due_date"] <= tomorrow_iso)
            or t.get("due_overdue")
        ]
        sections.append(f"📋 *Task aperti*: {len(tasks)} totali")
        if priority:
            sections.append(f"_Priorita' o scadenza imminente ({len(priority)}):_")
            for t in priority[:5]:
                sections.append(_fmt_task_line(t))
            if len(priority) > 5:
                sections.append(f"  _...+ altri {len(priority) - 5}_")
        else:
            sections.append("_Niente di urgente._")
        sections.append("")
    except Exception as exc:  # noqa: BLE001
        logger.error("morning_briefing notion error: %s", exc)
        sections.append(f"⚠️ Notion non raggiungibile: {exc}\n")

    # Eventi GCal di oggi
    try:
        from tools.gcal_client import list_today

        events = list_today()
        sections.append(f"📅 *Eventi oggi*: {len(events)}")
        if events:
            for ev in events[:8]:
                sections.append(_fmt_event_line(ev))
            if len(events) > 8:
                sections.append(f"  _...+ altri {len(events) - 8}_")
        else:
            sections.append("_Calendario libero._")
        sections.append("")
    except Exception as exc:  # noqa: BLE001
        logger.error("morning_briefing gcal error: %s", exc)
        sections.append(f"⚠️ Calendario non raggiungibile: {exc}\n")

    sections.append("_Buona giornata 🚀_")
    await _send("\n".join(sections), briefing=True, force=True)


# ─── Job 2: Polling scadenze ─────────────────────────────────────────────────


async def job_poll_deadlines() -> None:
    """Ogni 30 min lun-ven 8-19. Alert per task con scadenza entro 24h non gia' notificati."""
    logger.info("running: poll_deadlines")
    try:
        from tools.notion_tasks import list_open_tasks

        tasks = list_open_tasks(only_lorenzo=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("poll_deadlines notion error: %s", exc)
        return

    today_iso = date.today().isoformat()
    tomorrow_iso = (date.today() + timedelta(days=1)).isoformat()

    new_alerts: list[dict] = []
    for t in tasks:
        due = t.get("due_date")
        if not due:
            continue
        # Trigger: scaduto OR scade oggi OR scade domani
        is_urgent = due <= tomorrow_iso
        if not is_urgent:
            continue
        key = f"deadline_{t['id']}_{today_iso}"
        if _was_notified(key, within_hours=24):
            continue
        new_alerts.append(t)
        _mark_notified(key)

    if not new_alerts:
        return

    if len(new_alerts) == 1:
        t = new_alerts[0]
        due_label = "oggi" if t["due_date"] == today_iso else (
            "domani" if t["due_date"] == tomorrow_iso else f"era {t['due_date']}"
        )
        text = f"⏰ *Scadenza {due_label}*\n{_fmt_task_line(t)}"
    else:
        lines = [f"⏰ *{len(new_alerts)} task con scadenza imminente*\n"]
        for t in new_alerts[:5]:
            lines.append(_fmt_task_line(t))
        if len(new_alerts) > 5:
            lines.append(f"_...+ altri {len(new_alerts) - 5}_")
        text = "\n".join(lines)

    await _send(text)


# ─── Job 3: Polling email mittenti VIP ───────────────────────────────────────


async def job_poll_vip_emails() -> None:
    """Ogni 15 min lun-ven 8-19. Alert per email business da mittenti cliente non gia' notificati."""
    logger.info("running: poll_vip_emails")
    try:
        from tools.gmail_client import list_recent, load_service

        service = load_service("business")
        # ultimi 30 min
        msgs = list_recent(service, hours=1)
    except Exception as exc:  # noqa: BLE001
        logger.error("poll_vip_emails gmail error: %s", exc)
        return

    if not msgs:
        return

    # Filtra: solo da mittenti che matchano una keyword cliente VIP
    new_alerts: list[dict] = []
    for msg in msgs:
        msg_id = msg.get("id", "")
        if not msg_id:
            continue
        # Recupera dettagli per leggere il sender (lazy)
        try:
            from tools.gmail_client import get_message

            details = get_message(service, msg_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("poll_vip_emails get_message %s failed: %s", msg_id, exc)
            continue

        sender = (details.get("from") or "").lower()
        subject = (details.get("subject") or "").lower()
        haystack = sender + " " + subject

        if not any(kw in haystack for kw in VIP_KEYWORDS):
            continue

        key = f"email_{msg_id}"
        if _was_notified(key, within_hours=72):
            continue
        new_alerts.append(details)
        _mark_notified(key)

    if not new_alerts:
        return

    if len(new_alerts) == 1:
        m = new_alerts[0]
        sender = m.get("from", "?")
        subject = m.get("subject", "(no subject)")
        text = (
            f"📧 *Nuova email cliente*\n"
            f"*Da:* {sender}\n"
            f"*Oggetto:* {subject}"
        )
    else:
        lines = [f"📧 *{len(new_alerts)} email cliente nuove*\n"]
        for m in new_alerts[:5]:
            lines.append(
                f"• *{m.get('subject', '(no subj)')[:60]}*\n  _da {m.get('from', '?')[:60]}_"
            )
        text = "\n".join(lines)

    await _send(text)


# ─── Job 4: Report Klaviyo lunedi ────────────────────────────────────────────


async def job_klaviyo_weekly_report() -> None:
    """Lunedi 09:00. Pull campagne+flussi ultimi 7gg per ogni cliente con API key."""
    logger.info("running: klaviyo_weekly_report")
    try:
        from tools.klaviyo_client import KlaviyoError, list_campaigns, list_clients, list_flows
    except ImportError as exc:
        logger.error("klaviyo client import failed: %s", exc)
        return

    sections = ["📊 *Report Klaviyo settimanale*\n"]
    any_data = False

    for c in list_clients():
        slug = c["slug"]
        if not c["configured"]:
            continue
        try:
            camps = list_campaigns(slug, days_back=7)
            flows = list_flows(slug, active_only=True)
            sections.append(
                f"*{slug.upper()}*: {len(camps)} campagne, {len(flows)} flussi attivi"
            )
            for camp in camps[:3]:
                attrs = camp.get("attributes", {})
                name = attrs.get("name", "(no name)")[:50]
                sent = (attrs.get("send_time") or "")[:10]
                sections.append(f"  • {sent} — {name}")
            sections.append("")
            any_data = True
        except KlaviyoError as exc:
            sections.append(f"*{slug.upper()}*: ⚠️ {exc}\n")
        except Exception as exc:  # noqa: BLE001
            logger.error("klaviyo job %s error: %s", slug, exc)
            sections.append(f"*{slug.upper()}*: ⚠️ errore: {exc}\n")

    if not any_data:
        sections.append("_Nessuna API key Klaviyo configurata. Aggiungi `KLAVIYO_API_KEY_*` in `.env`._")

    sections.append("_Per analisi piu' approfondita: chiedimi 'report Klaviyo per [cliente]'_")
    await _send("\n".join(sections), force=True)


# ─── Job 5: Recap fine giornata ──────────────────────────────────────────────


async def job_evening_recap() -> None:
    """18:00 lun-ven. Eventi domani + task aperti rimanenti."""
    logger.info("running: evening_recap")

    sections = ["🌙 *Recap di fine giornata*\n"]

    # Task ancora aperti
    try:
        from tools.notion_tasks import list_open_tasks

        tasks = list_open_tasks(only_lorenzo=True)
        sections.append(f"📋 *Task ancora aperti*: {len(tasks)}")
        # Top 3 per priorita
        for t in tasks[:3]:
            sections.append(_fmt_task_line(t))
        sections.append("")
    except Exception as exc:  # noqa: BLE001
        logger.error("evening_recap notion error: %s", exc)
        sections.append(f"⚠️ Notion non raggiungibile: {exc}\n")

    # Eventi domani
    try:
        from tools.gcal_client import list_events

        tomorrow = date.today() + timedelta(days=1)
        start = datetime.combine(tomorrow, time.min, tzinfo=TZ)
        end = datetime.combine(tomorrow, time.max, tzinfo=TZ)
        events = list_events(start, end)
        sections.append(f"📅 *Domani in agenda*: {len(events)} eventi")
        for ev in events[:5]:
            sections.append(_fmt_event_line(ev))
        sections.append("")
    except Exception as exc:  # noqa: BLE001
        logger.error("evening_recap gcal error: %s", exc)
        sections.append(f"⚠️ Calendario non raggiungibile: {exc}\n")

    sections.append("_Buona serata 🌅_")
    await _send("\n".join(sections), force=True)


# ─── Job 6: Autofatture mensili (giorno 10, ore 09:00) ──────────────────────


async def job_monthly_autofatture() -> None:
    """Giorno 10 del mese, ore 09:00. Pipeline Revolut → classificazione → FiC → notifica."""
    import asyncio

    logger.info("running: monthly_autofatture")
    try:
        from tools.monthly_autofatture import run as run_autofatture

        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(None, run_autofatture)

        month = summary.get("month", "?")
        created = summary.get("created", 0)
        errors = summary.get("errors", [])
        already = summary.get("already_done", False)

        if already:
            text = (
                f"📄 *Autofatture {month}* — già elaborate\n"
                f"_{created} autofatture presenti. Usa /run monthly\\_autofatture --force per rieseguire._"
            )
        else:
            lines = [f"📄 *Autofatture {month}* — pipeline completata"]
            lines.append(f"✅ Create su FiC: *{created}*")
            if errors:
                lines.append(f"❌ Errori: {len(errors)}")
                for e in errors[:3]:
                    lines.append(f"  • {e[:80]}")
                if len(errors) > 3:
                    lines.append(f"  _...+ altri {len(errors) - 3}_")
            lines.append(
                "\n_Vai su Fatture in Cloud → Autofatture e clicca "
                "\"Verifica formale\" + \"Firma e invia\" per ciascuna._"
            )
            text = "\n".join(lines)

        await _send(text, force=True)
    except Exception as exc:
        logger.error("job_monthly_autofatture failed: %s", exc)
        await _send(f"❌ *Autofatture mensili* — errore: {exc}", force=True)


# ─── Job 7: Replan calendario ────────────────────────────────────────────────


async def job_replan_calendar() -> None:
    """08:30 lun-ven. Propone time-blocking per i prossimi 5gg via agent_runner.

    Non crea eventi su Google Calendar — mostra solo il piano, in attesa di
    /replan_ok da parte di Lorenzo (che riusa la sessione conversazionale).
    """
    import asyncio

    logger.info("running: replan_calendar")
    try:
        from tools.agent_runner import run_query

        prompt = (
            "Esegui il workflow workflows/replan_calendar.md per i prossimi 5 "
            "giorni lavorativi. Genera SOLO la proposta di piano time-blocked "
            "come definito nello step 7 del workflow (tabella markdown per "
            "ogni giorno + backlog + statistiche). NON creare eventi su Google "
            "Calendar — aspetta che Lorenzo risponda con /replan_ok."
        )

        loop = asyncio.get_event_loop()
        plan_text = await loop.run_in_executor(None, run_query, prompt, 180.0)

        if not plan_text or not plan_text.strip():
            logger.warning("replan_calendar: agent_runner returned empty")
            return

        message = (
            "📅 *Piano calendario proposto*\n\n"
            f"{plan_text}\n\n"
            "_Rispondi con /replan\\_ok per crearli su Google Calendar._"
        )
        await _send(message, briefing=True, force=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("job_replan_calendar failed: %s", exc)


# ─── Job registry per /run e /status ────────────────────────────────────────

JOBS: dict[str, dict[str, Any]] = {
    "morning_briefing": {
        "func": job_morning_briefing,
        "trigger": CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=TZ),
        "label": "Briefing mattutino (08:00 lun-ven)",
    },
    "replan_calendar": {
        "func": job_replan_calendar,
        "trigger": CronTrigger(day_of_week="mon-fri", hour=8, minute=30, timezone=TZ),
        "label": "Replan calendario (08:30 lun-ven)",
    },
    "poll_vip_emails": {
        "func": job_poll_vip_emails,
        "trigger": CronTrigger(
            day_of_week="mon-fri", hour="9,13,17", minute=0, timezone=TZ
        ),
        "label": "Check email VIP (09:00, 13:00, 17:00 lun-ven)",
    },
    "klaviyo_weekly_report": {
        "func": job_klaviyo_weekly_report,
        "trigger": CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=TZ),
        "label": "Report Klaviyo (09:00 lunedi)",
    },
    "evening_recap": {
        "func": job_evening_recap,
        "trigger": CronTrigger(day_of_week="mon-fri", hour=19, minute=0, timezone=TZ),
        "label": "Recap fine giornata (19:00 lun-ven)",
    },
    "monthly_autofatture": {
        "func": job_monthly_autofatture,
        "trigger": CronTrigger(day=10, hour=9, minute=0, timezone=TZ),
        "label": "Autofatture mensili (09:00 il 10 di ogni mese)",
    },
}


# ─── Lifecycle + API per telegram_bot ────────────────────────────────────────


def start_scheduler(bot: Bot, chat_id: int) -> AsyncIOScheduler:
    """Avvia lo scheduler. Chiamato da telegram_bot.main() dopo Application.initialize."""
    global _scheduler, _bot, _chat_id

    _bot = bot
    _chat_id = chat_id

    _scheduler = AsyncIOScheduler(timezone=TZ)
    for job_id, cfg in JOBS.items():
        _scheduler.add_job(
            cfg["func"],
            trigger=cfg["trigger"],
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    _scheduler.start()
    logger.info("scheduler avviato con %d job", len(JOBS))
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler fermato")


# ─── API per i comandi Telegram ──────────────────────────────────────────────


def set_snooze(duration: timedelta) -> datetime:
    global _snooze_until
    _snooze_until = datetime.now(timezone.utc) + duration
    return _snooze_until


def clear_snooze() -> None:
    global _snooze_until
    _snooze_until = None


def toggle_quiet_mode() -> bool:
    global _quiet_mode
    _quiet_mode = not _quiet_mode
    return _quiet_mode


def get_status() -> dict:
    """Stato per /status command."""
    out = {
        "snooze_until": _snooze_until.isoformat() if _snooze_until else None,
        "quiet_mode": _quiet_mode,
        "jobs": [],
    }
    if _scheduler:
        for job in _scheduler.get_jobs():
            cfg = JOBS.get(job.id, {})
            out["jobs"].append(
                {
                    "id": job.id,
                    "label": cfg.get("label", job.id),
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )
    return out


async def run_job_now(job_id: str) -> bool:
    """Esegue subito un job. True se trovato, False altrimenti."""
    cfg = JOBS.get(job_id)
    if not cfg:
        return False
    try:
        await cfg["func"]()
    except Exception as exc:  # noqa: BLE001
        logger.error("run_job_now %s failed: %s", job_id, exc)
        if _bot and _chat_id:
            await _bot.send_message(
                chat_id=_chat_id,
                text=f"⚠️ Job `{job_id}` fallito: {exc}",
            )
    return True
