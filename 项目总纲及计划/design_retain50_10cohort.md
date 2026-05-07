# Design: Retain50 + 10-Cohort

**Status:** Design only, not registered.

**Preceded by:** 
- `rr_exploratory_retain50_round2_20260501` — proven retain50 improves return/drawdown under 5-cohort
- `rr_exploratory_cohort10_feasibility_20260501` — proven 10-cohort reduces turnover to 0.199 (≤0.25 target)

---

## 1. Research Question

> 在 10-cohort 合同下（turnover 已降至 0.199，feasibility 已验证），加入 retain50 refresh rule，能否在保持 turnover ≤ 0.25 和 invested_weight 不崩溃的前提下，改善 return / IR / drawdown 和 cost_stress？

### 预期机制

10-cohort full refresh 的 turnover 为 0.199，距离 0.25 目标有充足 margin（0.051）。加入 retain50 后：
- 预期 turnover 约 0.16-0.20（仍在 ≤0.25 内）
- retain50 在 5-cohort 下已证明改善 return（-0.194→-0.064）
- 在 10-cohort 下预期也有类似增益
- 更低的 turnover + retention 保持的 alpha，可能改善 cost_stress

---

## 2. Formal Baseline

`exploratory_cohort10_c1_trendbias_only` — 10-cohort, full refresh, same signal.

### 次级诊断对照（不参与 formal verdict）

| 对照 | 角色 |
|---|---|
| `exploratory_retain50_c1` | retain50 在 5-cohort 下的效果 |
| `exploratory_cohort5_c1_trendbias_only` | 5-cohort full refresh |

---

## 3. Changed Dimension

```
changed_dimension = portfolio_refresh_rule
具体：在 10-cohort 合同下，将 full refresh 改为 retain_if_rank_leq = 50
```

---

## 4. Candidate

Single candidate this round:
- `exploratory_cohort10_retain50_c1`
- signal: intraday_trend_bias
- contract: holding_cohort_count = 10
- refresh: retain_if_rank_leq = 50

---

## 5. Prereg 草案

```yaml
research_round_id: rr_exploratory_retain50_10cohort_20260501

research_tier: exploratory
round_type: method_investigation

research_question: >
  在 10-cohort 合同下（turnover 已降至 0.199），
  加入 retain50 refresh rule，能否在保持 turnover ≤ 0.25
  和 invested_weight ≥ 0.30 的前提下，改善 return/IR/drawdown
  和 cost_stress？

formal_baseline: exploratory_cohort10_c1_trendbias_only
  (10-cohort, full refresh, same signal)
secondary_diagnostics:
  - exploratory_retain50_c1 (retain50 under 5-cohort)
  - exploratory_cohort5_c1_trendbias_only

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

changed_dimension: portfolio_refresh_rule
change_control_rule: single_dimension_only
change_detail: >
  在 10-cohort 合同下，将 refresh rule 从 full refresh 改为
  retain_if_rank_leq = 50。不改变：score family、TopK(10)、
  执行语义、成本合同、基准、持仓提取规则、purge gap、
  样本资格矩阵、流动性 guard、holding_cohort_count(10)、
  cash retention/no-replacement。

portfolio_refresh_contract:
  refresh_rule_name: retain_if_rank_leq
  reference_rank_field: rank_position
  retain_if_rank_leq: 50
  retain_if_guard_still_passes: true
  retain_if_entry_tradeable: true
  max_holdings: 10
  target_weight_rule: "Equal-weight across currently held names after refresh; unfilled slots remain cash."

candidate_scheme_ids:
  - exploratory_cohort10_retain50_c1

success_rules:
  9 gates, same as previous method rounds.
  Turnover gate uses ≤ 0.25 (10-cohort feasibility standard).

  pass_annual_relative_return: annual_relative_return >= 0.01
  pass_relative_ir: relative_ir >= 0.30
  pass_not_worse_than_baseline: annual_relative_return_delta_vs_10cohort_full_refresh >= -0.01
  pass_avg_invested_weight: avg_invested_weight >= 0.15
  pass_max_drawdown_not_worse: max_drawdown_delta_vs_10cohort_full_refresh >= -0.05
  pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
  pass_cost_stress: cost_stress_annual_relative_return >= 0.00
  pass_turnover_absolute: avg_turnover_daily <= 0.25

  core_pass_condition: all 8 strategy gates + 1 turnover gate = 9 gates must pass

forbidden:
  - 不能改 score family
  - 不能改 TopK、holding period、execution semantics
  - 不能改 holding_cohort_count（固定 10）
  - 不能同时改 retention threshold

serial_rule: |
  这轮是 refresh_rule 在 10-cohort 合同下的最终验证。
  只允许 1 个候选。
  如果 retain50 + 10-cohort 仍无法通过 9 gates，
  portfolio_refresh_rule 方向正式关闭。
```
