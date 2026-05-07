# Round Note: Exploratory Intraday Cohort5 Contract Design

## Why This Round Exists

Previous round (`rr_exploratory_intraday_microstructure_independent_baseline_20260501`) showed that all 3 intraday candidates failed prereg success rules. But all passed delta-vs-v18 gates, suggesting the binding constraint was the contract, not signal quality.

The key metric: all candidates had avg_invested_weight ≈ 16% under auto-detected 26-cohort allocation. This round tests whether changing to fixed 5-cohort allocation (each cohort gets 20% capital instead of 3.85%) is sufficient to make the intraday family viable.

## Contract Logic

`holding_cohort_count` determines `cohort_capital_fraction = 1 / holding_cohort_count`.

- 26 cohorts → 3.85% per cohort → single name target = 0.385% of total capital
- 5 cohorts → 20% per cohort → single name target = 2% of total capital

Expected effect: 5.2× increase in per-name target weight → invested_weight from ~16% to ~50-80%.

## Critical Design Decision

This round runs **v18 under the same 5-cohort contract** as a contract-matched baseline, not just the historical 26-cohort v18. This is necessary to distinguish:
- Contract effect (all strategies improve under 5-cohort)
- Intraday signal effect (intraday improves more than v18 under 5-cohort)

## 口径检查

- holding_cohort_count=5 只影响 `cohort_capital_fraction`，不改变执行语义、TopK、持仓提取、刷新规则等任何其他合同要素
- v18_ref_5cohort 与 c1/c2/c3 使用完全相同的 run_state pipeline（build_run_state_skeleton.py → build_portfolio_artifacts.py → build_fixed_test_minimal.py），唯一差异是 `--feature-preset`
- 所有 delta 字段将以 contract-matched v18 为基准（v18_5cohort），而非旧 26-cohort v18
- 4 个候选使用同一 snapshot、同一 contract、同一 execution_logic_version

## Runs

No changes needed to build_baseline_model_scores.py, build_run_state_skeleton.py, or build_fixed_test_minimal.py.
Only `build_portfolio_artifacts.py` needs `--holding-cohort-count 5`.
