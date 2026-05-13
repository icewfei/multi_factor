# Clean Liquidity Quality Failure Decomposition Design

This design starts `clean_liquidity_quality_failure_decomposition_round_v1`. The round only explains why `clean_reversal_5d_liquidity_quality_v1` improves full-cross-section edge while still failing deployed TopK head quality. It does not modify the liquidity-quality formula, tune thresholds, create a new candidate, train a model, run portfolio, backtest, generate holdings, generate formal metrics/readout, or read frozen test data.

## Research Object

The object is the RankIC-vs-TopK contradiction:

- `clean_reversal_5d_liquidity_quality_v1` validation RankIC is close to the p98 conditional baseline.
- Its validation TopK proxy is only slightly positive.
- Its validation TopK-minus-nextK remains negative.

The research question is whether the all-cross-section edge is coming from the head, the middle buckets, or the tail, and why that edge does not become a deployable TopK head edge.

## Comparison Set

- `no_p98_reversal_baseline_v1`: clean no-p98 anchor.
- `clean_reversal_5d_liquidity_quality_v1`: research object.
- `clean_composite_reversal_tradability_v1`: rejected comparator only.
- `p98_conditional_reference`: conditional reference only.
- `multi_equal_weight_v1`: conditional reference only.

`p98_conditional_reference` and `multi_equal_weight_v1` are not clean components, not clean gold standards, and cannot be used for clean source selection.

## Allowed Inputs

Allowed score inputs are already generated score artifacts from `clean_baseline_redesign_round_v1`, `no_p98_reversal_baseline_v1`, `clean_reversal_5d_liquidity_quality_v1`, the rejected `clean_composite_reversal_tradability_v1`, and conditional references for p98 and `multi_equal_weight_v1`.

Allowed D0-visible fields are OHLCV / amount / `adj_close` and `data_field_enrichment_v1` fields: `is_st`, `is_suspended`, `no_trade_flag`, `volume_zero_flag`, `amount_zero_flag`, `is_limit_up`, `is_limit_down`, `open_at_up_limit`, `close_at_down_limit`, `limit_rule_version`, `entry_buyable`, `exit_sellable`, `sellable_retry_next_open`, `list_date`, `listing_age_days`, `board_type`, `exchange`, and `limit_pct_rule`.

Blocked fields remain prohibited: `listing_age_trading_days`, `newly_listed_flag`.

## Diagnostic Dimensions

1. Decile / ventile return curve: identify whether the edge is head, middle, or tail driven.
2. TopK / nextK / rank 31-100: compare head, immediate next bucket, and broader near-head behavior.
3. TopK winner / loser contribution: quantify large winner, large loser, top 5% edge concentration, and worst 5% damage.
4. Yearly stability: train/validation direction and validation yearly consistency.
5. Amount bucket / liquidity exposure: full-universe amount bucket distribution for TopK and nextK.
6. Board / exchange exposure: D0 board and exchange concentration.
7. Tradability / limit status exposure: entry-buyable, no-trade, suspension, zero-volume/amount, and limit flags.
8. Overlap / divergence with no-p98 and p98 conditional: liquidity-only, comparator-only, overlap counts, Jaccard, and daily distribution.
9. Score dispersion / rank concentration: daily score dispersion and rank bucket concentration.
10. Middle-bucket contribution to RankIC: segment RankIC and return contribution for top, middle, and bottom buckets.

## Decision Use

If TopK-minus-nextK remains negative or unstable, the line cannot enter portfolio. If RankIC improvement is mainly middle-bucket or tail driven rather than head driven, it cannot enter portfolio. Any next candidate must be separately pre-registered; this round never tunes thresholds or opens a candidate.
