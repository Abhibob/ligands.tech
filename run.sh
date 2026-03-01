#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Start Postgres ──────────────────────────────────────────────────
echo "Starting Postgres..."
docker compose up -d --wait

export BIND_DB_URL="postgresql://bind:bind@localhost:5432/bindops"

# ── Install dependencies (if needed) ────────────────────────────────
if ! python -c "import psycopg2" 2>/dev/null; then
    echo "Installing dependencies..."
    ~/.local/bin/uv pip install -e ".[db]"
fi

# ── Run agent ───────────────────────────────────────────────────────
echo ""
exec bind-agent chat "$@"
