# 提出物チェックリスト

ハッカソン提出で揃えるもの。詳細は各ファイルへ。

| 提出物 | 場所 | 状態 |
|--------|------|------|
| GitHub リポジトリ | https://github.com/tsuide-takeda/civ-explorer | 公開前に下の確認を通す |
| README | [../../README.md](../../README.md) | 目的・環境・使い方をルートに記載 |
| プレゼン・台本 | [demo-v3.md](./demo-v3.md) | 設計・スライド原稿・当日操作（PPT 未作成なら § スライド原稿を転記） |
| 実行結果のまとめ | [RESULTS.md](./RESULTS.md) | LLM 接続済み。数値はデモ後に埋める |

設計の正は [../design/FeatureSpec.md](../design/FeatureSpec.md)。テーマ原案は [../design/memo.md](../design/memo.md)。

---

## GitHub リポジトリ

提出前:

- [ ] `origin` が上記 URL で、審査が clone できる（private なら招待）
- [ ] `.env` / API キーがコミットされていない（`.gitignore`）
- [ ] ルート README から起動手順に辿れる
- [ ] デフォルトブランチ `main` に動くコードがある
- [ ] ライセンスが未定のままでよいか確認（必要なら追記）

clone:

```bash
git clone https://github.com/tsuide-takeda/civ-explorer.git
cd civ-explorer
```

---

## コード側の現状（提出文面と矛盾させない）

- LLM は **地域観測 + 集団方針**（`LLM_PROVIDER=stub|ollama|openai`）。全 Agent 個別 LLM ではない
- 永続化（Drizzle / Postgres）は未実装。再実行は `GET /simulations/{id}/replay` またはパラメータ再入力
- 地球儀タブは非表示。観測は平面世界地図 + 状況パネル
- デモ用シナリオの実測記録・録画バックアップは [RESULTS.md](./RESULTS.md) で未記入

発表では「いま動く範囲」と「まだないこと（永続化・全員 LLM）」を分けて話す。
