# rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428 phase summary

## Summary

This round evaluated ten more orthogonal atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract after both round7 keepers returned mixed composability screens against the v18 core family.

The final classification is:

- `price_volume_single_signal_overnight_strength_share_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_overnight_intraday_consistency_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_downside_gap_fill_ratio_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_signed_turnover_imbalance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_amount_entropy_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_range_expansion_followthrough_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_low_break_recovery_rate_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_high_open_hold_ratio_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_overnight_gap_stability_20d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005550`
  - `avg_daily_ic(平均日IC) = 0.007620`
  - `positive_daily_ic_share(正IC日占比) = 0.534152`
  - `avg_label_top10(前10平均标签) = 0.004405`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004197`
  - `avg_label_bottom10(后10平均标签) = 0.001418`

- `price_volume_single_signal_high_open_hold_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005027`
  - `avg_daily_ic(平均日IC) = 0.007099`
  - `positive_daily_ic_share(正IC日占比) = 0.546270`
  - `avg_label_top10(前10平均标签) = 0.004374`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004370`
  - `avg_label_bottom10(后10平均标签) = 0.002458`

## Mixed signals

- `price_volume_single_signal_overnight_strength_share_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.003101`
  - `avg_daily_ic(平均日IC) = 0.011005`
  - `positive_daily_ic_share(正IC日占比) = 0.568461`
  - `avg_label_top10(前10平均标签) = 0.000633`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003510`

- `price_volume_single_signal_downside_gap_fill_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005232`
  - `avg_daily_ic(平均日IC) = 0.006654`
  - `positive_daily_ic_share(正IC日占比) = 0.534624`
  - `avg_label_top10(前10平均标签) = 0.003200`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003966`

- `price_volume_single_signal_signed_turnover_imbalance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005114`
  - `avg_daily_ic(平均日IC) = 0.008009`
  - `positive_daily_ic_share(正IC日占比) = 0.529976`
  - `avg_label_top10(前10平均标签) = 0.002845`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003037`

- `price_volume_single_signal_range_expansion_followthrough_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.020858`
  - `avg_daily_ic(平均日IC) = 0.028979`
  - `positive_daily_ic_share(正IC日占比) = 0.630370`
  - `avg_label_top10(前10平均标签) = 0.003877`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005163`

- `price_volume_single_signal_low_break_recovery_rate_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007531`
  - `avg_daily_ic(平均日IC) = 0.010822`
  - `positive_daily_ic_share(正IC日占比) = 0.551017`
  - `avg_label_top10(前10平均标签) = 0.003136`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004004`

- `price_volume_single_signal_overnight_gap_stability_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.007107`
  - `avg_daily_ic(平均日IC) = -0.008187`
  - `positive_daily_ic_share(正IC日占比) = 0.467338`
  - `avg_label_top10(前10平均标签) = 0.000490`
  - `avg_label_rank11_20(11-20名平均标签) = 0.000428`

## Rejected signals

- `price_volume_single_signal_overnight_intraday_consistency_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.006006`
  - `avg_daily_ic(平均日IC) = -0.003886`
  - `positive_daily_ic_share(正IC日占比) = 0.480013`
  - `avg_label_top10(前10平均标签) = -0.001981`
  - `avg_label_rank11_20(11-20名平均标签) = 0.000046`
  - `avg_label_bottom10(后10平均标签) = 0.002713`

- `price_volume_single_signal_amount_entropy_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.019016`
  - `avg_daily_ic(平均日IC) = -0.030858`
  - `positive_daily_ic_share(正IC日占比) = 0.324626`
  - `avg_label_top10(前10平均标签) = -0.005702`
  - `avg_label_rank11_20(11-20名平均标签) = -0.003185`
  - `avg_label_bottom10(后10平均标签) = 0.005732`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 8 produced at least one genuinely orthogonal clean positive keeper, which is enough new information to justify a later composability screen under the frozen v18 baseline.
