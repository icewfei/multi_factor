# rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428 phase summary

## Summary

This round evaluated six mechanism-orthogonal atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract with a composability-first intent.

The final classification is:

- `price_volume_single_signal_overnight_return_bias_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_gap_fill_rate_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_lower_shadow_support_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_downside_semivol_ratio_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_post_downday_volume_recovery_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_intraday_range_efficiency_20d_v1`: `signal_edge_negative`

## Newly retained clean positive keepers

- `price_volume_single_signal_lower_shadow_support_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006151`
  - `avg_daily_ic(平均日IC) = 0.010726`
  - `positive_daily_ic_share(正IC日占比) = 0.545555`
  - `avg_label_top10(前10平均标签) = 0.005563`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005020`
  - `avg_label_bottom10(后10平均标签) = 0.001136`

## Mixed signals

- `price_volume_single_signal_overnight_return_bias_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.003434`
  - `avg_daily_ic(平均日IC) = 0.011864`
  - `positive_daily_ic_share(正IC日占比) = 0.555870`
  - `avg_label_top10(前10平均标签) = -0.001028`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001626`

- `price_volume_single_signal_downside_semivol_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.015265`
  - `avg_daily_ic(平均日IC) = 0.024182`
  - `positive_daily_ic_share(正IC日占比) = 0.581589`
  - `avg_label_top10(前10平均标签) = 0.001741`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004150`

## Rejected signals

- `price_volume_single_signal_gap_fill_rate_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.007426`
  - `avg_daily_ic(平均日IC) = -0.009034`
  - `positive_daily_ic_share(正IC日占比) = 0.428234`
  - `avg_label_top10(前10平均标签) = 0.001071`
  - `avg_label_rank11_20(11-20名平均标签) = 0.002216`
  - `avg_label_bottom10(后10平均标签) = 0.003958`

- `price_volume_single_signal_post_downday_volume_recovery_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.010552`
  - `avg_daily_ic(平均日IC) = -0.016239`
  - `positive_daily_ic_share(正IC日占比) = 0.396128`
  - `avg_label_top10(前10平均标签) = -0.005362`
  - `avg_label_rank11_20(11-20名平均标签) = -0.000872`
  - `avg_label_bottom10(后10平均标签) = 0.005090`

- `price_volume_single_signal_intraday_range_efficiency_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.003758`
  - `avg_daily_ic(平均日IC) = -0.009714`
  - `positive_daily_ic_share(正IC日占比) = 0.449882`
  - `avg_label_top10(前10平均标签) = 0.001261`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001475`
  - `avg_label_bottom10(后10平均标签) = 0.003390`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 9 produced at least one clean positive keeper, so the next step can include a controlled composability screening stage before any family-level promotion.
