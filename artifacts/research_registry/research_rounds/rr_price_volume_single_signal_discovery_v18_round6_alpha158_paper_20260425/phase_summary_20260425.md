# rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425 phase summary

## Summary

This round evaluated ten more standardized atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

The final classification is:

- `price_volume_single_signal_price_volume_corr_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_turnover_mean_reversion_gap_5_20_v1`: `signal_edge_negative`
- `price_volume_single_signal_volume_momentum_5_20_v1`: `signal_edge_positive`
- `price_volume_single_signal_close_to_high_ratio_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_upper_shadow_pressure_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_path_efficiency_60d_v1`: `signal_edge_negative`
- `price_volume_single_signal_breakout_distance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_breakdown_distance_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_range_compression_5_20_v1`: `signal_edge_negative`
- `price_volume_single_signal_downside_recovery_strength_10d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_price_volume_corr_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.016661`
  - `avg_daily_ic(平均日IC) = 0.029966`
  - `positive_daily_ic_share(正IC日占比) = 0.636764`
  - `avg_label_top10(前10平均标签) = 0.007764`
  - `avg_label_rank11_20(11-20名平均标签) = 0.006709`
  - `avg_label_bottom10(后10平均标签) = -0.001614`

- `price_volume_single_signal_volume_momentum_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007194`
  - `avg_daily_ic(平均日IC) = 0.011316`
  - `positive_daily_ic_share(正IC日占比) = 0.557828`
  - `avg_label_top10(前10平均标签) = 0.003593`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003129`
  - `avg_label_bottom10(后10平均标签) = -0.005476`

## Mixed signals

- `price_volume_single_signal_close_to_high_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007015`
  - `avg_daily_ic(平均日IC) = 0.008827`
  - `positive_daily_ic_share(正IC日占比) = 0.521007`
  - `avg_label_top10(前10平均标签) = 0.003755`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004110`

- `price_volume_single_signal_upper_shadow_pressure_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.002355`
  - `avg_daily_ic(平均日IC) = 0.000354`
  - `positive_daily_ic_share(正IC日占比) = 0.505429`
  - `avg_label_top10(前10平均标签) = 0.003126`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003463`

- `price_volume_single_signal_breakout_distance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.014219`
  - `avg_daily_ic(平均日IC) = 0.026396`
  - `positive_daily_ic_share(正IC日占比) = 0.557129`
  - `avg_label_top10(前10平均标签) = 0.002664`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005822`

- `price_volume_single_signal_breakdown_distance_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006300`
  - `avg_daily_ic(平均日IC) = 0.012857`
  - `positive_daily_ic_share(正IC日占比) = 0.535411`
  - `avg_label_top10(前10平均标签) = -0.002305`
  - `avg_label_rank11_20(11-20名平均标签) = 0.002308`

- `price_volume_single_signal_downside_recovery_strength_10d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.006165`
  - `avg_daily_ic(平均日IC) = 0.007899`
  - `positive_daily_ic_share(正IC日占比) = 0.540762`
  - `avg_label_top10(前10平均标签) = 0.001345`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003708`

## Rejected signals

- `price_volume_single_signal_turnover_mean_reversion_gap_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = -0.006322`
  - `avg_daily_ic(平均日IC) = -0.011098`
  - `positive_daily_ic_share(正IC日占比) = 0.438395`
  - `avg_label_top10(前10平均标签) = -0.006493`
  - `avg_label_rank11_20(11-20名平均标签) = -0.003635`
  - `avg_label_bottom10(后10平均标签) = 0.002852`

- `price_volume_single_signal_path_efficiency_60d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.001670`
  - `avg_daily_ic(平均日IC) = -0.008432`
  - `positive_daily_ic_share(正IC日占比) = 0.480381`
  - `avg_label_top10(前10平均标签) = 0.003042`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003852`
  - `avg_label_bottom10(后10平均标签) = 0.001224`

- `price_volume_single_signal_range_compression_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = -0.001915`
  - `avg_daily_ic(平均日IC) = -0.002900`
  - `positive_daily_ic_share(正IC日占比) = 0.474587`
  - `avg_label_top10(前10平均标签) = -0.003696`
  - `avg_label_rank11_20(11-20名平均标签) = -0.000888`
  - `avg_label_bottom10(后10平均标签) = 0.002755`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 6 produced at least one new clean positive keeper, which is enough new information to reopen family construction or composability screening with a disciplined next step.
