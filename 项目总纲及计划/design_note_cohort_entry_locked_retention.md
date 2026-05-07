# Design: Cohort-Entry Locked Retention

**Status:** Design only, not registered.

---

## 1. Problem Recap

Three consecutive method rounds (full refresh → retain15 → retain50) all converged to the same turnover: **~0.399**. Return improved linearly with wider retention bands (-0.194 → -0.136 → -0.064), proving the mechanism has signal value. But turnover flatlined — the daily-recheck semantics prevent structural change.

## 2. Cohort-Entry Locked vs Daily-Recheck

### 当前实现（已测试，失败）

```
Cohort starts on signal_date T:
  rank check at T+1: if rank > threshold → replace
  rank check at T+2: if rank > threshold → replace  
  ...
  always sell on D5 no matter what
```

问题：每天检查 rank →每天都可能替换 →turnover 不变。

### 新设计（Cohort-Entry Locked）

```
Cohort starts on signal_date T:
  entry_rank = rank_at_time_T
  LOCKED: hold until D5 exit regardless of daily rank changes
  (unless stock exits universe, stops trading, or delists)
  Exception guard: retain_if_guard_still_passes (liquidity/tradability)
```

效果：持仓一旦被选入 cohort，在 D1-D5 持有期内锁定，除非股票变得不可交易。这样消除了"每日 rank 重排 → 每日换股"的来源。

### 为什么这更可能真正压缩 turnover

| 来源 | 当前 daily-recheck | Cohort-entry locked | 预期 |
|---|---|---|---|
| 结构性到期 (1/5 per day) | 0.20 | 0.20 | 不变 |
| 每日 rank 重排替换 | ~0.20 | **0.00** | 消除 |
| 提前退出（退市/停牌） | ~0.00 | <0.01 | 忽略 |
| **合计** | **~0.40** | **~0.20** | **目标达成** |

Cohort-entry locked 的预期 turnover ≈ 0.20，恰好等于方法目标（≤0.20）。如果达成，年化 stress 成本从 50% 降到约 25%，cost_stress 可能接近可通过。

### 主要风险

- **Alpha decay**：锁定 5 天可能导致持仓在持有期内变成"坏持仓"——如果 rank 在 D2-D4 急降，也无法退出。但 retain15/retain50 的证据表明 rank≤50 的原持仓在 5 天内大概率仍比新选标的好（return 改善的趋势支持这一点）。

---

## 3. Changed Dimension

**`portfolio_refresh_rule`** — 与前面方法轮相同的 changed_dimension。具体改动是 `refresh_rule_name` 从 `"retain_if_rank_leq"` 变为 `"cohort_entry_locked"`，以及对应的 `portfolio_refresh_contract` 结构。

### 需要改的实现

`build_portfolio_artifacts.py` 中的 `_parse_portfolio_refresh_contract_object` 函数需要新增对 `refresh_rule_name = "cohort_entry_locked"` 的支持：

```
- retain_if_rank_leq: 15/50 → 移除（不再需要每日 rank 检查）
+ lock_duration: 5 (hold until D5 regardless of daily rank)
+ exit_condition: ["scheduled_D5", "delisted", "suspended_long_term"]
```

### Formal Baseline

**`exploratory_cohort5_c1_trendbias_only`（daily full refresh）**——与用户倾向一致。retain15/retain50 保持为辅助诊断证据。

---

## 4. Prereg 草案

```yaml
research_round_id: rr_exploratory_cohort_entry_locked_20260501

research_tier: exploratory
round_type: method_investigation

research_question: >
  将 portfolio_refresh_rule 从 daily-recheck 改为 cohort-entry locked
  （持仓按 cohort 启动时的 rank 锁定 5 天，不再每日重检），
  是否能在保持 return / drawdown 的前提下，
  将 turnover 从 ~0.40 压缩到 ≤0.20，并使 cost_stress 通过？

anchor_signal: intraday trend_bias (same as previous method rounds)
formal_baseline: exploratory_cohort5_c1_trendbias_only (daily full refresh)
diagnostic_evidence: retain15 / retain50 partial findings

changed_dimension: portfolio_refresh_rule
change_control_rule: single_dimension_only
change_detail: >
  将 portfolio_refresh_rule 从 "daily-recheck retention" 替换为
  "cohort-entry locked retention"（持仓在 cohort 启动时锁定，
  持有到 D5 到期或退市/停牌，不再每日重检 rank）。
  不允许改变：score family、TopK(10)、执行语义、成本合同、
  基准、持仓提取规则、purge gap、样本资格矩阵、流动性 guard、
  holding_cohort_count(5)、cash retention/no-replacement。

portfolio_refresh_contract:
  refresh_rule_name: cohort_entry_locked
  lock_duration_signal_dates: 5
  exit_conditions: ["scheduled_D5", "delisted", "suspended_long_term"]
  retain_if_guard_still_passes: true
  retain_if_entry_tradeable: true
  max_holdings: 10
  target_weight_rule: "Equal-weight across currently held names after refresh; unfilled slots remain cash."
  note: >
    Unlike previous retain_if_rank_leq rules, this version does NOT
    recheck rank daily. Holdings are locked at cohort entry.
    This eliminates the daily rank-churn turnover source.

planned_candidates:
  - candidate_scheme_id: exploratory_locked_c1_trendbias
    base_signal: intraday_trend_bias_20d_raw
    refresh_rule: cohort_entry_locked (5-day lock)
    score_rule: percentile_rank(DESC); min_feature_count >= 1

success_rules:
  Same 9 gates as method round:
  - annual_relative_return >= 0.01
  - relative_ir >= 0.30
  - return_delta vs full_refresh >= -0.01
  - avg_invested_weight >= 0.15
  - drawdown_delta vs full_refresh >= -0.05
  - topk_8 >= 0 AND topk_12 >= 0
  - cost_stress >= 0.00
  - avg_turnover_daily <= 0.20

  core_pass_condition: all 9 gates must pass

serial_rule: >
  Cohort-entry locked 作为 portfolio_refresh_rule 方向的最终测试。
  如果仍然失败（turnover 仍 > 0.20），则 portfolio_refresh_rule
  方向正式关闭。
```

---

## 5. Sequential Constraint

```
这是 portfolio_refresh_rule 方向的第三回合。
如果 cohort-entry locked 仍然无法将 turnover 压到 0.20 以下，
该方向正式关闭，不再继续调参。
不开并行分支。
```
