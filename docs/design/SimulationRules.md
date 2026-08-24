# Simulation Rules（最小定義）

MVP 向けの最小ルール。  
「LLM が意思決定し、ルールが結果を確定する」二層構造とする。

* **意思決定層（LLM）**: 何をするか選ぶ
* **解決層（ルール）**: 選ばれた行動が世界状態をどう変えるか確定する

---

## 1. 時間

| 用語 | 定義 |
|------|------|
| Turn | シミュレーションの最小時間単位。全 Agent が最大 1 回行動する |
| Tick | 1 Turn を進める処理一式 |

1 Turn の順序は固定する。

```text
1. 観測スナップショット作成（全 Agent 共通の世界見え方を固定）
2. 各 Agent が行動を決定（LLM またはフォールバック）
3. 行動を優先度順に解決
4. 世界パラメータ・メトリクス更新
5. Event / History 記録
6. Turn 番号を +1
```

同時行動の衝突は「解決優先度」で処理する（後述）。ランダム性が必要な箇所は `seed` で再現可能にする。

---

## 2. 状態（State）

### 2.1 World

| フィールド | 型の目安 | 説明 |
|------------|----------|------|
| `turn` | int | 現在ターン |
| `seed` | int | 再現用シード |
| `population_cap` | int | 人口上限（出生で増える上限。初期人数とは別） |
| `initial_population` | int | 開始時の人数 |
| `resource_pool` | number | 世界全体の利用可能資源 |
| `education_level` | number (0–1) | 教育水準。協力成功率などに影響 |
| `tax_rate` | number (0–1) | 税率。従う選択時の徴収率 |
| `institution` | enum | `anarchy` / `autocracy` / `democracy` |
| `geography` | enum | `asia` / `europe` / `middle_east` / `america`。平面地図に投影する広域舞台 |
| `landform` | enum | `continent` / `island`。シミュレーション用の粗い地形グリッドの形 |
| `climate` | enum | `temperate` / `cold` / `wetland` / `arid`。地形バイオームと移動コスト・資源回復に効く。地図の舞台枠に薄い色を重ねる |
| `disaster_frequency` | number (0–1) | 災害の起きやすさ。種類（台風・地震・水害・熱波・冷害）は地形・気候で偏る |
| `religion` | enum | `folk` / `organized` / `secular`。服従・抵抗の出やすさ |
| `terrain` | object | 粗いタイル（既定 48×48）。biome は `ocean` / `coast` / `river` / `plain` / `mountain` / `marsh` / `tundra` / `desert` |
| `initial_values` | object | 初期価値観（例: 協力傾向・権威受容） |

### 2.2 Agent

| フィールド | 型の目安 | 説明 |
|------------|----------|------|
| `id` | string | 一意 ID |
| `name` | string | 表示名 |
| `position` | `{x, y}` | 簡易平面座標 |
| `wealth` | number | 個人資源 |
| `energy` | number (0–1) | 行動余力。0 で待機強制 |
| `happiness` | number (0–1) | 幸福度 |
| `personality` | object | 例: `{cooperation, aggression, ambition}` (各 0–1) |
| `goal` | string | 短期目標テキスト（LLM 用） |
| `memory` | string[] | 直近 Event の要約（上限あり、例: 10 件） |
| `settlement_id` | string \| null | 所属集落 |
| `allegiance` | `obey` / `resist` / `neutral` | 制度への態度 |
| `alive` | bool | 生存フラグ |
| `traits` | string[] | 稀少特性。`charisma` / `genius`（生涯で得たり失ったりする） |
| `age` | int | 年齢。1ターンで +1。高齢で死亡し世代が入れ替わる |

### 2.3 Relationship

Agent 間は向き付きで持たず、**無向 + スカラー** の最小形とする。

| フィールド | 型の目安 | 説明 |
|------------|----------|------|
| `a_id`, `b_id` | string | 両端 Agent |
| `trust` | number (-1–1) | 信頼。正=信頼、負=敵対 |
| `affinity` | number (-1–1) | 親近感 |

