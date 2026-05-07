# Future Signal Naming And Intake Rules (20260425)

## Purpose

This short rulebook turns the current `atomic keepers(原子保留信号)` dedup list into an operational intake rule for all future signal research.

Its purpose is:

- to stop naming variants from being treated as fresh alpha discoveries,
- to force deduplication before a new `single-signal discovery(单信号发现)` round is opened,
- to keep the research space small and interpretable.

## Rule 1: New signal naming must use canonical structure

Any new atomic signal name must follow:

- `domain_mechanism_window_raw`

Examples:

- `volume_price_synchronicity_20d_raw`
- `turnover_acceleration_5_20_raw`
- `liquidity_trend_20_60_raw`

Avoid vague or overloaded names such as:

- `shock`
- `confirmation`
- `quality`
- `pressure`

unless the mechanism is explicitly defined in one sentence and cannot be expressed with a more canonical label.

## Rule 2: Every new signal must declare its canonical mechanism family

Before preregistration, each new candidate must be assigned to one mechanism family:

- `momentum_family`
- `liquidity_improvement_family`
- `price_volume_confirmation_family`
- `range_position_family`
- `shadow_pressure_family`
- `compression_family`
- `recovery_resilience_family`
- or a newly justified family

If it belongs to an existing family, the proposer must state whether it is:

- `new_mechanism`
- `horizon_variant`
- `direction_variant`
- `naming_alias`

Only `new_mechanism` should normally consume fresh exploration budget.

## Rule 3: Alias and near-alias checks are mandatory before registration

Before a new `planned candidate(计划候选)` is registered, it must be checked against the current canonical map.

At minimum, the proposer must explicitly answer:

1. Is this signal only a renamed version of an existing canonical field?
2. Is this signal only the opposite-direction framing of an existing field?
3. Is this signal only a horizon variant of an existing field?
4. Is this signal only a composite restatement of an already failed family component?

If the answer to 1 or 2 is yes:

- do **not** register it as a new keeper candidate
- register it only as an alias test if there is a very specific governance reason

If the answer to 3 is yes:

- register it only if the horizon change itself is the actual research question

## Rule 4: Canonical field names take precedence over alternative labels

When both a canonical label and a near-equivalent alternative exist, future work must use the canonical label.

Current canonical precedence:

- `volume_price_synchronicity_20d_raw` over `price_volume_corr_20d_raw`
- `amount_shock_5_20_raw` over `volume_momentum_5_20_raw`
- `turnover_acceleration_5_20_raw` over `turnover_mean_reversion_gap_5_20_raw`
- `breakout_proximity_20d_raw` over `breakout_distance_20d_raw`
- `close_location_value_20d_raw` over `close_to_high_ratio_20d_raw`
- `upper_shadow_ratio_20d_raw` over `upper_shadow_pressure_20d_raw`

## Rule 5: Positive single-signal status does not justify direct promotion

`signal_edge_positive(正向信号边际优势)` is only an intake pass.

It does **not** mean the signal can:

- enter a family directly,
- replace an existing family component directly,
- become an overlay directly.

Any new positive keeper must still pass:

- `composability screening(组合相容性筛查)`, if it is intended for family promotion

## Rule 6: Historical positives may still be retired

A signal can remain historically positive while being removed from the active keeper pool.

This applies when later evidence shows:

- family-level interaction is harmful,
- ablation indicates it is a drag component,
- or direct promotion repeatedly fails.

Current example:

- `trend_consistency_20d_raw`

## Rule 7: Future preregistration must include a dedup note

Every future `single-signal discovery(单信号发现)` prereg must contain a short `dedup note(去重说明)` answering:

- nearest canonical signal
- whether this is an alias / direction variant / horizon variant / new mechanism
- why it deserves independent budget

If this note is missing, the round should not be opened.

## Rule 8: Family construction may only use canonical signals

Any future family round must use:

- canonical field names only

It must not mix:

- a canonical signal and its alias,
- two opposite-direction framings of the same signal,
- or two labels that the dedup map already marks as near-equivalent.

## Rule 9: Watchlist signals are not active promotion candidates

`watchlist keeper(观察名单保留信号)` means:

- keep for later observation
- do not automatically promote

Current watchlist priority:

- `volume_price_synchronicity_20d_raw`

## Rule 10: New exploration budget should prioritize orthogonal mechanisms

Future discovery rounds should prioritize signals that are not already in these active canonical clusters:

- `momentum_family`
- `liquidity_improvement_family`
- `price_volume_confirmation_family`

The goal is to add new mechanisms, not more labels for old ones.

## Rule 11: Composability promotion must pass a head-stability hard gate

Before any signal can move from `composability screening(组合相容性筛查)` into a new family-construction round, it must pass:

- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠)` must not be lower than
- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠)`
- by more than `0.10`.

Hard gate expression:

- block promotion if `reference_avg_top10_overlap_next_day - screen_avg_top10_overlap_next_day > 0.10`.

This gate is mandatory even when other static score-layer metrics improve, because repeated failures have shown that head-stability degradation is a primary path-to-production blocker.

## Rule 12: Next rounds run in Alpha158/Paper whitelist-only source mode

From `2026-04-28` onward, new `single-signal discovery(单信号发现)` rounds must use:

- `source_policy.mode = alpha158_paper_whitelist_only`

and each signal must include explicit `source_provenance(来源溯源)` from approved categories only:

- `alpha158_style`
- `academic_paper`
- `classic_factor_handbook`

Mandatory per-signal provenance fields:

- `source_category`
- `source_id`
- `source_title`
- `source_locator`
- `mechanism_mapping`
- `independent_implementation_note`

Any candidate missing provenance or using non-whitelist categories fails intake preflight.

## Operational checklist

Before registering any new atomic signal candidate, confirm:

- `canonical_name_check(标准命名检查) = pass`
- `family_assignment_check(机制家族归类检查) = pass`
- `alias_check(别名检查) = pass`
- `direction_variant_check(方向变体检查) = pass`
- `horizon_variant_check(时窗变体检查) = pass`
- `new_mechanism_justification(新机制说明) = pass`
- `source_whitelist_mode_check(白名单来源模式检查) = pass`
- `source_provenance_check(来源溯源检查) = pass`

If any of these fail, the candidate should be revised, merged into an existing canonical signal, or rejected before preregistration.
