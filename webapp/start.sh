#!/usr/bin/env bash
# Avvia la webapp Autofatture in dev mode (backend + frontend).
#
# Uso:
#   ./webapp/start.sh           # avvia entrambi, Ctrl+C ferma tutto
#   ./webapp/start.sh backend   # solo backend su :8000
#   ./webapp/start.sh frontend  # solo frontend su :5173
#
# Log backend: webapp/backend/.tmp/backend.log (viene seguito a schermo)
# Log frontend: webapp/frontend/.tmp/frontend.log (viene seguito a schermo)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV="$ROOT/.venv"
BACKEND_LOG="$BACKEND_DIR/.tmp/backend.log"
FRONTEND_LOG="$FRONTEND_DIR/.tmp/frontend.log"
mkdir -p "$BACKEND_DIR/.tmp" "$FRONTEND_DIR/.tmp"

if [ ! -x "$VENV/bin/python" ]; then
    echo "❌ .venv non trovato in $VENV. Eseguire prima: python3 -m venv .venv && source .venv/bin/activate && pip install -r webapp/backend/requirements.txt"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 node_modules mancante, eseguo npm install..."
    (cd "$FRONTEND_DIR" && npm install)
fi

start_backend() {
    echo "🚀 backend su http://localhost:8000"
    cd "$BACKEND_DIR"
    "$VENV/bin/uvicorn" app.main:app --port 8000 --reload 2>&1 | tee "$BACKEND_LOG"
}

start_frontend() {
    echo "🚀 frontend su http://localhost:5173"
    cd "$FRONTEND_DIR"
    npm run dev 2>&1 | tee "$FRONTEND_LOG"
}

mode="${1:-all}"

case "$mode" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        # Trap per kill di entrambi su Ctrl+C
        pids=()
        cleanup() {
            echo ""
            echo "🛑 fermo backend e frontend..."
            for pid in "${pids[@]}"; do
                kill "$pid" 2>/dev/null || true
            done
            wait 2>/dev/null || true
            exit 0
        }
        trap cleanup INT TERM

        echo "=========================================="
        echo "  Autofatture webapp — dev mode"
        echo "  Backend:  http://localhost:8000 (+ /docs)"
        echo "  Frontend: http://localhost:5173"
        echo "  Ctrl+C per fermare entrambi"
        echo "=========================================="

        # Backend in background
        (cd "$BACKEND_DIR" && "$VENV/bin/uvicorn" app.main:app --port 8000 --reload) \
            > >(sed 's/^/[backend] /' | tee "$BACKEND_LOG") \
            2> >(sed 's/^/[backend] /' | tee -a "$BACKEND_LOG" >&2) &
        pids+=("$!")

        # Piccola attesa per far partire uvicorn prima di Vite
        sleep 2

        # Frontend in background
        (cd "$FRONTEND_DIR" && npm run dev) \
            > >(sed 's/^/[frontend] /' | tee "$FRONTEND_LOG") \
            2> >(sed 's/^/[frontend] /' | tee -a "$FRONTEND_LOG" >&2) &
        pids+=("$!")

        # Aspetta uno qualunque dei due (se uno muore, cleanup)
        wait -n
        cleanup
        ;;
    *)
        echo "Uso: $0 [all|backend|frontend]"
        exit 1
        ;;
esac
