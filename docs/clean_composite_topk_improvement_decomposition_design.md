# Clean Composite TopK Improvement Decomposition Design

This design starts `clean_composite_topk_improvement_decomposition_round_v1`. The round only explains the observed contradiction in `clean_composite_reversal_tradability_v1`; it does not change the composite formula, tune weights, add candidates, train models, run portfolio, backtest, generate holdings, generate formal readouts, or read frozen test data.

## Research Object

The object is the validation contradiction:

- `clean_composite_reversal_tradability_v1` has weak full-cross-section RankIC.
- The same score has positive TopK realized-return proxy and positive TopK-minus-nextK.

The diagnostic question is whether the TopK improvement is a stable, low-degree, D0-visible structure, or whether it is a fragile validation artifact created by score compression, tail behavior, middle-rank distortion, or a small number of dates/samples.

## Comparison Set

- `no_p98_reversal_baseline_v1`: clean no-p98 anchor.
- `clean_liquidity_adjusted_reversal_baseline_v1` / `clean_reversal_5d_liquidity_quality_v1`: liquidity-quality clean comparator.
- `clean_composite_reversal_tradability_v1`: research object.
- `p98_conditional_reference`: conditional reference only. It is not a clean component, not a clean gold standard, and cannot be used for clean source selection.

## Allowed Inputs

The script may use already generated score artifacts from `clean_baseline_redesign_round_v1`, `no_p98_reversal_baseline_v1`, `clean_liquidity_adjusted_reversal_baseline_v1`, `clean_composite_reversal_tradability_v1`, and the p98 conditional baseline as a conditional reference only.

Allowed D0-visible enrichment fields are limited to `is_st`, `is_suspended`, `no_trade_flag`, `volume_zero_flag`, `amount_zero_flag`, `is_limit_up`, `is_limit_down`, `open_at_up_limit`, `close_at_down_limit`, `limit_rule_version`, `entry_buyable`, `exit_sellable`, `sellable_retry_next_open`, `list_date`, `listing_age_days`, `board_type`, `exchange`, and `limit_pct_rule`.

Blocked fields remain prohibited: `listing_age_trading_days`, `newly_listed_flag`.

## Diagnostic Dimensions

1. Full-cross-section rank correlation: daily RankIC, ICIR, yearly RankIC, and train/validation deltas.
2. TopK / nextK / bottom bucket: mean return, median return, spread, bottom-bucket behavior, and daily concentration.
3. Decile return shape: decile curve, top-bottom spread, monotonicity score, middle-decile inversion count, and bottom-decile diagnostics.
4. Yearly stability: train versus validation direction, validation yearly TopK improvement, and validation yearly RankIC damage.
5. Board / exchange exposure: TopK and composite-only exposure versus comparison-only exposure.
6. Liquidity bucket exposure: amount/liquidity buckets, with unavailable fields explicitly marked unavailable.
7. Tradability / limit status exposure: entry-buyable, no-trade, suspension, zero amount/volume, and limit-state flags.
8. Overlap / divergence with no-p98 and p98 conditional: daily overlap count, Jaccard, composite-only realized return, comparator-only realized return, and overlap return.
9. Score compression / dispersion: daily score standard deviation, range, interquartile spread, and compression versus comparators.
10. Large winner / large loser contribution: top winner contribution, bottom loser contribution, percentage of daily edge from top 5% days, and percentage of daily damage from worst 5% days.

## Decision Use

The result may support a later pre-registered clean candidate design only if train, validation, and yearly slices all show a stable, low-freedom, D0-visible explanation. This round never approves a strategy and never enters portfolio dry-run.
