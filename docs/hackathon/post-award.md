# 第2回ハッカソン講評と次の実装方針

> ステータス: 入賞後の引継ぎ（2026-09）／コード確認 2026-09-18  
> 用途: 講評の記録、ネクストアクション、レジリエンス方向の実装判断  
> 関連: [overview.md](./overview.md) · [gap.md](./gap.md) · [review.md](./review.md) · [world-model.md](./world-model.md) · [analysis/output/cross-run-summary-2026-08-30.md](../../analysis/output/cross-run-summary-2026-08-30.md)

---

## 0. いまの結論

**第2回は「対照実験装置として成立した」ことが評価され、入賞した。**  
次は「環境ノブが指標に映った」段階から、**危機に対して社会が回復するか崩壊するか（レジリエンス）**を問いの中心に据える。

| 今回（入賞） | 次回（修正の軸） |
|--------------|------------------|
| 同じ人間 × 異なる環境 → 歴史が分岐するか | 同じ危機 × 異なる社会応答 → 回復／崩壊の分岐条件 |
| ルール層が社会を動かし、LLM は地域観測 | ルール層は物理・制度の制約、LLM は住民／集団の意思決定 |
| 資源・災害の差は出た。人口はほぼ同一 | 人口・制度・協力がショック後に分岐する計測を先に作る |

---

## 1. 結果

* 発表題: **もし、同じ人間が違う世界に生きていたら？（Civilization Explorer）**
* PROJECT VIEW / 0106 · **入賞**
* 作者: 竹田俊亮
* タグ: 歴史・文明 / 環境・資源 / 危機対応

### 1.1 発表画面の要約（提出文面）

同一の 5,000 人を、共有資源と災害だけが異なる 4 世界に置き、ルール層が社会を動かし LLM は地域の解釈のみを担う対照実験。  
200 年進行後、争い・資源・台頭・個人の生死が世界ごとに分岐し、同一 ID が災害の多い世界では死に、乏しい世界だけで指導者化した。

### 1.2 作者による概要（提出文面）

歴史学・社会学とエージェントシミュレーション、LLM 観測を掛け合わせ、同一 5,000 人を共有資源と災害だけ異なる 4 世界に置く対照実験装置。ルール層が社会を解決し、LLM は地域の解釈のみ担当。200 年進行後、争い・資源・台頭・個人の生死が世界ごとに分岐する創発を観測した。歴史は偉人でも環境だけでもなく、人間と社会の相互作用で生まれる——その問いを、再現可能な人工世界で検証する。

---

## 2. 藤井学長からの講評

**藤井学長（デジタルハリウッド大学）**

同一の 5,000 人を環境だけ変えた 4 世界に置き、200 年 × 10 seed を CLI で完走させ、生ログと横断サマリーまで整備した工学的な完成度は評価できます。「争いは再現しにくい」と正直に書いた点も好印象です。ただ、得られた差は環境ノブがそのまま指標に現れたものに留まり、人口動態は 4 世界で同一、1b モデルの地域観測は意味を成しておらず、「メタ安全保障」との接続も語られていません。次は災害・資源の変動に対して社会が回復するか崩壊するかの分岐条件（レジリエンス）を問いの中心に据え、より大きなモデルで住民の意思決定を担わせると、テーマにも結果にも厚みが出るはずです。

### 2.1 評価された点

| 講評の言葉 | リポジトリでの根拠 |
|------------|-------------------|
| 対照実験の設計 | 同一ロスター × `lush` / `lean` / `volatile` / `balanced`（`experiment.py`） |
| 200 年 × 10 seed を CLI 完走 | `scripts/run-experiment-batch.sh` · [DEMO.md](../../DEMO.md) |
| 生ログ・横断サマリー | `result/raw/run-NNN/` · `analysis/output/cross-run-summary-*.md` |
| 「争いは再現しにくい」と書いた正直さ | 横断サマリーの争い Δ 平均 −4.3、σ ≈ 57 |

### 2.2 指摘された点

