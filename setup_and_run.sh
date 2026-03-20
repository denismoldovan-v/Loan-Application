#!/usr/bin/env bash
# AI Loan Intake — one script: venv, pip, .env prompt, open browser, run server
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo "  AI Loan Application Intake Assistant"
echo "========================================"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 not found. Install Python 3.10+."
  exit 1
fi

if [[ ! -f requirements.txt ]] || [[ ! -f single_file_app.py ]]; then
  echo "[ERROR] Run this script from the project folder (requirements.txt + single_file_app.py)."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "No .env yet — enter your OpenAI API key (or leave empty for fallback-only mode)."
  read -r -p "OpenAI API key: " OPENAI_KEY
  {
    echo "OPENAI_API_KEY=${OPENAI_KEY}"
    echo "OPENAI_MODEL=gpt-4.1-mini"
  } > .env
  chmod 600 .env
  echo ""
fi

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment .venv ..."
  python3 -m venv .venv
fi

echo "Installing dependencies (pip)..."
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

if command -v ss &>/dev/null && ss -tln 2>/dev/null | grep -q ':8000'; then
  echo "Something already listens on port 8000. Opening browser only..."
  xdg-open "http://localhost:8000/" 2>/dev/null || open "http://localhost:8000/" 2>/dev/null || true
  exit 0
fi

echo "Opening browser in ~2s (http://localhost:8000/) ..."
( sleep 2 && ( xdg-open "http://localhost:8000/" 2>/dev/null || open "http://localhost:8000/" 2>/dev/null || true ) ) &

echo "Starting server (Ctrl+C to stop)..."
echo ""
.venv/bin/python single_file_app.py
