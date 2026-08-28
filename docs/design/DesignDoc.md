# Design Doc

UI・API・データモデルの詳細設計と、**各技術が担う機能要件**の対応表。

> ステータス: 実装同期版（2026-08-28）

関連

* [FeatureSpec.md](./FeatureSpec.md) — 何を作るか
* [Architecture.md](./Architecture.md) — 技術と実装順
* [SimulationRules.md](./SimulationRules.md) — シミュレーション規則
* [ADR 0001](../decisions/0001-local-runtime-and-supabase.md) — ローカル実行方針
* [ADR 0005](../decisions/0005-threejs-world-globe.md) — 地球儀テクスチャ（写真地球は使わない）
* [ADR 0006](../decisions/0006-flat-map-primary.md) — 観測の主画面は平面世界地図
* [ADR 0003](../decisions/0003-drizzle-orm.md) — Drizzle ORM 方針
* [ADR 0004](../decisions/0004-better-auth.md) — Better Auth（将来）方針

---

## 1. 画面の役割分担（まずここ）

観測 UI は **2 層** に分ける（[ADR 0006](../decisions/0006-flat-map-primary.md)）。

| 層 | 技術 | 担当 |
|----|------|------|
| 操作・一覧・数値 UI | **PrimeVue**（Nuxt 上） | 初期条件モーダル（3ステップ）、進行ボタン、ヘッダー件数、出来事、状況パネル |
| 世界の空間表現 | **Canvas 2D 平面地図（既定）** | Agent・集団領域・争い・世界の便り |

PrimeVue は「文明の世界そのもの」を描かない。  
**人間がパラメータを変え、結果を読むための UI 部品ライブラリ**である。

```text
┌─────────────────────────────────────────────┐
│  Nuxt ページ                                 │
│  ┌───────────────────────────────────────┐  │
│  │ 平面世界地図（既定） / 地球儀タブ      │  │
│  │ ・領域（凸包）・所属色・争いの破線     │  │
│  └───────────────────────────────────────┘  │
│  初期条件＝中央モーダル / 状況＝地図左 digest / 出来事＝モーダル │
│           │  HTTP                           │
│           ├──────────────────────┐          │
│           ▼                      ▼          │
│        FastAPI              Nuxt Nitro      │
│     （sim / LLM）           ＋ Drizzle      │
│           │                      │          │
│           └──────┐               │          │
│                  ▼               ▼          │
│            Ollama / 外部    Supabase        │
│               LLM           (Postgres)      │
└─────────────────────────────────────────────┘
```

---

## 2. 技術別: 使い方と機能要件

### 2.1 Nuxt 4（フロントの土台）

**何をするか**

Vue ベースの Web アプリフレームワーク。ページ構成・ルーティング・状態・API 呼び出しをまとめる。PrimeVue と 2D マップを載せる「枠」になる。

