# Civilization Explorer

**AI エージェントが社会を創発し、人間がその法則を探索するプラットフォーム**

> What if...? を何度も試す。

人間は初期条件・環境・制度だけを変え、エージェント同士の相互作用から文明が生まれる過程を観測する。  
AI 文明そのものが目的ではなく、**人間社会の問い（格差・権力・幸福・少数派など）を探る実験場**として使う。

| | |
|--|--|
| GitHub | https://github.com/tsuide-takeda/civ-explorer |
| 提出物一覧 | [docs/hackathon/submission.md](./docs/hackathon/submission.md) |
| 実行結果 | [docs/hackathon/RESULTS.md](./docs/hackathon/RESULTS.md) |
| プレゼン原稿 | [docs/hackathon/slides.md](./docs/hackathon/slides.md) |
| テーマ根拠 | [docs/hackathon/review.md](./docs/hackathon/review.md) |

---

## 目的

社会シミュレーションは未来予測でも、人間への助言でもない。

**どんな条件から、どんな文明が繰り返し生まれるのか**を探索する。

| 役割 | やること |
|------|----------|
| 人間 | 世界の法則と初期条件を変え、結果を観測・比較する |
| Agent | 協力・争い・移住・服従などを自律的に決める |

今回のデモで固定する問い（案）: **制度は、次に生き残りやすい人物タイプをどう選別するか。**

---

## いま動く範囲

- 初期条件（年・舞台・大陸/島・気候・人口・制度・税率・教育・seed）からシミュレーションを作成できる
- Tick でエージェントが動き、集団領域・争い・出来事が平面世界地図に出る
- 意思決定は **ヒューリスティック**（LLM 接続は未了。提出前の最優先）

やらない（MVP）: 支援チャット、正解の制度提案、衛星写真、地球儀を主画面にすること、数千回バッチ UI

---

## 実行環境

| 層 | 技術 |
|----|------|
| Frontend | Nuxt 4 / Vue 3 / PrimeVue 3 / Canvas 2D 平面地図 |
| Backend | Python 3.12+ / FastAPI |
| LLM（予定） | Ollama（ローカル）または OpenAI 等（`.env` で切替） |
| DB | MVP では未接続。将来 Drizzle + ローカル Postgres（Supabase CLI） |

必要なもの:

- Node.js 22.19 以上
- Python 3.12 以上
- （任意）[Ollama](https://ollama.com/download) — LLM 接続後

詳細: [docs/guides/setup.md](./docs/guides/setup.md)

---

## 使い方

### 起動

```powershell
# 端末1 — API
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# 端末2 — UI
cd frontend
copy .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

macOS / Linux は `python3`、`source .venv/bin/activate`、`cp .env.example .env`。

- UI: http://127.0.0.1:3000/
- API: http://127.0.0.1:8000/docs

### 操作

1. 初期条件モーダルで舞台・地形・気候・人口・制度・税率・seed を決める
2. 作成する
3. Tick（または自動再生）でターンを進める
4. 地図の領域・争いの破線と、右下の出来事を読む
5. 対照するときは **seed 以外は1項目だけ**変えて作り直す

実行ログの書き方: [docs/hackathon/RESULTS.md](./docs/hackathon/RESULTS.md)

---

## ドキュメント

索引: [docs/README.md](./docs/README.md)

| 場所 | 内容 |
|------|------|
| [docs/hackathon/](./docs/hackathon/) | 提出・発表・デモ・結果 |
| [docs/design/](./docs/design/) | 要件・設計・ルール |
| [docs/guides/setup.md](./docs/guides/setup.md) | セットアップ詳細 |
| [docs/decisions/](./docs/decisions/) | ADR |

---

## 構成

```text
docs/          仕様・提出・手順
frontend/      Nuxt 観測 UI
backend/       FastAPI + シミュレーション
```

---

## ライセンス

未定
