# LLM 解析

4 世界の実行結果（`result/raw/`）を LLM で比較・要約するためのファイル群です。

## ディレクトリ

```text
analysis/
  README.md       本ファイル
  prompt.md       LLM に渡すプロンプト（入力指示）
  summary.md      解析後の定量・定性サマリー（提出用・デモ後に記入）
  output/         LLM の生出力（.md / .json 等）
```

## 手順

1. [DEMO.md](../DEMO.md) で `./scripts/run-experiment.sh` を実行（またはブラウザで同等の実験）
2. `result/raw/` に `.json`（定量）と `.txt`（全文ログ）が揃っていることを確認
3. `prompt.md` を LLM に渡す（`.json` 4 本推奨。長文比較なら `.txt` も可）
4. 応答を `output/` に保存し、要点を `summary.md` に転記

## 数値の正

| 優先 | ファイル | 内容 |
|------|----------|------|
| **1** | `result/raw/*.json` | `experiment_summary` — 画面 API と CLI で同一 |
| 2 | `result/raw/*.txt` | 「実験サマリー（API）」節（`.json` と同値） |

実行経路の説明: [docs/guides/execution-paths.md](../docs/guides/execution-paths.md)

## 注意

- LLM は要約・比較の補助。数値は `experiment_summary` をそのまま転記する
- API キーはコミットしない

開発用索引: [docs/hackathon/RESULTS.md](../docs/hackathon/RESULTS.md)