| 指摘 | 実証での対応事実 |
|------|------------------|
| 差は環境ノブの写像に留まる | 資源・災害はノブどおり。創発的な分岐（制度・協力・人口）は弱い |
| 人口動態は 4 世界で同一 | 10 run 平均でも生存人口 ≈ 818〜826（約 −84%）でほぼ重なる |
| 1b 地域観測が意味を成していない | Ollama `llama3.2:1b` は解釈ラベル寄り。意思決定の主因ではない |
| 「メタ安全保障」との接続が未語り | 提出文面・README に明示的な接続がない |

### 2.3 講評が求める次の問い

> 災害・資源の変動に対して、社会が**回復するか崩壊するか**の分岐条件（レジリエンス）を中心に据え、より大きなモデルで**住民の意思決定**を担わせる。

---

## 3. なぜ人口が揃ったか（実装上の原因）— Phase A 以前

講評の「人口が同一」はバグ報告ではなく、**当時のモデルの構造的帰結**だった（Phase A で経路を追加済み）。

| 仕組み | Phase A 以前 | Phase A 以降 |
|--------|--------------|--------------|
| 死亡 | 年齢ベースが主 | ＋資源不足・`shock_stress` |
| 災害 | ほぼ非致死 | 致死＋stress（頻度で増幅） |
| 疫病・天候 | 致死弱／ログなし | 致死＋`death_disaster` イベント |
| 出生 | wealth/happiness のみ | ＋資源 scarcity・stress で抑制 |
| 資源回復 | 教育・気候ベース | ＋scarcity・幸福・人口・制度 |

---

## 4. ネクストアクション（優先度）

Phase A–C のコードは `3fba352` 以降に入っている。**次は stub で動かして差の経路を確認する。** 詳細な未対応は §9–10。

### いま回す — stub 試験（LLM なし）

`backend/.env` は `LLM_PROVIDER=stub` が正。Ollama を繋いだままにしない。

1. **受け入れパイロット（短い）**
   - `backend/.venv/bin/python scripts/pilot_phase_a.py` — 環境ノブで人口が分かれるか
   - `backend/.venv/bin/python scripts/pilot_phase_c.py` — 同一危機 × 社会構造で指標が出るか
2. **resilience 単発（200 年・1 seed）**
   - `./scripts/run-experiment.sh --protocol resilience --start-year 1750 --years 200 --seed 42`
   - またはバッチ 1 本: `./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1`
3. **読む指標**（`resilience_label` は参考。年齢死で collapsed に寄りやすい）
   - `pop_retention_ratio` / `disaster_deaths` / `coop_vs_conflict_post_shock` / `regime_break`
4. **経路が見えたら seed を増やす**
   - `./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 10`
   - 解析: `./scripts/run-analysis-batch.sh --aggregate`

操作的な合格（stub）:

| 段階 | 合格の目安 |
|------|------------|
| Phase C パイロット | pulse が `[2,5,8]`、生存または保持率に差、ショック数が近い、指標が null でない |
| 200 年 1 seed | 4 variant の `pop_retention_ratio` が完全一致しない。差を災害死・協力比・制度で説明できる |
| ラベル | recovered 必須ではない。単調減少なら保持率を主指標にする |

### まだ対応できていない課題（要約）

実装済みに見せかけて、解釈や次の語りを崩すもの。詳細は §10。

| 優先 | 課題 | 状態 |
|------|------|------|
| 高 | 「同一ショック列」は近似（疫病が `trade_openness` に依存し、生存人数で RNG がずれる） | 未修正 |
| 高 | 年齢死が強く、ラベルが collapsed に寄る | 既知。保持率で読む |
| 中 | `inequality` が初期富に乗らない。社会差は協力バイアスと再生補正が主 | 未修正 |
| 中 | メタ安全保障の一文が README / overview に無い | 未 |
| 中 | UI は lush 系のみ。回復曲線なし | 未 |
| 低 | Phase D（中〜大モデルで住民意思決定） | 未。stub で差が出てから |

### P0 — 問いと計測の再定義

- [x] 中心の問いを文書化する: **「同じショックに対し、社会は回復するか崩壊するか」**
- [x] stub 試験用の成功条件を置く（上表。ラベル閾値の再調整は残件）
- [ ] 「メタ安全保障」との一文接続を README / overview に書く（後述 §6）
- [x] 本ファイルと [gap.md](./gap.md) の TODO を同期する（2026-09-18）

