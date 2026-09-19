# scripts/

ローカル実行用スクリプトです。講評後の実験手順の正は [docs/hackathon/post-award.md](../docs/hackathon/post-award.md)（§4・§12）。

## いまの実測

| 回 | 内容 |
|----|------|
| `run-001`〜`010` | 提出。environment × 1b |
| `run-011` | stub。resilience × LLM なし |
| `run-013` | 1b A/B。resilience × `llama3.2:1b` |

次の実装は Phase D（中〜大モデルの意思決定）。同一ショック列は固定済み。1b の 10 seed は先にしない。次の新規 run は `run-014`。

## stub / 1b の再現

```bash
backend/.venv/bin/python scripts/pilot_phase_a.py
backend/.venv/bin/python scripts/pilot_phase_c.py
./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1
LLM_PROVIDER=ollama ./scripts/run-experiment-batch.sh --protocol resilience --reps 1
./scripts/run-analysis-batch.sh --run 13
```
## 実証実験バッチ（提出用 environment / 講評対応 resilience）

```bash
chmod +x scripts/*.sh   # 初回のみ
./scripts/setup.sh      # 初回: venv + npm install
./scripts/run-experiment-batch.sh                              # environment（第2回提出と同じ）
./scripts/run-experiment-batch.sh --protocol resilience --stub # 講評対応
```

| 項目 | environment（既定） | resilience |
|------|---------------------|------------|
| variant | lush / lean / volatile / balanced | civic / autocrat / commune / fracture |
| 暦年 | AD **1750 → 1950**（表示用ラベル・200 年） | 同じ |
| 繰り返し | **10 回**（seed 42 … 51）。`--reps` で変更 | 同じ |
| 出力 | `result/raw/run-NNN/` + `analysis/output/run-NNN/` | 同じ（ファイル名の variant だけ違う） |

`--dry-run` で実行コマンドのみ表示。`--stub` は `LLM_PROVIDER=stub`。`--years` は 10 の倍数。

## 一括解析（実験完了後）

```bash
./scripts/run-analysis-batch.sh              # 定量 comparison + summary（全完了 run）
./scripts/run-analysis-batch.sh --aggregate  # 上記 + 横断サマリー
./scripts/run-analysis-batch.sh --llm        # Ollama で定性も生成（任意・遅い）
./scripts/run-analysis-batch.sh --from-run 3 # run-003 以降だけ
```

| モード | 出力 |
|--------|------|
| 既定 | `analysis/output/run-NNN/comparison-*.md` + `summary.md` |
| `--llm` | 上記 + `llm-response-*.md` |
| `--aggregate` | `analysis/output/cross-run-summary-*.md`（environment の争い Δ と resilience の保持率を振り分け） |

## 単発実行

```bash
./scripts/run-experiment.sh
./scripts/run-experiment.sh --protocol resilience --start-year 1750 --years 200 --seed 42
```

- 既定プロトコルは environment、既定 100 年（AD 1000 開始）
- `result/manifest.json` の `runs[]` を更新
- Backend 起動不要。`simulation.engine` を直接呼び出し

オプション:

```bash
./scripts/run-experiment.sh --variant lush
./scripts/run-experiment.sh --protocol resilience --variant civic
./scripts/run-experiment.sh --start-year 1750 --years 200 --seed 42
./scripts/run-experiment.py --help
```

詳細: [docs/guides/execution-paths.md](../docs/guides/execution-paths.md) · [DEMO.md](../DEMO.md) · [docs/hackathon/post-award.md](../docs/hackathon/post-award.md)

## UI 起動（ライブデモ用）

```bash
./scripts/start-backend.sh    # 端末 1
./scripts/start-frontend.sh   # 端末 2
```

ブラウザ操作は [DEMO.md](../DEMO.md) を参照。UI の対照実験切替は environment（豊か／乏しい／災害多／標準）のみ。resilience は CLI が正。

## Windows

PowerShell で手動起動（[README.md](../README.md) の「手動セットアップ」）。CLI は:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\scripts\run-experiment.py --protocol resilience
```
