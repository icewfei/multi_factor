# Clean Baseline Research Closure After TopK Failure

This document closes the entire clean baseline research program after the TopK selection failure diagnosis round. It integrates findings from four sub-rounds:

- `clean_baseline_redesign_round_v1`
- `clean_composite_topk_improvement_decomposition_round_v1`
- `clean_liquidity_quality_failure_decomposition_round_v1`
- `clean_topk_selection_failure_diagnosis_round_v1`

All evidence is train/validation diagnosis only: not OOS, not strategy approval, not a portfolio dry-run, not a backtest, not holdings generation, and not formal metrics/readout. Frozen test remains unread.

## Closure Boundary

- No portfolio, backtest, holdings, or `backtest_daily` was generated in any sub-round.
- No ML model was trained in any sub-round.
- No new candidate was created from the diagnosis sub-rounds.
- No threshold was tuned in any sub-round.
- No frozen test was read in any sub-round.
- Blocked fields were not used: `listing_age_trading_days`, `newly_listed_flag`.
- `p98` and `multi_equal_weight_v1` remain conditional reference only throughout.
- Trainval diagnosis is not OOS evidence.
- This is not a strategy effectiveness conclusion.

## Integrated Findings

### 1. Clean Baseline Redesign Round V1: No Portfolio-Ready Candidate

The redesign round produced six pre-registered clean candidates. All six passed score-layer gate. None simultaneously cleared the required validation RankIC improvement, positive TopK head proxy, and positive TopK-minus-nextK conditions.

- `clean_composite_reversal_tradability_v1` is the only new candidate with both positive validation TopK proxy and positive TopK-minus-nextK, but its validation RankIC falls to `0.006603`, materially below `no_p98_reversal_baseline_v1`.
- `clean_reversal_5d_liquidity_quality_v1` has the strongest validation RankIC among new candidates at `0.031770`, but TopK-minus-nextK remains negative.
- The three tradability/board/list-age clean candidates all have negative TopK proxy and negative TopK-minus-nextK.
- `clean_reversal_5d_limit_aware_v1` turns TopK proxy positive but TopK-minus-nextK remains negative and RankIC weakens.

Conclusion: no portfolio-ready candidate emerged from this round.

### 2. Composite Route: Rejected

The composite route was decomposed and rejected for the following reasons:

- Validation TopK proxy improvement versus clean comparators is real: composite beats no-p98 by `0.009859` and liquidity-quality by `0.004122`.
- However, composite TopK-minus-nextK is negative in train (`-0.001019`) and negative in validation year 2021 (`-0.000266`), so the improvement is not stable.
- RankIC damage is severe and persistent: validation RankIC delta is `-0.022099` versus no-p98, `-0.025167` versus liquidity-quality, `-0.027659` versus p98 conditional, appearing in every validation year.
- Score dispersion is compressed: validation daily score-std mean is about `0.1487`, versus about `0.2887` for comparators.
- Validation top-bottom decile spread is negative (`-0.000548`).
- Monotonicity score is only `0.556`, with four adjacent decile inversions.

The composite route is rejected. The TopK proxy improvement is real but the RankIC damage is too severe and the improvement is not stable enough to justify a next candidate.

### 3. Liquidity Quality Route: Rejected

The liquidity quality route was decomposed and rejected for the following reasons:

- Validation RankIC improvement versus no-p98 is real (`+0.003068`) and exists in each validation year (2019 `+0.005523`, 2020 `+0.002054`, 2021 `+0.001587`).
- However, the RankIC improvement is not a TopK head improvement. The edge is mainly middle/tail shaped.
- The top decile mean (`0.004413`) is below middle deciles 4-7 mean (`0.005809`).
- Segment RankIC is negative inside the top decile (`-0.0366`), mildly positive in the middle (`0.0123`), and strongest in the bottom decile (`0.0648`).
- TopK-minus-nextK remains negative (`-0.003235`) and is negative in every validation year.
- TopK beats nextK on only `43.6%` of validation days.
- The filter improves full-cross-section ordering mostly by avoiding weak low-liquidity tail names, not by making the first 30 names strongest.
- High-liquidity head concentration dilutes the reversal edge: top-liquidity names return `0.002408`, while mid-liquidity names return `0.003845`.

The liquidity quality route is rejected. The RankIC improvement is real but it is not a TopK head improvement, and TopK-minus-nextK remains persistently negative.

