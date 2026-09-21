# Civilization Explorer

**AI エージェントが社会を創発し、人間がその法則を探索するプラットフォーム**

> What if...? を何度も試す。

同一の人間ロスターに、違う外的環境だけを与えて文明の創発を比較する対照実験デモです。

国家や制度が前提の安全保障ではなく、**環境ショックの下で社会が協力・制度・指導を再編成できるか**を人工世界で測る。これが Civilization Explorer におけるメタ安全保障の実験的定義である。主指標は人口保持率・ショック後の協力比・制度破綻。

| | |
|--|--|
| GitHub | https://github.com/takedashunsuke/civilization-explorer |
| デモ再生手順 | [DEMO.md](./DEMO.md) |
| 実行結果（生ログ） | [result/](./result/) |
| 解析サマリー | [analysis/summary.md](./analysis/summary.md) |
| 入賞後の方針 | [docs/hackathon/post-award.md](./docs/hackathon/post-award.md) |

開発用ドキュメント（設計・発表原稿など）は [docs/](./docs/) にあります。

---

## 講評後の実測（同一ショック列）

入賞時は同一 5,000 人 × 環境差（`run-001`〜`010`）。講評後の主実験は同一ショック列 × 社会構造差（`run3`）。計画 42 件は `run3-001` / `002` / `003` で同一。

| | stub `run3-001` | 1b サンプル `run3-002` | 観測 1b・決定 8B `run3-003` |
|--|--|--|--|
| 生存の差 | civic 278 が最多 | 190 / 182 / 189 / 93 | **4 世界とも 10** |
| 人口保持率 | **0.056** / 0.032 / 0.047 / 0.025 | 0.038 / 0.036 / 0.038 / 0.019 | **0.002**（4 世界とも） |
| 共同 | 0 | 数十 | **318–372** |
| 初期名簿の 1 世界だけ生存 | **2**（a2670 が civic 指導者） | 4 | **15**（a1891 / a2418 が指導者） |

8B は行動を動かしたが社会差は潰れた。大きいモデル＝回復、ではない。初期名簿で 2 世界以上生き残った人は **0**。同一 ID の差は「1 世界だけ生き残ったか」に出る。生ログ: [result/raw/run3-003/](./result/raw/run3-003/)

## 今後の実証方針

**変えるのは一度に一つ。系列は `run3`。次番号は `run3-004`。** 詳細は [post-award.md §4.2](./docs/hackathon/post-award.md)。

| する | しない |
|------|--------|
| ショック計画を variant 間で固定したまま比較する | 入賞時 `run-001`〜`010` の上書き |
| 主指標は保持率・協力比・制度破綻（ラベルは参考） | recovered を必須にしない |
| 次の実験は 8B 協力偏りの切り分け 1 本（決定モデルを戻す / 上書き人数=1 / プロンプトで wait を明示） | 1b・8B の 10 seed、さらに大きい決定モデル、観測まで 8B |
| 観測の厚み（保持率 3 桁・同一 ID 比較は済。次は UI） | 全住民を毎ターン LLM |

講評後の一括は `./scripts/run-experiment-batch-v2.sh`（既定: resilience × `run3` × 1 seed）。v1 の environment 10 seed は残す。

---

## 提出物（ルート）

| ファイル / フォルダ | 内容 |
|---------------------|------|
| [README.md](./README.md) | 本ファイル — 環境構築・起動 |
| [DEMO.md](./DEMO.md) | デモ再生手順（実証: AD 1750→1950 × 10 回） |
| [scripts/](./scripts/) | `run-experiment-batch.sh`（一括）/ `run-experiment.sh`（単発） |
| [result/raw/](./result/raw/) | 実行結果（`test-001/` パイロット、`run-NNN/` 実証） |
| [analysis/](./analysis/) | LLM 解析用プロンプト・`output/run-NNN/` に解析結果 |

---

## 環境構築

### 必要なもの

| 項目 | バージョン |
|------|------------|
| Node.js | 22.19 以上 |
| Python | 3.12 以上 |
| （任意）Ollama | `LLM_PROVIDER=ollama` で地域観測に接続 |

### 初回セットアップ（macOS / Linux）

```bash
git clone https://github.com/takedashunsuke/civilization-explorer.git
cd civilization-explorer
chmod +x scripts/*.sh
./scripts/setup.sh
```

Windows は下記「手動セットアップ」を参照。詳細: [docs/guides/setup.md](./docs/guides/setup.md)

### 起動

```bash
# 端末 1 — API
./scripts/start-backend.sh

# 端末 2 — UI
./scripts/start-frontend.sh
```

| URL | 用途 |
|-----|------|
| http://127.0.0.1:3000/ | シミュレーション UI |
| http://127.0.0.1:8000/docs | API ドキュメント |
| http://127.0.0.1:8000/health | LLM 接続状態 |

### 手動セットアップ（全 OS）

**Backend**

```bash
cd backend
python3 -m venv .venv          # Windows: python -m venv .venv
source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env           # Windows: copy .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**

```bash
cd frontend
cp .env.example .env           # Windows: copy .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

### LLM（任意）

`backend/.env` で切り替え（既定は `stub` = ヒューリスティックのみ）:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
```

変更後は Backend を再起動。Ollama の手順: [docs/guides/setup.md](./docs/guides/setup.md)

---

## デモの流れ（概要）

**提出用ログの取得（ブラウザ不要）:**

```bash
./scripts/setup.sh                    # 初回のみ
./scripts/run-experiment-batch.sh     # 実証: AD 1750→1950・200年 × seed 10 回（約 4〜5 時間）
./scripts/run-experiment.sh           # 単発（自動で result/raw/run-NNN/）
```

実証プロトコル: **同一 5,000 人ロスター**を 4 環境に投入し、**200 年**を **seed 42〜51 で 10 回**繰り返す（**実測完了** · 約 415 分）。解析: `./scripts/run-analysis-batch.sh --aggregate` → [analysis/summary.md](./analysis/summary.md)

**ライブ発表:** [DEMO.md](./DEMO.md) のブラウザ手順で画面を見せながら操作。

1. 上記バッチまたは単発 CLI で `result/raw/run-NNN/` に保存
2. [analysis/prompt.md](./analysis/prompt.md) で LLM 比較 → [analysis/summary.md](./analysis/summary.md) 索引から各 run を参照

UI と CLI は同じ Python エンジン・同じ Ollama 設定。詳細: [docs/guides/execution-paths.md](./docs/guides/execution-paths.md)

固定: 5,000 人・seed 42・性格・位置。変える: **共有資源と災害のみ**。

---

## 技術スタック

| 層 | 技術 |
|----|------|
| Frontend | Nuxt 4 / Vue 3 / PrimeVue / Canvas 2D |
| Backend | Python 3.12+ / FastAPI |
| LLM | Ollama または OpenAI（`.env` で切替） |
| DB | MVP では未使用（インメモリ） |

---

## リポジトリ構成

```text
README.md          提出用 — 環境構築・起動
DEMO.md            提出用 — ウェブ操作手順
scripts/           提出用 — setup / 起動スクリプト
result/raw/        提出用 — 実行生ログ (.txt)
analysis/          提出用 — LLM プロンプト・解析サマリー
docs/              開発用 — 設計・発表原稿・ADR
frontend/          Nuxt 観測 UI
backend/           FastAPI + シミュレーション
```

---

## ライセンス

未定
