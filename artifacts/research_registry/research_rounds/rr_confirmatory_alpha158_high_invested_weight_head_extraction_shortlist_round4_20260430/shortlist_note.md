# Confirmatory shortlist note

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_high_invested_weight_head_extraction_shortlist_round4_20260430`
- `snapshot_id(快照ID) = warehouse_20260429_trainval_20211231`
- `validation_window(验证窗口) = 20190101-20211231`
- `baseline_reference_candidate_scheme_id(参考基准候选) = price_volume_v18_refresh_hysteresis`

Shortlist:

- `price_volume_single_signal_alpha158_imxd5_v1`
  Mechanism: path-ordering and breakout timing.
- `price_volume_single_signal_alpha158_cord30_v1`
  Mechanism: price-volume change correlation with stronger head-extraction intent.
- `price_volume_single_signal_alpha158_imax20_v1`
  Mechanism: breakout freshness / recent-high timing.

Why these three:

- `vsumd60` and `corr30` have already been frozen as `reserve atomic keeper(储备原子信号)`.
- This round deliberately changes the question from “which low-exposure winner is cleaner” to “which head-extraction reserve card can sustain a higher deployed-capital footprint”.
- The shortlist stays capped at three names to preserve confirmatory budget discipline and keep the next step small, hard, and fast.
