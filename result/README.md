# 実行結果（生ログ）

CLI またはブラウザのマイルストーン出力を格納します。

## ディレクトリ

```text
result/
  manifest.json          全実行回の索引（latest_run・runs[]）
  raw/
    test-001/            パイロット（AD 1000→1100・100年）
    run-001/             実証 1 回目（バッチ後）
      run.json           当該回のメタデータ
      civ-lush-*.json / .txt
      civ-lean-*.json / .txt
      civ-volatile-*.json / .txt
      civ-balanced-*.json / .txt
    run-002/             2 回目（同条件の再実行）
    run-003/             3 回目 …
```

**UI と CLI の違い:** [docs/guides/execution-paths.md](../docs/guides/execution-paths.md)

## 実証実験プロトコル（提出）

| 項目 | 値 |
|------|-----|
| 暦年ラベル | AD **1750 → 1950** |
| 年数 | **200 年**（20 ターン） |
| 繰り返し | seed **42 … 51**（10 回） |
| 一括実行 | `./scripts/run-experiment-batch.sh` |

```bash
./scripts/run-experiment.sh                              # 自動で次の run-NNN（例: run-002）
./scripts/run-experiment.sh --start-year 1750 --years 200 --seed 42   # 実証 1 回分
./scripts/run-experiment-batch.sh                      # 10 run 一括
```

1 ターン = 10 年。ファイル名は `civ-{variant}-AD{終了年}-turn{N}`（実証なら `AD1950-turn20`）。

`result/manifest.json` の `latest_run` と `runs[]` が更新されます。

## ファイル命名（各 run フォルダ内）

```text
civ-{variant}-AD{暦年}-turn{ターン}.json   ← 定量の正（experiment_summary）
civ-{variant}-AD{暦年}-turn{ターン}.txt    ← 全文ログ
```

| variant | UI ラベル |
|---------|-----------|
| `lush` | 豊か |
| `lean` | 乏しい |
| `volatile` | 災害多 |
| `balanced` | 標準 |

## ブラウザから保存する場合

1. [DEMO.md](../DEMO.md) の手順で 4 環境を進める
2. `.txt` を **手動で** `result/raw/run-NNN/` に保存（次の空き番号）
3. `manifest.json` と当該 `run.json` を更新（CLI 実行なら自動）

## 解析

- 1 回分の比較: その `run-NNN/` 内の 4 本 `.json`
- 解析の保存先: **`analysis/output/run-NNN/`**（同じ番号）
- 複数回の再現性: `run-001` vs `run-002` … で同指標を並べる（パイロットは `test-001`）

[analysis/](../analysis/) · [analysis/output/manifest.json](../analysis/output/manifest.json)
