# デモ再生手順（提出用）

対照実験 **同一 5,000 人 × 4 環境** を、審査員がローカルで再現するための手順です。  
設計の背景は開発用ドキュメント [docs/hackathon/demo-v3.md](./docs/hackathon/demo-v3.md) を参照してください。

> **講評後の次実験**は environment ではなく `--protocol resilience`（stub 試験が先）。手順は [docs/hackathon/post-award.md](./docs/hackathon/post-award.md) §11 と [scripts/README.md](./scripts/README.md)。  
> `./scripts/run-experiment-batch.sh` の既定は第2回提出と同じ **environment** のままです。

## 実証実験プロトコル（提出）

| 項目 | 値 |
|------|-----|
| 暦年（ラベル） | **AD 1750 → AD 1950**（表示・ファイル名用。歴史・産業は未モデル化） |
| シミュレーション年数 | **200 年**（20 ターン） |
| 繰り返し | **10 回**（`experiment_seed` 42 … 51） |
| 各 run | 4 環境 × `.json` + `.txt` → `result/raw/run-NNN/` |
| **実測（2026-08-30）** | **10 run 完了**（合計 **約 415 分**） |
| 解析 | `./scripts/run-analysis-batch.sh --aggregate` |
| 横断サマリー | [analysis/output/cross-run-summary-2026-08-30.md](./analysis/output/cross-run-summary-2026-08-30.md) |

開始年はレポートとファイル名の**暦年ラベル**のみ。産業革命・戦争・時代制度などの歴史背景はシミュレーションに含まれない（力学は `experiment_seed` と環境パターンで決まる）。

```bash
./scripts/setup.sh                  # 初回のみ
./scripts/run-experiment-batch.sh   # 10 run 一括（実測: 約 415 分）
./scripts/run-analysis-batch.sh --aggregate   # 解析（定量 + 横断表）
```

出力例: `civ-lush-AD1950-turn20.json`（各 run フォルダに 4 本 × 2 形式）

---

## 前提

- [README.md](./README.md) の「環境構築」まで完了していること
- **方法 A（推奨・ブラウザ不要）:** `./scripts/run-experiment.sh` → `result/raw/` に `.json` + `.txt`
- **方法 B（ライブデモ用）:** Backend / Frontend を起動し、ブラウザで操作（下記「ブラウザ操作」）

**UI と CLI（同じエンジン・同じ Ollama・結果の共通化）:** [docs/guides/execution-paths.md](./docs/guides/execution-paths.md)

### 方法 A — CLI（ブラウザ不要）

**提出用（推奨）:**

```bash
./scripts/setup.sh
./scripts/run-experiment-batch.sh     # AD 1750→1950・200年 × seed 10 回
```

**単発・カスタム:**

```bash
./scripts/run-experiment.sh                              # 既定: AD 1000→1100・100年
./scripts/run-experiment.sh --start-year 1750 --years 200   # 実証 1 回分
./scripts/run-experiment.sh --seed 43 --start-year 1750 --years 200
```

ドライラン（コマンド確認のみ）: `./scripts/run-experiment-batch.sh --dry-run`

各 **run フォルダ**に 4 環境 × 2 ファイル（`.json` + `.txt`）:

```text
result/raw/test-001/          # パイロット（AD 1000→1100）
result/raw/run-001/           # 実証 1 回目（バッチ後）
  run.json
  civ-lush-AD1100-turn10.json
  civ-lush-AD1100-turn10.txt
  …（lean / volatile / balanced）
```

> CLI は `simulation.engine` を直接呼び出し、`backend/.env` の `LLM_PROVIDER`（`ollama` 含む）を自動読み込みします。画面操作時の Backend API と **同じエンジン・同じ Ollama** です（[execution-paths.md](./docs/guides/execution-paths.md)）。

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
| 豊か | `result/raw/run-NNN/civ-lush-AD1100-turn10.txt` |
| 乏しい | `result/raw/run-NNN/civ-lean-AD1100-turn10.txt` |
| 災害多 | `result/raw/run-NNN/civ-volatile-AD1100-turn10.txt` |
| 標準 | `result/raw/run-NNN/civ-balanced-AD1100-turn10.txt` |

> ヘッダー切替は同一ブラウザ内で別世界を開き直す操作です。各環境は独立したシミュレーションです。

### 3. 画面で確認するポイント

| 場所 | 見ること |
|------|----------|
| 地図 | 集団の領域・争いの破線・個人の分布 |
| 状況パネル（左） | 地域ごとの緊張・繁栄・軌道・台頭タイプ |
| ヘッダー | 集団数・争い件数・LLM 状態（`stub` / `ollama` 等） |
| 出来事 | ターンごとの出生・死亡・争い・体制転換 |

### 4. LLM 解析（任意）

4 本の `.json`（または `.txt`）を [analysis/prompt.md](./analysis/prompt.md) のプロンプトで LLM に渡し、応答・要点を **`analysis/output/run-NNN/`**（生ログと同じ番号）に保存する。索引は [analysis/summary.md](./analysis/summary.md)。

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
| 解析索引 / 横断 | [analysis/summary.md](./analysis/summary.md) · [cross-run-summary](./analysis/output/cross-run-summary-2026-08-30.md) |