### P1 — ルール層で人口・ショックが分岐する（LLM なしでも差が出る）

- [x] 災害・資源不足が死亡・出生に効く経路を追加（§5.1）— 2026-09 実装
- [x] ショック後の回復軌跡を `experiment_summary` に載せる（§5.2）— Phase B
- [x] パイロット: 4 variant × 短い年数 × 少数 seed で人口が分かれることを確認（`scripts/pilot_phase_a.py`）
- [x] 横断サマリーの「読み方」をレジリエンス指標中心に更新（`analysis_batch.py` の比較表に 1b 節）
- [x] **stub で Phase A/C パイロットを再走し、200 年 1 seed の実測を残す**（`result/raw/run-011/`）

### P2 — 対照実験の軸を「環境ノブ」から「危機応答」へ拡張

- [x] 同一ロスター × **同一ショック予定** × **異なる初期制度／協力バイアス**の第2プロトコルを設計（§5.3）
- [x] CLI に `--protocol resilience` を追加（`scripts/run-experiment.py` / `pilot_phase_c.py`）
- [x] バッチシェルが `--protocol` / `--stub` / `--reps` を受け付ける（`scripts/run-experiment-batch.sh`）
- [x] 既存の lush/lean/volatile/balanced は「環境感度のベースライン」として残す
- [ ] ショック列を seed から事前生成し、全 variant に同じイベントを載せる（近似の解消）

### P3 — LLM を住民意思決定に引き上げ

- [ ] stub 試験でルール層だけの差を確認してから着手
- [ ] 1b 観測専用から、中〜大規模モデルで集団／サンプル住民の行動決定へ（§5.4）
- [ ] stub ヒューリスティックでも P1 の差が出ることを維持（LLM は増幅層）
- [ ] コスト上限: 地域サンプル数・ターンあたり呼び出し数を設定で制御（既存 `llm_group_sample_per_region` を拡張）

### P4 — 観測・語り（厚み）

- [ ] 同一 ID のクロスワールド生死・台頭比較をサマリーに固定枠で出す
- [ ] UI: ショック後の回復曲線（人口・資源）の最小表示。civic 等の variant 切替
- [ ] 争いの再現性は「主指標にしない／条件付きで見る」方針を維持

### やらない（当面）

* 全 5,000 人を毎ターン個別 LLM で動かす
* 石油・食料など資源種類の本格マルチコモディティ化
* 「メタ安全保障」を別プロダクトとして実装し直す（接続は語りと指標で先に）
* stub 確認前に Ollama 1b で 10 seed フルバッチを回す（入賞時の environment 再実行は必要なら明示する）

---

## 5. 具体的な実装方針

### 5.1 Phase A — 環境が人口に届く（必須）— **実装済（2026-09）**

**目的:** 講評の「人口が同一」を解消し、レジリエンスの土台を作る。

| 変更 | 方針 | 主な箇所 | 状態 |
|------|------|----------|------|
| 死亡 | 地域 `resource_pool` が低い／`shock_stress` で死亡確率を上げる | `engine.py` `_yearly_death_chance` / `apply_deaths` | ✅ |
| 災害致死 | 大規模災害でサンプル致死。`disaster_frequency` が高いほど率・幅が上がる | `engine.py` `apply_disasters`、`shocks.py` | ✅ |
| 出生 | 資源不足・shock で出生を抑える | `engine.py` `apply_births` | ✅ |
| 資源枯渇スパイラル | regen を scarcity・幸福・人口・制度に依存 | tick 末尾の regen | ✅ |

**パイロット:** `scripts/pilot_phase_a.py`（seed=42・10 turn・stub）  
例: lush 867 / lean 308 / volatile 672 / balanced 852（alive）。資源も lush ≫ lean。

**受け入れ条件**

* [x] 同一 seed で volatile の生存人口が lush より低い
* [x] lean は資源が lush より低い（回復しにくい）
* [x] 4 世界の alive スプレッドが十分（パイロット ≥ 30）

**注意:** 差を出すためにノブを極端にしすぎると「環境ノブの写像」批判が再発する。  
差の**経路**（死・出生・回復失敗）をログに残し、「なぜ分かれたか」を説明できること。

