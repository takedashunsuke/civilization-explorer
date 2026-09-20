#!/usr/bin/env bash
# 実験バッチ v2 — 講評後の主実験（同一ショック列 × 社会構造）
#
# v1 (run-experiment-batch.sh) は提出用 environment / --series run2 のまま残す。
# このスクリプトは v1 に委譲し、既定だけを差し替える。
#
# 既定: protocol=resilience · series=run3 · reps=1 · 200 年 · seed 42
# 着手の 1 手（ルール層のみ・LLM なし）:
#   ./scripts/run-experiment-batch-v2.sh --stub
# Phase D 以降（モデルを上げて同じ列）:
#   LLM_PROVIDER=ollama ./scripts/run-experiment-batch-v2.sh
#
# 正: docs/hackathon/post-award.md §4.1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
V1="$ROOT/scripts/run-experiment-batch.sh"

usage() {
  cat <<'EOF'
Usage: ./scripts/run-experiment-batch-v2.sh [options]

  講評後の主実験バッチ（v2）。v1 は残してある。

  既定（v1 との差）:
      --protocol resilience
      --series run3          → result/raw/run3-001/
      --reps 1               → seed 42 のみ（10 seed にしない）

  着手の 1 手:
      ./scripts/run-experiment-batch-v2.sh --stub

  解析:
      ./scripts/run-analysis-batch-v2.sh

  v1 と同じフラグを後ろに渡せる（--years / --from-seed / --dry-run 等）。
  --protocol や --series を上書きすると v2 の意味が崩れるので使わない。

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

exec "$V1" --protocol resilience --series run3 --reps 1 "$@"
