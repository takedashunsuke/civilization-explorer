#!/usr/bin/env bash
# 初回セットアップ（macOS / Linux）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Backend (Python venv)"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "    created backend/.env from .env.example"
fi

echo "==> Frontend (npm)"
cd "$ROOT/frontend"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "    created frontend/.env from .env.example"
fi
npm install

echo ""
echo "Done. Start with:"
echo "  ./scripts/start-backend.sh   # terminal 1"
echo "  ./scripts/start-frontend.sh  # terminal 2"
echo "Then open http://127.0.0.1:3000/ and follow DEMO.md"
