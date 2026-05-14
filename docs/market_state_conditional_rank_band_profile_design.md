# Market-State Conditional Rank-Band Profile Design

This design defines a market-state conditional rank-band profile diagnosis under the exploratory sandbox.

It is exploratory descriptive research only. It is not alpha research, not a candidate, not a new baseline, not v4, not training, not backtest, not portfolio, not portfolio dry-run, not holdings generation, not `backtest_daily`, not formal metrics/readout, and not OOS evidence. Frozen test remains unread.

## Research Questions

1. Is TopK failure worse under specific D0-visible states?
2. Is mid-rank strength concentrated under specific market states?
3. Does the non-monotonic rank-band profile change with liquidity, board, limit, tradability, or listing-age calendar states?
4. Do `p98` and `multi_equal_weight_v1` conditional references show different conditional structures from clean scores?
5. Which findings can become future paper-only pre-registration hypotheses?

This design must not propose a candidate, trading rule, portfolio recommendation, or deployment conclusion.

## Allowed Inputs

Allowed:

- existing clean score artifacts;
- rank-band full profile diagnosis outputs as context;
- data-field enrichment allowed fields;
- D0-visible OHLCV / amount / state fields already available in governed artifacts;
- `p98` and `multi_equal_weight_v1` only as conditional references.

Forbidden:

- `listing_age_trading_days`;
- `newly_listed_flag`;
- label diagnostics for source selection;
- future / realized / `actual_exit` / `sell_price` as conditioning fields;
- frozen/test fields.

Unavailable fields must be explicitly marked `unavailable` and must not be fabricated.

## Fixed Rank Bands

- `rank_1_30`
- `rank_31_60`
- `rank_31_100`
- `rank_31_200`
- `rank_101_300`
- `rank_301_600`
- `bottom_30`

## Conditional Dimensions

Required dimensions:

- liquidity state: amount bucket (`bottom_20pct`, `mid_60pct`, `top_20pct`), `amount_zero_flag`, `volume_zero_flag`;
- board / exchange: `board_type`, `exchange`;
- limit / tradability: `is_limit_up`, `is_limit_down`, `open_at_up_limit`, `close_at_down_limit`, `entry_buyable`, `exit_sellable`, `sellable_retry_next_open`, `no_trade_flag`, `is_suspended`;
- listing age calendar state: `listing_age_days` bucket only;
- market-wide daily condition, if D0-visible and derivable: daily amount aggregate bucket. Daily universe median return and volatility proxy must be marked unavailable unless D0-visible return inputs exist.

## Required Output Per Condition

Each `condition_dimension x condition_value x model x rank_band` output must include:

- count;
- mean return;
- median return;
- daily win rate vs 0;
- TopK-minus-rank31_100 within condition;
- rank31_100-minus-TopK within condition;
- worst 5% damage;
- best 5% contribution;
- whether condition worsens head_failure;
- whether condition strengthens mid_rank.

## Required Summary

The diagnosis must report train and validation:

- strongest head_failure conditions;
- strongest mid_rank_strength conditions;
- whether condition effect is same direction in train and validation;
- whether validation yearly direction is stable;
- whether the effect is cross-model or a single-model phenomenon;
- whether conditional references differ, with `p98` / `multi_equal_weight_v1` marked conditional reference only;
- unavailable fields explicitly.

## Final Boundary

The output is descriptive only. It cannot directly form any trading rule. Any future mechanism hypothesis may only enter paper-only pre-registration.