未定義ペアは `trust=0`, `affinity=0` として扱う。

### 2.4 Settlement（集落）

| フィールド | 型の目安 | 説明 |
|------------|----------|------|
| `id` | string | 一意 ID |
| `position` | `{x, y}` | 中心座標 |
| `member_ids` | string[] | 所属 Agent |
| `shared_wealth` | number | 共有資源 |
| `leader_id` | string \| null | 集落リーダー（富・野心・特性で決定） |

Agent の `position` が近い同士は、ターン末に自動で同一集落へマージしてよい（距離閾値は定数）。

### 2.5 Institution（制度状態）

World の `institution` に加え、実行時に次を持つ。

| フィールド | 説明 |
|------------|------|
| `authority` | 制度の実効力 (0–1)。`obey` が多いと上昇、`resist` が多いと低下 |
| `treasury` | 税収プール |

### 2.6 Event / History

| 種類 | 内容 |
|------|------|
| Event | 1 行動の結果（誰が・何を・誰に・数値変化） |
| History | ターン要約（メトリクススナップショット） |

---

## 3. 行動（Actions）

各 Turn、各生存 Agent は次のいずれか **1つ** を選ぶ。

| 行動 | 必要対象 | 概要 |
|------|----------|------|
| `wait` | なし | 何もしない。energy をわずかに回復 |
| `cooperate` | 他 Agent 1 | 協力して資源を分け合う／共同生産する |
| `conflict` | 他 Agent 1 | 争い。勝者が資源を奪う |
| `migrate` | 座標または集落 | 移動する |
| `obey` | 制度 | 制度に従い納税・忠誠を示す |
| `birth` | 新生 Agent | ターン末の世界処理。親の近くに子が生まれる |
| `resist` | 制度 | 制度に反抗し、納税拒否・権威低下 |

### 3.1 意思決定（LLM）

LLM への入力（最小）

* 自分の状態（wealth, energy, happiness, personality, goal, memory）
* 近傍 Agent 一覧（id, 距離, trust）
* 世界の要約（turn, tax_rate, institution, authority, resource_pool）

LLM の出力（JSON 必須）

```json
{
  "action": "cooperate",
  "target_id": "agent_3",
  "reason": "信頼が高い相手と資源を増やしたい"
}
```

制約

* `target_id` が必要な行動で対象不正 → `wait` にフォールバック
* energy が閾値未満 → `wait` 強制
* パース失敗・タイムアウト → personality に基づくヒューリスティック

### 3.2 解決ルール（最小）

数値は初期値の目安。バランス調整前提。

#### `wait`

* `energy += 0.1`（上限 1）
* Event: `wait`

#### `cooperate`（actor → target）

成功率の目安:

```text
p = clamp(
  0.5
  + 0.25 * trust(actor, target)
  + 0.20 * education_level
  + 0.15 * ((actor.cooperation + target.cooperation) / 2)
  - 0.10 * abs(actor.wealth - target.wealth) / max_wealth
, 0, 1)
```

成功時

* 両者 `wealth += gain`（`gain` は世界 `resource_pool` から供給。プール減少）
* `trust += 0.1`, `affinity += 0.05`
* 両者 `happiness += 0.05`

失敗時

* 両者 `energy -= 0.1`
* `trust -= 0.05`

#### `conflict`（actor → target）

勝敗力の目安:

```text
power(x) = x.wealth * 0.4 + x.energy * 0.3 + x.aggression * 0.3 + noise()
```

勝者

* `wealth += stolen`（敗者から移転）
* `energy -= 0.15`

敗者

* `wealth -= stolen`
* `happiness -= 0.1`
* `energy -= 0.2`

両者

* `trust -= 0.2`
* 同一集落内なら集落の緊張として記録（ログのみで可）

#### `migrate`

* 指定座標または対象集落中心へ移動（1 Turn で到達する簡易モデル）
* `energy -= 0.2`
* 所属集落を再計算
* 旧集落メンバーとの `affinity` をわずかに低下させてよい

