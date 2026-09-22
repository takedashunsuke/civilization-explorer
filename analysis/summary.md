# 実行結果サマリー（解析索引）

> 実証 **10 run 完了**（2026-08-30 · 約 415 分）。横断: [output/cross-run-summary-2026-08-30.md](./output/cross-run-summary-2026-08-30.md)

## 実証実験プロトコル

| 項目 | 値 |
|------|-----|
| 暦年（ラベル） | AD **1750 → 1950**（表示用。歴史・産業は未モデル化） |
| 年数 | **200 年**（20 ターン） |
| 繰り返し | seed **42 … 51**（**10 run**） |
| LLM | Ollama `llama3.2:1b` |
| 実験 | `./scripts/run-experiment-batch.sh` |
| 解析 | `./scripts/run-analysis-batch.sh --aggregate` |

## 横断結果（10 run 平均）

| 指標 | 豊か | 乏しい | 災害多 | 標準 |
|------|------|--------|--------|------|
| 生存人口 | 820 | 819 | 826 | 818 |
| 共有資源 | **990** | **440** | 556 | 717 |
| 争い（累計） | 90 | 99 | 94 | 89 |
| 災害（累計） | 12 | 18 | **28** | 16 |

- **資源・災害**は環境ノブどおりに安定して差が出る
- **人口**は 4 環境とも約 84% 減
- **争い**は run 間のばらつきが大きい（再現性の議論ポイント）

詳細: [cross-run-summary-2026-08-30.md](./output/cross-run-summary-2026-08-30.md)

## 実行回一覧

| 実行回 | seed | 生ログ | 解析 |
|--------|------|--------|------|
| run-001 | 42 | [raw/run-001/](../result/raw/run-001/) | [summary](./output/run-001/summary.md) |
| run-002 | 43 | [raw/run-002/](../result/raw/run-002/) | [summary](./output/run-002/summary.md) |
| run-003 | 44 | [raw/run-003/](../result/raw/run-003/) | [summary](./output/run-003/summary.md) |
| run-004 | 45 | [raw/run-004/](../result/raw/run-004/) | [summary](./output/run-004/summary.md) |
| run-005 | 46 | [raw/run-005/](../result/raw/run-005/) | [summary](./output/run-005/summary.md) |
| run-006 | 47 | [raw/run-006/](../result/raw/run-006/) | [summary](./output/run-006/summary.md) |
| run-007 | 48 | [raw/run-007/](../result/raw/run-007/) | [summary](./output/run-007/summary.md) |
| run-008 | 49 | [raw/run-008/](../result/raw/run-008/) | [summary](./output/run-008/summary.md) |
| run-009 | 50 | [raw/run-009/](../result/raw/run-009/) | [summary](./output/run-009/summary.md) |
| run-010 | 51 | [raw/run-010/](../result/raw/run-010/) | [summary](./output/run-010/summary.md) |
| test-001 | 42 | [raw/test-001/](../result/raw/test-001/) | [summary](./output/test-001/summary.md)（パイロット・100年） |

索引: [output/manifest.json](./output/manifest.json) · [result/manifest.json](../result/manifest.json)

## 講評後（resilience · 系列 `run3`）

同一ショック列 × 社会構造。計画 42 件は `run3-001`〜`004` で同一。方針: [post-award.md §4.2](../docs/hackathon/post-award.md)

| 実行回 | LLM | 生存 | 保持率 | 1 世界だけ生存 | 読み |
|--------|-----|------|--------|----------------|------|
| [run3-001](./output/run3-001/summary.md) | stub | 278 / 159 / 236 / 127 | **0.056** … 0.025 | 2 | 共和が最多。争い・共同は 0 |
| [run3-002](./output/run3-002/summary.md) | 1b 観測＋サンプル | 190 / 182 / 189 / 93 | 0.038 … 0.019 | 4 | stub と 014 の間 |
| [run3-003](./output/run3-003/summary.md) | 観測 1b・決定 8B・n=4 | **10 / 10 / 10 / 10** | **0.002** | 15 | 共同 318–372。社会差は消えた |
| [run3-004](./output/run3-004/summary.md) | 観測 1b・決定 8B・n=1 | 21 / 23 / 19 / 20 | 0.004–0.005 | 4 | 共同は半減。争いは戻る。生存差は薄い |

実験は `run3-004` まで。10 seed やさらに大きいモデルはしない。次は UI。

## 手順

1. `./scripts/run-experiment-batch.sh` → 生ログ
2. `./scripts/run-analysis-batch.sh --aggregate` → 解析
3. （任意）`--llm` で定性 · 個体深掘りは手動または別途

[DEMO.md](../DEMO.md)
