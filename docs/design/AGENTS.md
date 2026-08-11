# AGENTS.md

このリポジトリで実装・修正を行う AI / 開発エージェント向けの指針。

> ステータス: 初版

## 必読ドキュメント

1. [FeatureSpec.md](./FeatureSpec.md) — 要件と非ゴール
2. [SimulationRules.md](./SimulationRules.md) — 状態・行動・ターン
3. [Architecture.md](./Architecture.md) — スタックと実装 Phase
4. [ADR 0003](../decisions/0003-drizzle-orm.md) — 永続化は Drizzle（SQLAlchemy は使わない）
5. [ADR 0004](../decisions/0004-better-auth.md) — 認証は Better Auth 予定（MVP では実装しない）
6. （テーマ根拠）[../hackathon/review.md](../hackathon/review.md)

## プロダクトの立ち位置（短く）

* AI は人間支援チャットではなく、**社会を形成する主体**
* 人間は初期条件・制度（世界の法則）だけを変え、創発を観測する
* シミュレーションは真理の証明ではなく仮説探索
* 可視化は **Three.js の地球儀**（世界地図。建物モデルや衛星写真は広げない）
* 認証は将来 Better Auth + Drizzle。**MVP ではログインを作らない**

## 作業ルール

* MVP スコープ外（相図 UI、数千回バッチ分析、建物 3D、支援チャット、認証 UI 等）を勝手に広げない
* シミュレーションの数値解決はルール層、LLM は意思決定のみ
* 「便利ツール」「正解導出 AI」に寄る機能・コピーを追加しない
* 大きな設計変更は `docs/decisions/` に ADR を残す
* 進捗の要約は `docs/updates/` に日付ファイルで残す

## コード配置

`Architecture.md` のディレクトリ構成に従う。