#### `obey`

* `pay = actor.wealth * tax_rate`
* `actor.wealth -= pay`, `treasury += pay`
* `actor.allegiance = obey`
* `authority += 0.02`
* `happiness` は税率が高いと微減

#### `resist`

* 納税しない
* `actor.allegiance = resist`
* `authority -= 0.03`
* 周囲の `resist` が多いと `happiness += 0.02`、少ないと `happiness -= 0.05`（孤立ペナルティ）

---

## 4. 衝突と優先度

同一 Turn で対象が重なる場合の解決順:

```text
1. resist / obey（制度行動）
2. conflict
3. cooperate
4. migrate
5. wait
```

同一優先度内は `agent.id` 昇順（決定的）。

`conflict` と `cooperate` が同一ペアで双方向に出た場合:

* `conflict` を優先し、`cooperate` は無効化（`wait` 扱い）

---

## 5. ターン末の世界更新

1. 集落の再編成（距離閾値）
2. `resource_pool` の自然回復（定数、または education に比例）
3. `authority` を 0–1 にクランプ
4. 加齢（+1歳）と死亡（高齢・困窮。最低2人は残す）。遺産は同集落へ
5. 特性の獲得／喪失（カリスマ・天才は固定ではない）
6. 出生: 生存数が `population_cap` 未満で、繁殖適齢かつ富・幸福が高い親がいれば低確率で 1 人追加
7. 集落リーダー再選（富・野心・特性・年齢ゆらぎ。交代イベントを出す）
8. メトリクス更新
9. History 記録

### メトリクス（最小）

| 指標 | 計算の目安 |
|------|------------|
| 格差 | Agent wealth のジニ係数または分散 |
| 信頼 | Relationship.trust の平均 |
| 協力率 | 当該 Turn の `cooperate` 成功数 / 行動数 |
| 権威 | `authority` |
| 平均幸福 | `happiness` 平均 |

---

## 6. 初期化

1. `seed` から RNG を初期化
2. World パラメータを適用
3. `geography` でアジア／ヨーロッパ／中東／アメリカの広域舞台を選び、観測 UI の平面地図に投影する。`landform`（大陸／島）と `climate`（温帯／寒冷／湿地／乾燥）でシミュレーション地形を変える
4. Agent を `population` 人生成  
   * position は陸タイル上（平野・川・海岸寄り）  
   * personality / wealth / goal を初期価値観からサンプリング  
   * 移動・出生も海には出さない（最も近い陸へスナップ） 
5. Relationship は空（接触後に生成）で開始してよい
6. Institution を設定（`authority` 初期値は制度により変える）  
   * `anarchy`: 0.1  
   * `democracy`: 0.5  
   * `autocracy`: 0.8  
7. Turn = 0 で History を 1 件記録

---

## 7. MVP でやらないこと

* 多段戦闘・補給。地形の移動コストや交易補正（下塗りと陸拘束のみ実装済み）
* 言語ゲームとしての長期交渉（必要なら Event ログに reason を残す程度）
* 本格的な遺伝・世代交代（簡易な出生のみ）
* 複雑な法制度ツリー
* 連続時間シミュレーション

---

## 8. 実装チェックリスト

* [ ] World / Agent / Relationship / Settlement / Institution の状態がコード上で表現できる
* [ ] 1 Turn の順序が実装と一致している
* [ ] 6 行動が解決でき、Event が残る
* [ ] LLM 出力が不正でもシミュレーションが止まらない
* [ ] 同 `seed` + 同初期条件で、ルール解決部分が再現できる  
  （LLM 非決定性がある場合でも、スタブ意思決定では完全再現できること）

---

## 関連ドキュメント

* [FeatureSpec.md](./FeatureSpec.md) — 要件定義
* [Architecture.md](./Architecture.md) — 技術スタック・実装手順
* [DesignDoc.md](./DesignDoc.md) — UI / API / データ設計
* [../README.md](../README.md) — docs 全体の索引
