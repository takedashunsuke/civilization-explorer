# 提出物チェックリスト

ハッカソン提出で揃えるもの。詳細は各ファイルへ。

| 提出物 | 場所 | 状態 |
|--------|------|------|
| GitHub リポジトリ | https://github.com/tsuide-takeda/civ-explorer | 公開前に下の確認を通す |
| README | [../../README.md](../../README.md) | 目的・環境・使い方をルートに記載 |
| プレゼン資料 | [slides.md](./slides.md) | 原稿。PPT / Google スライドは未作成ならこの md を転記 |
| 実行結果のまとめ | [RESULTS.md](./RESULTS.md) | 現状はヒューリスティック実行。数値はデモ後に埋める |
| 発表台本 | [demo-script.md](./demo-script.md) | 5〜7 分想定 |

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

## まだコード側で足りないこと（提出文面と矛盾させない）

- LLM 意思決定は未接続（`backend/simulation/llm.py` はプロバイダ説明のみ。行動はヒューリスティック）
- 永続化（Drizzle / Postgres）は未実装。再実行は seed と初期条件の再入力
- 地球儀タブは非表示。観測は平面世界地図

発表では「いま動く範囲」と「次の1週間で足す LLM」を分けて話す。
