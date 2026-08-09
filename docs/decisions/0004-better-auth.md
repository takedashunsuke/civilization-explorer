# 0004. 認証は Better Auth + Drizzle（将来）

- Status: accepted
- Date: 2026-08-09

## Context

ハッカソン MVP はローカル単一利用者で十分だが、将来 Web 公開すると「自分の実験だけ見える」「複数人が触れる」操作がプロダクトとして面白くなる。  
認証・認可の候補として Supabase Auth / Auth.js / Better Auth を検討した。

制約・前提:

* 永続化はすでに Drizzle（[ADR 0003](./0003-drizzle-orm.md)）
* Frontend は Nuxt 4（Nitro）
* Supabase は主にローカル Postgres 置き場（[ADR 0001](./0001-local-runtime-and-supabase.md)）。Auth への全面依存は避けたい
* MVP では認証付きマルチユーザーを実装しない（現行 DesignDoc の非ゴール）

## Decision

**将来の認証・認可は Better Auth + Drizzle（`drizzleAdapter`）とする。ハッカソン MVP では実装しない。**

| 項目 | 方針 |
|------|------|
| ライブラリ | [Better Auth](https://www.better-auth.com/) |
| セッション／ユーザ表 | Better Auth コア schema（Drizzle adapter） |
| アプリ所有 | `simulations.owner_id`（公開導入時に追加。MVP スキーマには持たない＝後から列追加） |
| 初期スコープ | **個人所有のみ**（組織・ロールは発展。Better Auth プラグイン候補） |
| ゲート | Nuxt Nitro が session を検証し、許可した操作だけ FastAPI に渡す |
| MVP | ログイン UI・OAuth・保護 middleware・RLS 必須化は行わない |

採用しないもの:

* **Supabase Auth** — 速いが Auth と Drizzle の所有が分かれやすく、ロックイン感が強い
* **Auth.js** — 拡張のイメージはあるが Nuxt 本線が弱く、新規なら Better Auth の方が Drizzle／Nuxt と相性が良い

## Consequences

良くなること

* Web 公開時にプロバイダ追加・個人所有・（後から）組織機能へ伸ばしやすい
* 既存の Drizzle スキーマ運用に認証テーブルを載せられる
* FastAPI は引き続き DB／認証を持たずシミュレーションに集中できる

捨てること / 注意

* MVP 期間中は認証なし（ローカルデモ前提）
* FastAPI への JWT 転送が必要になったら別 ADR
* `owner_id` は公開導入時のマイグレーションで追加する（MVP で先行カラムは作らない）

## 将来の着手順（実装時）

1. Better Auth + `drizzleAdapter(db, { provider: "pg" })`
2. `server/api/auth/[...all].ts` と Vue client
3. `simulations.owner_id` と一覧／作成の所有者フィルタ
4. 保護ルート middleware
5. （任意）OAuth プロバイダ追加

## 参照

* [Architecture.md](../design/Architecture.md)
* [DesignDoc.md](../design/DesignDoc.md)
* [Better Auth](https://www.better-auth.com/)
* [Better Auth × Nuxt](https://www.better-auth.com/docs/integrations/nuxt)
* [ADR 0003](./0003-drizzle-orm.md)
