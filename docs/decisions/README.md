# decisions/

設計判断（ADR: Architecture Decision Record）の記録。

迷いどころ・トレードオフを短く残し、後から「なぜそうしたか」を追えるようにする。

## 記録一覧

| ファイル | 内容 | Status |
|----------|------|--------|
| [0001-local-runtime-and-supabase.md](./0001-local-runtime-and-supabase.md) | ローカル実行＋DB は Supabase（Docker） | accepted |
| [0002-2d-visualization.md](./0002-2d-visualization.md) | 可視化は 2D 中心（地球・本格 3D は不要） | superseded |
| [0005-threejs-world-globe.md](./0005-threejs-world-globe.md) | 可視化は Three.js の世界地図（地球儀） | accepted |
| [0003-drizzle-orm.md](./0003-drizzle-orm.md) | DB ORM は Drizzle（永続化は Nuxt / TypeScript） | accepted |
| [0004-better-auth.md](./0004-better-auth.md) | 認証は Better Auth + Drizzle（将来）。MVP は未実装 | accepted |

## テンプレート

ファイル名: `NNNN-short-title.md`（例: `0001-llm-provider-abstraction.md`）

```markdown
# NNNN. タイトル

- Status: proposed | accepted | superseded
- Date: YYYY-MM-DD

## Context

何が問題か。

## Decision

何を選んだか。

## Consequences

良くなること / 捨てること / 後続タスク。
```
