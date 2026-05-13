# Clean Baseline Redesign Round V1 Decision Record

This record closes `clean_baseline_redesign_round_v1`. It is trainval model-layer research only. It is not OOS, not strategy approval, not a portfolio readout, and not formal metrics/readout.

## Boundary

- No `p98` was used in new candidate construction.
- No label diagnostics were used for source selection.
- No frozen test was read.
- No ML model was trained.
- No portfolio, holdings, or `backtest_daily` was generated.
- Blocked enrichment fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98` and `multi_equal_weight_v1` are conditional references only, not clean gold standards.

## Score-Layer Gate

All six pre-registered candidates produced score artifacts and passed source-chain gate:

- `clean_reversal_5d_tradability_filtered_v1`: pass, included rows `10746604`.
- `clean_reversal_5d_board_neutral_v1`: pass, included rows `10776418`.
- `clean_reversal_5d_limit_aware_v1`: pass, included rows `10508613`.
- `clean_reversal_5d_liquidity_quality_v1`: pass, included rows `8689240`.
- `clean_reversal_5d_listing_age_calendar_v1`: pass, included rows `10514731`.
- `clean_composite_reversal_tradability_v1`: pass, included rows `10776418`.

## Model-Layer Result

Validation results:

| candidate | RankIC | ICIR | TopK proxy | TopK minus nextK | decision |
| --- | ---: | ---: | ---: | ---: | --- |
| `no_p98_reversal_baseline_v1` | 0.028702 | 0.2350 | -0.005425 | -0.008443 | existing clean anchor remains weak at TopK |
| `clean_reversal_5d_tradability_filtered_v1` | 0.027602 | 0.2257 | -0.005432 | -0.008475 | fails TopK head quality |
| `clean_reversal_5d_board_neutral_v1` | 0.030643 | 0.2705 | -0.005774 | -0.009227 | full-cross-section edge, fails TopK head quality |
| `clean_reversal_5d_limit_aware_v1` | 0.021216 | 0.1733 | 0.000754 | -0.002579 | TopK turns positive, but TopK-minus-nextK remains negative and RankIC weakens |
| `clean_reversal_5d_liquidity_quality_v1` | 0.031770 | 0.2519 | 0.000312 | -0.003235 | full-cross-section edge and positive TopK, but TopK-minus-nextK remains negative |
| `clean_reversal_5d_listing_age_calendar_v1` | 0.028052 | 0.2294 | -0.005612 | -0.008750 | fails TopK head quality |
| `clean_composite_reversal_tradability_v1` | 0.006603 | 0.0557 | 0.004434 | 0.001198 | TopK head quality improves, but full-cross-section edge collapses |

Conditional references:

| reference | status | validation RankIC | validation TopK proxy | validation TopK minus nextK |
| --- | --- | ---: | ---: | ---: |
| `p98_conditional_reference` | conditional reference only | 0.034263 | 0.004720 | 0.000210 |
| `multi_equal_weight_v1_conditional_reference` | conditional reference only | 0.056382 | 0.006025 | -0.000845 |

## Decision

No new clean redesign candidate is recommended for same-contract portfolio dry-run preparation.

Rationale:

- No candidate simultaneously clears the required validation RankIC improvement, positive TopK head proxy, and positive TopK-minus-nextK conditions.
- `clean_composite_reversal_tradability_v1` is the only new clean candidate with both positive validation TopK proxy and positive TopK-minus-nextK, but its validation RankIC falls to `0.006603`, materially below `no_p98_reversal_baseline_v1`.
- `clean_reversal_5d_liquidity_quality_v1` has the strongest validation RankIC among new candidates at `0.031770`, but TopK-minus-nextK remains negative.
- The current D0 visible enrichment fields help explain some TopK behavior, especially limit/liquidity/tradability quality, but they do not cleanly replace the p98 conditional enhancement.

## Interpretation

The round provides useful negative evidence. Clean D0 rules can improve parts of the head-quality profile, but not enough to justify portfolio dry-run preparation; continue not running portfolio.

This is not a strategy effectiveness conclusion and not OOS evidence. Frozen test remains unread.
