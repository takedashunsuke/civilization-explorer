# AGENTS.md

このリポジトリで実装・修正を行う AI / 開発エージェント向けの指針。

> ステータス: 初版

## 必読ドキュメント

1. [FeatureSpec.md](./FeatureSpec.md) — 要件と非ゴール
2. [SimulationRules.md](./SimulationRules.md) — 状態・行動・ターン
3. [Architecture.md](./Architecture.md) — スタックと実装 Phase
4. （テーマ根拠）[../hackathon/review.md](../hackathon/review.md)

## プロダクトの立ち位置（短く）

* AI は人間支援チャットではなく、**社会を形成する主体**
* 人間は初期条件・制度（世界の法則）だけを変え、創発を観測する
* シミュレーションは真理の証明ではなく仮説探索
* 可視化は **2D マップ**（地球・本格 3D なし）

## 作業ルール

* MVP スコープ外（相図 UI、数千回バッチ分析、本格 3D、支援チャット等）を勝手に広げない
* シミュレーションの数値解決はルール層、LLM は意思決定のみ
* 「便利ツール」「正解導出 AI」に寄る機能・コピーを追加しない
* 大きな設計変更は `docs/decisions/` に ADR を残す
* 進捗の要約は `docs/updates/` に日付ファイルで残す

## コード配置

`Architecture.md` のディレクトリ構成に従う。
