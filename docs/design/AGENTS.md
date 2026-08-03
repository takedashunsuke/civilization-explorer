# AGENTS.md

このリポジトリで実装・修正を行う AI / 開発エージェント向けの指針。

> ステータス: 未着手（スケルトン）

## 必読ドキュメント

1. [FeatureSpec.md](./FeatureSpec.md) — 要件と非ゴール
2. [SimulationRules.md](./SimulationRules.md) — 状態・行動・ターン
3. [Architecture.md](./Architecture.md) — スタックと実装 Phase

## 作業ルール（予定）

* MVP スコープ外（文明の相図など）を勝手に広げない
* シミュレーションの数値解決はルール層、LLM は意思決定のみ
* 大きな設計変更は `docs/decisions/` に ADR を残す
* 進捗の要約は `docs/updates/` に日付ファイルで残す

## コード配置

`Architecture.md` のディレクトリ構成に従う。
