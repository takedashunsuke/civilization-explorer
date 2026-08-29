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

1. `./scripts/run-experiment.sh` → `result/raw/run-NNN/` + `analysis/output/run-NNN/` 作成
2. `prompt.md` を LLM に渡す（入力: その run の 4 本 `.json`）
3. 応答を `analysis/output/run-NNN/llm-response-*.md` に保存
4. 要点を `analysis/output/run-NNN/summary.md` に整理

## 数値の正

`result/raw/run-NNN/*.json` の `experiment_summary`

実行経路: [docs/guides/execution-paths.md](../docs/guides/execution-paths.md)
