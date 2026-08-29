# 実行結果（生ログ）

CLI またはブラウザのマイルストーン出力を格納します。

## ディレクトリ

```text
result/
  README.md          本ファイル
  raw/               生ログ — 提出用
    *.json           定量の正（experiment_summary）
    *.txt            人間向けレポート（出来事ログ全文）
  manifest.json      収録ファイル一覧（CLI 実行時に自動更新）
```

**UI と CLI の違い・共通化方針:** [docs/guides/execution-paths.md](../docs/guides/execution-paths.md)

## ファイル命名規則

```text
civ-{variant}-{暦年}-turn{ターン}.json   ← 定量比較はこちらを正とする
civ-{variant}-{暦年}-turn{ターン}.txt    ← LLM への長文投入・目視確認用
```

| variant | UI ラベル | 例 |
|---------|-----------|-----|
| `lush` | 豊か | `civ-lush-AD1100-turn10.json` / `.txt` |
| `lean` | 乏しい | `civ-lean-AD1100-turn10.json` / `.txt` |
| `volatile` | 災害多 | `civ-volatile-AD1100-turn10.json` / `.txt` |
| `balanced` | 標準 | `civ-balanced-AD1100-turn10.json` / `.txt` |

## 何を共通化しているか

| データ | 画面 | CLI |
|--------|------|-----|
| 定量 (`experiment_summary`) | API JSON | `*.json` — **同一関数の出力** |
| 全文レポート (`.txt`) | `milestoneExport.ts` | `run-experiment.py` — **実装は別（将来 Backend 一本化予定）** |

`analysis/summary.md` への転記は **`.json` の `experiment_summary`** を優先してください。

## 収録手順

**A. CLI（推奨）**

```bash
./scripts/run-experiment.sh
```

**B. ブラウザ**

1. [DEMO.md](../DEMO.md) に従い 4 環境それぞれ 100 年まで進める
2. マイルストーンで `.txt` をダウンロードし `result/raw/` に保存（`.json` は API から手動取得するか CLI を推奨）
3. `manifest.json` を更新

解析は [analysis/](../analysis/) へ。
