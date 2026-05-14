# Market-State Conditional Rank-Band Profile Summary

This summary records the market-state conditional rank-band profile diagnosis.

The round is exploratory descriptive research. It is not alpha, not a candidate, not a new baseline, not v4, not training, not backtest, not portfolio, not portfolio dry-run, not holdings generation, not `backtest_daily`, not formal metrics/readout, and not OOS. Frozen test remains unread.

## Outputs

The implemented script writes:

- `/private/tmp/market_state_conditional_rank_band_profile.json`
- `/private/tmp/market_state_conditional_rank_band_profile.md`

## Scope

The diagnosis keeps fixed rank bands:

- `rank_1_30`
- `rank_31_60`
- `rank_31_100`
- `rank_31_200`
- `rank_101_300`
- `rank_301_600`
- `bottom_30`

It reports conditional profiles for liquidity state, board / exchange, limit / tradability state, listing-age calendar state, and D0-visible market-wide amount condition. Unavailable fields are explicitly marked unavailable.

The diagnosis also reports whether condition effects are same direction in train and validation, whether validation yearly direction is stable, and whether an effect appears across multiple clean models rather than only one model.

## Boundary

No condition in this output can directly form any trading rule. Any future mechanism hypothesis may only enter paper-only pre-registration.

`p98` and `multi_equal_weight_v1` are conditional reference only.

## Future Paper-Only Hypotheses

Allowed future paper-only hypotheses include:

- whether high-liquidity or low-liquidity states intensify TopK failure;
- whether limit / tradability states explain more TopK weakness than board / exchange;
- whether listing-age calendar buckets alter mid-rank strength without using blocked fields;
- whether conditional references show different state sensitivity from clean scores.

## Insufficient Evidence Boundary

The output does not make any condition deployable. Evidence is insufficient for candidate creation, validation tuning, portfolio recommendation, or trading rule design. Unavailable fields remain unavailable rather than inferred.

## Evidence Boundary

This is trainval diagnosis only and not OOS. It does not read frozen test and does not authorize portfolio recommendation.
