#!/usr/bin/env bash
# 提出用・実証実験の一括実行
# 暦年ラベル AD 1750→1950（表示用）・200 年 × seed 10 本 → result/raw/run-NNN/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$ROOT/scripts/run-experiment.sh"

# 実証プロトコル（提出ドキュメントと同期）
START_YEAR=1750
YEARS=200
SEED_START=42
REPS=10

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

END_YEAR=$((START_YEAR + YEARS))
TURNS=$((YEARS / 10))

echo "=== Civilization Explorer — 実証実験バッチ ==="
echo "  期間: AD ${START_YEAR} → AD ${END_YEAR}（${YEARS} 年 / ${TURNS} ターン・暦年は表示用ラベル）"
echo "  繰り返し: ${REPS} 回（seed ${SEED_START} … $((SEED_START + REPS - 1))）"
echo "  各 run: 4 環境 × 2 ファイル（.json + .txt）"
echo "  目安時間: 約 $((REPS * 26)) 分（Ollama llama3.2:1b・1 run ≈ 26 分）"
echo ""

if [[ ! -x "$RUNNER" ]]; then
  echo "Missing $RUNNER — run: chmod +x scripts/*.sh" >&2
  exit 1
fi

batch_start=$(date +%s)

for i in $(seq 0 $((REPS - 1))); do
  seed=$((SEED_START + i))
  n=$((i + 1))
  echo "--- [$n/${REPS}] seed=${seed} AD ${START_YEAR}→${END_YEAR} ---"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$RUNNER --seed $seed --start-year $START_YEAR --years $YEARS"
    continue
  fi
  run_start=$(date +%s)
  "$RUNNER" --seed "$seed" --start-year "$START_YEAR" --years "$YEARS"
  run_elapsed=$(( $(date +%s) - run_start ))
  echo "    done in ${run_elapsed}s"
  echo ""
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "(dry-run: コマンドのみ表示)"
  exit 0
fi

total_elapsed=$(( $(date +%s) - batch_start ))
echo "=== 完了 ==="
echo "  合計: $((total_elapsed / 60)) 分 $((total_elapsed % 60)) 秒"
echo "  生ログ: $ROOT/result/raw/（manifest: result/manifest.json）"
echo "  次: analysis/prompt.md で各 run を比較 → analysis/output/run-NNN/"
