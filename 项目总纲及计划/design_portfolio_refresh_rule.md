# Design: Portfolio Refresh Rule — Turnover Reduction Round

**Status:** Design only, not registered.

**Preceded by:** break_even_cost_budget_analysis (2026-05-01), which found that cost_stress >= 0.00 requires ~50% annualized gross alpha under current 0.39 turnover × 40bp stress slippage. All 5 previous rounds failed at cost_stress for this structural reason, not signal quality.

---

## 1. Research Question

> 在当前 5-cohort + daily percentile-rank + TopK framework 下，单独引入 incumbent-retention 型 portfolio_refresh_rule，是否能在不显著破坏 return / IR / invested_weight 的前提下，实质性压缩 turnover 并改善 cost_stress？

### 具体而言

| 指标 | 当前（5-cohort, daily refresh） | 目标 |
|---|---|---|
| avg_turnover_daily | ~0.39 | < 0.20 |
| cost_stress_return | -0.076 (intraday c1) | > 0.00 |
| annual_relative_return | -0.194 (intraday c1) | not materially worse |

---

## 2. Candidate Refresh Rules

### 候选 A：Rank-15 retention band（推荐首选）

| 字段 | 值 |
|---|---|
| 规则 | 现有持仓如果当期排名 ≤ 15，则保留（不替换）。仅当排名 > 15 时才被替换。 |
| 与 v18 的关系 | v18 也用了 `top-15 retention band`，但那次是在 26-cohort + 不同 score family 下。本轮在 5-cohort + intraday trend_bias 下重新测试。 |
| 预期 turnover 压缩 | 从 0.39 降至约 0.15-0.20（约 50-60% 压缩） |
| 预期 cost_stress | 从 -0.076 提升至约 -0.02 到 +0.02（接近通过） |

### 候选 B：Retain_all_incumbents（极端版本）

| 字段 | 值 |
|---|---|
| 规则 | 全部现有持仓无条件保留。仅当持仓自然退出（D5 到期卖出）后才用新选标的补位。 |
| 风险 | 可能完全失去对新信号的响应能力，属于过拟合方向 |
| 优先级 | 仅在候选 A 效果不足时考虑 |

### 候选 C：Rank-change threshold

| 字段 | 值 |
|---|---|
| 规则 | 仅当持仓排名下降超过 X 位（如 10 位）时才替换 |
| 复杂度 | 阈值需要调参，引入额外自由度 |

### 为什么选 A

1. **已有先例**：v18 使用过相同的 top-15 retention 逻辑，但当时在 26-cohort + 动量+流动性下效果不明显。在 5-cohort 高仓位下效果可能完全不同。
2. **单一参数、干净因果链**：不涉及调参、不涉及组合逻辑变化
3. **直接命中最根本的换手来源**：当前换手主要来自"每日全量刷新→每天 TopK 头部都在变→每天买卖"。保留 rank ≤ 15 的持仓可以直接消除"第 10 名到第 11 名之间的噪声换手"。

**主要风险组合：**
- 如果保留的旧持仓（rank 11-15）performance 不好，会拖累 return
- 如果换手降得不够多（仍 > 0.25），cost_stress 可能仍然不过

---

## 3. Anchor Signal Selection

### 推荐：Intraday c1（`intraday_trend_bias_20d_raw`）

| 候选 | 上一轮 6/9 | cost_stress | return | 理由 |
|---|---|---|---|---|
| **intraday c1 ✅** | 6/9 | **-0.076**（最佳） | -0.194 | 单信号，诊断最干净 |
| intraday c3 | 6/9 | -0.089 | **-0.157**（最佳） | 多信号组合，混淆 refresh 和 composability 效应 |
| fundamental c1 | 6/9 | -0.159 | -0.325 | return 太弱，refresh 可能掩盖信号问题 |

**为什么选 intraday c1：**
- 单信号 → 诊断最干净。如果 turnover 下降后 cost_stress 改善，可以归因于 refresh rule，不是信号交互
- 上一轮 cost_stress **最接近 0**（-0.076），说明它最可能通过 refresh 后达到 0
- 如果用 c3（3 信号），即使 cost_stress 改善了，也说不清是 refresh 的作用还是 reversal_asymmetry 的贡献

---

## 4. Prereg 草案