### 5.2 Phase B — レジリエンス指標 — **実装済（2026-09）**

**目的:** 「回復か崩壊か」を数値で語れるようにする。

| 指標 | 定義 | 状態 |
|------|------|------|
| `shock_count` | 災害イベント数 | ✅ |
| `disaster_deaths` | `death_disaster` 件数 | ✅ |
| `pop_trough` | ショック以降の人口最下点 | ✅ |
| `pop_recovery_ratio` | `(期末 − 最下点) / (ショック前 − 最下点)`（単調減少では 0 付近） | ✅ |
| `pop_retention_ratio` | `期末 / ショック前`（慢性減少時の主指標） | ✅ |
| `resource_recovery_halftime` | 50% を割ったあと戻るターン（割っていなければ null） | ✅ |
| `regime_break` | 権威が閾値割れ／大幅低下、または anarchy への転換 | ✅ |
| `coop_vs_conflict_post_shock` | ショック後の協力 / (協力+争い) | ✅ |
| `resilience_label` | `recovered` / `stressed` / `collapsed` | ✅ |

実装:
- 毎ターン `HistoryRecord` に人口・資源・権威を記録（`engine.py`）
- `compute_resilience_metrics` → `experiment_summary`（`experiment.py`）
- 比較表セクション 1b（`scripts/analysis_batch.py`）
- パイロット表示（`scripts/pilot_phase_a.py`）

### 5.3 Phase C — 実験プロトコルの進化 — **実装済（2026-09）**

**現行（残す）:** 同一人間 × 環境ノブ差（`--protocol environment`）  
→ 「環境は効くか」のベースライン。

**追加（講評対応の主プロトコル）:** `--protocol resilience`

```text
固定: 同一 5,000 人ロスター、同一シード、同一危機環境（resource=85, disaster_freq=0.35）
      + 独立した shock RNG + 強制パルス（例: turn 2/5/8）
変動: civic / autocrat / commune / fracture（制度・税率・福祉・協力バイアス）
観測: pop_retention_ratio・災害死・coop比・resilience_label
```

**注意（2026-09-18 確認）:** 「同一ショック列」は **同じ seed・同じ災害頻度・同じパルス turn** まで。疫病発生が `trade_openness` に依存し、生存人数で `shock_rng` の消費がずれるため、イベント列そのものは variant 間で完全一致しない。講評向けの語りでは「同一危機環境＋同一パルス予定」と書く。厳密な同一列は P2 の残件。

| variant | 意味 |
|---------|------|
| `civic` | 民主・協調 |
| `autocrat` | 専制・秩序 |
| `commune` | 高福祉・共同 |
| `fracture` | 無政府・分断 |

実装:
- `prepare_experiment_sim` / `bias_roster_to_identity`（`experiment.py`）
- `apply_pulse_shock` + shock 専用 RNG（`engine.py`）
- CLI: `python scripts/run-experiment.py --protocol resilience`
- バッチ: `./scripts/run-experiment-batch.sh --protocol resilience --stub`
- パイロット: `scripts/pilot_phase_c.py`

問いの言い換え:

* 今回: 同じ人間が違う世界に生きたら？
* 次回: **同じ危機を受けた社会は、なぜ折れる／折れないのか？**

### 5.4 Phase D — LLM の役割変更

| 層 | 現状 | 目標 |
|----|------|------|
| ルール層 | tick 解決・災害・出生死亡 | 物理・資源・致死・制度制約（強化） |
| LLM | 地域観測ラベル + 軽い集団スタンス（1b） | **サンプル住民／集団の行動選択**（中〜大モデル） |
| stub | ヒューリスティック決定 | 回帰テスト・オフライン再現の正として維持 |

段階:

1. ルール層だけで人口分岐（Phase A）を先に通す  
2. `LLM_PROVIDER=ollama|openai` で集団サンプル決定を厚くする（既存 `decide_batch` / `observe_and_steer_*` を拡張）  
3. モデルはデモ用に設定可能に（例: 8B〜それ以上）。1b は「観測デモ用」に格下げ  
4. LLM 有無の A/B をレジリエンス指標で比較（「モデルが意思決定に効いたか」を測る）

