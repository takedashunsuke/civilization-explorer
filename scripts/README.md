# scripts/

ローカル実行用スクリプトです。

## 対照実験（提出用ログ）— ブラウザ不要

```bash
chmod +x scripts/*.sh   # 初回のみ
./scripts/setup.sh      # 初回: venv + npm install
./scripts/run-experiment.sh
```

- 4 環境（豊か / 乏しい / 災害多 / 標準）× 10 ターン（100 年）を実行
- `result/raw/civ-*.txt` を生成し `result/manifest.json` を更新
- Backend 起動不要（シミュレーションエンジンを直接呼び出し）

オプション:

```bash
./scripts/run-experiment.sh --variant lush    # 1 環境のみ
./scripts/run-experiment.sh --turns 5         # 50 年
./scripts/run-experiment.py --help
```

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
