#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — One-command launcher for the UST Reception AI Dashboard
# Target: Raspberry Pi 5 (Linux, Python 3.11+, Node 20+)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    UST Reception AI Insight Dashboard            ║"
echo "║    Starting all services…                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Backend ────────────────────────────────────────────────────────────────
echo "▶ Installing Python dependencies…"
pip install --quiet -r "$BACKEND_DIR/requirements.txt"

echo "▶ Starting FastAPI backend on 127.0.0.1:8000…"
cd "$BACKEND_DIR"
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Give FastAPI a moment to bind before the frontend starts making requests
sleep 2

# ── 2. Frontend ───────────────────────────────────────────────────────────────
echo "▶ Installing Node dependencies…"
cd "$FRONTEND_DIR"
npm install --prefer-offline --silent

echo "▶ Building Next.js production bundle…"
npm run build --silent

echo "▶ Starting Next.js on http://localhost:3000…"
npm run start -- --port 3000 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# ── 3. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "✅ All services running."
echo "   Dashboard : http://localhost:3000"
echo "   API docs  : http://127.0.0.1:8000/docs"
echo ""
echo "   Camera index : $(grep CAMERA_INDEX "$BACKEND_DIR/.env" | cut -d= -f2)"
echo "   Demo mode    : $(grep DEMO_MODE    "$BACKEND_DIR/.env" | cut -d= -f2)"
echo ""
echo "   Press Ctrl+C to stop everything."
echo ""

# ── 4. Graceful shutdown ──────────────────────────────────────────────────────
trap "echo ''; echo 'Stopping services…'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; echo 'Done.'" SIGINT SIGTERM

wait $BACKEND_PID $FRONTEND_PID
