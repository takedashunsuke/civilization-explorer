# LLM 解析プロンプト（4 世界比較）

以下を LLM（ChatGPT / Claude / Ollama 等）に渡してください。

**推奨:** `result/raw/run-NNN/` の 4 本の **`.json`**（`experiment_summary` が定量の正）。  
**解析の保存先:** `analysis/output/run-NNN/`（生ログと同じ `run-NNN`）。

実行回は [result/manifest.json](../result/manifest.json) の `runs[]` / `tests[]` を参照（実証: `run-001` …、パイロット: `test-001`）。

---

## プロンプト（コピー用）

```
あなたは文明シミュレーションの実験結果を読むアナリストです。

## 実験設計
- 同一 5,000 人のロスター（各 run の `experiment_seed`）を 4 つの世界に投入した対照実験
- 変えたのは「共有資源」と「災害頻度」のみ。食の背景・初期制度・性格・位置は固定
- 4 環境: 豊か(lush) / 乏しい(lean) / 災害多(volatile) / 標準(balanced)
- 各世界を添付 JSON の `start_year` から `milestone_years` 年（`milestone_turn` ターン、1 ターン=10 年）進めた時点のレポート
- 開始年・終了年は各 `.json` の `start_year` / `calendar_year`、または manifest の当該 run を参照

## 依頼
各 .json の `experiment_summary`（または .txt の「実験サマリー（API）」節）を主な根拠に、次を日本語で出力してください。

1. **定量比較表**（Markdown 表）
   - 列: 豊か / 乏しい / 災害多 / 標準
   - 行: 生存人口、人口変化%、共有資源合計、交易開放平均、争い累計、共同累計、体制転換累計、災害累計、台頭タイプ、観測ソース

2. **環境ごとの一言要約**（各 2〜3 文）
   - どんな社会が創発したか（人口・災害・台頭タイプの観点）

3. **意外な差・面白い点**（箇条書き 3〜5 件）
   - 「同じ人間なのに世界で違う創発」に関わるものを優先

4. **発表用フック**（1 段落）
   - 審査員向けに「条件を変えたら何が違ったか」をストーリーで

5. **制限の明示**（1〜2 文）
   - 同一 Agent ID の役割差はログからは断定しにくい場合がある旨

数値は添付 txt の記載をそのまま使い、推測で補完しないでください。欠損は「—」と書いてください。
```

---

## 添付ファイル一覧（デモ後に確認）

| 環境 | JSON（推奨） | TXT（任意） |
|------|-------------|-------------|
| 豊か | `result/raw/run-NNN/civ-lush-AD{終了年}-turn{N}.json` | `...txt` |
| 乏しい | `result/raw/run-NNN/civ-lean-AD{終了年}-turn{N}.json` | `...txt` |
| 災害多 | `result/raw/run-NNN/civ-volatile-AD{終了年}-turn{N}.json` | `...txt` |
| 標準 | `result/raw/run-NNN/civ-balanced-AD{終了年}-turn{N}.json` | `...txt` |

例（実証: AD 1750→1950）: `civ-lush-AD1950-turn20.json`  
例（パイロット test-001: AD 1000→1100）: `civ-lush-AD1100-turn10.json`

（実証は `run-001` … — [result/manifest.json](../result/manifest.json) の `runs[]` を参照）

一覧は [result/manifest.json](../result/manifest.json) でも管理します。

## 出力の保存

LLM の応答全文を **`analysis/output/run-NNN/llm-response-YYYY-MM-DD.md`** に保存し、表と要点を同フォルダの **`summary.md`** に整理してください。

（`run-NNN` は入力に使った生ログの実行回と同じ番号）
