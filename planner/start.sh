#!/usr/bin/env bash
# Avvia Mailift Planner in dev mode (backend :8001 + frontend :5174).
#
# Uso:
#   ./planner/start.sh           # avvia entrambi, Ctrl+C ferma tutto
#   ./planner/start.sh backend   # solo backend su :8001
#   ./planner/start.sh frontend  # solo frontend su :5174

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "❌ .venv non trovato in $VENV."
    echo "   Eseguire: python3 -m venv .venv && .venv/bin/pip install -r planner/backend/requirements.txt"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 node_modules mancante, eseguo npm install..."
    (cd "$FRONTEND_DIR" && npm install)
fi

start_backend() {
    echo "🚀 backend su http://localhost:8001 (+ /docs)"
    cd "$BACKEND_DIR"
    exec "$VENV/bin/uvicorn" app.main:app --port 8001 --reload
}

start_frontend() {
    echo "🚀 frontend su http://localhost:5174"
    cd "$FRONTEND_DIR"
    exec npm run dev
}

mode="${1:-all}"
case "$mode" in
    backend) start_backend ;;
    frontend) start_frontend ;;
    all)
        pids=()
        cleanup() {
            echo ""
            echo "🛑 fermo backend e frontend..."
            for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
            wait 2>/dev/null || true
            exit 0
        }
        trap cleanup INT TERM
        echo "=========================================="
        echo "  Mailift Planner — dev mode"
        echo "  Backend:  http://localhost:8001 (+ /docs)"
        echo "  Frontend: http://localhost:5174"
        echo "=========================================="
        (cd "$BACKEND_DIR" && "$VENV/bin/uvicorn" app.main:app --port 8001 --reload) \
            > >(sed 's/^/[backend] /') 2> >(sed 's/^/[backend] /' >&2) &
        pids+=("$!")
        sleep 2
        (cd "$FRONTEND_DIR" && npm run dev) \
            > >(sed 's/^/[frontend] /') 2> >(sed 's/^/[frontend] /' >&2) &
        pids+=("$!")
        wait -n
        cleanup
        ;;
    *)
        echo "Uso: $0 [all|backend|frontend]"
        exit 1
        ;;
esac
