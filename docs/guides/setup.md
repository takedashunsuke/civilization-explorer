# ローカル起動（MVP スタブ）

## 前提

* Node.js 22.19+（Nuxt 4 の engines 要件）
* Python 3.12+（macOS では `python` ではなく `python3` のことが多い）
* （任意）Ollama — `LLM_PROVIDER=ollama` で意思決定に接続。失敗時はヒューリスティック。手順は下記「Ollama」
* （任意）Docker / Supabase CLI — 永続化 Phase 4 以降。MVP の結果キャッシュはブラウザの localStorage（1日）で足りる
## Backend

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

* API ドキュメント: http://127.0.0.1:8000/docs
* ヘルス: http://127.0.0.1:8000/health

## Frontend

### macOS / Linux

```bash
cd frontend
cp .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

### Windows (PowerShell)

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

* UI: http://127.0.0.1:3000/

## Ollama（ホストで動かす）

Docker には入れない。Backend と同じマシンで [Ollama](https://ollama.com/download) を動かし、`http://127.0.0.1:11434` に繋ぐ。

### インストールとモデル

1. [ollama.com/download](https://ollama.com/download) からインストールする（Windows / macOS はアプリ起動で API が立つことが多い）
2. モデルを取得する。16GB 前後のマシンでは 1B〜3B を推奨する

```bash
ollama pull llama3.2:1b
ollama list
```

| 狙い | 例 |
|------|-----|
| 負荷低め（デモ保険） | `llama3.2:1b` |
| バランス | `llama3.2:3b`、`qwen2.5:3b` |
| 避けがち | 7B 超（メモリ・待ち時間） |

3. 応答確認

```bash
ollama run llama3.2:1b "hello"
```

API だけ確認する場合: `http://127.0.0.1:11434/api/tags`

### Backend の設定

`backend/.env`（無い場合は `.env.example` をコピー）:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
LLM_MAX_AGENTS_PER_TURN=4
LLM_TIMEOUT_SEC=8
LLM_CONCURRENCY=1
```

`LLM_PROVIDER=stub` のままだとヒューリスティックのまま。切替後に Backend を再起動し、`http://127.0.0.1:8000/health` の `llm.wired` が `true` であることを確認する。

要約・理由の表示言語は `LLM_NARRATIVE_LANG=ja`（既定）または `en`。

各ターン、リーダー／特異 traits を優先して最大 `LLM_MAX_AGENTS_PER_TURN` 人だけ LLM が行動を選ぶ。残りと失敗時はヒューリスティック。出来事パネルに LLM 理由が表示される。

### トラブル

| 症状 | 確認 |
|------|------|
| 接続できない | Ollama アプリ / サービスが起動しているか。`OLLAMA_BASE_URL` が `127.0.0.1:11434` か |
| モデル不明 | `ollama list` の名前と `OLLAMA_MODEL` が一致しているか |
| 遅い | より小さいモデルへ。デモ中は `LLM_PROVIDER=stub` |

## 最短デモ

1. （任意）Ollama を起動し、モデルを pull する
2. Backend / Frontend を起動
3. UI で Create → Tick（または Tick ×5）
4. 2D マップと Event / メトリクスが更新されることを確認

## 結果のブラウザ保存（MVP）

Postgres の前段として、シミュレーション結果は **localStorage に簡単な JSON、有効期限 1 日** で足りる。ワールド全文・地形・全 Event は入れない（容量の上限にすぐ届く）。

既存の `GET /simulations/{id}/replay`（再実行用パラメータ）と `last_metrics` / `history` をそのまま載せる形が最適。

```json
{
  "v": 1,
  "savedAt": "2026-08-24T01:00:00.000Z",
  "expiresAt": "2026-08-25T01:00:00.000Z",
  "params": {
    "seed": 42,
    "population": 8,
    "resource_pool": 100,
    "education_level": 0.5,
    "tax_rate": 0.1,
    "institution": "democracy",
    "start_year": 700,
    "geography": "asia",
    "landform": "continent",
    "climate": "temperate",
    "initial_values": { "cooperation": 0.5, "authority_acceptance": 0.5 }
  },
  "outcome": {
    "id": "uuid",
    "turn": 24,
    "population": 8,
    "status": "paused",
    "last_metrics": {
      "inequality": 0.2,
      "mean_trust": 0.1,
      "cooperation_rate": 0.4,
      "authority": 0.5,
      "mean_happiness": 0.5
    },
    "history": [
      { "turn": 24, "summary": "…", "metrics": {} }
    ]
  }
}
```

* `params` だけで同条件の再 Create ができる
* `outcome` は観測用の要約。`history` は直近数十ターンまでに切る
* キーは 1 本に配列で複数 run を入れ、起動時に `expiresAt` を過ぎたものを捨てる
* 読めなければ新規作成にフォールバックする（容量超過・別 origin は想定内）
