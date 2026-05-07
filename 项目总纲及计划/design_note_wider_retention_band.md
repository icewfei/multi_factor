# Design: Wider Retention Band

**Status:** Design only, not registered.

**Preceded by:** `rr_exploratory_refresh_rule_turnover_reduction_20260501` — `completed_retain15_partial_finding`

---

## 1. Retain15 Finding Summary

前一回合验证了 retention mechanism 有正效应（return +0.058, drawdown +0.054），但 turnover 未被压缩（0.399 vs 目标 0.20）。根因定为：在 4,311 只宇宙中 `rank ≤ 15` 窗口太窄（top 0.35%），大多数持仓每日仍被替换。

## 2. 方向选择：Wider Retention Band ✅

### 推荐：Wider retention band（retain_if_rank_leq = 50 或 100）

**为什么选 wider retention 而不是 weight stability：**

| 维度 | Wider retention | Weight stability |
|---|---|---|
| 改动维度 | 单个参数（threshold: 15→50/100） | 需新增 weight change cap 逻辑 |
| 证据基础 | retain15 已证明 retention 本身有正效应 | 无直接先例 |
| 因果链 | 更宽的窗口 → 更多 incumbents 保留 → 换手下降 | 重量稳定 → 减少 retained 再平衡换手 → 换手下降，但 confounding with alpha decay |
| 结论干净度 | **高**（单一参数变化） | 低（需同时引入 cap 逻辑和 target weight rule 调整） |

**Wider retention 是 retain15 的自然延伸。** 如果 retain15 有正效应但窗口不够宽，那么更宽的窗口应该增加保留比例并降低 turnover，同时保持或进一步改善 return。这是一个单一参数变化，因果链最干净。

### 选择的 threshold

推荐 retain_if_rank_leq = **50**（宇宙 4,311 只，top 1.2%）。

对比：
| threshold | 覆盖 rank | 宇宙百分比 | 预期保留比例 |
|---|---|---|---|
| 15 | top 15 | top 0.35% | ~5-10% incumbents retained |
| **50** | **top 50** | **top 1.2%** | **~30-50% incumbents retained** |
| 100 | top 100 | top 2.3% | ~50-70% incumbents retained |

选 50 作为第一步。如果保留后 turnover 明显下降但仍未达到 ≤0.20，可以在后续轮次升级到 100。

---

## 3. Prereg 草案

```yaml
research_round_id: rr_exploratory_retain50_round2_20260501

research_tier: exploratory
round_type: method_investigation

research_question: >
  在 retain15 已验证 retention 有正效应的前提下，
  将 retain_if_rank_leq 从 15 放宽到 50，
  是否能显著提高 incumbent 保留比例、压缩 turnover 到 ≤0.20，
  并使 cost_stress 接近或达到 ≥0.00？

anchor_signal: intraday trend_bias (same as retain15 round)
anchor_candidate: exploratory_cohort5_c1_trendbias_only (daily full refresh)

baseline_reference_candidate_scheme_id: exploratory_cohort5_c1_trendbias_only
  (formal baseline — same signal, same contract, daily full refresh)
secondary_diagnostic_anchor: exploratory_cohort5_v18_ref

changed_dimension: portfolio_refresh_rule
change_control_rule: single_dimension_only
change_detail: >
  仅改变 portfolio_refresh_rule 的 retain_if_rank_leq 参数：15 → 50。
  所有其他要素不变：score family、TopK(10)、执行语义、成本合同、
  基准、持仓提取规则、purge gap、样本资格矩阵、流动性 guard、
  holding_cohort_count(5)、cash retention/no-replacement。

portfolio_refresh_contract:
  refresh_rule_name: retain_if_rank_leq
  reference_rank_field: rank_position
  retain_if_rank_leq: 50
  retain_if_guard_still_passes: true
  retain_if_entry_tradeable: true
  max_holdings: 10
  target_weight_rule: "Equal-weight across currently held names after refresh; unfilled slots remain cash."

planned_candidates:
  - candidate_scheme_id: exploratory_retain50_c1
    base_signal: intraday_trend_bias_20d_raw
    refresh_rule: retain_if_rank_leq = 50
    score_rule: percentile_rank(DESC); min_feature_count >= 1

success_rules:
  Same 9 gates as retain15 round (keep cross-round comparability):
  - annual_relative_return >= 0.01
  - relative_ir >= 0.30
  - return_delta vs c1_full_refresh >= -0.01
  - avg_invested_weight >= 0.15
  - drawdown_delta vs c1_full_refresh >= -0.05
  - topk_8 >= 0 AND topk_12 >= 0
  - cost_stress >= 0.00
  - avg_turnover_daily <= 0.20

  core_pass_condition: all 9 gates must pass

forbidden:
  - 不能改动 score family
  - 不能改动 TopK、合同参数
  - 不能将 threshold 从 50 改为其他值
  - 不能同时引入 weight stability
```

---

## 4. 串行约束

```
方法轮第二回合。
只改 retain_if_rank_leq: 15 → 50。
不改 signal、不改 contract、不改 refresh type。
完成后如果需要进一步放宽，再开第三回合（retain100）。
不开并行分支。
```
