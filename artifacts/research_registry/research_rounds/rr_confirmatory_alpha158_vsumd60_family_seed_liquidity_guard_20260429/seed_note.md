# VSUMD60 family seed note

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_vsumd60_family_seed_liquidity_guard_20260429`
- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_vsumd60_seed_liquidity_guard70_v1`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_single_signal_alpha158_vsumd60_v1`
- `changed_dimension(变更维度) = ranking_eligibility_guard`

Seed design:

- Keep `alpha158_vsumd60_raw` score unchanged.
- Add one fixed `ranking liquidity guard(排序流动性护栏)` at `liquidity_min_percentile = 0.70`.
- Evaluate primarily against the confirmed standalone `vsumd60` winner, not only against `v18`.

Why this seed first:

- It is the narrowest family move available after confirmatory round 1-2.
- It targets the remaining known weakness: `cost_stress(成本压力)` and `tradability(可交易性)`.
- It avoids reopening the failed `Alpha158 -> v18 overlay(覆盖层)` line.
