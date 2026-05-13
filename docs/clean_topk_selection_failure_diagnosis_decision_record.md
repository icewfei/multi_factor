# Clean TopK Selection Failure Diagnosis Decision Record

This closes `clean_topk_selection_failure_diagnosis_round_v1`. It is train/validation diagnosis only: not OOS, not strategy approval, not a portfolio dry-run, not a backtest, not holdings generation, and not formal metrics/readout. Frozen test remains unread.

Artifacts:

- JSON: `/private/tmp/clean_topk_selection_failure_diagnosis.json`
- Markdown: `/private/tmp/clean_topk_selection_failure_diagnosis.md`

## Boundary

- No baseline candidate was created.
- No `TopK` / `nextK` / `rank 31-100` parameter was changed.
- No threshold was tuned.
- No ML model was trained.
- No portfolio, backtest, holdings, or `backtest_daily` was generated.
- No frozen test was read.
- Blocked fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98` and `multi_equal_weight_v1` remain conditional reference only.
- Trainval diagnosis is not OOS evidence.

## Main Finding

TopK selection failure is widespread across clean baselines, but not universal enough and not stable enough to justify a generic head-exclusion candidate. In train, all six clean models have `TopK < nextK` and `TopK < rank31_100`. In validation, five of six do; the only exception is the rejected composite. The strongest D0-visible condition, high-liquidity head concentration, still fails the required cross-model and yearly stability test.

## Required Questions

1. TopK selection failure 是否是 clean baselines 的共性问题？

Largely yes, but not universal. In validation, `TopK < nextK` and `TopK < rank31_100` hold for five of six clean models:

- `no_p98_reversal_baseline_v1`
- `clean_reversal_5d_liquidity_quality_v1`
- `clean_reversal_5d_limit_aware_v1`
- `clean_reversal_5d_board_neutral_v1`
- `clean_reversal_5d_tradability_filtered_v1`

The rejected `clean_composite_reversal_tradability_v1` is the exception, so this is not a clean universal law across every clean score.

2. TopK 是否稳定弱于 nextK / rank 31-100？

For the five models above, yes. They are all negative in train, validation, and every validation year for both `TopK-minus-nextK` and `TopK-minus-rank31_100`. The composite is not stable in that direction, so a cross-model universal statement is not supported.

3. 失败主要来自极端反转、流动性暴露、board/exchange、limit/tradability，还是大亏损贡献？

The failure is best explained by a joint pattern:

- TopK is more extreme in `reversal_5d_raw` than nextK for all clean models.
- TopK is more concentrated in high-liquidity names than the stronger nearby buckets.
- TopK often carries more limit-down exposure than nextK.
- TopK frequently has worse large-loser concentration than nextK.

Board/exchange composition shifts are visible but do not look like the primary universal driver.

4. 是否存在稳定 D0-visible head-exclusion evidence？

No. The strongest candidate condition is `high_liquidity`, but it fails the required cross-model stability test because:

- composite turns positive on validation for that condition
- limit-aware breaks yearly consistency in validation 2020

`limit_down_like` and `state_anomaly` are also insufficient because some models are contradictory, some are null, and some yearly slices flip sign.

5. 是否建议进入下一轮 preregistered head-exclusion candidate design？

No. The rule requires cross-model, train/validation/yearly stable, D0-visible evidence. This round does not clear that bar.

6. 是否建议进入 portfolio dry-run？

No.

7. 是否需要补字段或新数据？

Probably yes if the goal is to solve TopK conversion rather than just diagnose it. The current clean daily OHLCV/state fields explain a large part of the failure pattern, but they do not provide a stable, cross-model head-exclusion condition. That suggests current fields may be insufficient for a generic clean head-selection fix.

8. p98 / multi_equal_weight_v1 是否仍只作为 conditional reference？

Yes. They remain conditional reference only and were not used as clean components.

9. 是否继续禁止使用 blocked fields？

Yes.

10. 是否继续禁止 frozen test？

Yes.

## Structure of Failure

Validation TopK structures:

- `no_p98`: `TopK-minus-nextK=-0.008443`, `TopK-minus-rank31_100=-0.009762`
- `liquidity_quality`: `-0.003235`, `-0.004194`
- `limit_aware`: `-0.002579`, `-0.003692`
- `board_neutral`: `-0.009227`, `-0.010028`
- `tradability_filtered`: `-0.008475`, `-0.009777`
- rejected composite: `+0.001198`, `+0.000698`

The near-head buckets are consistently stronger than TopK in most clean models. Common winners live more often in `nextK` / `rank31_100` than in common TopK intersections:

- common clean TopK mean return: about `0.00056`
- common losers across clean TopKs: mean about `-0.0545`
- common winners in clean nextK: mean about `0.0656`
- common winners in clean rank31_100: mean about `0.0607`

## Exposure Summary

Across the five failing clean models:

- high-liquidity TopK return is worse than mid-liquidity nextK return in every case
- TopK limit-down exposure is materially above nextK for no-p98, liquidity-quality, board-neutral, and tradability-filtered
- board-level `TopK-minus-nextK` is negative on both main board and ChiNext
- TopK is generally not failing because of missing entry-buyability; those rates are near 100% for both TopK and nextK

This points more toward extreme-head placement and liquidity/limit contamination than toward simple tradeability failure.

## Decision

Do not open a generic head-exclusion candidate from this evidence. Do not enter portfolio dry-run. Continue using `p98` / `multi_equal_weight_v1` only as conditional references, continue blocking frozen test, and continue blocking blocked fields.
