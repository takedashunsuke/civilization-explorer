# AGENTS.md

このリポジトリで実装・修正を行う AI / 開発エージェント向けの指針。

> ステータス: 実装同期版（2026-08-28）

## 必読ドキュメント

1. [FeatureSpec.md](./FeatureSpec.md) — 要件と非ゴール
2. [SimulationRules.md](./SimulationRules.md) — 状態・行動・ターン
3. [Architecture.md](./Architecture.md) — スタックと実装 Phase
4. [ADR 0003](../decisions/0003-drizzle-orm.md) — 永続化は Drizzle（SQLAlchemy は使わない）
5. [ADR 0004](../decisions/0004-better-auth.md) — 認証は Better Auth 予定（MVP では実装しない）
6. [ADR 0006](../decisions/0006-flat-map-primary.md) — 観測の主画面は平面世界地図
7. [ADR 0007](../decisions/0007-un-geoscheme-subregions.md) — 比較はマクロ5列、配置は国連サブ地域22
8. （テーマ根拠）[../hackathon/review.md](../hackathon/review.md)

## プロダクトの立ち位置（短く）

* AI は人間支援チャットではなく、**社会を形成する主体**
* 人間は初期条件・制度（世界の法則）だけを変え、創発を観測する
* シミュレーションは真理の証明ではなく仮説探索
* 可視化の既定は **Natural Earth の平面地図**（集団の領域・衝突）。地球儀コンポーネントは残るが UI からは非表示
* 初期条件は中央モーダル（3ステップ）、**状況パネル**（地図左 digest）と出来事モーダル。地図を常時広くする
* LLM はターン末の **地域観測 + 次ターン集団方針**。`LLM_PROVIDER=stub` でも完走する
* 比較の列は五マクロ固定。サブ地域は列内で1つ選び、エージェントはその枠だけに置く（[ADR 0007](../decisions/0007-un-geoscheme-subregions.md)）
* 認証は将来 Better Auth + Drizzle。**MVP ではログインを作らない**

## 作業ルール

* MVP スコープ外（相図 UI、数千回バッチ分析、建物 3D、支援チャット、認証 UI 等）を勝手に広げない
* シミュレーションの数値解決はルール層、LLM は意思決定のみ
* 「便利ツール」「正解導出 AI」に寄る機能・コピーを追加しない
* 大きな設計変更は `docs/decisions/` に ADR を残す
* 進捗の要約は `docs/updates/` に日付ファイルで残す

## コード配置

`Architecture.md` のディレクトリ構成に従う。
