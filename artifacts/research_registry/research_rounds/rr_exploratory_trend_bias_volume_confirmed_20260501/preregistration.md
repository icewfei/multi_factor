# Preregistration: Volume-Confirmed Intraday Trend Bias

- `research_round_id`: `rr_exploratory_trend_bias_volume_confirmed_20260501`
- `research_tier`: `exploratory`
- `round_type`: `signal_conditioning_investigation`
- `status`: `preregistered`

## Changed Dimension

`score_activation_condition` — adding a volume gate to the existing trend_bias signal.

## Gate Definition

| Field | Value |
|---|---|
| Variable | `volume_ratio_20d = raw_amount / median_20d_excluding_current` |
| Threshold | `> 1.0` (strict greater) |
| Window | Rolling 20 trading days, current day excluded |
| Amount unit | thousand CNY (Tushare Pro convention) |
| Gate failure | `model_score_D0 = NULL`, retained in audit |

## Baseline Reference

`exploratory_cohort5_c1_trendbias_only` — same contract (`holding_cohort_count=5`), same signal (`intraday_trend_bias`), no gate.

## Candidate

Single candidate: `exploratory_trend_bias_volume_gated_v1`

## Success Rules

Same 9 gates as previous round (cross-candidate comparability). All delta rules reference the contract-matched baseline (`c1_5cohort`, no gate).
