# Learnability Diagnostic Report (20260502)

**Status: frozen.** Phase transition diagnostic. First-round learnability audit complete.

## Research Question
Do any existing features or signals contain non-zero rank correlation with the oracle 5d forward label?

## Success Criterion
|median daily IC| > 0.03 AND bootstrap 95% CI does not cross zero.
Both conditions must hold for a signal to be considered a confirmed pass.

**Criterion note:** The threshold applies to the point estimate (median), not the CI bounds.
A signal passes if its median IC exceeds 0.03 in absolute value AND its CI excludes zero.
The CI is NOT required to lie entirely above 0.03 — a signal with median 0.032 and
CI [0.028, 0.035] passes because |0.032| > 0.03 and 0.028 > 0.

## Results: IC Summary

| Signal | N Days | Full IC | Mean Daily IC [95% CI] | Median Daily IC [95% CI] | Std | Pos Share | Classification |
|---|---|---|---|---|---|---|---|---|
| pv_beta_rank | 5325 | 0.019366 | 0.030725 [0.028035, 0.033374] | 0.030264 [0.027330, 0.033293] | 0.101227 | 0.6190 | **positive_pass** |
| intraday_trend_rank | 5327 | 0.013621 | 0.019292 [0.015776, 0.022680] | 0.016212 [0.012333, 0.020350] | 0.128138 | 0.5536 | **marginal** |
| liq_trend_rank | 5327 | 0.011742 | 0.019244 [0.016533, 0.021924] | 0.022911 [0.019901, 0.025943] | 0.101835 | 0.5876 | **marginal** |
| momentum_rank | 5267 | 0.008586 | 0.013058 [0.009020, 0.016936] | 0.006979 [0.002409, 0.011767] | 0.148479 | 0.5217 | **below_threshold** |
| upside_share_rank | 5327 | 0.009392 | 0.015789 [0.012876, 0.018582] | 0.013773 [0.010021, 0.017366] | 0.106969 | 0.5504 | **marginal** |
| baseline_v1 (5sig equal-weight) | 5327 | 0.017758 | 0.029527 [0.025813, 0.033111] | 0.029716 [0.025534, 0.033917] | 0.136339 | 0.5894 | **marginal** |
| alpha158_cord30 | 5325 | 0.021099 | 0.035785 [0.033504, 0.038033] | 0.032511 [0.029984, 0.034649] | 0.084613 | 0.6661 | **positive_pass** |
| alpha158_corr30 | 5326 | 0.019181 | 0.030307 [0.027810, 0.032783] | 0.031348 [0.028368, 0.034500] | 0.092305 | 0.6431 | **positive_pass** |
| alpha158_imxd5 | 5327 | 0.018795 | 0.035324 [0.032659, 0.037940] | 0.031616 [0.027963, 0.034643] | 0.098611 | 0.6364 | **positive_pass** |
| alpha158_imax20 | 5327 | 0.007080 | 0.013720 [0.010990, 0.016390] | 0.013080 [0.009631, 0.016706] | 0.100178 | 0.5545 | **marginal** |
| alpha158_vsumd60 | 5326 | 0.015118 | 0.024919 [0.022538, 0.027364] | 0.027709 [0.025136, 0.029951] | 0.089462 | 0.6269 | **marginal** |
| intraday_trend_bias (exploratory) | 5327 | 0.013621 | 0.019292 [0.015776, 0.022680] | 0.016212 [0.012333, 0.020350] | 0.128138 | 0.5536 | **marginal** |
| reversal (exploratory) | 5322 | -0.025218 | -0.046434 [-0.049869, -0.042905] | -0.044182 [-0.047901, -0.040470] | 0.128950 | 0.3561 | **sign_inverted_pass** |
| momentum (exploratory) | 5267 | 0.008586 | 0.013058 [0.009020, 0.016936] | 0.006979 [0.002409, 0.011767] | 0.148479 | 0.5217 | **below_threshold** |
| ROE (exploratory) | 4888 | -0.000328 | -0.004976 [-0.010515, 0.000304] | 0.006401 [0.001205, 0.011834] | 0.192032 | 0.5170 | **below_threshold** |
| ROA (exploratory) | 5176 | -0.002623 | -0.008956 [-0.014446, -0.003306] | 0.001733 [-0.003660, 0.008088] | 0.202553 | 0.5029 | **below_threshold** |

## Results: Decile Monotonicity
(avg oracle label by score decile, D1 = highest score)

