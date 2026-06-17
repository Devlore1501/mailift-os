"""Agent runner per la Segretaria Mailift Telegram bot.

Versione: invoca direttamente il binario `claude` di Claude Code via subprocess.
Vantaggi:
- Usa l'auth della subscription Claude Code di Lorenzo (zero crediti API)
- Carica automaticamente il CLAUDE.md della cwd
- Niente Claude Agent SDK (che falliva silenziosamente nel context del bot)
- Niente Anthropic API base (che richiede credito sulla console)

Per ciascun messaggio:
1. Sceglie il modello (haiku default, opus su trigger keyword o /opus)
2. Spawn `claude --print --model <X> --append-system-prompt <telegram suffix>`
3. Manda il messaggio via stdin
4. Ritorna stdout
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = PROJECT_ROOT / "Claude.md"

# Path al binario claude. Preferisce CLAUDE_CODE_EXECPATH se settato (ereditato
# quando il processo e' avviato da Claude Code), fallback al path noto VSCode
# ext.
DEFAULT_CLAUDE_BIN = (
    "/Users/lorenzobaretta/.antigravity/extensions/"
    "anthropic.claude-code-2.1.92-darwin-arm64/resources/native-binary/claude"
)
CLAUDE_BIN = os.environ.get("CLAUDE_CODE_EXECPATH") or DEFAULT_CLAUDE_BIN

# Modelli (alias accettati da Claude Code CLI)
OPUS_MODEL = "claude-opus-4-6"
HAIKU_MODEL = "claude-haiku-4-5"

OPUS_TRIGGERS = (
    "klaviyo",
    "discovery call",
    "briefing",
    "report settimanale",
    "report klaviyo",
    "pianifica",
    "replan",
    "time-block",
    "time block",
    "autofattura",
    "triage email",
    "analizza",
    "proponi",
    "weekly",
)

TELEGRAM_SUFFIX = """

---

# Contesto canale: Telegram mobile

Stai rispondendo via Telegram a Lorenzo da mobile. Adatta lo stile:

- **Concisione**: max ~1500 caratteri salvo richiesta esplicita
- **Niente preamboli**: vai dritto al punto
- **Tabelle markdown**: ok ma piccole (max 3 colonne, 5 righe). Per dataset
  piu' grandi, sintetizza e offri "vuoi i dettagli?"
- **Niente blocchi di codice lunghi**: solo se Lorenzo li chiede
- **Emoji**: zero, salvo singoli marker tipo ✅/❌/⚠️ quando aiutano la scansione
- **Italiano** sempre
"""


def choose_model(user_message: str) -> str:
    msg_lower = user_message.strip().lower()
    if msg_lower.startswith("/opus"):
        return OPUS_MODEL
    if msg_lower.startswith("/haiku"):
        return HAIKU_MODEL
    if any(trigger in msg_lower for trigger in OPUS_TRIGGERS):
        return OPUS_MODEL
    return HAIKU_MODEL


def strip_model_prefix(user_message: str) -> str:
    stripped = user_message.lstrip()
    for prefix in ("/opus", "/haiku"):
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix):].lstrip()
    return user_message


# Stato della conversazione (in-memory, single-user).
# Il primo messaggio crea una sessione con --session-id <uuid>.
# I successivi usano --resume <uuid> per continuare lo stesso thread.
# La sessione si perde al riavvio del bot (volutamente, Fase 1).
_session_lock = threading.Lock()
_session_id: str | None = None


def _get_or_create_session() -> tuple[str, bool]:
    """Ritorna (session_id, is_first_call). Thread-safe."""
    global _session_id
    with _session_lock:
        if _session_id is None:
            _session_id = str(uuid.uuid4())
            return _session_id, True
        return _session_id, False


def reset_session() -> str | None:
    """Cancella la sessione corrente. Ritorna l'ID precedente (per logging)."""
    global _session_id
    with _session_lock:
        previous = _session_id
        _session_id = None
        return previous


def run_query(user_message: str, timeout_s: float = 180.0) -> str:
    """Chiama il binario claude in modalita' --print e ritorna la risposta.

    Mantiene memoria conversazionale via --session-id / --resume.
    Sincrono. Per usarlo da un event loop asyncio (tipo telegram_bot),
    wrappare con `await asyncio.to_thread(run_query, msg)`.
    """
    model = choose_model(user_message)
    prompt = strip_model_prefix(user_message)

    session_id, is_first = _get_or_create_session()
    session_args = (
        ["--session-id", session_id] if is_first else ["--resume", session_id]
    )

    cmd = [
        CLAUDE_BIN,
        "--print",
        "--model",
        model,
        "--append-system-prompt",
        TELEGRAM_SUFFIX,
        "--permission-mode",
        "bypassPermissions",
        *session_args,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"⚠️ Timeout dopo {timeout_s:.0f}s."
    except FileNotFoundError:
        return f"⚠️ Binario claude non trovato a: {CLAUDE_BIN}"

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(
            f"[agent_runner] claude exit {result.returncode}, stderr:\n{stderr}",
            file=sys.stderr,
        )
        return f"⚠️ Errore claude (exit {result.returncode}): {stderr[:300] or 'no stderr'}"

    output = (result.stdout or "").strip()
    return output or "(nessuna risposta)"


# CLI usage
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        user_msg = sys.stdin.read().strip()
        if not user_msg:
            print("(messaggio vuoto)", file=sys.stderr)
            sys.exit(2)
        print(run_query(user_msg))
    else:
        user_msg = (
            " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "ciao, presentati in 2 righe"
        )
        print(f"[smoke test] modello scelto: {choose_model(user_msg)}")
        print(f"[smoke test] binario: {CLAUDE_BIN}")
        print(f"[smoke test] prompt: {user_msg!r}")
        print("[smoke test] ---")
        print(run_query(user_msg))
