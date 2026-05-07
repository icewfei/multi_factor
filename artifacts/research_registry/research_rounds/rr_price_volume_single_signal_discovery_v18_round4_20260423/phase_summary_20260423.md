# rr_price_volume_single_signal_discovery_v18_round4_20260423 phase summary

## Summary

This round evaluated ten orthogonal atomic price-volume signals under the frozen `price_volume_v18_refresh_hysteresis` operational contract.

The final classification is:

- `price_volume_single_signal_breakout_proximity_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_breakout_proximity_60d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_close_location_value_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_upper_shadow_ratio_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_amount_shock_5_20_v1`: `signal_edge_positive`
- `price_volume_single_signal_up_volume_share_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_breakout_volume_confirmation_20d_v1`: `signal_edge_positive`
- `price_volume_single_signal_gap_followthrough_10d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_downside_tail_pressure_20d_v1`: `signal_edge_mixed`
- `price_volume_single_signal_path_efficiency_20d_v1`: `signal_edge_mixed`

## Newly retained clean positive keepers

- `price_volume_single_signal_amount_shock_5_20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007194`
  - `avg_daily_ic(平均日IC) = 0.011316`
  - `positive_daily_ic_share(正IC日占比) = 0.557828`
  - `avg_label_top10(前10平均标签) = 0.003593`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003129`
  - `avg_label_bottom10(后10平均标签) = -0.005476`

- `price_volume_single_signal_breakout_volume_confirmation_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007258`
  - `avg_daily_ic(平均日IC) = 0.011053`
  - `positive_daily_ic_share(正IC日占比) = 0.554611`
  - `avg_label_top10(前10平均标签) = 0.004263`
  - `avg_label_rank11_20(11-20名平均标签) = 0.001971`
  - `avg_label_bottom10(后10平均标签) = -0.006743`

## Mixed signals

- `price_volume_single_signal_breakout_proximity_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.014219`
  - `avg_daily_ic(平均日IC) = 0.026396`
  - `positive_daily_ic_share(正IC日占比) = 0.557129`
  - `avg_label_top10(前10平均标签) = 0.002664`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005822`

- `price_volume_single_signal_breakout_proximity_60d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.016031`
  - `avg_daily_ic(平均日IC) = 0.028719`
  - `positive_daily_ic_share(正IC日占比) = 0.551464`
  - `avg_label_top10(前10平均标签) = 0.005599`
  - `avg_label_rank11_20(11-20名平均标签) = 0.008413`

- `price_volume_single_signal_close_location_value_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007015`
  - `avg_daily_ic(平均日IC) = 0.008827`
  - `positive_daily_ic_share(正IC日占比) = 0.521007`
  - `avg_label_top10(前10平均标签) = 0.003755`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004110`

- `price_volume_single_signal_upper_shadow_ratio_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007568`
  - `avg_daily_ic(平均日IC) = 0.009568`
  - `positive_daily_ic_share(正IC日占比) = 0.526200`
  - `avg_label_top10(前10平均标签) = 0.003453`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003738`

- `price_volume_single_signal_up_volume_share_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.007952`
  - `avg_daily_ic(平均日IC) = 0.014569`
  - `positive_daily_ic_share(正IC日占比) = 0.550747`
  - `avg_label_top10(前10平均标签) = 0.003427`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003990`

- `price_volume_single_signal_gap_followthrough_10d_v1`
  - `full_sample_corr_ic(全样本IC) = -0.001863`
  - `avg_daily_ic(平均日IC) = -0.000972`
  - `positive_daily_ic_share(正IC日占比) = 0.500315`
  - `avg_label_top10(前10平均标签) = -0.001923`
  - `avg_label_rank11_20(11-20名平均标签) = 0.000971`

- `price_volume_single_signal_downside_tail_pressure_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.005615`
  - `avg_daily_ic(平均日IC) = 0.010972`
  - `positive_daily_ic_share(正IC日占比) = 0.518647`
  - `avg_label_top10(前10平均标签) = 0.001900`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003842`

- `price_volume_single_signal_path_efficiency_20d_v1`
  - `full_sample_corr_ic(全样本IC) = 0.011511`
  - `avg_daily_ic(平均日IC) = 0.020042`
  - `positive_daily_ic_share(正IC日占比) = 0.553907`
  - `avg_label_top10(前10平均标签) = 0.001921`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003672`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Round 4 produced at least one new clean positive keeper, which is enough new information to reopen family construction with a disciplined one-step composition test.
