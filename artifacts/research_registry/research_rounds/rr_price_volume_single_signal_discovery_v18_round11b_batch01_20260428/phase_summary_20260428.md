# rr_price_volume_single_signal_discovery_v18_round11b_batch01_20260428 phase summary

## Summary

This batch is the first serial executable tranche inside round11b full158 governance under frozen `price_volume_v18_refresh_hysteresis` contract.

The final classification is:

- `price_volume_single_signal_price_volume_beta_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_price_volume_rank_corr_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_turnover_entropy_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_candle_body_efficiency_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_upper_lower_shadow_asymmetry_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_gap_to_range_ratio_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_close_position_stability_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_rolling_vwap_distance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_downside_range_convexity_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_updown_volume_balance_persistence_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_intraday_path_curvature_20d_v1`: `signal_edge_negative`
- `price_volume_single_signal_liquidity_shock_recovery_ratio_20d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_price_volume_beta_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.017161`
  - `avg_daily_ic(平均日IC) = 0.028287`
  - `positive_daily_ic_share(正IC日占比) = 0.608059`
  - `avg_label_top10(前10平均标签) = 0.008462`
  - `avg_label_rank11_20(11-20名平均标签) = 0.007726`
  - `avg_label_bottom10(后10平均标签) = 0.000683`

- `price_volume_single_signal_price_volume_rank_corr_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.011394`
  - `avg_daily_ic(平均日IC) = 0.020216`
  - `positive_daily_ic_share(正IC日占比) = 0.626849`
  - `avg_label_top10(前10平均标签) = 0.005890`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005759`
  - `avg_label_bottom10(后10平均标签) = 0.000290`

- `price_volume_single_signal_downside_range_convexity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.002081`
  - `avg_daily_ic(平均日IC) = 0.004594`
  - `positive_daily_ic_share(正IC日占比) = 0.525098`
  - `avg_label_top10(前10平均标签) = 0.003632`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003491`
  - `avg_label_bottom10(后10平均标签) = 0.002003`

## Mixed signals

- `price_volume_single_signal_upper_lower_shadow_asymmetry_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005203`
  - `avg_daily_ic(平均日IC) = 0.006725`
  - `positive_daily_ic_share(正IC日占比) = 0.533596`
  - `avg_label_top10(前10平均标签) = 0.004636`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004962`

- `price_volume_single_signal_close_position_stability_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.000124`
  - `avg_daily_ic(平均日IC) = 0.002456`
  - `positive_daily_ic_share(正IC日占比) = 0.511489`
  - `avg_label_top10(前10平均标签) = 0.001460`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003029`

- `price_volume_single_signal_rolling_vwap_distance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006054`
  - `avg_daily_ic(平均日IC) = 0.012831`
  - `positive_daily_ic_share(正IC日占比) = 0.522109`
  - `avg_label_top10(前10平均标签) = 0.004965`
  - `avg_label_rank11_20(11-20名平均标签) = 0.006689`

- `price_volume_single_signal_liquidity_shock_recovery_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.000388`
  - `avg_daily_ic(平均日IC) = -0.000947`
  - `positive_daily_ic_share(正IC日占比) = 0.500866`
  - `avg_label_top10(前10平均标签) = 0.004084`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004648`

## Rejected signals

- `price_volume_single_signal_turnover_entropy_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.013125`
  - `avg_daily_ic(平均日IC) = -0.021195`
  - `positive_daily_ic_share(正IC日占比) = 0.391660`
  - `avg_label_top10(前10平均标签) = -0.003467`
  - `avg_label_rank11_20(11-20名平均标签) = -0.002496`
  - `avg_label_bottom10(后10平均标签) = 0.006145`

- `price_volume_single_signal_candle_body_efficiency_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.003758`
  - `avg_daily_ic(平均日IC) = -0.009714`
  - `positive_daily_ic_share(正IC日占比) = 0.449882`
  - `avg_label_top10(前10平均标签) = 0.001261`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001475`
  - `avg_label_bottom10(后10平均标签) = 0.003390`

- `price_volume_single_signal_gap_to_range_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.008871`
  - `avg_daily_ic(平均日IC) = -0.007815`
  - `positive_daily_ic_share(正IC日占比) = 0.443185`
  - `avg_label_top10(前10平均标签) = 0.000285`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001362`
  - `avg_label_bottom10(后10平均标签) = 0.003985`

- `price_volume_single_signal_updown_volume_balance_persistence_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.005004`
  - `avg_daily_ic(平均日IC) = -0.007986`
  - `positive_daily_ic_share(正IC日占比) = 0.433113`
  - `avg_label_top10(前10平均标签) = 0.001599`
  - `avg_label_rank11_20(11-20名平均标签) = 0.002398`
  - `avg_label_bottom10(后10平均标签) = 0.004265`

- `price_volume_single_signal_intraday_path_curvature_20d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.005445`
  - `avg_daily_ic(平均日IC) = -0.009257`
  - `positive_daily_ic_share(正IC日占比) = 0.471912`
  - `avg_label_top10(前10平均标签) = 0.000129`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001064`
  - `avg_label_bottom10(后10平均标签) = 0.003155`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Batch01 produced at least one clean positive keeper and can proceed to composability-screening intake after serial batch completion policy.
