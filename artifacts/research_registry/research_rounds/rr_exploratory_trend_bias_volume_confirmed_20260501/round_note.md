# Round Note: Volume-Confirmed Intraday Trend Bias

## Why This Round Exists

Previous two rounds:
1. 26-cohort: intraday family 5/9, failed topk_perturbation
2. 5-cohort: intraday family 6/9, topk fixed but cost_stress and absolute return still failed

The remaining bottleneck is signal-level, not contract-level. This round tests whether conditioning intraday_trend_bias on a volume regime (high volume = lower cost + higher signal quality) can close the gap.

## Expected Mechanism

- High-volume stocks have lower trading costs (smaller bid-ask spread, less slippage)
- High-volume intraday trends are more likely genuine order-flow imbalance (less noise)
- Gate removes low-conviction trading days from the ranking pool
- Fewer names traded → lower cumulative costs → better cost_stress

## If This Round Also Fails

This will be the third consecutive failure for the intraday microstructure direction. The recommendation would be to formally close this research direction.
