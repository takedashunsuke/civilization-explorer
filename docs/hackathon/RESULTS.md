# 実行結果まとめ（開発用索引）

> **提出用の正はリポジトリルートです。**
>
> | 用途 | 場所 |
> |------|------|
> | 生ログ | [result/raw/](../../result/raw/)（`run-NNN/`） |
> | 再生手順 | [DEMO.md](../../DEMO.md) |
> | 解析プロンプト | [analysis/prompt.md](../../analysis/prompt.md) |
> | 解析索引 | [analysis/summary.md](../../analysis/summary.md) → `output/run-NNN/` |

デモ後は `./scripts/run-experiment-batch.sh` で生ログを揃え、`./scripts/run-analysis-batch.sh --aggregate` で解析。要点は [analysis/summary.md](../../analysis/summary.md) と [cross-run-summary](../../analysis/output/cross-run-summary-2026-08-30.md)。  
設計: [demo-v3.md](./demo-v3.md)

---

## クイック参照（対照実験）

| 世界 | variant | UI ラベル |
|------|---------|-----------|
| A | `lush` | 豊か |
| B | `lean` | 乏しい |
| C | `volatile` | 災害多 |
| D | `balanced` | 標準 |

定量表・定性メモのテンプレは [analysis/summary.md](../../analysis/summary.md) を編集してください。
