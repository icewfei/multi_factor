# Implementation Design: Volume-Confirmed Intraday Trend Bias

---

## 1. Implementation Position Design

### Gate 位置选择

Volume gate 应该落在 **rank VIEW 的 WHERE 子句**层。

```
bars CTE          →  raw amount pass-through
                      ↓
bar_features CTE   →  windowed median computation
                      ↓
feature_frame VIEW →  volume_ratio_20d = amount / median_20d
                      ↓
*_ranks VIEW       →  WHERE ranking_eligible_D0
                      AND trend_bias IS NOT NULL
                      AND volume_ratio_20d > 1.0    ← GATE HERE
                      ↓
score_frame        →  LEFT JOINs all rank views
                      ↓
final SELECT       →  WHEN score_component_count >= N THEN score
```

### 为什么选 rank 层而非其他层

| 层 | 为什么不选 |
|---|---|
| raw feature（bar_features） | 改信号本体，不符合 changed_dimension = score_activation_condition |
| feature_frame（派生字段加入） | 可以加 volume_ratio_20d 作为 pass-through 字段，但 gate 本身不放在这层 |
| final SELECT（score 生成） | 在 score 生成时过滤会保留 rank 但丢弃 score，audit 中 rank_rows 和 scored_rows 不一致，更难诊断 |
| **rank VIEW（WHERE 子句）** | **最干净**：不满足 gate 的 stock-day 根本不出现在 rank 中 → rank=NULL → score=NULL → 不进 TopK。与现有 `IS NOT NULL` 过滤模式一致。audit 中 rank_rows = scored_rows（一致）。 |

### 改动范围评估

1 个文件，约 15-20 行改动，不涉及任何现有流程。

---

## 2. Mathematical Definition（可执行无歧义版本）

### 变量定义

```
raw_amount_t = amount_t  (Tushare Pro daily.amount, thousand CNY)
```

### 中位数计算

```
median_20d_excl_current_t = 
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY raw_amount)
  OVER (PARTITION BY instrument ORDER BY signal_date
        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING)
```

即：过去 20 个交易日（不含当日）的成交额中位数。

### Volume ratio

```
volume_ratio_20d_t = raw_amount_t / median_20d_excl_current_t

WHEN median_20d_excl_current_t IS NULL OR median_20d_excl_current_t <= 0
THEN NULL
```

### Gate condition

```
signal_active_t = volume_ratio_20d_t > 1.0  (strict >)

WHEN signal_active_t = FALSE → intraday_trend_bias_rank = NULL
                               → model_score_D0 = NULL
                               → stock-day not in TopK
```

### Gate failure 时的样本处理

- `model_score_D0 = NULL`
- 仍保留在 `feature_frame` 中（不删除样本）
- 在 audit 的 `ranking_eligible_rows` 和 `scored_rows` 之差中可见
- 可通过 `volume_ratio_20d` 字段反推过滤比例

---

## 3. Impact Assessment

### 必须改的文件

| 文件 | 改动内容 |
|---|---|
| `build_baseline_model_scores.py` | **(1)** `bar_features` CTE 中追加 `MEDIAN(amount) OVER w20_prev_excl AS median_amount_20d`<br>**(2)** `feature_frame` 中追加 `amount / median_amount_20d AS volume_ratio_20d`<br>**(3)** 新增 rank VIEW `intraday_trend_bias_volume_gated_ranks`（复制现有 trend_bias ranks 但 WHERE 子句加 `AND volume_ratio_20d > 1.0`）<br>**(4)** 新增 FEATURE_PRESETS entry `single_signal_intraday_trend_bias_volume_gated` 指向该新 rank VIEW<br>**(5)** score_frame 中新增 LEFT JOIN 到该 gated rank VIEW<br>**(6)** final SELECT 中新增该 rank 列<br>**(7)** audit 中新增该 rank 的 count<br>**(8)** JSON audit output 中新增对应 entry |

### 可以不改的文件

| 文件 | 理由 |
|---|---|
| `build_run_state_skeleton.py` | 不关心 gate 逻辑，只消费 model_scores_D0.parquet |
| `build_portfolio_artifacts.py` | 不关心 gate 逻辑 |
| `build_fixed_test_minimal.py` | 不关心 gate 逻辑 |
| `build_confirmatory_validation_readout.py` | 不关心 gate 逻辑 |

### 对现有 presets / 旧 round 复现的影响

**无影响。** 理由：
- 新增的 `median_amount_20d` 是 bar_features 中的新列，**不影响现有列的计算**
- 新增的 `volume_ratio_20d` 是 feature_frame 中的新列，现有 rank VIEWs 不引用它
- 新增的 rank VIEW (`intraday_trend_bias_volume_gated_ranks`) 是完全独立的新 VIEW
- 现有 presets 仍然引用现有的 `intraday_trend_bias_ranks` VIEW（无 volume gate）
- 旧 round 的复现不受影响，因为 model_scores_D0.parquet 不包含 volume_ratio_20d 列

### 新增的 vs 复用的 rank VIEW

两种方案对比：

**方案 A（推荐）：新增独立的 gated rank VIEW**

```
intraday_trend_bias_ranks                (原版，无 gate) ← 现有 presets 继续用
intraday_trend_bias_volume_gated_ranks   (新版，有 gate) ← 新 preset 用
```

优点：不会影响任何现有逻辑，改动完全隔离。

**方案 B：复用现有 rank VIEW，在 feature_frame 层设 volume_ratio_20d**

不推荐，因为需要在 feature_frame 层处理 NULL 条件，逻辑不干净。

---

## 4. Smoke Test Plan（不执行，只计划）

### 步骤 1：Score-layer 验证

运行 `build_baseline_model_scores.py` 使用新 preset：

```
--feature-preset single_signal_intraday_trend_bias_volume_gated
--min-feature-count 1
```

### 步骤 2：检查 audit metrics

与上一轮 c1_5cohort 的无 gate audit 对比：

| 指标 | c1_5cohort（无 gate）| volume_gated | 预期变化 |
|---|---|---|---|
| `ranking_eligible_rows` | 10,780,956 | 10,780,956 | 不变（gate 不减少 eligible）|
| `intraday_trend_bias_rank_rows` | 10,780,956 | **约 6-7M** | 减少约 30-40%（低量 stock-day 被 gate）|
| `scored_rows` | 10,780,956 | **约 6-7M** | 同 rank_rows（rank 失败 = score 失败）|
| gate exclusion rate | 0% | **约 30-40%** | 计算 1 - scored_rows_gated/scored_rows_ungated |

### 步骤 3：健康检查条件

仅在以下条件满足时继续到 full-chain：
- scored_rows 仍 > 5M（候选池足够大）
- gate exclusion rate 不极端（< 70%）
- 无明显数据异常

### 步骤 4：确认 baseline c1_5cohort 不受影响

用现有 preset `single_signal_intraday_trend_bias` 再跑一次，确认 audit 值与上一轮一致。

---

## 5. Serial Execution Constraint

```
本轮只实现 1 个 candidate: exploratory_trend_bias_volume_gated_v1
不实现其他 gate 变体
不并行展开 score_activation_condition 的其他维度
不改其他任何文件
实现 + 验证完成后，再决定是否进入 full-chain
```

---

## 6. Implementation Order（获批后执行）

```
1. build_baseline_model_scores.py 改完 → 2. syntax check → 
3. smoke test（score-layer only）→ 4. 汇报 gate exclusion rate →
5. 如通过健康检查 → full-chain → 6. verdict
```
