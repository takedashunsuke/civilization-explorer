#!/usr/bin/env bash
# 解析バッチ v2 — run3 系列（講評後の主実験）だけを対象にする
#
# v1 (run-analysis-batch.sh) は全系列用に残す。
#   ./scripts/run-analysis-batch.sh --series run2 --aggregate
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
V1="$ROOT/scripts/run-analysis-batch.sh"

usage() {
  cat <<'EOF'
Usage: ./scripts/run-analysis-batch-v2.sh [options]

  v1 に --series run3 を付けて委譲する。入賞 run-001〜010 と run2 は混ぜない。

  着手の 1 手のあと:
      ./scripts/run-analysis-batch-v2.sh --aggregate

  -h, --help      このヘルプ
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -x "$V1" ]]; then
  echo "Missing $V1 — run: chmod +x scripts/*.sh" >&2
  exit 1
fi

exec "$V1" --series run3 "$@"
