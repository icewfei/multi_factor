# pv-corr Family Engineering Round 1 — Results (20260502)

## Baseline: alpha158_cord30
- Median daily IC: 0.032511
- 95% CI: [0.029984, 0.034649]
- Mean daily IC: 0.035785
- N days: 5325

## Candidate Results

| Candidate | Full IC | Mean Daily IC | Median Daily IC [95% CI] | Std | N Days | Median Δ vs cord30 | Top10-Bot10 Spread | Tier 1 | Tier 2 |
|---|---|---|---|---|---|---|---|---|---|
| pv_corr_ensemble_v1 | 0.022058 | 0.037528 | 0.034045 [0.031375, 0.037288] | 0.088953 | 5325 | +0.001534 | 0.008848 | **FAIL** | **FAIL** |
| pv_corr_delta_v1 | -0.001184 | -0.002530 | -0.000323 [-0.002587, 0.001695] | 0.069201 | 5316 | -0.032834 | 0.001603 | **FAIL** | **FAIL** |

## Decile Monotonicity

| Candidate | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| pv_corr_ensemble_v1 | 0.006221 | 0.005712 | 0.005300 | 0.004908 | 0.004651 | 0.004126 | 0.003743 | 0.003153 | 0.002572 | 0.000839 |
| pv_corr_delta_v1 | 0.003838 | 0.004088 | 0.004132 | 0.004104 | 0.004021 | 0.004182 | 0.004250 | 0.004357 | 0.004315 | 0.003959 |

## Success Criteria

| Rule | Definition |
|---|---|
| Tier 1 | median daily IC >= 0.040, 95% CI excludes zero |
| Tier 2 | median IC delta >= +0.005 over alpha158_cord30 |

## Family Verdict

**pv-corr family near saturation; reopen data acquisition discussion**

Generated: 20260502
