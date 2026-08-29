# hackathon/

ハッカソン発表・デモ・提出向けの資料。**設計の正は `docs/design/`、ここは発表・当日運用の正。**

## どこに何を書くか（重複防止）

| 層 | ファイル | 書くこと | 書かないこと |
|----|----------|----------|--------------|
| 設計 | [demo-v3.md](./demo-v3.md) | 問い・仮説・対照実験・LLM 役割・優先度・TimeMap 対比 | スライド全文・操作の秒数 |
| スライド | [slides.md](./slides.md) | 投影用テキスト（10 枚） | 実験設計の表・API 詳細（→ demo-v3） |
| 台本 | [demo-script.md](./demo-script.md) | 時間配分・ライブ操作・指差し | 障害時手順（→ checklist） |
| ピッチ | [overview.md](./overview.md) | 一言・課題・解決・見せる/見せない（短く） | 仮説図・デモ骨格（→ demo-v3） |
| 当日 | [checklist.md](./checklist.md) | 起動順・事前確認・障害時 | デモの話の流れ（→ demo-script） |
| 実測 | [RESULTS.md](./RESULTS.md) | 実行環境・数値・定性メモ | デモ設計・ピッチ |
| 根拠 | [review.md](./review.md) | 第1回反省・第2回テーマの経緯 | 当日手順 |
| Q&A | [faq.md](./faq.md) | 想定質問と回答 | — |
| 提出 | [submission.md](./submission.md) | 提出物一覧・提出前チェック | — |

## 読む順（初めての人）

1. [overview.md](./overview.md) — 30 秒で全体像
2. [demo-v3.md](./demo-v3.md) — デモの設計（採用版）
3. [slides.md](./slides.md) + [demo-script.md](./demo-script.md) — 発表当日
4. [checklist.md](./checklist.md) — 起動・障害時
5. [RESULTS.md](./RESULTS.md) — デモ後に数値を記入

## ファイル一覧

| ファイル | 内容 |
|----------|------|
| [demo-v3.md](./demo-v3.md) | **デモ設計（採用版）** — 問い・対照実験・山場・実装優先度 |
| [review.md](./review.md) | 第1回反省・第2回テーマ根拠 |
| [overview.md](./overview.md) | 一言ピッチ・課題・解決 |
| [slides.md](./slides.md) | スライド原稿（10 枚） |
| [demo-script.md](./demo-script.md) | 発表・デモ台本（5〜7 分） |
| [checklist.md](./checklist.md) | 当日チェックリスト |
| [faq.md](./faq.md) | 想定質問と回答 |
| [submission.md](./submission.md) | 提出物一覧 |
| [RESULTS.md](./RESULTS.md) | 実行結果（デモ後に記入） |

実装・セットアップ: [../guides/setup.md](../guides/setup.md)  
プロダクト要件: [../design/FeatureSpec.md](../design/FeatureSpec.md)  
設計判断: [../decisions/](../decisions/)

## 関連方針（短く）

* テーマ: AI 文明を実験場にし、人間社会の問いを探索する（[review.md](./review.md)）
* デモは **ローカル実演＋録画**（[ADR 0001](../decisions/0001-local-runtime-and-supabase.md)）
* 可視化は **2D マップ**（[ADR 0002](../decisions/0002-2d-visualization.md)）
* やらない: 支援チャット、正解導出 AI、業務効率化ツールとしての見せ方
