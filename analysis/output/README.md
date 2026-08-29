# 解析出力

`result/raw/run-NNN/` と **同じ run ID** で解析結果を格納します。

## ディレクトリ

```text
analysis/output/
  manifest.json       索引（tests[] / runs[]）
  test-001/           パイロット解析
  run-001/            実証 1 回目（バッチ後）
  run-002/
    …
```

## 対応関係

| 生ログ | 解析 |
|--------|------|
| `result/raw/test-001/` | `analysis/output/test-001/` |
| `result/raw/run-NNN/` | `analysis/output/run-NNN/` |

CLI で `./scripts/run-experiment.sh` を実行すると、`analysis/output/run-NNN/` フォルダが自動作成されます（中身は手動または LLM で記入）。

## 手順

1. `./scripts/run-experiment.sh` → `result/raw/run-NNN/` に 4 本 `.json`
2. [prompt.md](../prompt.md) で LLM 比較（入力パスは `run-NNN` を指定）
3. 応答を `analysis/output/run-NNN/llm-response-*.md` に保存
4. 要点を `analysis/output/run-NNN/summary.md` に整理

索引: [../summary.md](../summary.md)（最新 run へのリンク）
