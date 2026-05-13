# Current Data Regime Research Stop Decision

This document formally closes all clean baseline / TopK / mid-rank research under the current D0 OHLCV + state field regime. It integrates findings from five completed sub-rounds and issues a research stop decision. No new experiments were conducted for this record. No training, backtest, portfolio, or frozen test access was performed.

This is not a strategy effectiveness conclusion. All evidence cited is train/validation diagnosis only and is not OOS.

## Covered Research

| round | outcome |
| --- | --- |
| `clean_baseline_redesign_round_v1` | six candidates, none portfolio-ready |
| `clean_composite_topk_improvement_decomposition_round_v1` | TopK proxy improvement real but RankIC damage severe, route rejected |
| `clean_liquidity_quality_failure_decomposition_round_v1` | RankIC improvement real but edge is middle/tail, not TopK, route rejected |
| `clean_topk_selection_failure_diagnosis_round_v1` | TopK failure widespread, no stable D0-visible head-exclusion evidence |
| `clean_mid_rank_portfolio_hypothesis_round_v1` | mid-rank edge directionally present but yearly stability insufficient |

## Current Data Regime

The project operates under the following data constraints:

- No new information sources beyond the existing daily OHLCV + state fields.
- No new data modalities (no intraday, no order-book, no fundamental, no alternative, no text data).
- `data_field_enrichment_v1` is a conditional enrichment layer with blocked fields `listing_age_trading_days` and `newly_listed_flag` still unavailable.
- `p98` and `multi_equal_weight_v1` are conditional reference only, not clean gold standards and not clean components.
- Frozen test access remains prohibited.
- Train/validation evidence must not be relabeled as OOS.

## Cumulative Judgments

### 1. No Portfolio-Ready Candidate

The redesign round produced six pre-registered clean candidates. All passed score-layer gate. None simultaneously cleared the required validation RankIC improvement, positive TopK head proxy, and positive TopK-minus-nextK. No portfolio-ready candidate exists.

### 2. Composite Route: Rejected

The composite route was fully decomposed. TopK proxy improvement versus clean comparators is real but the RankIC damage is severe (`-0.022` versus no-p98) and appears in every validation year. TopK-minus-nextK is not stable (negative in train and in validation year 2021). Score dispersion is compressed and top-bottom decile spread is negative. The route is rejected.

### 3. Liquidity Quality Route: Rejected

The liquidity quality route was fully decomposed. RankIC improvement versus no-p98 is real (`+0.003`) and present in every validation year. However, the improvement is not a TopK head improvement. The edge is mainly middle/tail shaped: segment RankIC is negative inside the top decile (`-0.0366`), mildly positive in the middle (`0.0123`), and strongest in the bottom decile (`0.0648`). TopK-minus-nextK remains negative (`-0.003235`) in every validation year. The route is rejected.

### 4. Head-Exclusion Evidence: Insufficient

The TopK selection failure diagnosis confirmed the failure is widespread across clean baselines but found no stable D0-visible head-exclusion evidence. The strongest candidate condition, high-liquidity head concentration, fails the required cross-model and yearly stability test. `limit_down_like` and `state_anomaly` conditions are also insufficient. No generic head-exclusion candidate is justified.

### 5. Mid-Rank Edge: Directionally Present, Yearly Stability Insufficient

The mid-rank diagnosis found that rank31-100 > TopK holds for 6 of 7 clean models in validation and 7 of 7 in training. However, the pre-registered yearly consistency check is not met. Some clean models show mid-rank-minus-TopK direction flips within validation years. The fixed-band, no-tuning, cross-model, cross-split, cross-year stability requirement is not satisfied. A diagnostic portfolio dry-run is not recommended.

### 6. Do Not Continue Rule-Based Design on Existing D0 OHLCV + State Fields

The five sub-rounds collectively demonstrate that:

- D0 rules can explain and partially reshape TopK and rank-band exposure profiles.
- D0 rules can improve either full-cross-section RankIC or TopK proxy, but not both simultaneously.
- D0 rules cannot produce a stable, cross-model head-exclusion or mid-rank deployment condition from the current field set.
- The failure patterns are now well-characterized; the missing piece is not another rule variation.

Further rule iteration on the same field space has exhausted its diagnostic value.

### 7. Do Not Enter Portfolio Dry-Run

Portfolio dry-run is not recommended for any clean score under the current data regime. The clean baseline family lacks sufficient TopK head quality. The mid-rank edge lacks the required stability. p98 / multi_equal_weight_v1 are conditional reference only and are not clean enough to serve as portfolio construction inputs.

### 8. Do Not Open V4

A v4 round is not recommended. The diagnostic space of rule-based candidate design within the existing D0 OHLCV + state field set has been exhausted.

### 9. Conditional References

`p98` and `multi_equal_weight_v1` remain conditional reference only. They were used only for comparison and overlap analysis. Their validation RankIC and TopK proxy values are not clean evidence and must not be treated as clean gold standards.

### 10. Frozen Test: Prohibited

Frozen test access remains prohibited. No frozen test evidence was introduced in any sub-round.

### 11. Trainval Diagnosis: Not OOS

All evidence across all five sub-rounds is train/validation diagnosis only. It is not out-of-sample evidence and must not be interpreted as strategy validation.

### 12. Not a Strategy Effectiveness Conclusion

This stop decision is a research program closure. It does not claim that any strategy is effective or ineffective. It concludes that the current D0 OHLCV + state field regime has been fully explored for the stated research questions and has not yielded a stable, clean, portfolio-adjacent deployment candidate.

## Stop Decision

**Stop pursuing clean baseline, TopK head selection, and mid-rank deployment under the current D0 OHLCV + state field regime.**

Continue all existing prohibitions indefinitely:

- No portfolio or portfolio dry-run.
- No v4.
- No frozen test access.
- No relabeling trainval as OOS.
- No treating p98 / multi_equal_weight_v1 as clean gold standards.
- No entering a new round of rule-based candidate design on the current field set.

## Conditions for Resumption

Research may resume only when at least one of the following conditions is met:

1. A new information source becomes available (beyond the current daily OHLCV + state fields).
2. A new data modality becomes available (intraday, order-book, fundamental, alternative, text, or other).
3. The research question is reframed to no longer depend on solving clean TopK head quality or mid-rank deployment from D0-visible daily rules alone.

Any successor phase must be separately pre-registered and must articulate which condition is satisfied and how the new setup avoids the documented failure modes.

## Ratification

This decision record is the final word on the current data regime research program. It is not a strategy assessment. It does not authorize any new research activity. It closes the current phase and pauses strategy advancement pending new data or a reframed research question.