**公式:** [Nuxt Introduction](https://nuxt.com/docs/4.x/getting-started/introduction)

**このプロジェクトでの使い方**

| 使い方 | 内容 |
|--------|------|
| ページ | `/` 観測メイン、`/simulations` 過去一覧 など file-based routing |
| レイアウト | 地図全幅。初期条件は中央モーダル、状況は地図左 digest、出来事はモーダル |
| データ取得 | FastAPI への `fetch` / `$fetch`（作成・tick・状態）。永続化済み一覧等は Nitro＋Drizzle |
| 永続化 | `server/db` の Drizzle client で Postgres を読み書き（[ADR 0003](../decisions/0003-drizzle-orm.md)） |
| リアルタイム | SSE（またはポーリング）でターン更新を受け取り、画面と 2D マップを更新 |
| 設定 | `.env` で API ベース URL・DB 接続文字列を切替 |

**実現する機能要件**

* [x] ブラウザからシミュレーションを作成・1 ターン進行（+10年 / +50年）・自動再生できる
* [x] 現在ターンの状態（Agent・地域観測・件数）を表示できる
* [x] Event タイムラインを時系列で読める
* [ ] 過去 Simulation を一覧し、読み込んで再観測できる（API のみ。UI 未実装）
* [x] 2D マップと操作 UI を同一画面に共存させられる

**やらないこと（MVP）**

* 認証付きマルチユーザー（将来は Better Auth。MVP では作らない）
* 高度なダッシュボード／相図 UI

---

### 2.2 PrimeVue 3（操作・情報 UI）

**何をするか**

Vue 向けの **UI コンポーネントライブラリ**（ボタン、入力、表、ダイアログ、タブなど）。  
自前で CSS を組まずに、実験操作に必要な画面部品を早く揃える。

**公式:** [PrimeVue Setup](https://v3.primevue.org/setup/)

**このプロジェクトでの使い方（コンポーネント対応）**

| 画面要素 | 想定コンポーネント例 | 機能 |
|----------|----------------------|------|
| 世界パラメータ入力 | `DataTable`, `Dropdown`, `LevelRating`, `InputNumber` | 3ステップ: 地理・社会・創発の偏り |
| 実行コントロール | `Button`, `Tag` | Tick / Tick×5 / 自動再生 |
| 状況パネル | `Tag`, カスタム digest | 地域観測・件数・因果要約 |
| Event タイムライン | カスタムリスト | ターンごとの Event。LLM 由来にはバッジ |
| 通知 | ヘッダー見出し | 大きな衝撃（災害・体制遷移など）。トーストは使わない |

**実現する機能要件**

* [x] 初期条件（人口・教育・税率・制度・宗教・対外開放・列ごとの創発パラメータ）をフォームで設定できる
* [x] シミュレーション操作（Tick・自動再生）が一目で分かる
* [x] 状況パネルで地域ごとの観測（緊張・繁栄・不満・結束・軌道）を読める
* [x] Event をターン順にスクロールできる
* [ ] Agent を選ぶと属性の要約をサイド／ダイアログで見られる

**やらないこと**

* 世界マップの描画（2D マップ層の領域）
* カスタムデザインシステムの大規模構築（PrimeVue 既定＋最小テーマでよい）

---

### 2.3 平面世界地図（空間可視化）

**何をするか**

文明の配置を **Natural Earth の平面世界地図**で表現する（[ADR 0006](../decisions/0006-flat-map-primary.md)）。実装の既定は Canvas 2D（`WorldMap2D.vue`）。`WorldGlobe.vue` は残るが UI からは非表示。

**背景方針**

| 使う | 使わない |
|------|----------|
| Natural Earth のベクトル陸地、標高の濃淡、主要河川・湖・山脈 | 衛星写真・地球の写真テクスチャ |
| 集団色（HEX）、凸包、人数ラベル、争いの破線 | 建物モデル・国旗 |

**このプロジェクトでの使い方**

| 対象 | MVP 表現 | 更新トリガ |
|------|----------|------------|
| Agent | 円（塗り = 所属集団） | 各 tick 後の状態 |
| 位置 | 舞台枠内の緯度経度へ投影 | 移住行動の結果 |
| 集落 | メンバー位置の凸包＋人数ラベル（集団／都市／国家） | 所属変化 |
| 争い | 集団中心同士の破線 | 当該ターンの `conflict` |
| 操作 | パン / ズーム / 全体表示（南極側下 1 割は既定から除外） | ユーザー操作 |

**実現する機能要件**

* [x] Agent を平面上で色と位置で識別できる
* [x] tick ごとに位置・所属色が更新され、文明の変化が目で追える
* [x] 集落のまとまりが領域として分かる
* [x] パン / ズームで観測範囲を変えられる
* [ ] Agent クリックで PrimeVue 側の詳細パネルと連動できる（任意だが推奨）

**やらないこと（MVP）**

* 地球背景・3D カメラ・ライティング演出
* リアルな地形・建物・シネマティック演出
* 数百 Agent の描画最適化

---
### 2.4 FastAPI（バックエンド API・シミュレーション司令塔）

**何をするか**

Python の API フレームワーク。シミュレーションエンジン・LLM 呼び出しを HTTP でフロントに公開する。  
**Postgres への永続化は持たない**（Drizzle 側。 [ADR 0003](../decisions/0003-drizzle-orm.md)）。

**公式:** [FastAPI（日本語）](https://fastapi.tiangolo.com/ja/)

**このプロジェクトでの使い方**

| 領域 | 内容 |
|------|------|
| シミュレーション制御 | 作成・開始・tick・状態取得 |
| ルール層 | [SimulationRules.md](./SimulationRules.md) に沿った状態遷移・行動解決 |
| LLM 層 | プロンプト送信・JSON パース・フォールバック |
| 永続化 | しない（応答 JSON を Nuxt / Drizzle が保存） |
| 配信 | REST 必須、SSE/WebSocket は任意（ターン更新プッシュ） |

**MVP API（機能要件に直結）**

| メソッド | パス | 機能要件 |
|----------|------|----------|
| `POST` | `/simulations` | 世界パラメータから Simulation を作成できる |
| `POST` | `/simulations/{id}/start` | 実行を開始できる |
| `POST` | `/simulations/{id}/tick` | 1 ターン（または N ターン）進められる |
| `POST` | `/simulations/{id}/pause` | 一時停止できる |
| `GET` | `/simulations/{id}` | 現在状態（World / Agents / metrics）を取得できる |
| `GET` | `/simulations/{id}/events` | Event / History を取得できる |
| `GET` | `/simulations` | 過去一覧を取得できる |
| `GET` | `/simulations/{id}/replay` | 同条件再実行用の初期パラメータを取得できる |

| `GET` | `/health` | LLM プロバイダ状態を返す |

**実現する機能要件**

* [x] LLM なし（`stub`）でも tick が完走する
* [x] LLM 成功時は地域観測・集団方針が状態に反映される
* [x] LLM 失敗時もシミュレーションが止まらない（フォールバック）
* [x] OpenAPI（`/docs`）で API を確認・試せる
* [x] フロントと CORS でローカル連携できる

**やらないこと（MVP）**

* 複雑な認証認可
* マイクロサービス分割

---

### 2.5 LLM（Ollama / OpenAI / stub）

**何をするか**

ターン末の **地域観測** と次ターンの **集団方針** を担う。数値解決・勝敗・資源移動はルール層（FastAPI 側）が行う。

**このプロジェクトでの使い方**

| 項目 | 内容 |
|------|------|
| 入力 | 地域 factsheet（人口・行動集計・衝撃・制度など） |
| 出力 | `RegionReading`（緊張・繁栄・不満・結束・台頭人物・軌道・要約）+ `RegionPolicy`（推奨行動・強度・理由） |
| 実行 | 列あたり最大 `LLM_GROUP_SAMPLE_PER_REGION` 人のサンプル実行者に方針を適用 |
| 開発 | `LLM_PROVIDER=stub`（既定）または Ollama（ローカル） |
| 発表・品質 | 外部 API（OpenAI）に `.env` で切替 |
| 制約 | タイムアウト・並列度あり。失敗時ヒューリスティック必須 |

**実現する機能要件**

* [x] ターン末に地域ごと観測し、次ターン方針を返す
* [x] 出力がスキーマ不正でもルール層が安全にフォールバックできる
* [x] 同一 seed＋`stub` では完全再現できる
* [x] プロバイダ切替（`stub` / Ollama / OpenAI）がコード変更なし（設定のみ）でできる
* [x] 観測要約・方針理由を Event / 状況パネルに残せる

**やらないこと**

* LLM に物理法則や資源計算そのものを任せる
* 数百 Agent の毎ターンフル推論

---

### 2.6 Supabase CLI + PostgreSQL + Drizzle（構造化・蓄積）

**何をするか**

文明シミュレーションの結果を **構造化して保存**する置き場。  
Supabase CLI はローカル Postgres（＋ Studio）の起動手段。**ORM は Drizzle** でスキーマ・クエリ・マイグレーションを行う。

**公式**

* [Supabase CLI Getting started](https://supabase.com/docs/guides/local-development/cli/getting-started)
* [Drizzle ORM](https://orm.drizzle.team/)
* [Drizzle × Supabase](https://orm.drizzle.team/docs/connect-supabase)

**このプロジェクトでの使い方**

| 項目 | 内容 |
|------|------|
| DB 起動 | `supabase init` / `supabase start` |
| ORM | `drizzle-orm`（テーブル定義・select/insert/update） |
| マイグレーション | `drizzle-kit`（`drizzle.config.ts` → generate / migrate） |
| 接続 | Nuxt Nitro の `server/db` から接続文字列で接続 |
| 確認 | Supabase Studio（例: `http://127.0.0.1:54323`）または `drizzle-kit studio` |

**最低限エンティティと機能要件**

| エンティティ | 保存する理由（機能要件） |
|--------------|--------------------------|
| Simulation | 実験単位。一覧・再実行の起点 |
| World | 初期条件・seed・制度スナップショット |
| Agent | 各ターン or 最終の状態・Personality / Goal |
| Institution | 制度パラメータの履歴 |
| Event | 「何が起きたか」のタイムライン材料 |
| History | ターン要約・メトリクス推移 |
| Relationship | 信頼・敵対など関係の推移 |

**実現する機能要件**

* [ ] Drizzle schema で上記エンティティを型付き定義できる
* [ ] `drizzle-kit` でマイグレーションを生成・適用できる
* [ ] ターン終了時に状態・Event を永続化できる
* [ ] プロセス再起動後も過去 Simulation を読み出せる
* [ ] 同条件（seed + 初期パラメータ）で再実行できる
* [ ] メトリクス推移を History から復元できる

**やらないこと（MVP）**

* SQLAlchemy など Python ORM との二重管理
* Supabase Auth / Realtime への全面依存（認証は [ADR 0004](../decisions/0004-better-auth.md) の Better Auth）
* クラウド必須デプロイ

---

### 2.7 Better Auth（将来・Web 公開時）

**何をするか**

Web 公開後に「誰の実験か」を分離するための認証・セッション。DB は既存の Drizzle 接続を共有する。

**公式:** [Better Auth](https://www.better-auth.com/) / [Nuxt 連携](https://www.better-auth.com/docs/integrations/nuxt)

**このプロジェクトでの使い方（導入時）**

| 項目 | 内容 |
|------|------|
| アダプタ | `drizzleAdapter(db, { provider: "pg" })` |
| ハンドラ | `server/api/auth/[...all].ts` |
| クライアント | `better-auth/vue` |
| 所有 | `simulations.owner_id`（導入時マイグレーションで追加） |
| ゲート | Nitro middleware が session を確認し、許可操作だけ FastAPI へ |
| 初期スコープ | 個人所有のみ（組織・ロールは発展） |

**実現する機能要件（将来）**

* [ ] ログイン／ログアウトできる
* [ ] 自分の Simulation だけ一覧・作成・読込できる
* [ ] 未ログインでは保護ルートに入れない

**やらないこと（MVP）**

* ログイン UI、OAuth、保護 middleware
* RLS 必須化
* FastAPI への JWT 転送（必要なら別 ADR）
* Auth.js / Supabase Auth の採用

詳細は [ADR 0004](../decisions/0004-better-auth.md)。

---

## 3. 画面構成（MVP）

### 3.1 メイン観測画面 `/`

1. **地図ビューポート**  
   平面世界地図。パン・ズーム・世界の便り（衝撃通知）
2. **コントロール（ヘッダー）**  
   初期条件 / 出来事 / 状況 / Tick / 自動再生。LLM 状態表示
3. **初期条件（中央モーダル、3ステップ）**  
   STEP 1: 地理・自然（サブ地域・地形・気候）  
   STEP 2: 開始年と社会（制度・税率・教育・宗教・対外開放・価値観）  
   STEP 3: 創発の偏り（特異の出やすさ・施し・列人口 1000〜10000）
4. **ヘッダー件数**  
   西暦・時代、集団／都市／国家／未所属、今ターンの争い・共同・出生・死亡・特異
5. **状況パネル（地図左、digest）**  
   地域ごとの緊張・繁栄・不満・結束・台頭人物・軌道・因果要約。観測ソース（LLM / ヒューリスティック）表示
6. **出来事（モーダル）**  
   集団セット単位の Event。LLM 由来にはバッジと理由文

### 3.2 一覧画面 `/simulations`（Phase 4 以降）

* 過去 Simulation の表
* 読込 → メイン画面で再観測 / 同条件再実行

---

## 4. 機能要件マトリクス（技術 × MVP）

| MVP 機能 | Nuxt | PrimeVue | 2D マップ | FastAPI | LLM | Drizzle / Postgres | Better Auth |
|----------|:----:|:--------:|:---------:|:-------:|:---:|:------------------:|:-----------:|
| 初期条件の設定 | ○ | ○ | | ○ | | ○ | |
| シミュレーション進行 | ○ | ○ | | ○ | ○ | | |
| Agent 自律意思決定 | | | | ○ | ○ | | |
| 平面で文明を眺める | ○ | | ○ | | | | |
| Event / メトリクス観測 | ○ | ○ | | ○ | | ○ | |
| 構造化蓄積・再実行 | ○ | ○ | | | | ○ | |
| ログイン・所有分離（将来） | ○ | ○ | | | | ○ | ○ |

○ = 主担当または必須の協力者。Better Auth 列は MVP では未実装（Phase 7）。

---

## 5. API / データ（次に埋める詳細）

実装フェーズで以下を追記する。

* 各エンドポイントのリクエスト・レスポンス JSON 例
* Drizzle schema（カラム型・FK）とマイグレーション方針
* 2D マップの座標・描画レイヤ規則
* PrimeVue テーマ設定（Nuxt モジュール）

暫定の API 一覧は [Architecture.md](./Architecture.md) Phase 3、状態規則は [SimulationRules.md](./SimulationRules.md) を正とする。
