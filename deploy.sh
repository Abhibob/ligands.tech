#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Load .env if present
[ -f .env ] && { set -a; source .env; set +a; }

echo "=== BindingOps Platform ==="

echo "[1/4] Starting PostgreSQL..."
docker compose up -d --wait

echo "[2/4] Installing dependencies..."
~/.local/bin/uv pip install -e ".[api,db]" 2>/dev/null || pip install -e ".[api,db]"

echo "[3/4] Starting API server (port 8000)..."
export BIND_DB_URL="${BIND_DB_URL:-postgresql://bind:bind@localhost:5432/bindops}"
uvicorn bind_tools.api.app:create_app --factory --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "[4/4] Starting frontend (port 5173)..."
(cd frontend_SAMPLE && npm install --silent 2>/dev/null && npm run dev) &
FE_PID=$!

echo ""
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  Swagger:  http://localhost:8000/docs"
echo ""
trap "kill $API_PID $FE_PID 2>/dev/null; docker compose stop; exit 0" INT TERM
wait
