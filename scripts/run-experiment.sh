#!/usr/bin/env bash
# 対照実験をブラウザなしで実行し result/raw/ に .txt を出力
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$ROOT/backend/.venv" ]]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/backend/.venv/bin/activate"
exec python "$ROOT/scripts/run-experiment.py" "$@"
