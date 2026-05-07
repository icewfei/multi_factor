# Confirmatory shortlist note

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_head_extraction_shortlist_round2_20260430`
- `snapshot_id(快照ID) = warehouse_20260429_trainval_20211231`
- `validation_window(验证窗口) = 20190101-20211231`
- `baseline_reference_candidate_scheme_id(参考基准候选) = price_volume_v18_refresh_hysteresis`
- `reserve_anchor_candidate_scheme_id(储备锚点候选) = price_volume_single_signal_alpha158_vsumd60_v1`

Shortlist:

- `price_volume_single_signal_alpha158_corr20_v1`
  Mechanism: price-volume correlation with stronger head-extraction intent.
- `price_volume_single_signal_alpha158_corr30_v1`
  Mechanism: medium-horizon price-volume correlation with stronger head-extraction intent.
- `price_volume_single_signal_alpha158_cord30_v1`
  Mechanism: price-volume change correlation with stronger head-extraction intent.

Why these three:

- `vsumd60` has already been frozen as a `reserve atomic keeper(储备原子信号)` after walk-forward and regime diagnosis.
- This round deliberately changes the question from “which signal avoids weak names best” to “which signal extracts strong head names better”.
- The shortlist stays capped at three names to preserve confirmatory budget discipline and keep the next step small, hard, and fast.
