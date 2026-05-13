# Clean Mid-Rank Portfolio Hypothesis Design

This design starts `clean_mid_rank_portfolio_hypothesis_round_v1`. The round studies whether clean score edge exists mainly in the mid-rank band (rank 31-100 / 31-200) rather than in TopK. It does not introduce new alpha factors, new information sources, or new data modalities. It does not train models, does not run portfolio, and does not generate holdings/backtest_daily/formal metrics/readout. Frozen test remains unread.

This is not a strategy proposal and not a portfolio approval round.

## Research Object

The object is the persistent observation across four prior sub-rounds:

- TopK selection failure is widespread across clean baselines.
- rank 31-100 consistently beats TopK in multiple clean models.
- liquidity_quality shows RankIC improvement mainly from middle/tail separation, not TopK.
- No stable D0-visible head-exclusion rule exists from the current field set.

The diagnostic question: does clean score edge primarily reside in mid-rank bands (rank 31-100, rank 31-200) rather than in TopK? If so, a rank-band deployment hypothesis may be more natural than a head-exclusion refinement.

## Fixed Rank Bands

The bands are fixed by design and must not be tuned based on validation results:

| band | rank range | definition |
| --- | --- | --- |
| TopK | 1-30 | top 30 names by effective score |
| nextK | 31-60 | immediate next 30 |
| mid_head | 31-100 | rank 31-100 inclusive |
| broad_head | 31-200 | rank 31-200 inclusive |
| middle | 101-300 | rank 101-300 inclusive |

No band adjustment based on validation is permitted. If bands need to be changed to produce an edge, the hypothesis is falsified.

## Allowed Scores

Clean scores (diagnostic objects, not strategy candidates):

- `no_p98_reversal_baseline_v1`
- `clean_reversal_5d_tradability_filtered_v1`
- `clean_reversal_5d_board_neutral_v1`
- `clean_reversal_5d_limit_aware_v1`
- `clean_reversal_5d_liquidity_quality_v1`
- `clean_reversal_5d_listing_age_calendar_v1`
- `clean_composite_reversal_tradability_v1` (rejected comparator only)

Conditional references (not clean components):

- `p98_conditional_reference`
- `multi_equal_weight_v1_conditional_reference`

## Hard Boundaries

- No new alpha factors.
- No ML model training.
- No frozen test reading.
- No formal portfolio / holdings / backtest_daily / formal metrics / readout.
- No tuning rank bands based on validation.
- No modifying existing score formulas.
- p98 / multi_equal_weight_v1 conditional reference only.
- Trainval diagnosis is not OOS evidence.
- This is not a strategy effectiveness conclusion.

## Allowed Inputs

- Already generated score artifacts from `clean_baseline_redesign_round_v1`, `clean_baseline_family_score_gate`, and prior rounds.
- Existing label panel, split panel from `project_panels_research_trainval_20211231_20260429`.
- `data_field_enrichment_v1` allowed fields only; blocked fields (`listing_age_trading_days`, `newly_listed_flag`) remain prohibited.
- p98 / multi_equal_weight_v1 as conditional reference only.

## Diagnostic Dimensions

1. **Rank-band return profile**: mean, median, daily win rate vs TopK, for each band and each clean score in train and validation.
2. **Band stability**: train/validation direction consistency, validation yearly consistency, whether rank31-100 > TopK consistently.
3. **Exposure decomposition**: liquidity bucket, board/exchange, limit/tradability status, listing_age_days bucket within each band.
4. **Tail contribution**: worst 5% damage and best 5% contribution per band.
5. **Comparison with p98 conditional reference**: band-level comparison, with p98 explicitly marked as conditional reference only.
6. **Cross-model consistency**: whether mid-rank > TopK is common across clean models.

## Decision Rules

The following decision rules are pre-registered:

- If mid-rank edge only appears in validation but not train: do not promote.
- If yearly stability fails (any validation year flips direction): do not promote.
- If edge depends on p98 reference: do not promote as clean.
- If bands must be tuned to produce edge: do not promote.
- Only if fixed bands show mid-rank > TopK consistently in train, validation, and every validation year, may this round recommend a next-stage same-contract diagnostic portfolio dry-run.
- This round itself never runs portfolio.

## Decision Use

This round never approves a strategy, never runs portfolio, and never enters portfolio dry-run. At most, it may recommend a separately pre-registered diagnostic portfolio dry-run as the next step. Any such recommendation is conditional on passing all pre-registered decision rules.
