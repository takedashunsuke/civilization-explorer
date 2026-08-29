# 実行結果サマリー（解析索引）

> 実行回ごとの解析は **`analysis/output/run-NNN/`** に格納（`result/raw/run-NNN/` と同じ ID）。

## 実証実験プロトコル

| 項目 | 値 |
|------|-----|
| 暦年（ラベル） | AD **1750 → 1950**（表示用。歴史・産業は未モデル化） |
| 年数 | **200 年** |
| 繰り返し | seed **42 … 51**（10 run） |
| 一括実行 | `./scripts/run-experiment-batch.sh` |

各 run は 4 環境（豊か / 乏しい / 災害多 / 標準）の対照実験。開始年は表示用、**再現性は `experiment_seed`**。

## 完了済み run

| 実行回 | 条件 | 生ログ | 解析 |
|--------|------|--------|------|
| **test-001** | AD 1000→1100・100年・seed 42（パイロット） | [raw/test-001/](../result/raw/test-001/) | [output/test-001/](./output/test-001/summary.md) |

実証 run（バッチ後）: `run-001` … `run-010`（AD 1750→1950・seed 42…51）— [result/manifest.json](../result/manifest.json) の `runs[]`

## 全実行回

索引: [output/manifest.json](./output/manifest.json) · 生ログ: [result/manifest.json](../result/manifest.json)

## 手順

1. `./scripts/run-experiment-batch.sh` → `result/raw/run-NNN/` × 10（`analysis/output/run-NNN/` も自動作成）
2. [prompt.md](./prompt.md) で LLM 比較（パスに `run-NNN` を指定）
3. 応答・要点を `analysis/output/run-NNN/` に保存

取得手順: [DEMO.md](../DEMO.md)
