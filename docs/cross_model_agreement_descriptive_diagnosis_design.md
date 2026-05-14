# Cross-Model Agreement Descriptive Diagnosis Design

This design starts `cross_model_agreement_descriptive_diagnosis_round_v1`.

The round is exploratory descriptive research only. It is not alpha research, not a candidate, not a new baseline, not `v4`, not training, not backtest, not portfolio, not portfolio dry-run, not holdings generation, not formal metrics/readout, and not OOS. Frozen test remains unread.

## Round Intent

The round only describes cross-model agreement / disagreement structure among existing clean scores. It does not restart strategy research. It does not propose a candidate, a filter, a trading rule, a baseline replacement, a validation-tuned threshold, or a portfolio action.

## Fixed Objects

Clean models must include:

- `no_p98_reversal_baseline_v1`
- `clean_reversal_5d_tradability_filtered_v1`
- `clean_reversal_5d_board_neutral_v1`
- `clean_reversal_5d_limit_aware_v1`
- `clean_reversal_5d_liquidity_quality_v1`
- `clean_reversal_5d_listing_age_calendar_v1`

Rejected comparator only:

- `clean_composite_reversal_tradability_v1`

Conditional references only:

- `p98 conditional baseline`
- `multi_equal_weight_v1 conditional baseline`

`p98` and `multi_equal_weight_v1` are conditional reference only. They are not clean evidence, not clean gold standards, and not promotion anchors.

## Research Questions

The diagnosis must answer, descriptively only:

1. Whether common TopK names selected by multiple clean models are weaker.
2. Whether stronger `nextK` / `rank_31_100` names come more from model disagreement than model consensus.
3. Whether common TopK is more concentrated in low-liquidity, limit-like, or state-anomaly conditions.
4. How model-specific TopK-only names differ from common TopK.
5. Whether common `nextK` / `rank_31_100` winners represent more stable middle-head consensus.
6. Whether `p98` conditional reference overlap structure differs. This must be labeled conditional reference only.
7. Whether the round produces future paper-only hypotheses.
8. Which mechanism claims remain insufficient.

## Rank Groups

Fixed rank groups:

- `TopK`: `rank_1_30`
- `nextK`: `rank_31_60`
- `mid_head`: `rank_31_100`
- `broad_head`: `rank_31_200`
- `middle`: `rank_101_300`

Cross-band migration uses exclusive placement bands:

- `TopK`: 1-30
- `nextK`: 31-60
- `mid_head`: 61-100
- `middle`: 101-300

This exclusive migration note exists only to avoid double-counting between `nextK` and aggregated `rank_31_100`.

## Allowed Inputs

Allowed sources:

- existing clean score artifacts
- existing rank-band full profile diagnosis outputs
- existing market-state conditional diagnosis outputs
- `data_field_enrichment_v1` allowed fields
- D0-visible OHLCV / amount / adj_close derived descriptive fields already present in existing artifacts
- `p98` / `multi_equal_weight_v1` as conditional references only

## Forbidden Inputs

The round must fail fast on forbidden inputs:

- `listing_age_trading_days`
- `newly_listed_flag`
- label diagnostics for source selection
- future / realized / `actual_exit` / `sell_price` as conditioning fields
- frozen / fixed test fields

Unavailable fields must be explicitly marked `unavailable`. No silent fallback is allowed.

## Required Outputs

The implementation must write:

- `/private/tmp/cross_model_agreement_descriptive_diagnosis.json`
- `/private/tmp/cross_model_agreement_descriptive_diagnosis.md`

Required descriptive sections:

1. Cross-model agreement count
   - agreement_count bucket `0..N`
   - mean return / median return / count
   - high-agreement TopK return vs low-agreement TopK return
2. Common TopK vs model-specific TopK
   - common TopK: `>= 4` clean models
   - model-specific TopK: exactly `1` clean model
   - compare mean return, median return, worst 5% damage, best 5% contribution
   - compare amount bucket, limit / tradability exposure, board / exchange exposure
3. Agreement in `nextK` / `rank_31_100`
   - common `nextK` return
   - common `mid_head` return
   - compare with common TopK
   - explicitly test whether stronger names sit in disagreement / near-head bands
4. Cross-band migration
   - TopK by one model but `nextK` / `mid_head` by others
   - TopK by many models
   - mid_head by many models
   - returns by migration pattern
5. Exposure decomposition
   - amount bucket distribution
   - `is_limit_down`
   - `close_at_down_limit`
   - `open_at_up_limit`
   - `entry_buyable`
   - `no_trade_flag`
   - suspension / `is_suspended`
   - `board_type`
   - `exchange`
   - `listing_age_days` bucket
6. `p98` conditional reference comparison
   - p98 TopK overlap with common clean TopK
   - p98 TopK overlap with common `nextK` / `mid_head`
   - p98-only return vs clean-common-only return
   - explicit `conditional reference only` label
7. Stability
   - train vs validation direction consistency
   - validation yearly consistency
   - if unstable, state `insufficient evidence`

## Summary Requirements

The summary document must state:

- exploratory descriptive research only
- not alpha
- not candidate
- not portfolio
- not OOS
- no frozen test
- no strategy restart
- agreement_count cannot directly form any trading rule
- which mechanism hypotheses can enter future paper-only pre-registration
- which mechanism evidence is insufficient

## Language Boundary

Allowed language:

- descriptive evidence suggests
- hypothesis candidate for paper-only
- insufficient evidence

Forbidden language:

- actionable rule
- deployable filter
- portfolio candidate
- validated edge
