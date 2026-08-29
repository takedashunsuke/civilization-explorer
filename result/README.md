# 実行結果（生ログ）

マイルストーン画面の **「レポートを出力 (.txt)」** で取得したファイルを格納します。

## ディレクトリ

```text
result/
  README.md          本ファイル
  raw/               生ログ（.txt）— 提出用
  manifest.json      収録ファイル一覧（デモ後に更新）
```

## ファイル命名規則

UI が自動生成する名前の例:

```text
civ-{variant}-{暦年}-turn{ターン}.txt
```

| variant | UI ラベル | 例 |
|---------|-----------|-----|
| `lush` | 豊か | `civ-lush-AD1100-turn10.txt` |
| `lean` | 乏しい | `civ-lean-AD1100-turn10.txt` |
| `volatile` | 災害多 | `civ-volatile-AD1100-turn10.txt` |
| `balanced` | 標準 | `civ-balanced-AD1100-turn10.txt` |

## ログに含まれる主な内容

- 実験条件（variant・seed・ターン・暦年）
- 累計指標（人口・争い・共同・台頭タイプなど）
- **実験サマリー（API）** — `experiment_summary` と同一（定量比較の記入元）
- 地域観測・全出来事ログ

## 収録手順

**A. CLI（推奨）**

```bash
./scripts/run-experiment.sh
```

**B. ブラウザ**

1. [DEMO.md](../DEMO.md) に従い 4 環境それぞれ 100 年まで進める
2. マイルストーンで `.txt` をダウンロードし `result/raw/` に保存
3. `manifest.json` の `files` を実際のファイル名で更新

解析は [analysis/](../analysis/) へ。
