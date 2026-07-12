#!/usr/bin/env bash
# AEGIS · one-command setup + launch (macOS / Linux)
set -e

cd "$(dirname "$0")"

echo ""
echo "  AEGIS · Campaign Intelligence — Ezor Media"
echo "  -------------------------------------------"

# 1. Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "  ✗ Python 3 not found. Install Python 3.9+ and re-run."
  exit 1
fi

# 2. venv
if [ ! -d ".venv" ]; then
  echo "  → Creating virtual environment…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. deps
echo "  → Installing dependencies (first run only)…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  → Created .env (DEMO mode). Add an Anthropic key for LIVE AI."
fi

# 5. launch
echo ""
echo "  ✓ Ready. Opening http://localhost:8000"
echo "    (Ctrl+C to stop)"
echo ""
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
