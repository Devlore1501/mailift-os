#!/usr/bin/env bash
# Mailift OS — avvia tutta la piattaforma con un comando.
#
#   ./mailift.sh            # hub + tutte le app
#   ./mailift.sh hub        # solo l'hub (:4000)
#
# Hub:               http://localhost:4000
# Content Dashboard: http://localhost:5174 (backend :8010)
# Autofatture:       http://localhost:5173 (backend :8000)
#
# Se una singola app non parte (dipendenze mancanti), le altre continuano:
# il suo pallino sull'hub resta rosso e il log prefissato dice perché.

set -uo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "❌ .venv non trovato. Setup: python3 -m venv .venv && .venv/bin/pip install -r content-dashboard/backend/requirements.txt"
    exit 1
fi

pids=()
cleanup() {
    echo ""
    echo "🛑 fermo la piattaforma..."
    for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

run() { # run <prefisso> <dir> <comando...>
    local prefix="$1" dir="$2"; shift 2
    (cd "$dir" && "$@" 2>&1 | sed "s/^/[$prefix] /") &
    pids+=("$!")
}

mode="${1:-all}"

echo "=============================================="
echo "  Mailift OS"
echo "  Hub:               http://localhost:4000"
if [ "$mode" = "all" ]; then
echo "  Content Dashboard: http://localhost:5174"
echo "  Autofatture:       http://localhost:5173"
fi
echo "  Ctrl+C ferma tutto"
echo "=============================================="

run "hub" "$ROOT/hub" "$VENV/bin/uvicorn" app:app --port 4000

if [ "$mode" = "all" ]; then
    # Content Dashboard
    run "content-api" "$ROOT/content-dashboard/backend" "$VENV/bin/uvicorn" app.main:app --port 8010 --reload
    if [ ! -d "$ROOT/content-dashboard/frontend/node_modules" ]; then
        echo "[content-web] 📦 npm install (prima volta)..."
        (cd "$ROOT/content-dashboard/frontend" && npm install)
    fi
    run "content-web" "$ROOT/content-dashboard/frontend" npm run dev

    # Autofatture (se le sue dipendenze non sono installate, fallisce solo lei)
    run "fatture-api" "$ROOT/webapp/backend" "$VENV/bin/uvicorn" app.main:app --port 8000 --reload
    if [ -d "$ROOT/webapp/frontend/node_modules" ]; then
        run "fatture-web" "$ROOT/webapp/frontend" npm run dev
    else
        echo "[fatture-web] ⚠️  node_modules mancante: esegui 'cd webapp/frontend && npm install' per attivare l'Autofatture"
    fi
fi

sleep 3
echo ""
echo "✅ Piattaforma avviata → apri http://localhost:4000"
wait -n 2>/dev/null || wait
cleanup
