# 0003. DB ORM は Drizzle

- Status: accepted
- Date: 2026-08-09

## Context

永続化の ORM として SQLAlchemy（Python）が仮置きされていたが、次を満たす TypeScript ORM が必要になった。

* Nuxt 4 と同じ言語・型でスキーマを定義したい
* Supabase（PostgreSQL）との接続・マイグレーションが素直
* SQL に近いクエリ API で、シミュレーション結果の蓄積・再実行を扱いやすい

候補の Drizzle ORM（https://orm.drizzle.team/）は TypeScript 向けであり、Python/FastAPI プロセス内では使えない。

## Decision

**DB のスキーマ定義・マイグレーション・クエリは Drizzle ORM（＋ drizzle-kit）で行う。**

| 項目 | 方針 |
|------|------|
| ORM | [Drizzle ORM](https://orm.drizzle.team/) |
| マイグレーション | drizzle-kit（`generate` / `migrate`） |
| 接続先 | Supabase CLI のローカル PostgreSQL（[ADR 0001](./0001-local-runtime-and-supabase.md)） |
| 配置 | Nuxt 側（`frontend/server/db/` ＋ `drizzle.config.ts`） |
| FastAPI の役割 | シミュレーション実行・LLM。**Postgres への直接接続は持たない** |

データ経路（MVP）:

1. Nuxt が FastAPI に作成 / tick を依頼する
2. 返ってきた状態・Event を **Nuxt Nitro（Drizzle）** が Postgres に保存する
3. 一覧・再読込・再実行用パラメータも Drizzle 経由で読む

[ADR 0001](./0001-local-runtime-and-supabase.md) の「アプリは FastAPI 経由で Postgres に接続する」は、本決定により **「永続化は Drizzle 経由」** に更新する（Supabase を DB 置き場にする方針は維持）。

## Consequences

良くなること

* スキーマとアプリ型が TypeScript で一貫する
* マイグレーションと Studio（drizzle-kit studio）でスキーマ運用しやすい
* FastAPI はルール／LLM に集中できる

捨てること / 注意

* Python 側で ORM を持たない（SQLAlchemy は採用しない）
* tick 結果の保存はフロント／Nitro 側の責務になる（API 設計で受け渡しを明示する）
* 将来 FastAPI からも DB が必要になった場合は、共有スキーマ方針を再検討する

## 参照

* [Architecture.md](../design/Architecture.md)
* [DesignDoc.md](../design/DesignDoc.md)
* [Drizzle ORM](https://orm.drizzle.team/)
* [Drizzle × Supabase](https://orm.drizzle.team/docs/connect-supabase)
