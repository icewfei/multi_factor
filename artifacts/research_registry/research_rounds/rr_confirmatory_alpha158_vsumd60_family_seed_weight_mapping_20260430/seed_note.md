# VSUMD60 Weight-Mapping Seed

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_vsumd60_family_seed_weight_mapping_20260430`
- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_vsumd60_seed_liquidity_rank_tilt_v1`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_single_signal_alpha158_vsumd60_v1`
- `external_anchor_candidate_scheme_id(外部锚候选方案ID) = price_volume_v18_refresh_hysteresis`
- `changed_dimension(变更维度) = weight_mapping`

This round keeps the confirmed `VSUMD60` score unchanged and changes only the mapping from frozen TopK membership to target weights.

Design intent:
- Keep `alpha158_vsumd60_raw` score unchanged.
- Keep ranking eligibility, `TopK=10`, equal-weight extraction, refresh semantics, and benchmark contract unchanged.
- Apply one restrained liquidity-rank tilt inside the same selected `TopK`.
- Evaluate primarily against the confirmed standalone `vsumd60` winner, not only against `v18`.
