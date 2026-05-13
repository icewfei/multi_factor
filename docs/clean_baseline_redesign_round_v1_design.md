# Clean Baseline Redesign Round V1 Design

This is a pre-registered clean baseline redesign round. It is not alpha, not strategy approval, not OOS, and not a portfolio or formal metrics/readout exercise.

## Hard Boundaries

- No `p98`.
- No `label_*` or trainval label diagnostics for source selection.
- No frozen test access.
- No ML training.
- No portfolio run.
- No holdings or `backtest_daily`.
- No formal metrics/readout.
- No validation retuning.
- No blocked enrichment fields: `listing_age_trading_days`, `newly_listed_flag`.
- No silent fallback.

## Candidate Set

All candidates use D0 visible inputs only and lower `model_score_D0` means better rank.

- `clean_reversal_5d_tradability_filtered_v1`: 5d reversal with fixed D0 tradability filter.
- `clean_reversal_5d_board_neutral_v1`: 5d reversal ranked within `board_type / exchange`.
- `clean_reversal_5d_limit_aware_v1`: 5d reversal after fixed D0 limit-state exclusion.
- `clean_reversal_5d_liquidity_quality_v1`: 5d reversal with fixed zero-volume/zero-amount and same-day amount percentile gate.
- `clean_reversal_5d_listing_age_calendar_v1`: 5d reversal with `listing_age_days >= 180`; this is explicitly a calendar-day proxy, not `listing_age_trading_days`.
- `clean_composite_reversal_tradability_v1`: fixed equal-weight composite of reversal rank, board-neutral rank, liquidity quality rank, and tradability penalty.

## Inputs

Allowed input families are:

- D0 visible OHLCV and `adj_close`.
- `ranking_eligible_D0`.
- Allowed `data_field_enrichment_v1` fields such as tradability flags, limit flags, `board_type`, `exchange`, and `listing_age_days`.

The manifest at `configs/clean_baselines/redesign_round_v1/clean_baseline_redesign_manifest.json` is the source of record for formulas, allowed fields, forbidden fields, fail-fast rules, intended diagnosis, cleanliness rationale, and expected TopK head-quality rationale.

## Diagnosis Plan

The round reports model-layer train/validation diagnostics only:

- RankIC.
- ICIR.
- Top-bottom spread.
- Decile forward return.
- Coverage.
- Yearly stability.
- TopK head realized return proxy.
- TopK minus nextK.
- Score coverage difference.

Comparisons include `no_p98_reversal_baseline_v1` and older clean baseline family candidates. `p98` and `multi_equal_weight_v1` may appear only as conditional references, not clean gold standards.
