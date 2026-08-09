# 0001. ローカル実行と Supabase（Docker）

- Status: accepted
- Date: 2026-08-04

## Context

ハッカソン提出にあたり、デプロイの要否・DB・LLM の置き場を決める必要があった。  
フルクラウドはコストと障害面が重く、一方で Postgres の運用は Docker 化した方が再現しやすい。

## Decision

**基本はすべてローカルで動かす。DB だけ Supabase CLI（Docker）で起動する。**

| 層 | 実行場所 |
|----|----------|
| Frontend（Nuxt / PrimeVue / 2D マップ） | ローカル |
| Backend（FastAPI） | ローカル |
| LLM | ローカル Ollama（発表時は外部 API に切替可） |
| DB | Supabase CLI（`supabase start` → Docker 上の Postgres 等） |

方針の詳細:

* 提出用の必須デプロイはしない（録画＋ローカル実演を主とする）
* Supabase は主に DB 置き場（マネージド Auth / Realtime には依存しない）
* Postgres へのアプリ接続は **Drizzle ORM** 経由（[ADR 0003](./0003-drizzle-orm.md)）。FastAPI はシミュレーションに専念する
* LLM はプロバイダ抽象を置き、開発は Ollama、必要時のみ外部 API

## Consequences

良くなること

* ネットワークや課金に依存せずデモできる
* DB スキーマ・接続情報をチームで揃えやすい
* 後からマネージド Supabase や外部 LLM に差し替えやすい

捨てること / 注意

* 審査員が URL だけで触る提出には弱い（必要なら後からフロントだけデプロイを検討）
* Docker Desktop（または互換ランタイム）が前提
* ローカル Ollama の品質・速度はマシン依存

## 参照

* [Architecture.md](../design/Architecture.md)
* [Supabase CLI](https://supabase.com/docs/guides/local-development/cli/getting-started)
