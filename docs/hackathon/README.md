# hackathon/

ハッカソン発表・デモ向けの**開発用**資料。  
**審査員向け提出物はリポジトリルート**（[README.md](../../README.md)、[DEMO.md](../../DEMO.md)、[result/](../../result/)、[analysis/](../../analysis/)）。

## 提出物（ルート）

| 場所 | 内容 |
|------|------|
| [../../README.md](../../README.md) | 環境構築・起動 |
| [../../DEMO.md](../../DEMO.md) | 再生手順・実証プロトコル（AD 1750→1950） |
| [../../scripts/run-experiment-batch.sh](../../scripts/run-experiment-batch.sh) | 10 run 一括 |
| [../../result/](../../result/) | 生ログ |
| [../../analysis/](../../analysis/) | LLM 解析・サマリー |

## このフォルダ（開発・発表）

| ファイル | 書くこと |
|----------|----------|
| [demo-v3.md](./demo-v3.md) | 設計・発表当日の操作 |
| [slides.md](./slides.md) | **スライド原稿のみ**（PPT 転記用） |
| [overview.md](./overview.md) | 30 秒ピッチ |
| [checklist.md](./checklist.md) | 起動・事前確認・障害時 |
| [RESULTS.md](./RESULTS.md) | → ルート [analysis/summary.md](../../analysis/summary.md) への索引 |
| [gap.md](./gap.md) | 方針と実装の AS-IS / ギャップ / TODO |
| [world-model.md](./world-model.md) | **固定・変動・創発**の四層モデル（概念の正） |
| [review.md](./review.md) | テーマ根拠・経緯 |
| [post-award.md](./post-award.md) | **入賞講評・ネクストアクション・実装方針** |
| [faq.md](./faq.md) | 想定 Q&A |
| [submission.md](./submission.md) | 提出物一覧（ルート + docs） |

## 読む順

1. [overview.md](./overview.md) — 30 秒で全体像
2. [demo-v3.md](./demo-v3.md) — 設計 + 発表当日 / [slides.md](./slides.md) — 投影用
3. [checklist.md](./checklist.md) — 起動・障害時
4. [analysis/summary.md](../../analysis/summary.md) — デモ後に記入（生ログは [result/](../../result/)）

実装・セットアップ: [../guides/setup.md](../guides/setup.md)  
プロダクト要件: [../design/FeatureSpec.md](../design/FeatureSpec.md)  
設計判断: [../decisions/](../decisions/)

## 関連方針（短く）

* テーマ: AI 文明を実験場にし、人間社会の問いを探索する（[review.md](./review.md)）
* 入賞後: レジリエンス（回復／崩壊）を次の中心に（[post-award.md](./post-award.md)）
* デモは **ローカル実演＋録画**（[ADR 0001](../decisions/0001-local-runtime-and-supabase.md)）
* 可視化は **2D マップ**（[ADR 0002](../decisions/0002-2d-visualization.md)）
* やらない: 支援チャット、正解導出 AI、業務効率化ツールとしての見せ方
