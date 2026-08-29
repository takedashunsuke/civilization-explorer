# scripts/

ローカル実行用スクリプトです。

## 実証実験バッチ（提出用）— ブラウザ不要

```bash
chmod +x scripts/*.sh   # 初回のみ
./scripts/setup.sh      # 初回: venv + npm install
./scripts/run-experiment-batch.sh
```

| 項目 | 値 |
|------|-----|
| 暦年 | AD **1750 → 1950**（200 年） |
| 繰り返し | **10 回**（seed 42 … 51） |
| 出力 | `result/raw/run-NNN/`（自動採番）+ `analysis/output/run-NNN/` |
| 目安時間 | **約 4〜5 時間**（Ollama `llama3.2:1b`） |

`--dry-run` で実行コマンドのみ表示。

## 単発実行

```bash
./scripts/run-experiment.sh
```

- 4 環境 × 既定 100 年（AD 1000 開始）
- `result/manifest.json` の `runs[]` を更新
- Backend 起動不要。`simulation.engine` を直接呼び出し

オプション:

```bash
./scripts/run-experiment.sh --variant lush
./scripts/run-experiment.sh --start-year 1750 --years 200 --seed 42
./scripts/run-experiment.py --help
```

詳細: [docs/guides/execution-paths.md](../docs/guides/execution-paths.md) · [DEMO.md](../DEMO.md)

## UI 起動（ライブデモ用）

```bash
./scripts/start-backend.sh    # 端末 1
./scripts/start-frontend.sh   # 端末 2
```

ブラウザ操作は [DEMO.md](../DEMO.md) を参照。

## Windows

PowerShell で手動起動（[README.md](../README.md) の「手動セットアップ」）。CLI は:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\scripts\run-experiment.py
```