| Signal | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| pv_beta_rank | 0.006350 | 0.005374 | 0.004932 | 0.004650 | 0.004518 | 0.004252 | 0.003737 | 0.003310 | 0.002693 | 0.001345 |
| intraday_trend_rank | 0.004989 | 0.004703 | 0.004740 | 0.004771 | 0.004704 | 0.004701 | 0.004464 | 0.004036 | 0.003272 | 0.000851 |
| liq_trend_rank | 0.004720 | 0.004752 | 0.004750 | 0.004728 | 0.004756 | 0.004502 | 0.004412 | 0.003894 | 0.003422 | 0.001298 |
| momentum_rank | 0.005086 | 0.004602 | 0.004425 | 0.004261 | 0.004197 | 0.004126 | 0.003904 | 0.003737 | 0.003218 | 0.002862 |
| upside_share_rank | 0.004440 | 0.004681 | 0.004713 | 0.004628 | 0.004544 | 0.004489 | 0.004316 | 0.004029 | 0.003532 | 0.001869 |
| baseline_v1 (5sig equal-weight) | 0.005886 | 0.005176 | 0.004969 | 0.004853 | 0.004604 | 0.004368 | 0.004106 | 0.003520 | 0.002888 | 0.000856 |
| alpha158_cord30 | 0.006025 | 0.005612 | 0.005376 | 0.004933 | 0.004488 | 0.004262 | 0.003797 | 0.003227 | 0.002535 | 0.000902 |
| alpha158_corr30 | 0.005937 | 0.005442 | 0.005072 | 0.004786 | 0.004447 | 0.004256 | 0.003939 | 0.003460 | 0.002877 | 0.000965 |
| alpha158_imxd5 | 0.005045 | 0.005299 | 0.005173 | 0.005326 | 0.005111 | 0.004676 | 0.004094 | 0.003428 | 0.002537 | 0.000539 |
| alpha158_imax20 | 0.003741 | 0.004445 | 0.004644 | 0.004726 | 0.004786 | 0.004730 | 0.004566 | 0.004172 | 0.003690 | 0.001740 |
| alpha158_vsumd60 | 0.005082 | 0.004811 | 0.004764 | 0.004719 | 0.004769 | 0.004715 | 0.004622 | 0.004289 | 0.003480 | -0.000066 |
| intraday_trend_bias (exploratory) | 0.004989 | 0.004703 | 0.004740 | 0.004771 | 0.004704 | 0.004701 | 0.004464 | 0.004036 | 0.003272 | 0.000851 |
| reversal (exploratory) | -0.000687 | 0.001994 | 0.003448 | 0.004216 | 0.004825 | 0.005103 | 0.005484 | 0.005642 | 0.005875 | 0.005458 |
| momentum (exploratory) | 0.005086 | 0.004602 | 0.004425 | 0.004261 | 0.004197 | 0.004126 | 0.003904 | 0.003737 | 0.003218 | 0.002862 |
| ROE (exploratory) | 0.003970 | 0.004278 | 0.004823 | 0.004228 | 0.004341 | 0.004517 | 0.004214 | 0.004465 | 0.004260 | 0.004375 |
| ROA (exploratory) | 0.004149 | 0.004311 | 0.003992 | 0.004230 | 0.004043 | 0.004382 | 0.004363 | 0.004612 | 0.004602 | 0.004718 |

## Classification Key

| Class | Meaning |
|---|---|
| positive_pass | |median IC| > 0.03, CI not crossing zero, positive direction |
| sign_inverted_pass | |median IC| > 0.03, CI not crossing zero, negative direction (anti-oracle) |
| threshold_met_ci_overlaps_zero | |median IC| > 0.03 but CI crosses zero — threshold met but not confirmed |
| marginal | 0.01 < |median IC| <= 0.03 |
| below_threshold | |median IC| <= 0.01 |

## Interpretation

### Confirmed positive passes (|median IC| > 0.03, CI clear of zero, positive direction)
- **pv_beta_rank**: median IC = 0.0303 [0.0273, 0.0333]
- **alpha158_cord30**: median IC = 0.0325 [0.0300, 0.0346]
- **alpha158_corr30**: median IC = 0.0313 [0.0284, 0.0345]
- **alpha158_imxd5**: median IC = 0.0316 [0.0280, 0.0346]

### Sign-inverted candidates (|median IC| > 0.03, CI clear of zero, negative direction)
These signals are negatively correlated with oracle forward returns. They are NOT directly usable in a positive-score compositing pipeline, but represent information that could be inverted or used as a contra signal.
- **reversal (exploratory)**: median IC = -0.0442 [-0.0479, -0.0405]

### Marginal (0.01 < |median IC| <= 0.03)
- intraday_trend_rank: median IC = 0.0162
- liq_trend_rank: median IC = 0.0229
- upside_share_rank: median IC = 0.0138
- baseline_v1 (5sig equal-weight): median IC = 0.0297
- alpha158_imax20: median IC = 0.0131
- alpha158_vsumd60: median IC = 0.0277
- intraday_trend_bias (exploratory): median IC = 0.0162

### Below threshold (|median IC| <= 0.01)
- momentum_rank: median IC = 0.0070
- momentum (exploratory): median IC = 0.0070
- ROE (exploratory): median IC = 0.0064
- ROA (exploratory): median IC = 0.0017

## Decision

- 4 signal(s) fully meet the success criterion (positive_pass).
- 1 signal(s) meet threshold and CI requirements in the negative direction (sign-inverted).
  These are informative but cannot enter the current positive-score compositing pipeline directly.

### Bottom line

Current feature space contains **weak but non-zero oracle-related information**.
The strongest signals have |median IC| in the 0.03-0.04 range with CIs that exclude zero,
confirming the information is real but its magnitude is small.

**This justifies a narrow, family-focused feature engineering round** on the positive-pass
families (price-volume correlation) before considering new data sources.
It does NOT rule out future data acquisition — 0.03 IC is still weak,
and if feature engineering on current families plateaus without improvement,
expanding to new data modalities remains a live option.

The sign-inverted candidate (reversal) should be evaluated separately:
either inverted before compositing, or treated as a hedge/contra input
rather than a standard positive-alpha signal.

Generated: 20260502
Bootstrap: 10000 resamples, seed=42
