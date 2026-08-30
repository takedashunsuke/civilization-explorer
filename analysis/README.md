# LLM 解析

4 世界の実行結果（`result/raw/run-NNN/`）を LLM で比較・要約するためのファイル群です。

## ディレクトリ

```text
analysis/
  README.md           本ファイル
  prompt.md           LLM プロンプト（入力指示）
  summary.md          解析索引（最新 run へのリンク）
  output/
    manifest.json     実行回ごとの解析フォルダ索引
  test-001/          パイロット解析
  run-001/           実証解析（バッチ後）
    run-002/
```

**`result/raw/run-NNN/` と `analysis/output/run-NNN/` は同じ番号で対応。**

## 手順

1. `./scripts/run-experiment-batch.sh` → `result/raw/run-NNN/`（実験）
2. **一括解析（推奨）:** `./scripts/run-analysis-batch.sh` → 各 run に `comparison-*.md` + `summary.md`
3. 定性が必要なら `./scripts/run-analysis-batch.sh --llm`（Ollama・時間がかかる）
4. 手動の場合: [prompt.md](./prompt.md) を LLM に渡し、`analysis/output/run-NNN/` に保存

## 数値の正

`result/raw/run-NNN/*.json` の `experiment_summary`

実行経路: [docs/guides/execution-paths.md](../docs/guides/execution-paths.md)