### 5.5 推奨実装順（短期スプリント）

1. ~~死亡・災害致死・出生の資源連動~~（Phase A 済）  
2. ~~レジリエンス指標を summary に追加~~（Phase B 済）  
3. **stub でパイロット → resilience 1 seed**（いまここ）  
4. 差の経路が説明できるなら stub 10 seed。必要なら同一ショック列の固定  
5. overview / README にメタ安全保障の一文接続  
6. LLM モデルサイズ引き上げ + 集団決定の比重増（stub で差が出てから）

---

## 6. 「メタ安全保障」との接続（語り）

コードに同名モジュールはまだない。接続はまず**問いのフレーミング**で行う。

提案する一文（overview / README 用）:

> 国家や制度が前提の安全保障ではなく、**環境ショックの下で社会が協力・制度・指導を再編成できるか**を人工世界で測る。これが Civilization Explorer におけるメタ安全保障の実験的定義である。

指標との対応: `pop_recovery_ratio`・`regime_break`・ショック後の協力比が、その操作的定義になる。

---

## 7. 自己評価メモ（入賞の意味）

* 評価されたのは「面白いアイデア」単体より、**実験装置として完走・再現できたこと**。
* 第1回の「人間を助ける AI」から、第2回の「人工世界を観測する AI」への転換は、外部評価に耐えた。
* 入賞はゴールではなく、**レジリエンスを中心に据えた第3段階**へ進む土台ができた、という意味で扱う。

---

## 8. 関連ファイル（実装時）

| 領域 | ファイル |
|------|----------|
| 対照実験定義 | `backend/simulation/experiment.py` |
| 人口・災害・tick | `backend/simulation/engine.py` |
| ショック | `backend/simulation/shocks.py` |
| LLM | `backend/simulation/llm.py` · `backend/config.py` |
| バッチ | `scripts/run-experiment-batch.sh` · `scripts/analysis_batch.py` · `scripts/pilot_phase_a.py` · `scripts/pilot_phase_c.py` |
| 概念 | [world-model.md](./world-model.md) |
| 現状ギャップ | [gap.md](./gap.md) |

---

## 9. コード確認メモ（2026-09-18）

対象: `3fba352`（Phase A・講評文書化）から 3 コミット。

| コミット | 内容 |
|----------|------|
| `43ee625` Phase B | 毎ターンの人口・資源・権威を記録し、回復／崩壊指標を `experiment_summary` に載せた |
| `ba97f31` Phase C | 同一危機環境 × civic / autocrat / commune / fracture の第2プロトコル |
| `8b9ef7d` | 上記を `main` にマージ |

講評の「人口が同一」「差は環境ノブの写像」への返しとして、方向は合っている。実行は可能。ただし次を知ったうえで回す。

**よくできている点**

* 問いの分離: environment は「環境は効くか」、resilience は「同じ危機で社会が折れるか」
* 指標が `compute_resilience_metrics` にまとまり、比較表 1b まで繋がる
* 行動 RNG とショック RNG を分け、パルス turn を variant 間で揃えている
* ロスターは共通 ID のまま、性格だけ社会バイアスを足す

**解釈をずらす点（§10 に残件化）**

* 「同一ショック」は完全同一ではない
* バッチ既定は environment のまま（`--protocol resilience` が必要）。2026-09-18 にシェルへフラグを追加済み
* ラベルは collapsed に寄りやすい。保持率・災害死・協力比で読む
* 社会ノブの効きにムラ（`inequality` ほぼ未使用、疫病が交易開放に漏れる）
* フロントは lush 系のみ

---

## 10. まだ対応できていない課題

Phase A–C で「コードはある」が、講評の次の問いに耐えるには不足が残る。

### 10.1 実験設計（高）

