# 提出物チェックリスト

ハッカソン提出で揃えるもの。**審査員向けの正はリポジトリルート**、開発・発表原稿は `docs/hackathon/`。

## ルート（提出用）

| 提出物 | 場所 | 状態 |
|--------|------|------|
| GitHub リポジトリ | https://github.com/takedashunsuke/civilization-explorer | 公開済み |
| README | [../../README.md](../../README.md) | 環境構築・起動 |
| デモ再生手順 | [../../DEMO.md](../../DEMO.md) | CLI またはブラウザ |
| 実行スクリプト | [../../scripts/run-experiment-batch.sh](../../scripts/run-experiment-batch.sh) | **10 run 一括**（AD 1750→1950） |
| 単発 CLI | [../../scripts/run-experiment.sh](../../scripts/run-experiment.sh) | カスタム条件 |
| 生ログ | [../../result/raw/](../../result/raw/) | `run-NNN/` に `.json` + `.txt` |
| LLM 解析 | [../../analysis/](../../analysis/) | `prompt.md` + `output/run-NNN/` |
| 解析サマリー | [../../analysis/summary.md](../../analysis/summary.md) | 索引 → `output/run-NNN/summary.md` |

## docs/hackathon（開発・発表用）

| ファイル | 内容 |
|----------|------|
| [demo-v3.md](./demo-v3.md) | 設計・発表当日の補足 |
| [slides.md](./slides.md) | スライド原稿 |
| [RESULTS.md](./RESULTS.md) | → ルート `analysis/summary.md` への索引 |
| [checklist.md](./checklist.md) | 障害時・事前確認 |
| [post-award.md](./post-award.md) | 入賞講評・次の実装方針 |

設計の正: [../design/FeatureSpec.md](../design/FeatureSpec.md)

---

## GitHub リポジトリ

提出前:

- [ ] `origin` が上記 URL で、審査が clone できる（private なら招待）
- [ ] `.env` / API キーがコミットされていない（`.gitignore`）
- [ ] ルート README → DEMO → result / analysis に辿れる
- [ ] `./scripts/run-experiment-batch.sh` で実証 10 run 完了（または manifest で pending 理由を明記）
- [ ] 各 `result/raw/run-NNN/` に 4 本の `.json` + `.txt`
- [ ] `analysis/output/run-NNN/summary.md` に定量表を記入（索引は `analysis/summary.md`）
- [ ] デフォルトブランチ `main` に動くコードがある

clone:

```bash
git clone https://github.com/takedashunsuke/civilization-explorer.git
cd civilization-explorer
./scripts/setup.sh
```

---

## コード側の現状（提出文面と矛盾させない）

- LLM は **地域観測 + 集団方針**（`LLM_PROVIDER=stub|ollama|openai`）
- 永続化は未実装。再実行はパラメータ再入力または `GET /replay`
- 地球儀タブは非表示。観測は平面世界地図 + 状況パネル
- 4 環境ラベル: **豊か / 乏しい / 災害多 / 標準**（旧称 Peace/Famine 等ではない）

発表では「いま動く範囲」と「まだないこと」を分けて話す。
