# Overnight/Intraday Decomposition — Learnability Diagnostic
Generated: 20260506

## p98 Baseline: median daily IC = 0.046045

## Results

| Scheme | Median IC [95% CI] | Top10 Label | Spread | Corr w/ p98 | Classification |
|---|---|---|---|---|---|---|
| p98 (reversal baseline) | 0.046045 [0.042276, 0.049974] | 0.007474 | 0.004785 | N/A | **baseline** |
| overnight_rev_5d_v1 | -0.013648 [-0.016016, -0.011817] | 0.004375 | 0.009522 | -0.1816 | **marginal** |
| intraday_rev_5d_v1 | -0.036641 [-0.040229, -0.033580] | -0.005403 | -0.009821 | -0.8581 | **threshold_met_ci_issues** |
| overnight_rev_20d_v1 | -0.012454 [-0.014799, -0.010164] | 0.002321 | 0.003008 | -0.0837 | **marginal** |
| intraday_rev_20d_v1 | -0.016212 [-0.020350, -0.012333] | -0.002148 | -0.008642 | -0.3515 | **marginal** |
| overnight_vol_5d_v1 | 0.008258 [0.004937, 0.012010] | 0.003140 | 0.001648 | 0.0252 | **below_threshold** |
| overnight_intraday_divergence_v1 | -0.011357 [-0.013214, -0.009564] | 0.003944 | 0.004817 | -0.0879 | **marginal** |
| overnight_p98_ew_v1 | 0.023048 [-0.001722, 0.102409] | 0.005899 | 0.009121 | 0.6436 | **marginal** |
| intraday_p98_ew_v1 | 0.008412 [0.007110, 0.009884] | 0.003478 | -0.001918 | 0.2930 | **below_threshold** |
| overnight_intraday_ew_v1 | -0.041772 [-0.045688, -0.037743] | -0.003381 | -0.006998 | -0.8533 | **threshold_met_ci_issues** |
| overnight70_p98_30_v1 | 0.003189 [-0.029579, 0.122229] | 0.005148 | 0.009009 | 0.2468 | **below_threshold** |
| intraday70_p98_30_v1 | -0.024920 [-0.027472, -0.021564] | 0.002042 | -0.003375 | -0.6355 | **marginal** |

## Recommendations

- SKIP: overnight_rev_5d_v1 — marginal IC, not worth full-chain
- SKIP: overnight_rev_20d_v1 — marginal IC, not worth full-chain
- SKIP: intraday_rev_20d_v1 — marginal IC, not worth full-chain
- SKIP: overnight_intraday_divergence_v1 — marginal IC, not worth full-chain
- SKIP: overnight_p98_ew_v1 — marginal IC, not worth full-chain
- SKIP: intraday70_p98_30_v1 — marginal IC, not worth full-chain
