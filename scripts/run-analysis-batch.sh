#!/usr/bin/env bash
# 完了済み result/raw/{series}-NNN/ から analysis/output/{series}-NNN/ を一括生成
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$ROOT/backend/.venv" ]]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/backend/.venv/bin/activate"
exec python "$ROOT/scripts/run-analysis-batch.py" "$@"
