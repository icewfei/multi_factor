# Design Note: Cross-Horizon Signal Family

**Status:** Design only, not yet registered.

---

## 1. Problem Redefinition

### What is a cross-horizon signal family?

跨持有期信号族的核心思想：**将不同时间频率的信号组合成一个基线，利用它们在 alpha 来源、换手率特征和市场状态上的互补性。**

具体来说，这个方向组合两个经典但不同频率的信号：
- **短持有期反转（reversal_5d）**：过去 5 天的收益，预期反转。频率高，换手高，但 alpha 衰减快。
- **中持有期动量（momentum_60_5）**：过去 60 天相对于 5 天的收益，预期延续。频率低，换手低，但 alpha 衰减慢。

### 与已关闭的 intraday standalone line 的本质区别

| 维度 | Intraday standalone（已关闭） | Cross-horizon family（新方向） |
|---|---|---|
| 信号频率 | 同频（intraday 日频统计量） | **跨频**（5d 反转 + 60d 动量） |
| 换手特征 | 全部高换手（0.39+） | **混合**（反转高换手 + 动量低换手） |
| 市场状态覆盖 | 同频同时失效 | 不同频率对不同市场状态敏感 |
| 费用压力来源 | 所有信号都被 cost 吃掉 | 低换手信号的费用压力自然更低 |
| 与前序两轮的关系 | 直系延续 | **无延续**（全新信号组合） |

### 为什么更有希望解决 absolute return / IR 不足

前三次失败的共同模式是：所有信号在同一频率下，cost_stress 是系统性瓶颈。反转+动量的跨频组合可以通过以下方式突破该瓶颈：

1. **动量的低换手天然降低 cost_stress**：`momentum_60_5` 的日均换手明显低于 intraday 信号（v18 在 26-cohort 下 avg_turnover=0.074，intraday 在同样合同下是 0.09）。低换手 = 更低费用 = 更好的 cost_stress 表现。

2. **不同频率的反向市场暴露**：反转在超买/超卖时有效，动量在趋势延续时有效。两者很少同时完全失效。

3. **不依赖任何已关闭的 intraday 信号**：这是一个干净的新起点。

---

## 2. 候选信号来源

### 候选 A：Cross-horizon reversal + momentum（推荐首选）

| 字段 | 值 |
|---|---|
| 短频信号 | `reversal_5d_raw`（5 日短持有期反转） |
| 中频信号 | `momentum_60_5_raw`（60-5 日中持有期动量） |
| 组合方式 | 等权 percentile_rank |
| 经济含义 | 反转捕捉短期过度反应，动量捕捉趋势延续 |
| 已有证据 | 两者均为 `signal_edge_positive`（早期 exploratory），但从未在 5-cohort 合同下作为 family 测试 |

### 候选 B：Overnight + intraday cross-frequency

| 字段 | 值 |
|---|---|
| 短频信号 | `overnight_strength_share_20d` |
| 中频信号 | 与 intraday 组合 |
| 已有证据 | 单信号 `signal_edge_mixed`，信号质量不足以支撑 family 设计 |

### 候选 C：Multi-horizon momentum（60-5 + 20-5）

同频动量只差在窗口长度，不是真正的 cross-horizon。

### 为什么选 A

1. **最干净的新起点**：两个信号都是 daily-level，与已关闭的 intraday 线无直接关系
2. **成本结构最合理**：动量（60 天窗口）的换手率天然低于日内信号
3. **实现最快**：两个信号都已存在于 `build_baseline_model_scores.py` 的 feature_frame 中，不需要新 SQL

---

## 3. 单一优先方案

### 推荐：Reversal(5d) + Momentum(60-5d) cross-horizon family

**经济含义：**
- `reversal_5d_raw` =（L5_close / L0_close - 1），反向。过去 5 天涨幅过大 → 预期回落（过度反应/流动性提供）
- `momentum_60_5_raw` =（L5_close / L60_close - 1），正向。过去 60 天相对于 5 天的趋势 → 继续（动量延续）

**为什么比 intraday 家族更可能提供更厚的 alpha：**
- Intraday 信号（trend_bias, upside_share）本质上是同频的，intraday 层面，共享同一信息集。反转和动量是不同频的，它们的 alpha 来源几乎是正交的。
- 动量作为信号已在学术界和业界被验证为最稳定的因子之一。Intraday 信号则高度依赖市场微观结构，受交易制度变化影响更大。

**为什么比继续做 additive layer / 合同微调更值得优先做：**
- 合同已到极限（5-cohort, 81% invested_weight，不可能更高了）
- Additive layer 的问题是需要一个可用的 baseline，但 v18 在 5-cohort 下的 annual_relative_return = -0.571
- 这是一个全新的信号组合，而不是对已有失败方向的微调

---

## 4. Shortlist 建议

### 候选 c1：Reversal-only（5d 反转单信号基线）

| 字段 | 值 |
|---|---|
| 信号 | `reversal_5d_raw`（DESC） |
| min_feature_count | 1 |
| 角色 | 单信号对照 |
| 已有证据 | 早期 exploratory 中 `signal_edge_positive`，但从未在 5-cohort 下测试 |

### 候选 c2：Momentum-only（60d 动量单信号基线）

| 字段 | 值 |
|---|---|
| 信号 | `momentum_60_5_raw`（DESC） |
| min_feature_count | 1 |
| 角色 | 单信号对照 |
| 已有证据 | v18 的成分之一，但 v18 在 5-cohort 下从未以纯动量形式测试 |

