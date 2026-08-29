#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if [[ ! -d node_modules ]]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Frontend: http://127.0.0.1:3000/"
exec npm run dev -- --host 127.0.0.1 --port 3000
