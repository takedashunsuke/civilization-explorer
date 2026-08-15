# ローカル起動（MVP スタブ）

## 前提

* Node.js 22.19+（Nuxt 4 の engines 要件）
* Python 3.12+（macOS では `python` ではなく `python3` のことが多い）
* （任意）Docker / Supabase CLI — 永続化 Phase 4 以降
* （任意）Ollama — LLM Phase 2 以降。現状はヒューリスティック

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

## 最短デモ

1. Backend / Frontend を起動
2. UI で Create → Tick（または Tick ×5）
3. 2D マップと Event / メトリクスが更新されることを確認
