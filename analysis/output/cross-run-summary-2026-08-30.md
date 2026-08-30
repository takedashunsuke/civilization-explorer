# 実証実験 — 横断サマリー（2026-08-30）

**プロトコル:** AD 1750→1950（表示ラベル）· **200 年** · seed **42…51** · **10 run**  
**実行:** `./scripts/run-experiment-batch.sh`（合計 **約 415 分**）· Ollama `llama3.2:1b`  
**生ログ:** [result/raw/run-001](../../result/raw/run-001/) … [run-010](../../result/raw/run-010/)  
**解析:** `./scripts/run-analysis-batch.sh --aggregate`

---

## 1. 10 run 平均（4 環境 × experiment_summary）

| 指標 | 豊か | 乏しい | 災害多 | 標準 |
|------|------|--------|--------|------|
| 生存人口 | 820 | 819 | 826 | 818 |
| 人口変化 % | 約 −84 | 約 −84 | 約 −83 | 約 −84 |
| 共有資源（合計） | **990** | **440** | 556 | 717 |
| 争い（累計） | 90 | 99 | 94 | 89 |
| 災害（累計） | 12 | 18 | **28** | 16 |
| 台頭タイプ（代表） | warlord | warlord | warlord | warlord |

**読み方（安定して出た差）**

- **資源:** 豊か ≫ 標準 ≫ 災害多 ≫ 乏しい（環境ノブどおり）
- **災害:** 災害多が **全 run で最多**（平均 28 vs 乏しい 18）
- **人口:** 4 環境とも **約 84% 減** — 環境差より長期人口動態が支配的
- **争い:** run 内・run 間とも **ばらつき大**（LLM 非決定性の影響）。seed 42（run-001）では災害多 113・乏しい 22 と差が最大だったが、10 run 平均では環境間の順位は一定しにくい

---

## 2. 争い（累計）— 災害多 − 乏しい（run 別）

| run | seed | 豊か | 乏しい | 災害多 | 標準 | Δ(災害多−乏しい) |
|-----|------|------|--------|--------|------|------------------|
| run-001 | 42 | 78 | 22 | 113 | 67 | **+91** |
| run-002 | 43 | 75 | 108 | 76 | 90 | −32 |
| run-003 | 44 | 62 | 99 | 129 | 131 | +30 |
| run-004 | 45 | 87 | 122 | 104 | 73 | −18 |
| run-005 | 46 | 57 | 58 | 70 | 131 | +12 |
| run-006 | 47 | 80 | 136 | 82 | 49 | −54 |
| run-007 | 48 | 150 | 153 | 114 | 120 | −39 |
| run-008 | 49 | 97 | 89 | 58 | 94 | −31 |
| run-009 | 50 | 127 | 63 | 145 | 93 | +82 |
| run-010 | 51 | 90 | 137 | 53 | 43 | −84 |

Δ の平均 **−4.3**（σ ≈ 57）— **再現性は争いより災害・資源の方が読みやすい**。

---

## 3. run ごとの解析

| run | seed | 比較 | サマリー |
|-----|------|------|----------|
| run-001 | 42 | [comparison](./run-001/comparison-2026-08-30.md) | [summary](./run-001/summary.md) |
| run-002 | 43 | [comparison](./run-002/comparison-2026-08-30.md) | [summary](./run-002/summary.md) |
| run-003 | 44 | [comparison](./run-003/comparison-2026-08-30.md) | [summary](./run-003/summary.md) |
| run-004 | 45 | [comparison](./run-004/comparison-2026-08-30.md) | [summary](./run-004/summary.md) |
| run-005 | 46 | [comparison](./run-005/comparison-2026-08-30.md) | [summary](./run-005/summary.md) |
| run-006 | 47 | [comparison](./run-006/comparison-2026-08-30.md) | [summary](./run-006/summary.md) |
| run-007 | 48 | [comparison](./run-007/comparison-2026-08-30.md) | [summary](./run-007/summary.md) |
| run-008 | 49 | [comparison](./run-008/comparison-2026-08-30.md) | [summary](./run-008/summary.md) |
| run-009 | 50 | [comparison](./run-009/comparison-2026-08-30.md) | [summary](./run-009/summary.md) |
| run-010 | 51 | [comparison](./run-010/comparison-2026-08-30.md) | [summary](./run-010/summary.md) |

パイロット（100年）: [test-001](./test-001/summary.md)

---

## 4. 次のステップ

- 定性: `./scripts/run-analysis-batch.sh --llm`（任意）
- 個体深掘り: run-001 の `.txt` で agent-role-deep-dive（test-001 更新版）
- 発表: [slides.md](../../docs/hackathon/slides.md) スライド 6 は run-001、横断は本ファイル
