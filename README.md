# Civilization Explorer

**AIエージェントが社会を創発し、人間がその法則を探索するプラットフォーム**

> What if...? を何万回も試す。

人間は初期条件・環境・制度だけを変え、AIエージェント同士の相互作用から文明が生まれる過程を観測する。

---

## コンセプト

社会シミュレーションの目的は「未来予測」ではない。

**どんな条件から、どんな文明が繰り返し生まれるのか**を探索するための実験環境である。

| 役割 | やること |
|------|----------|
| 人間 | パラメータを変え、結果を観測・比較する |
| AI Agent | 協力・争い・移住・服従などを自律的に意思決定する |

---

## MVP の完成ライン

1. LLMエージェントが自律的に社会を形成すること
2. その過程を Three.js で直感的に観測できること
3. 結果を構造化して蓄積し、同条件で再実行できること

「文明の相図」などの高度な比較 UI は発展機能とする。

---

## 技術スタック

| 層 | 技術 |
|----|------|
| Frontend | Nuxt 4 / Three.js / PrimeVue |
| Backend | Python / FastAPI |
| LLM | Ollama（ローカル） / OpenAI API（切替可） |
| DB | Supabase CLI（Docker 上の PostgreSQL） |

詳細な実装手順は [docs/design/Architecture.md](./docs/design/Architecture.md) を参照。

---

## 公式ドキュメント（参照）

| 技術 | ドキュメント |
|------|--------------|
| Nuxt 4 | [Introduction](https://nuxt.com/docs/4.x/getting-started/introduction) |
| Three.js | [Docs](https://threejs.org/docs/) |
| Supabase CLI | [Getting started](https://supabase.com/docs/guides/local-development/cli/getting-started) |
| FastAPI | [公式（日本語）](https://fastapi.tiangolo.com/ja/) |
| PrimeVue 3 | [Setup](https://v3.primevue.org/setup/) |

---

## ドキュメント

索引: [docs/README.md](./docs/README.md)

| 場所 | 内容 |
|------|------|
| [docs/design/](./docs/design/) | 要件・設計・ルール（FeatureSpec / Architecture / SimulationRules など） |
| [docs/updates/](./docs/updates/) | 進捗・変更記録 |
| [docs/guides/](./docs/guides/) | セットアップ・デモ手順 |
| [docs/decisions/](./docs/decisions/) | 設計判断（ADR） |

主な設計ドキュメント:

| ファイル | 内容 |
|----------|------|
| [FeatureSpec.md](./docs/design/FeatureSpec.md) | 要件定義（背景・コンセプト・MVP・非ゴール） |
| [Architecture.md](./docs/design/Architecture.md) | 技術スタック・構成・**実装手順** |
| [SimulationRules.md](./docs/design/SimulationRules.md) | 行動・ターン・状態の最小定義 |

---

## リポジトリ構成（予定）

```text
docs/
├── design/      # 仕様・設計
├── updates/     # 進捗記録
├── guides/      # 手順書
└── decisions/   # 設計判断
frontend/        # Nuxt 4 + Three.js
backend/         # FastAPI + シミュレーションエンジン
```

現状はドキュメント整備フェーズ。実装は Architecture の Phase 0 から着手する。

---

## 開発の進め方（概要）

```text
環境構築
  → ルール＋スタブ tick
  → API
  → 最小 UI（可視化）
  → LLM 接続
  → 永続化
  → 磨き込み
```

シミュレーションの行動空間（MVP）:

`wait` / `cooperate` / `conflict` / `migrate` / `obey` / `resist`

---

## ライセンス

未定
