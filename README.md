# Civilization Explorer

**AI エージェントが社会を創発し、人間がその法則を探索するプラットフォーム**

> What if...? を何度も試す。

同一の人間ロスターに、違う外的環境だけを与えて文明の創発を比較する対照実験デモです。

| | |
|--|--|
| GitHub | https://github.com/takedashunsuke/civilization-explorer |
| デモ再生手順 | [DEMO.md](./DEMO.md) |
| 実行結果（生ログ） | [result/](./result/) |
| 解析サマリー | [analysis/summary.md](./analysis/summary.md) |

開発用ドキュメント（設計・発表原稿など）は [docs/](./docs/) にあります。

---

## 提出物（ルート）

| ファイル / フォルダ | 内容 |
|---------------------|------|
| [README.md](./README.md) | 本ファイル — 環境構築・起動 |
| [DEMO.md](./DEMO.md) | ウェブ画面での再生手順（4 世界 × 100 年） |
| [scripts/](./scripts/) | `run-experiment.sh`（CLI・ブラウザ不要）/ `start-*.sh`（UI） |
| [result/raw/](./result/raw/) | 実行結果（`.json` = 定量の正、`.txt` = 全文ログ） |
| [analysis/](./analysis/) | LLM 解析用プロンプト・解析後サマリー |

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
./scripts/setup.sh           # 初回のみ
./scripts/run-experiment.sh  # → result/raw/ に 4 本の .txt
```

**ライブ発表:** [DEMO.md](./DEMO.md) のブラウザ手順で画面を見せながら操作。

1. 4 環境（豊か / 乏しい / 災害多 / 標準）それぞれ 100 年まで進める
2. `.json` / `.txt` を `result/raw/` に保存（CLI なら自動）
3. [analysis/prompt.md](./analysis/prompt.md) で LLM 比較 → [analysis/summary.md](./analysis/summary.md) に整理

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
