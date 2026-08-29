# デモ再生手順（提出用）

対照実験 **同一 5,000 人 × 4 環境** を、審査員がローカルで再現するための手順です。  
設計の背景は開発用ドキュメント [docs/hackathon/demo-v3.md](./docs/hackathon/demo-v3.md) を参照してください。

---

## 前提

- [README.md](./README.md) の「環境構築」まで完了していること
- **方法 A（推奨・ブラウザ不要）:** `./scripts/run-experiment.sh` で 4 世界 × 100 年を一括実行し `result/raw/` に `.txt` を出力
- **方法 B（ライブデモ用）:** Backend / Frontend を起動し、ブラウザで操作（下記「ブラウザ操作」）

### 方法 A — CLI（ブラウザ不要）

```bash
./scripts/setup.sh              # 初回のみ
./scripts/run-experiment.sh     # 4 環境 × 10 ターン（100 年）→ result/raw/
```

単一環境のみ: `./scripts/run-experiment.sh --variant lush`  
ターン数変更: `./scripts/run-experiment.sh --turns 10`（既定）

> CLI はシミュレーションエンジンを直接呼び出します。Backend の起動は不要です（`LLM_PROVIDER=stub` 相当。地域観測はヒューリスティック）。

### 方法 B — ブラウザ（ライブ発表向け）

Backend / Frontend を起動:

```bash
./scripts/start-backend.sh    # 端末 1
./scripts/start-frontend.sh   # 端末 2
```

---

## シナリオ概要

| 項目 | 値 |
|------|-----|
| モード | 対照実験（controlled experiment） |
| seed | 42 |
| 人口 | 5,000 人（列あたり 1,000） |
| 変えるもの | **共有資源**・**災害頻度** のみ |
| 固定 | Agent ID・性格・初期位置・食の背景・初期制度など |
| 進行 | 1 ターン = 10 年。100 年ごとにマイルストーン停止 |

| UI ラベル | variant id | 意図 |
|-----------|------------|------|
| 豊か | `lush` | 資源多・災害少 |
| 乏しい | `lean` | 資源少 |
| 災害多 | `volatile` | 災害頻度高 |
| 標準 | `balanced` | 中間（基準線） |

---

## 操作手順（ブラウザ — 方法 B）

### 1. 世界を作成（豊か）

1. ブラウザで http://127.0.0.1:3000/ を開く
2. 初期条件モーダルが開いたら **STEP 1** で **対照実験** を選び **次へ**
3. **STEP 2** で環境 **豊か** を選び **作成**（自動再生が始まる）
4. 100 年（10 ターン）まで進める  
   - 自動再生のまま待つ、または **+50年** / **+10年** で手動進行
5. **マイルストーン**（100 年節目）が出たら **レポートを出力 (.txt)** をクリック
6. ダウンロードしたファイルを `result/raw/` に保存  
   - 推奨名: `civ-lush-AD1100-turn10.txt`

### 2. 残り 3 環境を繰り返す

ヘッダーの環境タブ **豊か / 乏しい / 災害多 / 標準** で切り替え、各環境で新しい sim を作成して 100 年まで進め、`.txt` を保存する。

| 環境 | 保存先（例） |
|------|----------------|
| 豊か | `result/raw/civ-lush-AD1100-turn10.txt` |
| 乏しい | `result/raw/civ-lean-AD1100-turn10.txt` |
| 災害多 | `result/raw/civ-volatile-AD1100-turn10.txt` |
| 標準 | `result/raw/civ-balanced-AD1100-turn10.txt` |

> ヘッダー切替は同一ブラウザ内で別世界を開き直す操作です。各環境は独立したシミュレーションです。

### 3. 画面で確認するポイント

| 場所 | 見ること |
|------|----------|
| 地図 | 集団の領域・争いの破線・個人の分布 |
| 状況パネル（左） | 地域ごとの緊張・繁栄・軌道・台頭タイプ |
| ヘッダー | 集団数・争い件数・LLM 状態（`stub` / `ollama` 等） |
| 出来事 | ターンごとの出生・死亡・争い・体制転換 |

### 4. LLM 解析（任意）

4 本の `.txt` を [analysis/prompt.md](./analysis/prompt.md) のプロンプトで LLM に渡し、要約を [analysis/summary.md](./analysis/summary.md) に記入する。  
解析結果の保存先: `analysis/output/`

---

## 障害時

| 症状 | 対処 |
|------|------|
| 作成が長い | そのまま待つ（5,000 人は数分かかることがある） |
| LLM が遅い / 落ちる | `backend/.env` で `LLM_PROVIDER=stub` にし Backend 再起動 |
| 画面が止まる | ブラウザ再読込。必要なら環境を選び直して作成 |
| API が応答しない | Backend 端末のログを確認し再起動 |

詳細: [docs/hackathon/checklist.md](./docs/hackathon/checklist.md)

---

## 提出物との対応

| 提出物 | 場所 |
|--------|------|
| 環境構築・起動 | [README.md](./README.md) |
| 再生手順（本ファイル） | [DEMO.md](./DEMO.md) |
| 実行スクリプト | [scripts/](./scripts/) |
| 生ログ | [result/raw/](./result/raw/) |
| LLM プロンプト | [analysis/prompt.md](./analysis/prompt.md) |
| 解析後サマリー | [analysis/summary.md](./analysis/summary.md) |
