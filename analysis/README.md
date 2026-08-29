# LLM 解析

4 世界の生ログ（`result/raw/*.txt`）を LLM で比較・要約するためのファイル群です。

## ディレクトリ

```text
analysis/
  README.md       本ファイル
  prompt.md       LLM に渡すプロンプト（入力指示）
  summary.md      解析後の定量・定性サマリー（提出用・デモ後に記入）
  output/         LLM の生出力（.md / .json 等）
```

## 手順

1. [DEMO.md](../DEMO.md) で 4 本の `.txt` を `result/raw/` に保存
2. `prompt.md` を開き、4 ファイルの内容を添付（または `result/raw/` のパスを LLM に読ませる）
3. LLM の応答を `output/` に保存（例: `output/comparison-2026-08-29.md`）
4. 定量表・発表用の要点を `summary.md` に転記

## 注意

- 数値の**正**は各 `.txt` の「実験サマリー（API）」節。LLM は要約・比較の補助に使う
- `LLM_PROVIDER=stub` で取得したログでも解析可能（観測ソースは `heuristic`）
- API キーはコミットしない

開発用の詳細メモ: [docs/hackathon/RESULTS.md](../docs/hackathon/RESULTS.md)
