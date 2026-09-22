# scripts/

ローカル実行用スクリプトです。講評後の実験手順の正は [docs/hackathon/post-award.md](../docs/hackathon/post-award.md)（§4・§12）。

## いまの実測

| 回 | 内容 |
|----|------|
| `run-001`〜`010` | 提出。environment × 1b |
| `run-011` | stub。resilience × LLM なし（**列固定前**） |
| `run-013` | 1b。resilience × `llama3.2:1b`（**列固定前**） |
| `run-014` | 1b。同一ショック列 × `llama3.2:1b`（1b 側の比較の正） |
| `run2-001`〜`010` | 改善版 environment。入賞分とは別系列 |
| `run3-001`〜`004` | 講評後の主実験（バッチ **v2**）。同一列 × resilience。004 で切り分け済 |

v1 バッチ（`run-experiment-batch.sh`）は提出・`run2` 用に残す。講評後は v2。着手の 1 手は stub 1 seed（[post-award.md](../docs/hackathon/post-award.md) §4.1）。1b の 10 seed は先にしない。

## stub / 1b の再現

```bash
backend/.venv/bin/python scripts/pilot_phase_a.py
backend/.venv/bin/python scripts/pilot_phase_c.py
```

## 実証実験バッチ

**v1** — 提出用 environment / 改善版 `run2`。既定は 10 seed。**このファイルは残す。**

```bash
./scripts/run-experiment-batch.sh                              # environment → 次の run-NNN
./scripts/run-experiment-batch.sh --series run2                # 改善版 environment
./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1  # 旧手順（run-011 相当）
```

**v2** — 講評後の主実験。既定は resilience × `run3` × 1 seed。`.env` の LLM を使う（`--stub` を付けない）。

観測と決定はモデルを分けられる。

| 変数 | 役割 |
|------|------|
| `OLLAMA_MODEL` | 地域観測・集団スタンス（`run3-003` では 1b のまま） |
| `LLM_MAX_AGENTS_PER_TURN` | 地域あたりの個人決定人数（`run3-003` は 4、`run3-004` は 1） |

```bash
./scripts/run-experiment-batch-v2.sh --dry-run   # 系列確認
./scripts/run-experiment-batch-v2.sh --stub      # 済: run3-001
./scripts/run-experiment-batch-v2.sh             # 済: run3-002 / run3-003（.env の観測・決定モデル）
LLM_MAX_AGENTS_PER_TURN=1 ./scripts/run-experiment-batch-v2.sh  # 済: run3-004
./scripts/run-analysis-batch-v2.sh --aggregate --force
```

| 項目 | environment（既定） | resilience |
|------|---------------------|------------|
| variant | lush / lean / volatile / balanced | civic / autocrat / commune / fracture |
| 暦年 | AD **1750 → 1950**（表示用ラベル・200 年） | 同じ |
| 繰り返し | **10 回**（seed 42 … 51）。`--reps` で変更 | 同じ |
| 出力 | `result/raw/run-NNN/` + `analysis/output/run-NNN/` | 同じ（ファイル名の variant だけ違う） |

`--series run2` は `result/raw/run2-001/` から採番する。入賞の `run-001`〜`010` は上書きしない。`--dry-run` で実行コマンドのみ表示。`--stub` は `LLM_PROVIDER=stub`。`--years` は 10 の倍数。

## 一括解析（実験完了後）

```bash
./scripts/run-analysis-batch.sh              # 定量 comparison + summary（全完了 run）
./scripts/run-analysis-batch.sh --aggregate  # 上記 + 横断サマリー
./scripts/run-analysis-batch.sh --llm        # Ollama で定性も生成（任意・遅い）
./scripts/run-analysis-batch.sh --from-run 3 # run-003 以降だけ
./scripts/run-analysis-batch.sh --series run2 --aggregate # 改善版だけ横断
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
