# 当日チェックリスト

> ステータス: 実装同期版（2026-08-29）

## 事前（発表の数時間前）

* [ ] Backend（FastAPI）が起動し、`/docs` が開く
* [ ] Frontend（Nuxt）が開く
* [ ] `http://127.0.0.1:8000/health` で `llm` 状態を確認（`wired: true` なら LLM 接続済み）
* [ ] LLM 使用時: Ollama（または外部 API）が応答する
* [ ] デモ用シナリオを決める（推奨: 対照実験・[RESULTS.md](./RESULTS.md)）
* [ ] 4 環境それぞれ 100 年まで進め、マイルストーンで **レポートを出力 (.txt)** → `result/raw/` に保存
* [ ] [analysis/summary.md](../../analysis/summary.md) に定量表を記入（または LLM 解析後に転記）
* [ ] 発表の問いを [demo-v3.md](./demo-v3.md) と一致しているか確認
* [ ] ピッチが「支援 AI」になっていないか [overview.md](./overview.md) で確認
* [ ] 録画バックアップを用意する（ライブ失敗用）
* [ ] 画面共有解像度・フォントサイズを確認する
* [ ] （任意）`supabase start` — 永続化 Phase 4 まで必須ではない

## 起動順（ローカル）

1. （任意）Ollama — `LLM_PROVIDER=ollama` のとき
2. Backend — `uvicorn main:app --reload --host 127.0.0.1 --port 8000`
3. Frontend — `npm run dev -- --host 127.0.0.1 --port 3000`
4. ブラウザで http://127.0.0.1:3000/ を開く
5. `/health` で LLM 状態を確認

コマンド詳細: [../guides/setup.md](../guides/setup.md)

## 障害時

| 症状 | 対処 |
|------|------|
| LLM が遅い / 落ちる | `LLM_PROVIDER=stub` に切替（Backend 再起動）または録画に切替 |
| 作成が長い | 列人口を 1000 前後に下げる |
| 画面が更新されない | 手動 Tick / ブラウザ再読込 |
| 全体が不安定 | 録画デモへ即切替 |
| DB 接続失敗 | MVP では DB 未使用。無視してよい |

## 発表直前

* [ ] 余計なタブを閉じる
* [ ] API キーや `.env` が画面に映らない
* [ ] デモ用データが初期状態に戻っている
* [ ] ヘッダーの LLM 表示が意図どおり（`stub` / `ollama`）になっている
