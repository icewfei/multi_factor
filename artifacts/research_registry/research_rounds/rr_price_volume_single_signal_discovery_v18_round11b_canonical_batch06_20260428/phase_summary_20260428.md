# rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch06_20260428 phase summary

## Summary

This batch is the sixth and final exact qlib Alpha158 canonical execution tranche under round11b governance. All 8 features are implemented independently on the project's own adjusted-price daily-bar contracts.

The final classification is:

- `price_volume_single_signal_alpha158_vsumn20_v1`: `signal_edge_positive`
- `price_volume_single_signal_alpha158_vsumn30_v1`: `signal_edge_positive`
- `price_volume_single_signal_alpha158_vsumn60_v1`: `signal_edge_positive`
- `price_volume_single_signal_alpha158_vsumd5_v1`: `signal_edge_mixed`
- `price_volume_single_signal_alpha158_vsumd10_v1`: `signal_edge_mixed`
- `price_volume_single_signal_alpha158_vsumd20_v1`: `signal_edge_positive`
- `price_volume_single_signal_alpha158_vsumd30_v1`: `signal_edge_positive`
- `price_volume_single_signal_alpha158_vsumd60_v1`: `signal_edge_positive`

## Newly retained clean positive keepers

- `price_volume_single_signal_alpha158_vsumn20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.010994`
  - `avg_daily_ic(平均日IC) = 0.017571`
  - `positive_daily_ic_share(正IC日占比) = 0.587504`
  - `avg_label_top10(前10平均标签) = 0.005347`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004847`
  - `avg_label_bottom10(后10平均标签) = -0.007203`

- `price_volume_single_signal_alpha158_vsumn30_v1`
  - `full_sample_corr_ic(全样本IC) = 0.013640`
  - `avg_daily_ic(平均日IC) = 0.022342`
  - `positive_daily_ic_share(正IC日占比) = 0.610482`
  - `avg_label_top10(前10平均标签) = 0.006593`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005548`
  - `avg_label_bottom10(后10平均标签) = -0.007310`

- `price_volume_single_signal_alpha158_vsumn60_v1`
  - `full_sample_corr_ic(全样本IC) = 0.014042`
  - `avg_daily_ic(平均日IC) = 0.023203`
  - `positive_daily_ic_share(正IC日占比) = 0.618665`
  - `avg_label_top10(前10平均标签) = 0.005517`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004933`
  - `avg_label_bottom10(后10平均标签) = -0.008008`

- `price_volume_single_signal_alpha158_vsumd20_v1`
  - `full_sample_corr_ic(全样本IC) = 0.010995`
  - `avg_daily_ic(平均日IC) = 0.017574`
  - `positive_daily_ic_share(正IC日占比) = 0.587347`
  - `avg_label_top10(前10平均标签) = 0.005347`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004847`
  - `avg_label_bottom10(后10平均标签) = -0.007213`

- `price_volume_single_signal_alpha158_vsumd30_v1`
  - `full_sample_corr_ic(全样本IC) = 0.013641`
  - `avg_daily_ic(平均日IC) = 0.022346`
  - `positive_daily_ic_share(正IC日占比) = 0.610324`
  - `avg_label_top10(前10平均标签) = 0.006593`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005548`
  - `avg_label_bottom10(后10平均标签) = -0.007320`

- `price_volume_single_signal_alpha158_vsumd60_v1`
  - `full_sample_corr_ic(全样本IC) = 0.014043`
  - `avg_daily_ic(平均日IC) = 0.023207`
  - `positive_daily_ic_share(正IC日占比) = 0.618508`
  - `avg_label_top10(前10平均标签) = 0.005517`
  - `avg_label_rank11_20(11-20名平均标签) = 0.004933`
  - `avg_label_bottom10(后10平均标签) = -0.008018`

## Mixed signals

- `price_volume_single_signal_alpha158_vsumd5_v1`
  - `full_sample_corr_ic(全样本IC) = 0.011686`
  - `avg_daily_ic(平均日IC) = 0.021649`
  - `positive_daily_ic_share(正IC日占比) = 0.613157`
  - `avg_label_top10(前10平均标签) = 0.004659`
  - `avg_label_rank11_20(11-20名平均标签) = 0.005214`

- `price_volume_single_signal_alpha158_vsumd10_v1`
  - `full_sample_corr_ic(全样本IC) = 0.008974`
  - `avg_daily_ic(平均日IC) = 0.015932`
  - `positive_daily_ic_share(正IC日占比) = 0.580737`
  - `avg_label_top10(前10平均标签) = 0.003232`
  - `avg_label_rank11_20(11-20名平均标签) = 0.003782`

## Decision

- `continue_pool_expansion(继续扩单信号池) = false`
- `reopen_family_construction(回到family构造) = true`
- reason: Canonical batch06 produced at least one clean positive exact-Alpha158 keeper, but controller policy still blocks family reopening and requires continued serial-only canonical execution.
