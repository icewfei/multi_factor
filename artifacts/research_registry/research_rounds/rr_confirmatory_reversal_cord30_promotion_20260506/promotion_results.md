# Reversal + Cord30 Promotion Results

- `research_round_id = rr_confirmatory_reversal_cord30_promotion_20260506`
- `generated_at = 2026-05-06T11:54:45+08:00`

## Candidate vs Baseline

- `baseline_candidate_scheme_id = reversal_tail_exclude_p98_v1`
- `candidate_scheme_id = reversal_p98_cord30_ew_v1`

## Validation deltas vs baseline

- `validation_annual_relative_return_delta = -0.020932`
- `validation_relative_ir_delta = -0.100452`
- `validation_max_drawdown_delta = 0.020746`
- `validation_avg_turnover_daily_delta = -0.013927`
- `cost_stress_annual_relative_return_delta = 0.015021`
- `low_liquidity_weight_share_delta = 0.013048`
- `topk8_annual_relative_return_delta = 0.003449`
- `topk12_annual_relative_return_delta = 0.010007`

## Rule evaluation

- `validation_annual_relative_return_delta_gt_0 = false`
- `validation_relative_ir_delta_gt_0 = false`
- `validation_max_drawdown_delta_ge_0 = true`
- `cost_stress_annual_relative_return_delta_ge_0 = true`
- `topk8_annual_relative_return_delta_gt_0 = true`
- `topk12_annual_relative_return_delta_gt_0 = true`
- `validation_avg_turnover_daily_delta_le_002 = true`
- `low_liquidity_weight_share_delta_le_0 = false`
- `candidate_avg_invested_weight_ge_018 = true`

## Decision

- `round_decision = KEEP_P98_BASELINE`
- `verdict = fail`
