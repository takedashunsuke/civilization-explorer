# Architecture（技術スタック・実装手順）

## 技術スタック

### Frontend

* Nuxt 4 — [Introduction](https://nuxt.com/docs/4.x/getting-started/introduction)
* PrimeVue 3 — [Setup](https://v3.primevue.org/setup/)
* Three.js 地球儀（補助タブ）。主画面は Canvas 2D の平面世界地図。操作 UI は PrimeVue（[ADR 0006](../decisions/0006-flat-map-primary.md)）

役割

* アプリの枠（ページ・ルーティング・API 連携）: **Nuxt 4**
* 操作・一覧・数値 UI: **PrimeVue**（フォーム、表、タイムライン、メトリクス）
* 空間可視化: **平面世界地図が既定**（領域・衝突・所属色）。地球儀は同一データの補助表示

> PrimeVue は世界マップを描かない。パラメータ変更や Event 閲覧など「実験操作 UI」を担当する。  
> 技術ごとの機能要件の詳細は [DesignDoc.md](./DesignDoc.md) を参照。

### Backend

* Python
* FastAPI — [公式（日本語）](https://fastapi.tiangolo.com/ja/)

役割

* シミュレーション管理
* エージェント管理
* API

### LLM

* Ollama（ローカル開発・ローカルデモ）
* 外部 API（OpenAI など。発表・品質重視時に切替）
* プロバイダは `.env` で切替可能な薄い抽象層にする（Kimi 等も同層に追加可）

用途

* Agent の思考
* Agent 間対話
* 意思決定

### データベース

**PostgreSQL** ＋ **Drizzle ORM**

理由は単なる保存ではない。文明を構造化して蓄積し、比較・再実行・分析できるようにする。

| 項目 | 技術 |
|------|------|
| RDB | PostgreSQL（Supabase CLI / Docker） |
| ORM | [Drizzle ORM](https://orm.drizzle.team/) |
| マイグレーション | drizzle-kit |
| スキーマ配置 | `frontend/server/db/`（TypeScript） |

運用の目安（[ADR 0001](../decisions/0001-local-runtime-and-supabase.md) / [ADR 0003](../decisions/0003-drizzle-orm.md)）

* Frontend / Backend / LLM はローカルで動かす
* DB は [Supabase CLI](https://supabase.com/docs/guides/local-development/cli/getting-started)（`supabase init` → `supabase start`、Docker 上）を使う
* **永続化は Nuxt（Nitro）＋ Drizzle** が担当する。FastAPI はシミュレーション／LLM に専念し、Postgres へ直接接続しない
* 接続はローカル Postgres の接続文字列（例: `postgres://...@127.0.0.1:54322/postgres`）を `.env` で渡す

最低限のテーブル（Drizzle schema で定義）

* Simulation
* World
* Agent
* Institution
* Event
* History
* Relationship

### Auth（将来・Web 公開時）

* [Better Auth](https://www.better-auth.com/) ＋ Drizzle（`drizzleAdapter`）— [ADR 0004](../decisions/0004-better-auth.md)
* ハッカソン MVP では **実装しない**（ローカル単一利用者）
* Auth.js / Supabase Auth は採用しない
* 公開時は `simulations.owner_id` で個人所有を表し、Nitro が session をゲートする

### 公式ドキュメント一覧

| 技術 | URL |
|------|-----|
| Nuxt 4 | https://nuxt.com/docs/4.x/getting-started/introduction |
| Three.js（任意・後追い） | https://threejs.org/docs/ |
| Supabase CLI | https://supabase.com/docs/guides/local-development/cli/getting-started |
| Drizzle ORM | https://orm.drizzle.team/ |
| Drizzle × Supabase | https://orm.drizzle.team/docs/connect-supabase |
| Better Auth | https://www.better-auth.com/ |
| Better Auth × Nuxt | https://www.better-auth.com/docs/integrations/nuxt |
| FastAPI | https://fastapi.tiangolo.com/ja/ |
| PrimeVue 3 | https://v3.primevue.org/setup/ |

---

## ディレクトリ構成

```text
docs/
├── README.md
├── design/                 # 要件・設計・ルール
│   ├── FeatureSpec.md
│   ├── Architecture.md
│   ├── SimulationRules.md
│   ├── DesignDoc.md
│   └── AGENTS.md
├── updates/                # 進捗・変更記録
├── guides/                 # セットアップ・デモ手順
├── hackathon/              # ハッカソン発表・デモ資料
└── decisions/              # 設計判断（ADR）

frontend/
├── pages/
├── components/
├── server/
│   └── db/          # Drizzle: schema / client / migrations
├── drizzle.config.ts
└── three/           # （任意）後追い 2.5D 用。MVP は components/map 等の 2D を優先

backend/
├── api/
├── simulation/
│   ├── world.py
│   ├── agent.py
│   ├── llm.py
│   ├── event.py
│   ├── simulation.py
│   └── metrics.py
└── models/          # ドメイン／Pydantic（永続化スキーマは Drizzle 側）
```

---

## 開発方針

実装より先にドキュメントを整備する（本ドキュメント群がその第一段階）。

AI に実装を任せる前提で、「AI が理解しやすいプロジェクト構成」を採用する。

関連ドキュメント

* [FeatureSpec.md](./FeatureSpec.md) — 要件定義
* [SimulationRules.md](./SimulationRules.md) — 行動・ターン・状態
* [DesignDoc.md](./DesignDoc.md) — UI / API / データ設計
* [AGENTS.md](./AGENTS.md) — 開発エージェント向け指針
* [../hackathon/review.md](../hackathon/review.md) — ハッカソンテーマ根拠
* [../updates/](../updates/) — 進捗記録
* [../decisions/](../decisions/) — 設計判断

---

## 実装手順

MVP は「動くシミュレーションループ → 観測 UI → 永続化」の順で積み上げる。  
LLM 依存部分は後から差し替え可能な薄い層として置く。

### Phase 0 — リポジトリ・環境

1. `frontend/`（Nuxt 4）と `backend/`（FastAPI）を初期化する
2. Supabase CLI でローカル DB を起動する（`supabase init` → `supabase start`）
3. Ollama を起動し、使用モデルを決める（例: `llama3.2`）
4. `.env` で LLM プロバイダ切替（`ollama` / `openai`）を可能にする

完了条件: `frontend` と `backend` がそれぞれ起動し、DB に接続できる

---

### Phase 1 — コア状態モデル（ルール実装）

[SimulationRules.md](./SimulationRules.md) に従い、コード上の状態を定義する。

1. `World` / `Agent` / `Relationship` / `Institution` のデータモデルを実装する
2. ターン進行の骨格 `simulation.tick()` を実装する（LLM なしでも動くスタブで可）
3. 行動の解決ロジック（協力・争う・移住・従う）をルールベースで先に実装する
4. メトリクス（格差・信頼・協力率など）の最小計算を追加する

完了条件: 固定シードで数ターン進められ、状態変化と Event がログに残る

---

### Phase 2 — LLM 意思決定の接続

1. `llm.py` にプロバイダ抽象（Ollama / OpenAI）を作る
2. Agent ごとに「観測 → 候補行動 → 選択」のプロンプトを定義する
3. レスポンスを行動スキーマ（JSON）にパースし、ルール解決に渡す
4. 失敗時フォールバック（パース失敗・タイムアウト時はランダム/ヒューリスティック）を入れる
5. Agent 数・並列度・呼び出し頻度を制限する（MVP: 5〜20 Agent）

完了条件: LLM の選択結果で社会状態が変わり、同条件再実行で傾向が観察できる

---

### Phase 3 — API

1. `POST /simulations` — 世界パラメータから Simulation 作成
2. `POST /simulations/{id}/start` — 実行開始
3. `POST /simulations/{id}/tick` — 1ターン進行（またはバッチ）
4. `GET /simulations/{id}` — 現在状態取得
5. `GET /simulations/{id}/events` — Event / History 取得
6. （任意）WebSocket または SSE でターン更新を配信

完了条件: API だけでシミュレーションを作成・進行・観測できる

---

### Phase 4 — 永続化（Drizzle）

1. `frontend/server/db/` に Drizzle schema を定義し、`drizzle-kit generate` / `migrate` で適用する
2. Nuxt server API（または server util）から Postgres へ接続する（postgres.js 等）
3. ターン終了時に Agent / Relationship / Event / History を保存する（FastAPI の応答を受けて Nitro 側で書く）
4. 同条件再実行用に初期パラメータ（seed 含む）を保存する
5. 過去 Simulation の一覧・詳細取得を Nuxt server 経由で追加する

完了条件: 再起動後も結果を読み出せ、同条件で再実行できる

---

### Phase 5 — Frontend（観測 UI）

1. パラメータ入力画面（人口・資源・税率・制度など）
2. シミュレーション開始 / 一時停止 / 1ターン進行
3. **平面世界地図**で Agent・集団領域・争いを可視化（Natural Earth。地球儀はタブ）
4. タイムライン（Event の時系列）と簡易メトリクス表示
5. 過去 Simulation の読み込み

完了条件: ブラウザからパラメータを変え、文明の変化を眺められる

---

### Phase 6 — 磨き込み（余裕があれば）

1. Agent 間の短い対話ログ表示
2. 制度パラメータの効果が見えるデモシナリオを 1〜2 本用意する
3. パフォーマンス調整（LLM バッチ化、表示間引き）
4. README / デモ手順の整備

---

### Phase 7 — 認証（発展・Web 公開時）

[ADR 0004](../decisions/0004-better-auth.md) に従う。ハッカソン MVP の完了条件には含めない。

1. Better Auth + `drizzleAdapter(db, { provider: "pg" })` を導入する
2. `server/api/auth/[...all].ts` と Vue client を置く
3. `simulations.owner_id` をマイグレーションで追加し、一覧／作成を所有者でフィルタする
4. 保護ルート middleware を入れる
5. （任意）OAuth プロバイダを追加する

完了条件: ログインした利用者だけが自分の Simulation を作成・閲覧できる

---

## 実装上の制約（MVP）

| 項目 | MVP の目安 |
|------|------------|
| Agent 数 | 5〜20 |
| 行動空間 | 協力 / 争う / 移住 / 従う（＋待機） |
| 地図 | Natural Earth の平面世界地図（既定）＋地球儀タブ。衛星写真・建物 3D は作らない |
| ターン進行 | 同期 tick（全 Agent が各ターン 1 回意思決定） |
| LLM | 構造化 JSON 出力必須、失敗時フォールバックあり |
| 相図 UI | 作らない（発展機能） |
| 認証・認可 | 作らない（Phase 7 / Better Auth） |

---

## 推奨実装順序（最短パス）

```text
Phase 0 環境
  → Phase 1 ルール＋スタブ tick
  → Phase 3 API（スタブのまま）
  → Phase 5 最小 UI（スタブでも可視化）
  → Phase 2 LLM 接続
  → Phase 4 永続化
  → Phase 6 磨き込み
```

「先に画面で回す → 後から知能と保存を足す」方が、ハッカソンでは完成度を上げやすい。