```yaml
research_round_id: rr_exploratory_refresh_rule_turnover_reduction_20260501

research_tier: exploratory
round_type: method_investigation

research_question: >
  在 5-cohort + intraday trend_bias + TopK framework 下，
  仅将 portfolio_refresh_rule 从 daily_full_refresh 改为 top15_retention_band，
  能否在保持 return / IR / invested_weight 的前提下，
  将 turnover 从 0.39 压低到 0.20 以下，使 cost_stress 从 -0.076 提升到 >= 0.00？

anchor_signal: intraday trend_bias (single_signal_intraday_trend_bias)
anchor_candidate: intraday c1 (same as exploratory_cohort5_c1_trendbias_only)

baseline_reference_candidate_scheme_id: exploratory_cohort5_c1_trendbias_only
  (formal baseline — same signal, same 5-cohort contract, daily full refresh)
secondary_diagnostic_anchor: exploratory_cohort5_v18_ref
  (secondary anchor for context, NOT used for formal delta comparison)

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

contract_params:
  holding_cohort_count: 5
  score_builder: build_baseline_model_scores.py

changed_dimension: portfolio_refresh_rule
change_control_rule: single_dimension_only
change_detail: >
  仅改变 portfolio_refresh_rule：从 daily_full_refresh 改为
  retain_if_rank_leq_15（现有持仓在当期排名 <= 15 时保留）。
  不允许改变：score family（仅 intraday_trend_bias）、TopK(10)、
  执行语义、成本合同、基准、持仓提取规则（equal_weight_top10）、
  purge gap、样本资格矩阵、流动性 guard、holding_cohort_count(5)、
  cash retention / no-replacement。

planned_candidates:
  - candidate_scheme_id: exploratory_refresh_c1_retain15
    base_signal: intraday_trend_bias_20d_raw
    refresh_rule: retain_if_current_rank <= 15
    score_rule: percentile_rank(DESC); min_feature_count >= 1
    description: >
      Intraday trend_bias with top-15 incumbent retention.
      Current refresh: daily full replacement of all TopK positions.
      New refresh: incumbents ranked <= 15 are retained.
      Only incumbents ranked > 15 or positions where the stock-day
      is no longer ranking_eligible are replaced.

refresh_rule_definition:
  type: retain_if_rank_leq
  threshold: 15
  max_holdings: 10
  retain_if_guard_still_passes: true
    (持仓保留仅当该股票在当期仍满足 ranking_eligibility 和流动性 guard)
  retain_if_entry_tradeable: true
    (保留的持仓在 D1 开盘仍需满足可交易条件；不可买时保留现金，不补位)
  target_weight_rule: equal-weight across currently held names after refresh
    (刷新后所有持仓等权；未填满的 slot 保留为现金)
  refresh_timing: daily, after new signal date scores are available
  current_rule: daily_full_refresh — all TopK positions replaced each signal date
  new_rule: >
    O = current holdings at signal_date t-1 (still active)
    H = TopK new selections at signal_date t
    F = {i in O | rank_i(t) <= 15}  (incumbents retained)
    N = {i in H | i not in F}  (new entries filling remaining slots)
    final_holdings_t = F + first(|H| - |F|, N)  (cap at TopK=10)
    unfilled slots → cash, no replacement

success_rules:
  pass_validation_annual_relative_return: annual_relative_return >= 0.01
  pass_validation_relative_ir: relative_ir >= 0.30
  pass_not_worse_than_baseline: annual_relative_return_delta_vs_c1_5cohort >= -0.01
    (formal baseline: exploratory_cohort5_c1_trendbias_only, same signal, daily full refresh)
  pass_avg_invested_weight: avg_invested_weight >= 0.15
  pass_max_drawdown_not_worse: max_drawdown_delta_vs_c1_5cohort >= -0.05
  pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
  pass_cost_stress: cost_stress_annual_relative_return >= 0.00
  pass_turnover_absolute: avg_turnover_daily <= 0.20
    (替换旧 turnover_delta gate。本轮是方法轮，直接打绝对 turnover 目标)

  core_pass_condition: all 9 gates must pass

forbidden:
  - 不能增加第二个 refresh rule 候选
  - 不能改动 score family
  - 不能改动 TopK、提取规则、合同参数
  - 不能将 retention threshold（15）在运行中调整
  - 不能根据结果调整 threshold 后重试
```

---

## 5. Serial Constraint

```
这是方法轮，不是新信号轮。
只允许 1 条主线：top15_retention_band。
只允许 1 个 anchor signal：intraday trend_bias（c1）。
不并行展开 refresh rule 家族。
不改任何信号相关代码。
不改任何合同参数。
```

---

## 6. Verdict Interpretation

| avg_turnover | cost_stress | return_delta | 解读 |
|---|---|---|---|
| <= 0.20 | >= 0.00 | >= -0.01 | **方法成功**。换手压缩到阈值内，cost_stress 通过，return 未显著损失 |
| <= 0.20 | >= 0.00 | < -0.01 | 换手降了、stress 过了、但 return 损失大 → trade-off 存在 |
| > 0.20, < 0.30 | >= -0.05 | >= -0.01 | 部分改善但不足 → 考虑更强的 retention（如 retain all） |
| > 0.30 | — | — | retention 无效 → 根因不在 refresh |
