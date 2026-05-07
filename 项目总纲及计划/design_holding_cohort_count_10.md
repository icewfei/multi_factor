# Design: Holding Cohort Count = 10

**Status:** Design only, not registered.

**Preceded by:** turnover_floor_analysis.md — established that `avg_turnover_daily <= 0.20` under 5-cohort + 5-day hold is mathematically infeasible (floor = 2 × 0.81 / 5 = 0.324).

---

## 1. Research Question

> 在当前 D5 持有期和 5-cohort high-invested-weight framework 下，turnover target ≤ 0.20 数学不可达。若仅将 `holding_cohort_count` 从 5 改为 10，是否能把结构性 turnover floor 压缩到可达区间，同时保持可接受的 invested_weight 和 signal efficacy？

### 预期计算

| 参数 | 5-cohort（当前） | 10-cohort（新） |
|---|---|---|
| cohort_capital_fraction | 1/5 = 20% | 1/10 = 10% |
| 正常活跃 cohort 数 | 5（D1-D5） | 5（D1-D5） |
| 正常 max invested | 5 × 20% = 100% | 5 × 10% = 50% |
| 预期 avg_invested_weight | ~0.81 | **~0.50-0.55** |
| **结构性 turnover floor** | 2 × 0.81 / 5 = **0.324** | **2 × 0.50 / 5 = 0.20** |

**核心 tradeoff：10-cohort 降低 turnover（从 0.40→~0.20-0.25），但也降低 invested_weight（从 0.81→~0.50）。** Cost_stress 预期改善，但 absolute return 可能因 lower inv_wt 而持平或下降。

---

## 2. Anchor Signal

**`intraday_trend_bias` (c1)** — 与前面所有方法轮一致。

Same rationale: 单信号诊断最干净，cost_stress 最接近 0（-0.076），retain15/retain50 已验证 retention 正效应。

---

## 3. Baseline 定义

### Formal baseline

`exploratory_cohort5_c1_trendbias_only` — same signal, 5-cohort contract, full refresh.

### Contract-matched reference（本轮需新建）

`cohort10_c1_full_refresh` — same signal, **10-cohort contract**, full refresh.

必须先有这个 reference 才能判断：
- 10-cohort 本身是否改善了 turnover / cost_stress
- 后续是否还需要在 10-cohort 上加 retention
- 还是 10-cohort alone 就已经足够

---

## 4. Changed Dimension

```
changed_dimension = portfolio_contract_parameter
参数：holding_cohort_count: 5 → 10
唯一变化：cohort_capital_fraction 从 1/5 变为 1/10
```

与前面方法轮不同，这一轮不是 refresh_rule，而是合同参数。refresh 保留 full refresh（不额外加 retention），先隔离单一变量的效果。

---

## 5. Success Rules

### 这轮是 contract-feasibility round，不是 standard family construction。

因此 success rules 需要分层：

#### Layer A: Feasibility target（方法通过标准）

```
avg_turnover_daily <= 0.25
```
结构性 turnover floor 从 0.324 降到约 0.20。0.25 为含 margin 的可达目标。如果 10-cohort 下 turnover 仍 > 0.25，则 cohort_count 参数调整方向本身不成立。

#### Layer B: Strategy target（与之前一致的 9 gates）

保留与之前轮次一致的 9 gates：

```
1. annual_relative_return >= 0.01
2. relative_ir >= 0.30
3. return_delta vs 5-cohort baseline >= -0.01
4. avg_invested_weight >= 0.15
5. drawdown_delta vs 5-cohort baseline >= -0.05
6. topk_8 >= 0.00 AND topk_12 >= 0.00
7. cost_stress >= 0.00
8. avg_turnover_daily <= 0.25（方法目标，替代旧 0.20）
```

core_pass_condition: all 8 gates must pass.

**注意：** Layer A 是"10-cohort 是否将 turnover 压到可达区间"的可行性验证。Layer B 是完整的 strategy verdict。这轮很可能只通过 Layer A 但不通过 Layer B——如果这样，结论是"10-cohort 在方法层面有效，但策略层面仍不足以通过所有 gates"。

---

## 6. 后续路径

### 如果 10-cohort 下 turnover 降到 ≤0.25

```
下一步：
在 10-cohort 合同下，重新应用 retain15/retain50 refresh rule，
测试 retention + 10-cohort 的组合是否能进一步改善 cost_stress。
因为 10-cohort 更低的 inv_wt 给 retention 留出了更多操作空间。

预期：
turnover: 0.25 (10-cohort) → 0.20 (10-cohort + retention)
cost_stress: 可能接近或达到 0
```

### 如果 10-cohort 下 turnover 仍 > 0.25

```
结构性 turnover 公式不成立 → 说明存在 turnover 模型之外的因素
（如严重延迟退出导致更多 signal_date 同时活跃）
→ 需重新审视 turnover 模型假设
→ 或放弃 turnover <= 0.25 目标，转向其他方法层定义
```

### 如果 10-cohort 下 invested_weight 崩溃（< 0.30）

```
10-cohort 导致 inv_wt 过低 → 即使 turnover 降至目标，return 也会崩溃。
→ 需在 10-cohort 上引入 retention 来保 inv_wt（保留高排名持仓）
→ 或接受较低的 inv_wt 作为 tradeoff
```

---

## 7. Prereg 草案（先不注册）

```yaml
research_round_id: rr_exploratory_cohort10_feasibility_20260501

research_tier: exploratory
round_type: contract_feasibility_investigation

research_question: >
  将 holding_cohort_count 从 5 改为 10，是否能将 turnover floor
  从 0.324 压缩到 ~0.20-0.25 的可达区间？同时保持 invested_weight
  不崩溃？

anchor_signal: intraday_trend_bias (c1)
baseline_reference: exploratory_cohort5_c1_trendbias_only
contract_matched_reference: exploratory_cohort10_c1_trendbias (需新建)

snapshot_id: warehouse_20260429_trainval_20211231
execution_logic_version: warehouse_execution_v3

changed_dimension: portfolio_contract_parameter
change_control_rule: single_dimension_only
change_detail: >
  唯一变化：holding_cohort_count 5 → 10。
  不改变：score family、TopK(10)、执行语义、成本合同、基准、
  持仓提取规则、refresh rule (保留 full refresh)、
  purge gap、样本资格矩阵、流动性 guard。

candidate_scheme_ids:
  - exploratory_cohort10_c1_trendbias

success_rules:
  layer_A_feasibility:
    pass_turnover_reduction: avg_turnover_daily <= 0.25
    pass_invested_weight_not_collapsed: avg_invested_weight >= 0.30
  layer_B_strategy:
    pass_annual_relative_return: annual_relative_return >= 0.01
    pass_relative_ir: relative_ir >= 0.30
    pass_not_worse_than_5cohort: annual_relative_return_delta_vs_5cohort_full_refresh >= -0.01
    pass_avg_invested_weight: avg_invested_weight >= 0.15
    pass_max_drawdown_not_worse: max_drawdown_delta_vs_5cohort >= -0.05
    pass_topk_perturbation: topk_8 >= 0 AND topk_12 >= 0
    pass_cost_stress: cost_stress >= 0.00
    pass_turnover_absolute: avg_turnover_daily <= 0.25
  verdict:
    feasibility_pass: both layer_A gates
    strategy_pass: all 8 layer_B gates

forbidden:
  - 不能同时改 refresh rule
  - 不能改 score family
  - 不能改 TopK、holding period、execution semantics
```
