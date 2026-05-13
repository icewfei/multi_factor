# Clean TopK Selection Failure Diagnosis Design

This design starts `clean_topk_selection_failure_diagnosis_round_v1`. The round only diagnoses clean TopK selection failure. It does not design a new candidate, tune any threshold, change `TopK` / `nextK` definitions, train a model, run portfolio, run backtest, generate holdings or formal metrics/readout, or read frozen test data.

## Research Goal

The goal is to explain the return structure among `TopK`, `nextK`, and `rank 31-100` for clean baselines, especially when full-cross-section or middle-bucket edge exists but deployed `TopK` head remains weaker than nearby buckets.

## Comparison Set

- `no_p98_reversal_baseline_v1`
- `clean_reversal_5d_liquidity_quality_v1`
- `clean_composite_reversal_tradability_v1`
- `clean_reversal_5d_limit_aware_v1`
- `clean_reversal_5d_board_neutral_v1`
- `clean_reversal_5d_tradability_filtered_v1`
- `p98_conditional_reference` only as conditional reference

`p98` and `multi_equal_weight_v1` are not clean components and not unconditional gold standards.

## Allowed Inputs

Allowed score artifacts are existing clean baseline redesign scores, `no_p98_reversal_baseline_v1`, and conditional references for `p98` / `multi_equal_weight_v1`. Allowed D0-visible fields are OHLCV / `amount` / `adj_close` and `data_field_enrichment_v1` allowed fields. Blocked fields remain prohibited: `listing_age_trading_days`, `newly_listed_flag`.

## Diagnostic Dimensions

1. `TopK` vs `nextK` vs `rank 31-100` return.
2. Yearly stability.
3. Daily win rate.
4. Score extremeness / score dispersion.
5. Reversal extremeness.
6. Liquidity exposure.
7. Board / exchange exposure.
8. Limit / suspension / tradability exposure.
9. Large winner / large loser contribution.
10. Overlap / divergence across clean baselines.
11. Whether head-exclusion evidence exists.

## Decision Use

This round may only support a later pre-registered head-exclusion candidate design if evidence is cross-model, train/validation/yearly consistent, D0-visible, and not blocked-field dependent. This round never enters portfolio dry-run.