| 課題 | いま起きること | 望ましい形 |
|------|----------------|------------|
| 同一ショック列が近似 | `apply_epidemics` が `trade_openness` に依存。生存人数で `shock_rng` の消費がずれ、パルスの当りも変わる | seed から危機列（turn・地域・種類・強度）を先に作り、全 variant に同じイベントを適用。社会は応答だけ変える |
| 回復ラベルが潰れる | 年齢死の単調減少で `pop_recovery_ratio ≈ 0`、`resilience_label=collapsed` になりやすい | 保持率を主指標にするか、年齢死を分離した「ショック帰属死」を測る。閾値の再調整は実測後 |
| 社会ノブの写像リスク | 差が出ても協力バイアスと regen 補正（民主主義 1.05 / 無政府 0.88）の写像に見えやすい | 経路ログ（災害死・出生抑制・資源回復）をサマリーの定位置にする。ノブを極端にしない |

### 10.2 計測・出力（中）

| 課題 | 詳細 |
|------|------|
| 比較表の小数 | `pop_recovery_ratio` 等が 1 桁（0.55 → 0.6） |
| `.txt` と JSON | レジリエンス指標は JSON が正。txt には 2026-09-18 から主要キーを追加 |
| 横断集計 | 以前は environment の争い Δ のみ。resilience の保持率・災害死・ラベル表を追加済み。旧 run と混在しても振り分ける |
| API パルス | `POST /simulations` は常に 20 turn 前提。UI で 10 turn しか回さないとパルス 4 だけ発火 |
| `pilot_phase_a.py` | `prepare_experiment_sim` を呼んでいない（environment では実害小） |

### 10.3 社会ノブの穴（中）

| ノブ | 効くか |
|------|--------|
| 性格バイアス（協力・野心・攻撃） | 効く。協力／争いへ |
| 制度 | 資源再生の係数。体制ドリフト |
| 福祉 | 再分配・幸福・権威 |
| 税率 | 服従時の支払い。0.2 超で幸福減 |
| `authority_acceptance` | 初期権威のみ。エージェント性格には乗らない |
| `inequality` | ロスター生成は 0.5 固定。初期富の再配置なし。3 人以上では富の分散で上書き |

### 10.4 語り・UI・LLM（中〜低）

| 課題 | 詳細 |
|------|------|
| メタ安全保障 | §6 の一文が README / overview に未掲載 |
| UI | `experimentWorlds.ts` は lush 系のみ。回復曲線なし |
| Phase D | 1b 観測のまま。stub で差が出てから中〜大モデルへ |
| 同一 ID 比較 | サマリーの固定枠なし |

---

## 11. stub 試験の手順

LLM は増幅層。**ルール層だけで差が出ることを先に確認する。** いまの `backend/.env` は `LLM_PROVIDER=stub`。

### 11.1 パイロット（数分）

リポジトリルートから:

```bash
backend/.venv/bin/python scripts/pilot_phase_a.py
backend/.venv/bin/python scripts/pilot_phase_c.py
```

Phase C が `needs tuning` なら、200 年バッチの前にパルス・社会差・ショック数を見る。

### 11.2 resilience 1 seed（stub）

```bash
./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1 --dry-run
./scripts/run-experiment-batch.sh --protocol resilience --stub --reps 1
```

同等の単発:

```bash
LLM_PROVIDER=stub ./scripts/run-experiment.sh \
  --protocol resilience --start-year 1750 --years 200 --seed 42
```

出力: `result/raw/run-NNN/civ-{civic,autocrat,commune,fracture}-AD1950-turn20.{json,txt}`

見る場所: 各 JSON の `experiment_summary`（保持率・災害死・協力比・制度破綻・ラベル）。

### 11.3 解析

```bash
./scripts/run-analysis-batch.sh --from-run <今回の run 番号>
# 2 本以上そろったら
./scripts/run-analysis-batch.sh --aggregate
```

### 11.4 伸ばす条件

* 1 seed で 4 世界の保持率が分かれ、災害死か協力比で「なぜ」が言える → `--reps 10`（stub）
* 差がノブの写像にしか見えない → 同一ショック列の固定（§10.1）を先にする
* stub で差が出た → そのあと Ollama（1b は観測デモ。意思決定はより大きいモデル）

environment の再実行（入賞時と同じ lush 系）が必要なときだけ:

```bash
./scripts/run-experiment-batch.sh --protocol environment --stub --reps 1
```

既定の `./scripts/run-experiment-batch.sh` は **environment** のまま（提出手順を壊さない）。講評対応の主実験は **必ず `--protocol resilience`**。
