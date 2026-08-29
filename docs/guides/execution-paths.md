# 実行経路（UI と CLI）

画面操作と CLI は **同じ Python シミュレーションエンジン**・**同じ `backend/.env`（Ollama 含む）** で動きます。違うのは入出力の経路だけです。

---

## 処理の流れ

```text
                    backend/.env  (LLM_PROVIDER, OLLAMA_*)
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
   方法 A: CLI                          方法 B: ブラウザ
   run-experiment.py                    Frontend → FastAPI
          │                                       │
          └───────────┬───────────────────────────┘
                      ▼
        simulation.engine.create_simulation
        simulation.engine.tick
                      │
                      ▼
        end_of_turn → llm.observe_and_steer_regions
                      │  (ollama 時は _call_ollama)
                      ▼
              SimulationState + experiment_summary
```

| 層 | 画面（Browser） | CLI |
|----|-----------------|-----|
| 入口 | HTTP `POST /simulations`, `POST .../tick` | `scripts/run-experiment.py` が関数を直接呼ぶ |
| エンジン | `simulation.engine` | **同一** |
| LLM | `simulation.llm` + `config.get_settings()` | **同一** |
| 対照実験の組み立て | `experiment.world_params_for_variant` 等 | **同一** |
| Backend プロセス | uvicorn 必須 | **不要**（in-process） |

`LLM_PROVIDER=ollama` なら、どちらも同じ Ollama（`OLLAMA_BASE_URL` / `OLLAMA_MODEL`）に繋がります。

---

## 結果の出し方（現状と共通化）

### いま共通化されているもの

| データ | 定義場所 | 画面 | CLI |
|--------|----------|------|-----|
| 定量サマリー | `experiment.experiment_summary()` | API JSON の `experiment_summary` | `result/raw/*.json` の `experiment_summary` |
| シミュレーション本体 | `SimulationState` | API JSON（全フィールド） | エンジン内（`.txt` に要約して書き出し） |

**数値比較・`analysis/summary.md` への転記は `experiment_summary` を正とする。** 画面の状況パネルもこの API 応答と同源です。

### いま二系統なもの（要・将来一本化）

| 形式 | 生成元 | 用途 |
|------|--------|------|
| `.txt` レポート全文 | **CLI:** `scripts/run-experiment.py`（Python） / **UI:** `frontend/.../milestoneExport.ts`（TypeScript） | 人間向けログ・LLM への長文投入 |
| 画面表示 | Frontend が API JSON を描画 | ライブデモ |

`.txt` は **セクション構成が似ているが、実装は別**（言語・整形・i18n の差があり、バイト一致はしない）。

### 推奨（提出・再現）

1. **定量:** `result/raw/*.json` の `experiment_summary`（CLI 実行時に自動出力）
2. **定性・出来事ログ:** `result/raw/*.txt`（CLI 推奨。ブラウザ出力を使う場合は同フォルダに手動配置）
3. **LLM 比較:** [analysis/prompt.md](../../analysis/prompt.md) — `.json` 4 本でも `.txt` 4 本でも可

### 将来の一本化（TODO）

- [ ] Backend に `milestone_export` モジュール（Python）を置き、CLI・API・（任意で）UI から同じ `.txt` / `.json` を生成
- [ ] UI の「レポートを出力」は `GET /simulations/{id}/export` を呼ぶ形に寄せる

詳細ギャップ: [../hackathon/gap.md](../hackathon/gap.md)

---

## 関連

- 提出用手順: [../../DEMO.md](../../DEMO.md)
- 結果フォルダ: [../../result/README.md](../../result/README.md)
- CLI: [../../scripts/README.md](../../scripts/README.md)
