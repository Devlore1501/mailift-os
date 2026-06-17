#!/usr/bin/env bash
# Processa tutti i file nuovi in inbox/ e li sposta in inbox/processed/ una volta fatti.
# Pensato per essere lanciato da cron settimanale.
#
# Crontab esempio (lunedì alle 9:00):
#   0 9 * * 1 /Users/lorenzobaretta/workflow\ ai/tools/process_inbox.sh >> /Users/lorenzobaretta/workflow\ ai/.tmp/cron.log 2>&1

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

INBOX="$PROJECT_DIR/inbox"
DONE="$INBOX/processed"
mkdir -p "$DONE"

# Attiva venv se esiste
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
fi

shopt -s nullglob
files=("$INBOX"/*.pdf "$INBOX"/*.csv "$INBOX"/*.xls "$INBOX"/*.xlsx)

if [ ${#files[@]} -eq 0 ]; then
    echo "[$(date)] Inbox vuota, niente da processare."
    exit 0
fi

for f in "${files[@]}"; do
    name="$(basename "$f")"
    echo "[$(date)] Processo: $name"
    if python tools/run_autofatture.py "$f"; then
        ts="$(date +%Y%m%d-%H%M%S)"
        mv "$f" "$DONE/${ts}_${name}"
        echo "[$(date)] OK -> spostato in processed/"
    else
        echo "[$(date)] ERRORE su $name (resta in inbox/ per riprovare)"
    fi
done
