# Design Note: Higher Invested-Weight Contract for Intraday Microstructure Signals

**Status:** Design only, not yet registered.

**Previous round:** `rr_exploratory_intraday_microstructure_independent_baseline_20260501` — `completed_intraday_family_not_viable`

---

## 1. Background

Previous round verdict: all 3 intraday candidates failed the same 4 gates (absolute return, IR, topk_perturbation, cost_stress) while passing all delta-vs-v18 gates. Root cause diagnosed as: contract-produced low invested_weight (~16%) under `holding_cohort_count = 26`.

### Why holding_cohort_count = 26 → 5 is the single most impactful change

**The mechanism:**

| 参数 | 26-cohort | 5-cohort | 变化倍率 |
|---|---|---|---|
| `cohort_capital_fraction` | 1/26 = 3.85% | 1/5 = 20% | 5.2× |
| 单标的最多总资本占比 | 3.85% × 1/10 = 0.385% | 20% × 1/10 = 2% | 5.2× |
| 预期 avg_invested_weight | ~16% | ~50-80% | 3-5× |

**为什么不是其他维度：**

| 维度 | 为什么不选 |
|---|---|
| 顺位补位 | 总纲宪法级规则（3.2A: "不得顺位补位"），制度成本高于参数调整 |
| TopK | 增大 TopK 虽能增加持仓数，但对单标的权重的杠杆弱于 cohort 调整 |
| refresh hysteresis / extraction | 这些是 portfolio-layer 微调，不是 invested-weight 的根本杠杆 |

Cohort count 是**总纲附录 A 的参数级治理规则**（`cohort_capital_fraction`），允许版本化修订，是改变 invested-weight 最直接、最干净的单参数杠杆。

---

## 2. Research Question

> 在保持 score family（intraday microstructure signals）和所有其他合同要素不变的前提下，
> 仅将 `holding_cohort_count` 从 26（auto-detected）改为 5（fixed），
> **在同合同下并行评估 v18 baseline 与 intraday c1/c2/c3**，
> 判断两项：
> - **Layer A**：intraday family 在新合同下是否从 "not viable" 变为 "viable"
> - **Layer B**：在同一新合同下，intraday family 相对 v18(contract-matched) 是否更优

---

## 3. Round Positioning

- `research_tier`: exploratory
- `round_type`: contract_design_exploratory
- `changed_dimension`: portfolio_contract_parameter
- `changed_parameter`: holding_cohort_count (26 → 5)
- `single_dimension_only`: true

这不是 confirmatory（没有已存在的 winner）。这不是 signal discovery（信号本身已测过）。
这是：**在改了一个合同参数后，对所有相关候选做平行重新评估。**

---

## 4. Planned Runs（4 个，并行独立）

| Run | Score Family | holding_cohort_count | 角色 |
|---|---|---|---|
| v18_ref_5cohort | [momentum_60_5, liquidity_trend_20_60] | 5 | **contract-matched baseline** |
| intraday_c1_5cohort | [intraday_trend_bias] | 5 | 单信号测试 |
| intraday_c2_5cohort | [trend_bias, upside_share] | 5 | 双信号测试 |
| intraday_c3_5cohort | [trend_bias, upside_share, reversal_asym] | 5 | 3 信号完整测试 |

### v18_ref_5cohort 的必要性

没有它就无法区分 Layer A vs Layer B：
- 如果 4 个候选全部通过 success rules → 结论是 "合同本身救了所有策略"（不是 intraday 信号的功劳）
- 如果只有 c1/c2/c3 通过而 v18_ref_5cohort 没通过 → 结论是 "合同改善了条件，且 intraday 信号有增量"
- 如果 4 个全部失败 → 结论是 "合同不是唯一约束，信号层面仍不足"

### 不改变的其他要素

TopK=10、执行语义（D0→D5）、成本合同、基准、持仓提取规则（equal-weight Top10）、
组合刷新规则（refresh hysteresis）、purge gap、样本资格矩阵、流动性 guard（0.70）、
cash retention / no-replacement、预处理合同（mad_clip_5, robust_zscore, neutralization=none）

---

## 5. Prereg 草案

