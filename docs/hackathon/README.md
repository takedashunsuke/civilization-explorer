# hackathon/

ハッカソン発表・デモ・提出向けの資料。**設計の正は `docs/design/`、発表・デモの正は [demo-v3.md](./demo-v3.md)。**

## どこに何を書くか

| ファイル | 書くこと |
|----------|----------|
| [demo-v3.md](./demo-v3.md) | 設計・発表当日の操作 |
| [slides.md](./slides.md) | **スライド原稿のみ**（PPT 転記用） |
| [overview.md](./overview.md) | 30 秒ピッチ |
| [checklist.md](./checklist.md) | 起動・事前確認・障害時 |
| [RESULTS.md](./RESULTS.md) | 実測数値（デモ後） |
| [review.md](./review.md) | テーマ根拠・経緯 |
| [faq.md](./faq.md) | 想定 Q&A |
| [submission.md](./submission.md) | 提出物一覧 |

## 読む順

1. [overview.md](./overview.md) — 30 秒で全体像
2. [demo-v3.md](./demo-v3.md) — 設計 + 発表当日 / [slides.md](./slides.md) — 投影用
3. [checklist.md](./checklist.md) — 起動・障害時
4. [RESULTS.md](./RESULTS.md) — デモ後に記入

実装・セットアップ: [../guides/setup.md](../guides/setup.md)  
プロダクト要件: [../design/FeatureSpec.md](../design/FeatureSpec.md)  
設計判断: [../decisions/](../decisions/)

## 関連方針（短く）

* テーマ: AI 文明を実験場にし、人間社会の問いを探索する（[review.md](./review.md)）
* デモは **ローカル実演＋録画**（[ADR 0001](../decisions/0001-local-runtime-and-supabase.md)）
* 可視化は **2D マップ**（[ADR 0002](../decisions/0002-2d-visualization.md)）
* やらない: 支援チャット、正解導出 AI、業務効率化ツールとしての見せ方
