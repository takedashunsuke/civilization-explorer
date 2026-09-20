#!/usr/bin/env bash
# 実証実験の一括実行
# 暦年ラベル AD 1750→1950（表示用）・既定 200 年 × seed 10 本 → result/raw/{series}-NNN/
#
# 第2回提出（environment）:
#   ./scripts/run-experiment-batch.sh
# 入賞 run-001〜010 を残した改善版:
#   ./scripts/run-experiment-batch.sh --series run2
# 講評対応（resilience・stub 試験）:
#   ./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$ROOT/scripts/run-experiment.sh"

PROTOCOL="environment"
START_YEAR=1750
YEARS=200
SEED_START=42
REPS=10
REPS_SET=0
DRY_RUN=0
STUB=0
SERIES="run"

usage() {
  cat <<'EOF'
Usage: ./scripts/run-experiment-batch.sh [options]

  --protocol environment|resilience
      environment: lush/lean/volatile/balanced（第2回提出・既定）
      resilience: civic/autocrat/commune/fracture（講評対応の主プロトコル）
  --series NAME   出力フォルダの接頭辞（既定: run → run-001）。
                  入賞分を残す改善版は run2 → run2-001
  --stub          LLM_PROVIDER=stub で実行（ヒューリスティックのみ）
  --reps N        seed 本数（既定: 10。--from-seed 未指定時）
  --years N       シミュレーション年数（既定: 200。10 の倍数）
  --from-seed N   再開用の開始 seed（既定: 42）
  --dry-run       実行コマンドのみ表示
  -h, --help      このヘルプ
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --protocol)
      PROTOCOL="${2:-}"
      if [[ "$PROTOCOL" != "environment" && "$PROTOCOL" != "resilience" ]]; then
        echo "Unknown protocol: ${PROTOCOL:-} (environment|resilience)" >&2
        exit 1
      fi
      shift 2
      ;;
    --stub) STUB=1; shift ;;
    --reps)
      REPS="${2:-}"
      REPS_SET=1
      shift 2
      ;;
    --years)
      YEARS="${2:-}"
      shift 2
      ;;
    --from-seed)
      SEED_START="${2:-}"
      shift 2
      ;;
    --series)
      SERIES="${2:-}"
      if [[ -z "$SERIES" || ! "$SERIES" =~ ^[A-Za-z][A-Za-z0-9]*$ ]]; then
        echo "--series must be alphanumeric starting with a letter (e.g. run2)" >&2
        exit 1
      fi
      shift 2
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if ! [[ "$YEARS" =~ ^[0-9]+$ ]] || (( YEARS <= 0 || YEARS % 10 != 0 )); then
  echo "--years must be a positive multiple of 10" >&2
  exit 1
fi
if ! [[ "$REPS" =~ ^[0-9]+$ ]] || (( REPS <= 0 )); then
  echo "--reps must be a positive integer" >&2
  exit 1
fi
if ! [[ "$SEED_START" =~ ^[0-9]+$ ]]; then
  echo "--from-seed must be an integer" >&2
  exit 1
fi

# Remaining reps when resuming the original 10-seed batch (42…51)
if [[ "$REPS_SET" -eq 0 && "$SEED_START" -gt 42 ]]; then
  REPS=$((51 - SEED_START + 1))
  if (( REPS <= 0 )); then
    echo "--from-seed $SEED_START is past the default batch (42…51); pass --reps" >&2
    exit 1
  fi
fi

END_YEAR=$((START_YEAR + YEARS))
TURNS=$((YEARS / 10))
SEED_END=$((SEED_START + REPS - 1))

if [[ "$PROTOCOL" == "resilience" ]]; then
  VARIANT_NOTE="4 社会構造（civic / autocrat / commune / fracture）"
else
  VARIANT_NOTE="4 環境（lush / lean / volatile / balanced）"
fi
if [[ "$STUB" -eq 1 ]]; then
  LLM_NOTE="stub（ヒューリスティック）"
  MINUTES_PER_RUN=4
else
  LLM_NOTE="backend/.env の LLM_PROVIDER"
  MINUTES_PER_RUN=26
fi

echo "=== Civilization Explorer — 実証実験バッチ ==="
echo "  プロトコル: ${PROTOCOL}"
echo "  系列: ${SERIES}（result/raw/${SERIES}-NNN/。既存 run-001〜 は上書きしない）"
echo "  各 run: ${VARIANT_NOTE} × 2 ファイル（.json + .txt）"
echo "  期間: AD ${START_YEAR} → AD ${END_YEAR}（${YEARS} 年 / ${TURNS} ターン・暦年は表示用ラベル）"
echo "  繰り返し: ${REPS} 回（seed ${SEED_START} … ${SEED_END}）"
echo "  LLM: ${LLM_NOTE}"
echo "  目安時間: 約 $((REPS * MINUTES_PER_RUN)) 分"
echo ""

if [[ ! -x "$RUNNER" ]]; then
  echo "Missing $RUNNER — run: chmod +x scripts/*.sh" >&2
  exit 1
fi

if [[ "$STUB" -eq 1 ]]; then
  export LLM_PROVIDER=stub
fi

batch_start=$(date +%s)

for i in $(seq 0 $((REPS - 1))); do
  seed=$((SEED_START + i))
  n=$((i + 1))
  echo "--- [$n/${REPS}] protocol=${PROTOCOL} seed=${seed} AD ${START_YEAR}→${END_YEAR} ---"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$RUNNER --protocol $PROTOCOL --series $SERIES --seed $seed --start-year $START_YEAR --years $YEARS"
    continue
  fi
  run_start=$(date +%s)
  "$RUNNER" --protocol "$PROTOCOL" --series "$SERIES" --seed "$seed" --start-year "$START_YEAR" --years "$YEARS"
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
echo "  次: ./scripts/run-analysis-batch.sh --aggregate"
