# Confirmatory shortlist note

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_standalone_shortlist_round1_20260429`
- `snapshot_id(快照ID) = warehouse_20260429_trainval_20211231`
- `validation_window(验证窗口) = 20190101-20211231`
- `baseline_reference_candidate_scheme_id(参考基准候选) = price_volume_v18_refresh_hysteresis`

Shortlist:

- `price_volume_single_signal_alpha158_cord30_v1`
  Mechanism: price-volume change correlation.
- `price_volume_single_signal_alpha158_vsumd60_v1`
  Mechanism: volume expansion balance.
- `price_volume_single_signal_alpha158_imxd5_v1`
  Mechanism: path-ordering breakout.

Why these three:

- They are all `signal_edge_positive(正向边际优势)` standalone keepers under the Alpha158 exact canonical run.
- They are more orthogonal to one another on the trainval-only panels than the near-neighbor clusters that were kept as reserve.
- This round asks a narrower confirmatory question: can any one of these standalone signals beat the frozen `v18` working reference under a predeclared validation rule?