### 候选 c3：Reversal + Momentum cross-horizon family（反转+动量跨频组合）

| 字段 | 值 |
|---|---|
| 信号 | `reversal_5d_raw`（DESC）+ `momentum_60_5_raw`（DESC） |
| min_feature_count | 2 |
| 组合公式 | `mean(percentile_rank(reversal DESC), percentile_rank(momentum DESC))` |
| 角色 | 主测试候选 |
| 为什么值得优先推进 | 首次在 5-cohort 合同下测试 cross-horizon 组合 |

---

## 5. Prereg 草案

```yaml
research_round_id: rr_exploratory_cross_horizon_reversal_momentum_20260501

research_tier: exploratory
round_type: family_construction

research_question: >
  在 5-cohort 合同下，以短持有期反转（reversal_5d）与中持有期动量（momentum_60_5）
  构建的跨频信号基线，能否在验证集（2019-2021）上通过 prereg success rules？
  反转与动量的跨频组合是否比各自单信号具有更优的 cost_stress 和绝对收益表现？

baseline_reference_candidate_scheme_id: price_volume_v18_refresh_hysteresis
  (注：仅作为项目参考基线，非 contract-matched。实际 delta 比较使用 contract-matched
  的单一信号对照)

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

score_builder: build_baseline_model_scores.py
  (所有信号已有，无需新增 SQL)

contract_param:
  holding_cohort_count: 5

changed_dimension: score_family
change_control_rule: single_dimension_only
change_detail: >
  完全替换 score family。仅允许使用 reversal_5d_raw 和 momentum_60_5_raw。
  不允许改变：TopK(10)、执行语义、成本合同、基准、持仓提取规则、
  组合刷新规则、purge gap、样本资格矩阵、流动性 guard(0.70)、
  holding_cohort_count(5)、cash retention/no-replacement。

planned_candidates:
  - candidate_scheme_id: exploratory_cross_horizon_c1_reversal_only
    feature_preset: single_signal_reversal_5d_v1
    feature_set: [reversal_5d_raw]
    score_rule: percentile_rank(reversal_5d_raw DESC); min_feature_count >= 1
    description: 5d 反转单信号基线（5-cohort）

  - candidate_scheme_id: exploratory_cross_horizon_c2_momentum_only
    feature_preset: single_signal_momentum_60_5_v1
    feature_set: [momentum_60_5_raw]
    score_rule: percentile_rank(momentum_60_5_raw DESC); min_feature_count >= 1
    description: 60d 动量单信号基线（5-cohort）

  - candidate_scheme_id: exploratory_cross_horizon_c3_reversal_momentum
    feature_preset: price_volume_v16_remove_trend_consistency
    feature_set: [reversal_5d_raw, momentum_60_5_raw]
    score_rule: mean(percentile_rank(reversal_5d_raw DESC), percentile_rank(momentum_60_5_raw DESC)); min_feature_count >= 2
    description: 反转+动量跨频组合基线（5-cohort）

  (注：c3 使用 reversal + momentum，虽然与 v16 preset 同名但实际 feature 列表不同)

success_rules:
  保持与前几轮一致的 9 道 gates，保证跨候选可比性：

  pass_validation_annual_relative_return: annual_relative_return >= 0.01
  pass_validation_relative_ir: relative_ir >= 0.30
  pass_not_worse_than_single_signal_reversal: annual_relative_return_delta_vs_reversal >= -0.005
  pass_not_worse_than_single_signal_momentum: annual_relative_return_delta_vs_momentum >= -0.005
  pass_avg_invested_weight: avg_invested_weight >= 0.15
  pass_max_drawdown_not_worse: max_drawdown_delta_vs_best_single >= -0.05
  pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
  pass_cost_stress: cost_stress_annual_relative_return >= 0.00
  pass_turnover_not_materially_worse: avg_turnover_daily_delta_vs_momentum <= 0.04

  core_pass_condition: all 9 gates must pass

forbidden:
  - 不能新增第四个候选
  - 中途不能更换候选名单
  - 不能查看 2022-2025 测试集
  - 不能加入 intraday 信号（intraday standalone line 已关闭）
  - 不能加入流动性趋势类信号（避免与已关闭的 v18 链条重叠）
  - 不能改动任何合同参数
  - 不能改动信号预处理合同

serial_execution:
  order: [c1_reversal, c2_momentum, c3_cross_horizon]
  rule: 严格串行。前一个 run 完成并汇报后，才允许进入下一个。
  不得并行，不得边改边跑。

relationship_to_previous_rounds:
  previous_intraday_26cohort: rr_exploratory_intraday_microstructure_independent_baseline_20260501 (closed)
  previous_intraday_5cohort: rr_exploratory_intraday_cohort5_contract_design_20260501 (closed)
  previous_volume_gate: rr_exploratory_trend_bias_volume_confirmed_20260501 (closed)
  relationship: new direction, clean slate. No intraday signals. Cross-horizon (5d + 60d).
```

---

## 6. 执行顺序

```
第 1 步：c1 — reversal_5d only（单信号对照）
第 2 步：c2 — momentum_60_5 only（单信号对照）
第 3 步：c3 — reversal + momentum（跨频组合，主测试候选）
```

前两个单信号基线提供 contract-matched 比较基准，c3 是真正的测试候选。