```yaml
research_round_id: rr_exploratory_intraday_cohort5_contract_design_20260501

research_tier: exploratory
round_type: contract_design_exploratory

research_question: >
  在保持 score family 和所有其他合同要素不变的前提下，
  仅将 holding_cohort_count 从 auto-detected (26) 改为 fixed 5，
  intraday microstructure independent baseline 是否从 "not viable"
  变为 "viable"（Layer A），以及在同一新合同下，intraday family
  相对 v18(contract-matched) 是否更优（Layer B）？

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

score_builder: build_baseline_model_scores.py
  (复用现有 presets，无需修改)

changed_dimension: portfolio_contract_parameter
change_control_rule: single_dimension_only
change_detail: >
  只改变 holding_cohort_count 从 auto-detected 值改为 5
  （通过 build_portfolio_artifacts.py 的 --holding-cohort-count 参数）。
  不允许改变：score family、TopK(10)、执行语义、成本合同、基准、
  持仓提取规则、组合刷新规则、purge gap、样本资格矩阵、
  流动性 guard、cash retention / no-replacement 规则。

baseline_reference:
  candidate_scheme_id: price_volume_v18_refresh_hysteresis
  contract: holding_cohort_count = 5 (new, contract-matched)
  note: >
    与上一轮不同，baseline_reference 必须在同一新合同下运行。
    旧合同下的 v18 结果仅作为背景参考，不作为 success rules 的比较基准。

planned_candidates:

  - candidate_scheme_id: exploratory_cohort5_v18_ref
    score_preset: price_volume_v16_remove_trend_consistency
    feature_set: [momentum_60_5_raw, liquidity_trend_20_60_raw]
    contract: holding_cohort_count = 5
    role: contract-matched baseline reference
    note: >
      "v18 under 5-cohort contract" — 控制合同本身对结果的影响。
      如果这个候选也通过 success rules，说明合同改动是唯一原因，
      不能归因于 intraday signals。

  - candidate_scheme_id: exploratory_cohort5_c1_trendbias_only
    score_preset: single_signal_intraday_trend_bias
    feature_set: [intraday_trend_bias_20d_raw]
    contract: holding_cohort_count = 5
    min_feature_count: 1

  - candidate_scheme_id: exploratory_cohort5_c2_trendbias_upsideshare
    score_preset: intraday_trend_bias_upside_share_2sig
    feature_set: [intraday_trend_bias_20d_raw, upside_range_share_20d_raw]
    contract: holding_cohort_count = 5
    min_feature_count: 2

  - candidate_scheme_id: exploratory_cohort5_c3_trendbias_upsideshare_reversalasym
    score_preset: intraday_full_microstructure_3sig
    feature_set: [intraday_trend_bias_20d_raw, upside_range_share_20d_raw, intraday_reversal_asymmetry_20d_raw]
    contract: holding_cohort_count = 5
    min_feature_count: 3

success_rules:
  两轮 success rules 保持一致，保证跨合同可比性。

  pass_validation_annual_relative_return: annual_relative_return >= 0.01
  pass_validation_relative_ir: relative_ir >= 0.30
  pass_not_worse_than_contract_matched_baseline: >
    annual_relative_return_delta_vs_v18_5cohort >= -0.005
    # 注意：基线是 contract-matched v18（5-cohort），不是旧 26-cohort v18
  pass_avg_invested_weight: avg_invested_weight >= 0.15
  pass_max_drawdown_not_worse: max_drawdown_delta_vs_v18_5cohort >= -0.05
  pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
  pass_cost_stress: cost_stress_annual_relative_return >= 0.00
  pass_turnover_not_materially_worse: avg_turnover_daily_delta_vs_v18_5cohort <= 0.04

  core_pass_condition: all 8 gates must pass

  两层判定逻辑（phase summary 中使用，不写入 pass/fail verdict）:
    Layer A (viability): >
      any intraday candidate (c1/c2/c3) passes core_pass_condition
      under 5-cohort contract
    Layer B (relative superiority): >
      best intraday candidate has positive delta_vs_v18_5cohort
      AND passes core_pass_condition while v18_ref_5cohort does not

forbidden:
  - 不能新增第五个候选
  - 中途不能更换候选名单
  - 不能查看 2022-2025 测试集
  - 不能改动 score family（禁止将 intraday 信号与 momentum/liquidity_trend 混合）
  - 不能改动 TopK（固定 10）
  - 不能改动 refresh hysteresis
  - 不能改动流动性 guard（0.70）
  - 不能启用顺位补位
  - 不能改变信号预处理合同
  - 不能新增中性化
  - 不能在运行中途更改 holding_cohort_count

relationship_to_previous_round:
  previous_round: rr_exploratory_intraday_microstructure_independent_baseline_20260501
  previous_status: completed_intraday_family_not_viable
  relationship: same score family, different capital allocation contract (parallel, not supersede)
```

---

## 6. Verdict Interpretation Guide

### Layer A: New contract → viability?

| 结果 | 解读 |
|---|---|
| c1/c2/c3 任一通过 | Intraday signals 在新合同下 viable → 问题确认在旧合同 |
| 全部失败 | 即使换了合同，intraday independent baseline 也不可行 → 方向关闭 |

### Layer B: Relative to contract-matched v18

| 结果 | 解读 |
|---|---|
| Intraday 通过且 v18_ref_5cohort 未通过 | Intraday 信号在合同之上有独立增量信息 |
| Intraday 和 v18_ref_5cohort 都通过 | 合同本身救了所有策略；需进一步区分质量和合同贡献 |
| 都未通过 | 问题不在合同，在信号或组合层其他维度 |

### 不提前承诺的含义

不提前承诺 "如果 4 个候选都通过就直接进入 confirmatory"——必须等结果出来后再判断。