### 4. TopK Selection Failure: Widespread but No Stable D0-Visible Head-Exclusion Evidence

TopK selection failure is widespread across clean baselines, but not universal enough and not stable enough to justify a generic head-exclusion candidate.

- In validation, TopK < nextK and TopK < rank31_100 hold for five of six clean models. The rejected composite is the exception.
- The failure is best explained by a joint pattern: TopK is more extreme in reversal, more concentrated in high-liquidity names, carries more limit-down exposure, and has worse large-loser concentration than nextK.
- The strongest candidate D0-visible condition, high-liquidity head concentration, fails the required cross-model and yearly stability test.
- `limit_down_like` and `state_anomaly` conditions are also insufficient because some models are contradictory, some are null, and some yearly slices flip sign.

No stable D0-visible head-exclusion evidence exists. The current clean daily OHLCV/state fields explain a large part of the failure pattern, but they do not provide a stable, cross-model head-exclusion condition.

## Cumulative Judgments

### No Portfolio-Ready Candidate

Across all four sub-rounds, no clean baseline candidate simultaneously achieves: (a) validation RankIC parity or improvement versus no-p98, (b) positive TopK head proxy, and (c) positive TopK-minus-nextK. No portfolio-ready candidate exists in the clean baseline family.

### Do Not Enter Portfolio Dry-Run

Portfolio dry-run is not recommended. The clean baseline family has insufficient TopK head quality. p98 / multi_equal_weight_v1 are conditional reference only and are not clean enough to serve as portfolio construction inputs. Trainval diagnosis is not portfolio approval evidence.

### Do Not Open V4

A v4 round is not recommended. The four sub-rounds have exhausted the diagnostic value of the current clean D0 OHLCV + state field space. Further rounds of rule-based candidate design within this field space are unlikely to produce a qualitatively different outcome. The failure patterns are now well-characterized; the missing piece is not another rule variation but a different kind of information.

### Do Not Continue Hard-Coding Rules on Existing D0 OHLCV + State Fields

The current approach of hand-crafting D0-visible rules on the existing daily OHLCV and state fields (liquidity, tradability, limit status, board, exchange, listing age) has reached diminishing returns. The four sub-rounds collectively demonstrate that:

- D0 rules can explain and partially reshape TopK exposure profiles.
- D0 rules can improve full-cross-section RankIC (liquidity quality) or TopK proxy (composite), but not both simultaneously.
- D0 rules cannot produce a stable, cross-model head-exclusion condition from the current field set.
- The failure is structural, not a matter of insufficient rule granularity.

Further rule iteration on the same field space is not recommended.

### New Information Source / New Data Modality / Reframed Research Question Required for Next Phase

The next phase requires at least one of:

- A new information source beyond the current daily OHLCV + state fields.
- A new data modality (e.g., intraday, order-book, fundamental, alternative, or text data).
- A reframed research question that does not depend on solving clean TopK head quality from D0-visible daily rules alone.

The current clean baseline program is closed. Any successor research must be separately pre-registered and must articulate which new information source or modality it introduces, or how it reframes the problem to avoid the documented failure modes.

### P98 / Multi Equal Weight V1: Conditional Reference Only

`p98` and `multi_equal_weight_v1` remain conditional reference only. They were not used as clean components in any sub-round. They were used only for comparison and overlap analysis. Their validation RankIC and TopK proxy values are not clean evidence and must not be treated as clean gold standards.

### Frozen Test: Still Prohibited

Frozen test access remains prohibited. No frozen test evidence is introduced in this closure.

### Trainval Diagnosis: Not OOS

All evidence in this closure and in all four sub-rounds is train/validation diagnosis only. It is not out-of-sample evidence and must not be interpreted as strategy validation.

### Not a Strategy Effectiveness Conclusion

This closure is a research program closure, not a strategy assessment. It does not claim that any strategy is effective or ineffective. It only concludes that the clean baseline research program has exhausted its diagnostic value within the current field space.

## Decision

Close the clean baseline research program. Do not enter portfolio dry-run. Do not open v4. Do not continue rule-based candidate design on existing D0 OHLCV + state fields. Require new information source / new data modality / reframed research question for any successor phase. Maintain all existing prohibitions: no frozen test, no portfolio, p98 as conditional reference only, trainval not OOS.
