# Architecture（技術スタック・実装手順）

## 技術スタック

### Frontend

* Nuxt 4 — [Introduction](https://nuxt.com/docs/4.x/getting-started/introduction)
* PrimeVue 3 — [Setup](https://v3.primevue.org/setup/)
* Three.js 地球儀（補助タブ）。主画面は Canvas 2D の平面世界地図。操作 UI は PrimeVue（[ADR 0006](../decisions/0006-flat-map-primary.md)）

役割

* アプリの枠（ページ・ルーティング・API 連携）: **Nuxt 4**
* 操作・一覧・数値 UI: **PrimeVue**（フォーム、表、タイムライン）
* 状況パネル: 地域観測（緊張・繁栄・不満・結束・軌道）のカスタム digest UI
* 空間可視化: **平面世界地図が既定**（領域・衝突・所属色）

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

* ターン末の **地域観測**（緊張・繁栄・不満・結束・台頭人物・軌道）
* 次ターンの **集団方針**（推奨行動・強度・理由）
* 列あたりサンプル実行者への方針適用

`LLM_PROVIDER=stub` 時はヒューリスティックのみ。Ollama / OpenAI は `.env` で切替。

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
│   └── routes.py       # REST API（インメモリ store）
├── simulation/
│   ├── engine.py       # ターン進行・ルール解決
│   ├── llm.py          # LLM 地域観測・集団方針
│   ├── models.py       # Pydantic ドメインモデル
│   ├── continents.py   # 大陸・サブ地域プリセット
│   └── ...
└── config.py           # .env 設定
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
**現状（2026-08-28）**: Phase 0〜1、3、5 の大半と Phase 2（地域観測 + 集団方針）が完了。Phase 4（Drizzle 永続化）と Phase 7（認証）は未着手。

### Phase 0 — リポジトリ・環境 ✅

1. `frontend/`（Nuxt 4）と `backend/`（FastAPI）を初期化する
2. Supabase CLI でローカル DB を起動する（`supabase init` → `supabase start`）— 永続化 Phase 4 まで任意
3. Ollama を起動し、使用モデルを決める（例: `llama3.2:1b`）
4. `.env` で LLM プロバイダ切替（`stub` / `ollama` / `openai`）を可能にする

完了条件: `frontend` と `backend` がそれぞれ起動し、API `/health` が応答する

---

### Phase 1 — コア状態モデル（ルール実装） ✅

[SimulationRules.md](./SimulationRules.md) に従い、コード上の状態を定義する。

1. `World` / `Agent` / `Relationship` / `Institution` のデータモデルを実装する
2. ターン進行の骨格 `tick()` を実装する
3. 行動の解決ロジック（協力・争う・移住・従う・抵抗）をルールベースで実装する
4. 出生・加齢・死亡・集落・災害・体制遷移を実装する

完了条件: 固定シードで数ターン進められ、状態変化と Event がログに残る

---

### Phase 2 — LLM 接続 ✅（集団方針モデル）

1. `llm.py` にプロバイダ抽象（Ollama / OpenAI / stub）を実装する
2. ターン末に地域ごと観測 → 次ターン方針（`RegionPolicy`）を生成する
3. 列あたりサンプル実行者に方針を適用する（`decide_actions`）
4. 失敗時フォールバック（パース失敗・タイムアウト時はヒューリスティック）を入れる
5. タイムアウト・サンプル数・並列度を `.env` で制限する

完了条件: `LLM_PROVIDER=ollama|openai` で地域観測が UI に反映され、失敗しても tick が止まらない

残タスク: デモ用プロンプト調整、録画バックアップ、実測記録

---

### Phase 3 — API ✅

1. `POST /simulations` — 世界パラメータから Simulation 作成
2. `POST /simulations/{id}/start` — 実行開始
3. `POST /simulations/{id}/tick` — 1ターン進行（またはバッチ）
4. `GET /simulations/{id}` — 現在状態取得
5. `GET /simulations/{id}/events` — Event / History 取得
6. `GET /simulations/{id}/replay` — 同条件再実行用パラメータ
7. `GET /health` — LLM プロバイダ状態

完了条件: API だけでシミュレーションを作成・進行・観測できる

---

### Phase 4 — 永続化（Drizzle） ⬜ 未着手

1. `frontend/server/db/` に Drizzle schema を定義し、`drizzle-kit generate` / `migrate` で適用する
2. Nuxt server API（または server util）から Postgres へ接続する（postgres.js 等）
3. ターン終了時に Agent / Relationship / Event / History を保存する（FastAPI の応答を受けて Nitro 側で書く）
4. 同条件再実行用に初期パラメータ（seed 含む）を保存する
5. 過去 Simulation の一覧・詳細取得を Nuxt server 経由で追加する

完了条件: 再起動後も結果を読み出せ、同条件で再実行できる

---

### Phase 5 — Frontend（観測 UI） ✅（MVP 範囲）

1. パラメータ入力（中央モーダル: **対照実験は2ステップ**、カスタムは地理・社会・人口）
2. シミュレーション開始 / 1ターン進行 / 自動再生
3. **平面世界地図**で Agent・集団領域・争いを可視化
4. **状況パネル**（digest）で地域観測・件数・出来事要約
5. **出来事パネル**で Event タイムライン
6. 作成中の準備オーバーレイ、ヘッダー見出し・世界の便り

完了条件: ブラウザからパラメータを変え、文明の変化を眺められる

未実装: 過去 Simulation の一覧 UI（API はある）、Agent クリック連動

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
| Agent 数 | 列あたり 1000〜10000（LLM は地域観測 + 列あたり最大 12 人のサンプル実行） |
| 行動空間 | 協力 / 争う / 移住 / 従う / 抵抗（＋待機） |
| 地図 | Natural Earth の平面世界地図（既定）。地球儀コンポーネントは残るが UI からは非表示 |
| ターン進行 | 同期 tick。暦上限は西暦 2500 |
| LLM | 地域観測 + 集団方針。失敗時ヒューリスティック。`stub` で完走可 |
| 相図 UI | 作らない（発展機能） |
| 認証・認可 | 作らない（Phase 7 / Better Auth） |

---

## 推奨実装順序（最短パス）

```text
Phase 0 環境 ✅
  → Phase 1 ルール＋tick ✅
  → Phase 3 API ✅
  → Phase 5 観測 UI ✅
  → Phase 2 LLM 地域観測・集団方針 ✅
  → Phase 4 永続化 ⬜
  → Phase 6 磨き込み（デモシナリオ・録画）進行中
```

「先に画面で回す → 後から保存を足す」方針で、ハッカソン向けの観測ループは成立している。
