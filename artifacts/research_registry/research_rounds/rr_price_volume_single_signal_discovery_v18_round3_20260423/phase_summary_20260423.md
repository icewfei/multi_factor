# rr_price_volume_single_signal_discovery_v18_round3_20260423 phase summary

## Summary

This round evaluated four additional atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

The final classification is:

- `price_volume_single_signal_liquidity_trend_60_120_v1`: `signal_edge_positive`
- `price_volume_single_signal_momentum_250_20_v1`: `signal_edge_negative`
- `price_volume_single_signal_trend_consistency_60d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_momentum_20_5_v1`: `signal_edge_mixed`

## Key Findings

### Newly retained clean positive keeper

- `price_volume_single_signal_liquidity_trend_60_120_v1`
  - `full_sample_corr_ic(全样本IC) = 0.008324`
  - `avg_daily_ic(平均日IC) = 0.013666`
  - `positive_daily_ic_share(正IC日占比) = 0.555153`
  - `avg_label_top10(前10平均标签) = 0.006167`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005726`
  - `avg_label_bottom10(后10平均标签) = 0.000994`

This signal is a clean positive keeper and should enter the next family-construction pool.

### Rejected signal

- `price_volume_single_signal_momentum_250_20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.000253`
  - `avg_daily_ic(平均日IC) = -0.000670`
  - `positive_daily_ic_share(正IC日占比) = 0.489024`
  - `avg_label_top10(前10平均标签) = 0.002782`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003568`
  - `avg_label_bottom10(后10平均标签) = 0.003961`

This longer-horizon trend hypothesis did not produce usable positive edge and should be rejected.

### Mixed signals

- `price_volume_single_signal_trend_consistency_60d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.004400`
  - `avg_daily_ic(平均日IC) = 0.005803`
  - `positive_daily_ic_share(正IC日占比) = 0.514713`
  - `avg_label_top10(前10平均标签) = 0.002922`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003954`

- `price_volume_single_signal_momentum_20_5_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007226`
  - `avg_daily_ic(平均日IC) = 0.008331`
  - `positive_daily_ic_share(正IC日占比) = 0.515549`
  - `avg_label_top10(前10平均标签) = 0.000268`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003301`

Both signals showed weak positive broad ordering, but their `head_slice(头部切片)` was materially worse than `rank11_20(11-20名)`, so neither should be promoted as a clean keeper.

## Decision

Round 3 produced exactly one new clean positive keeper: `liquidity_trend_60_120_raw`.

That is enough new information to reopen family construction. The next step should not be another pool-expansion round. Instead, the project should return to a new family-construction round using the retained atomic pool and explicitly test whether the longer-horizon liquidity-improvement signal is a better partner than `liquidity_trend_20_60_raw` under the frozen `v18` portfolio contract.

## Recommended Next Direction

Open a new family-construction round rather than continuing single-signal expansion.

Recommended first candidate shape:

- keep `momentum_60_5_raw`
- replace `liquidity_trend_20_60_raw` with `liquidity_trend_60_120_raw`
- do not reintroduce `trend_consistency_20d_raw`
- do not add any mixed or negative signals from round 2 or round 3

In other words, the most natural next candidate is a direct family-level substitution test, not another discovery-only batch.
