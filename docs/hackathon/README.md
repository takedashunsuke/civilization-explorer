# hackathon/

ハッカソン発表・デモ向けの資料置き場。

設計ドキュメント（`docs/design/`）とは分け、**テーマ根拠・当日の説明・手順・提出物**をここにまとめる。

## ファイル一覧

| ファイル | 内容 |
|----------|------|
| [review.md](./review.md) | 第1回反省・第2回テーマ根拠（必読） |
| [overview.md](./overview.md) | 一言ピッチ・課題・解決・デモで見せること |
| [demo-script.md](./demo-script.md) | 発表・デモの台本（時間配分付き） |
| [checklist.md](./checklist.md) | 当日チェックリスト（起動順・障害時） |
| [slides.md](./slides.md) | スライド原稿・構成メモ |
| [faq.md](./faq.md) | 想定質問と回答 |

実装・セットアップの詳細手順は [../guides/](../guides/) を参照。  
プロダクト要件は [../design/FeatureSpec.md](../design/FeatureSpec.md)、実行方針は [../decisions/](../decisions/) を参照。

## 関連方針（短く）

* テーマ: AI 文明を実験場にし、人間社会の問いを探索する（[review.md](./review.md)）
* デモは **ローカル実演＋録画** を主とする（[ADR 0001](../decisions/0001-local-runtime-and-supabase.md)）
* 可視化は **2D マップ**（地球・本格 3D なし）（[ADR 0002](../decisions/0002-2d-visualization.md)）
* MVP で見せるのは「LLM エージェントの社会形成」「2D での観測」「蓄積・再実行の土台」
* やらない: 支援チャットボット、正解導出 AI、業務効率化ツールとしての見せ方
