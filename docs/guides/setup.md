# ローカル起動

## 前提

* Node.js 22.19+（Nuxt 4 の engines 要件）
* Python 3.12+（macOS では `python` ではなく `python3` のことが多い）
* （任意）Ollama — `LLM_PROVIDER=ollama` で地域観測・集団方針に接続。失敗時はヒューリスティック。手順は下記「Ollama」
* （任意）Docker / Supabase CLI — 永続化 Phase 4 以降。MVP はインメモリ + `GET /simulations/{id}/replay`
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
LLM_GROUP_SAMPLE_PER_REGION=12
LLM_TIMEOUT_SEC=8
LLM_CONCURRENCY=1
LLM_NARRATIVE_LANG=ja
```

`LLM_PROVIDER=stub` のままだとヒューリスティックのみ。切替後に Backend を再起動し、`http://127.0.0.1:8000/health` の `llm.wired` が `true` であることを確認する。

要約・理由の表示言語は `LLM_NARRATIVE_LANG=ja`（既定）または `en`。

各ターン末、LLM（接続時）が地域ごとに観測し、次ターンの集団方針を決める。方針は列あたり最大 `LLM_GROUP_SAMPLE_PER_REGION` 人のサンプル実行者（リーダー・特異 traits 優先）に反映される。失敗時はヒューリスティック。状況パネルと出来事に要約・理由が表示される。

### トラブル

| 症状 | 確認 |
|------|------|
| 接続できない | Ollama アプリ / サービスが起動しているか。`OLLAMA_BASE_URL` が `127.0.0.1:11434` か |
| モデル不明 | `ollama list` の名前と `OLLAMA_MODEL` が一致しているか |
| 遅い | より小さいモデルへ。デモ中は `LLM_PROVIDER=stub` |

## 最短デモ

1. （任意）Ollama を起動し、モデルを pull する
2. Backend / Frontend を起動
3. UI で Create → Tick（または Tick ×5 / 自動再生）
4. 平面地図・状況パネル・出来事が更新されることを確認

## 結果の保存（将来）

Postgres（Drizzle Phase 4）の前段として、以下が想定されている。

* `GET /simulations/{id}/replay` で同条件再 Create 用パラメータを取得
* ブラウザ localStorage への簡易 JSON 保存（設計メモのみ。**現行フロント未実装**）

永続化が必要になったら `frontend/server/db/` に Drizzle schema を追加する。
