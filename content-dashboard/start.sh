#!/usr/bin/env bash
# Avvia la Content Dashboard in dev mode (backend :8010 + frontend :5174).
#
# Uso:
#   ./content-dashboard/start.sh           # entrambi, Ctrl+C ferma tutto
#   ./content-dashboard/start.sh backend   # solo backend
#   ./content-dashboard/start.sh frontend  # solo frontend

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV="$ROOT/.venv"
mkdir -p "$BACKEND_DIR/.tmp" "$FRONTEND_DIR/.tmp"

if [ ! -x "$VENV/bin/python" ]; then
    echo "❌ .venv non trovato. Setup: python3 -m venv .venv && .venv/bin/pip install -r content-dashboard/backend/requirements.txt"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 node_modules mancante, eseguo npm install..."
    (cd "$FRONTEND_DIR" && npm install)
fi

start_backend() {
    echo "🚀 backend su http://localhost:8010 (docs: /docs)"
    cd "$BACKEND_DIR"
    exec "$VENV/bin/uvicorn" app.main:app --port 8010 --reload
}

start_frontend() {
    echo "🚀 frontend su http://localhost:5174"
    cd "$FRONTEND_DIR"
    exec npm run dev
}

mode="${1:-all}"
case "$mode" in
    backend)  start_backend ;;
    frontend) start_frontend ;;
    all)
        pids=()
        cleanup() {
            echo ""; echo "🛑 fermo backend e frontend..."
            for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
            wait 2>/dev/null || true
            exit 0
        }
        trap cleanup INT TERM
        echo "=============================================="
        echo "  Mailift Content Dashboard — dev mode"
        echo "  Backend:  http://localhost:8010 (+ /docs)"
        echo "  Frontend: http://localhost:5174"
        echo "  Login default: lorenzo@mailift.it / mailift-admin"
        echo "=============================================="
        (cd "$BACKEND_DIR" && "$VENV/bin/uvicorn" app.main:app --port 8010 --reload 2>&1 | sed 's/^/[backend] /') &
        pids+=("$!")
        sleep 2
        (cd "$FRONTEND_DIR" && npm run dev 2>&1 | sed 's/^/[frontend] /') &
        pids+=("$!")
        wait -n
        cleanup
        ;;
    *)
        echo "Uso: $0 [all|backend|frontend]"; exit 1 ;;
esac
