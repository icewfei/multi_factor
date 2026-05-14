# TopK Failure Mechanism Map After Data Regime Stop

This document is exploratory descriptive research under [exploratory_sandbox_policy_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/exploratory_sandbox_policy_after_data_regime_stop.md).

It summarizes current clean baseline / TopK / mid-rank diagnostic evidence after `current_data_regime_research_stopped`. It does not introduce a strategy, train a model, run a backtest, run portfolio, read frozen test, create a candidate, design a trading rule, or claim strategy effectiveness.

## Governance Boundary

Current status:

- `strategy_research: paused`;
- `repository_role: audit asset and engineering asset`;
- paper-only allowed;
- exploratory descriptive research allowed;
- pre-registered implementation blocked by default;
- portfolio / promotion prohibited;
- `p98` / `multi_equal_weight_v1` conditional reference only;
- trainval diagnosis not OOS.

Hard prohibitions retained:

- no training;
- no backtest;
- no portfolio;
- no portfolio dry-run;
- no frozen test;
- no new candidate;
- no trading rule design;
- no strategy effectiveness claim;
- no trainval-as-OOS;
- no p98 as clean gold standard.

All evidence below is train/validation diagnosis only and is not OOS.

## Mechanism Map

| mechanism | current evidence | current evidence does not support | D0-visible? | stable? | candidate use now? | future paper-only pre-registration need |
| --- | --- | --- | --- | --- | --- | --- |
| 1. extreme reversal failure | Clean TopK diagnosis reports TopK is more extreme in `reversal_5d_raw` than nextK across clean models. Mid-rank diagnosis says TopK failure is partially explained by extreme reversal, high-liquidity concentration, and limit-down contamination. | Does not prove a generic reversal-threshold exclusion rule; does not prove any single reversal band is deployable. | Yes, reversal state is D0-visible in the current daily field regime. | Partially stable as a descriptive failure pattern, but not stable enough for candidate admission. | no | Pre-register fixed reversal exposure definitions, fixed rank bands, split/year stability checks, and stop rules before any implementation. |
| 2. high-liquidity dilution | Liquidity-quality decomposition finds TopK is overrepresented in high-liquidity names; top-liquidity names underperform mid-liquidity names. TopK selection failure says high-liquidity TopK return is worse than mid-liquidity nextK in every failing clean model. | Does not support a tuned liquidity threshold or a generic head-exclusion candidate; liquidity cleanup can remove weak names but also dilute reversal edge. | Yes, amount/liquidity buckets are D0-visible. | Insufficient for candidate use: high-liquidity condition fails cross-model/year stability because composite and limit-aware slices break the required pattern. | no | Pre-register fixed liquidity buckets, no threshold search, cross-model/year tests, and a rule that any result remains descriptive unless separately approved. |
| 3. limit / state anomaly exposure | TopK selection failure reports TopK often has more limit-down exposure than nextK; `limit_down_like` and `state_anomaly` help explain some bad-head behavior. | Does not support a generic limit/state exclusion rule because some models are contradictory, null, or flip by year. | Yes, limit and state fields are D0-visible where allowed by current contracts. | Not stable enough; evidence is explanatory but insufficient across models and years. | no | Pre-register exact state definitions, allowed fields, blocked-field exclusions, and cross-model/year pass criteria. |
| 4. TopK large loser concentration | TopK selection failure reports common clean TopK losers have much worse average return than nearby-bucket winners; TopK frequently has worse large-loser concentration than nextK. | Does not support post-hoc removal of large losers, because loser identity is realized after the fact; does not identify a stable D0-visible exclusion condition. | The realized loser outcome is not D0-visible; some associated state/liquidity/reversal exposures are D0-visible. | Evidence of the outcome pattern is strong, but D0-visible predictors are not stable enough for candidate use. | no | Pre-register D0-visible proxy variables before analysis, define false-positive/false-negative cost, and prohibit using realized loser labels for rule selection. |
| 5. nextK / rank31-100 stronger than TopK | Clean TopK diagnosis reports five of six clean models have `TopK < nextK` and `TopK < rank31_100` in validation, and the same five are negative in train, validation, and every validation year. Mid-rank diagnosis reports rank31-100 beats TopK for many clean models. | Does not support rank-band deployment; the composite exception and validation-year flips prevent a universal deployment conclusion. | Rank membership is D0-visible once the score is computed, but it is a portfolio mapping artifact, not an independent alpha source. | Directionally strong in many clean models; insufficient across all models/splits/years for deployment. | no | Pre-register fixed bands, no band tuning, population/weighting/cash treatment only on paper, and yearly stability requirements. |
| 6. full-cross-section RankIC not converting to TopK edge | Clean baseline redesign shows several clean scores have positive/full-cross-section RankIC while TopK proxy or TopK-minus-nextK remains weak. Liquidity-quality improves RankIC but edge is middle/tail shaped. | Does not support using RankIC alone as a promotion gate; does not prove TopK can be rescued by another local rule. | RankIC is a diagnostic statistic; the underlying D0 score is visible, but conversion failure is an ex-post diagnosis. | Stable as a recurring diagnostic theme; not a stable candidate mechanism by itself. | no | Pre-register separate discovery verdict and deployability verdict, with TopK and near-head conversion checks defined before analysis. |
| 7. p98 conditional reference remains stronger but not clean | Clean baseline redesign shows `p98_conditional_reference` has stronger validation RankIC and TopK proxy than most clean candidates. Baseline status records keep `p98` / `multi_equal_weight_v1` as conditional reference only because source-chain/provenance blockers remain. | Does not support treating p98 as clean gold standard, clean component, or proof that clean candidates failed absolutely. | The visible score output exists as a conditional reference; provenance cleanliness is not resolved. | Stronger in comparison, but governance status is not clean and not upgradeable without source-chain repair. | no | Pre-register any future use as comparison-only, require provenance disclosure, and require source-chain repair before any upgrade discussion. |
| 8. composite improves TopK but damages RankIC | Composite decomposition finds validation TopK proxy improves versus clean comparators, but validation RankIC damage is severe and persistent; TopK-minus-nextK is not stable because it is negative in train and in validation year 2021. | Does not support opening a clean composite candidate or portfolio dry-run; does not support sacrificing full-cross-section structure for aggregate TopK proxy. | Mostly yes: composite TopK is D0-visible and tradability/liquidity shaped. | Not stable enough; TopK improvement is incomplete and RankIC damage is severe. | no | Pre-register whether a future question studies score compression, tail separation, or TopK-only behavior, and block any weight tuning. |
| 9. liquidity_quality improves RankIC but not TopK | Liquidity-quality decomposition finds validation RankIC improves versus no-p98 in every validation year, but TopK-minus-nextK is negative in train, validation, and every validation year; the edge is middle/tail shaped. | Does not support a liquidity-quality candidate, portfolio dry-run, or liquidity-threshold tuning. | Yes, liquidity quality uses D0-visible state/exposure fields under the allowed field boundary. | Stable as a failure pattern: RankIC improvement persists, TopK conversion fails consistently. | no | Pre-register a descriptive head-placement versus liquidity-filtering question with fixed thresholds and no candidate output. |
| 10. mid-rank edge direction exists but yearly stability insufficient | Mid-rank diagnosis reports rank31-100 > TopK in many aggregate checks, including 6 of 7 clean models in validation and 7 of 7 in training. | Does not support diagnostic portfolio dry-run or mid-rank deployment because some validation-year directions flip and the fixed-band, no-tuning, cross-model/year requirement fails. | Rank bands are D0-visible after score ranking, but band choice is vulnerable to validation tuning. | Direction exists; stability is insufficient for promotion. | no | Pre-register fixed rank bands, no band search, split/year stability checks, and an explicit statement that any implementation is blocked by default. |

## Evidence Table

| evidence source | supports | insufficient for | governance status |
| --- | --- | --- | --- |
| `clean_baseline_redesign_round_v1` | Clean candidates pass score-layer gates, but none clear RankIC + TopK proxy + TopK-minus-nextK together. | Portfolio readiness, candidate promotion, p98 replacement. | trainval diagnosis not OOS; no portfolio; no frozen test. |
| `clean_topk_selection_failure_diagnosis_round_v1` | TopK failure is widespread; extreme reversal, high-liquidity concentration, limit exposure, and large-loser concentration explain much of the failure shape. | Generic stable D0-visible head-exclusion candidate. | exploratory/descriptive evidence only. |
| `clean_composite_topk_improvement_decomposition_round_v1` | Composite can improve validation TopK proxy versus clean comparators. | Stable TopK improvement, RankIC preservation, candidate opening. | rejected diagnostic object only. |
| `clean_liquidity_quality_failure_decomposition_round_v1` | Liquidity quality improves full-cross-section RankIC and helps explain middle/tail structure. | TopK head edge, portfolio dry-run, threshold tuning. | diagnostic object only. |
| `clean_mid_rank_portfolio_hypothesis_round_v1` | Mid-rank > TopK direction appears in many aggregate checks. | Deployment, same-contract diagnostic portfolio dry-run, fixed-band promotion. | closed; no portfolio-adjacent recommendation. |
| `multi_equal_weight_v1` / `p98` status records | Conditional references remain useful for disclosed comparison. | Clean gold standard, unconditional baseline, source-clean promotion anchor. | conditional reference only. |

## Rejected Interpretations

The current evidence rejects or does not authorize the following interpretations:

- "TopK failure means all A-share daily alpha is impossible." The evidence only closes this current D0 OHLCV + state regime and current research question.
- "RankIC improvement is enough for strategy promotion." Full-cross-section RankIC repeatedly fails to convert into TopK head edge.
- "TopK proxy improvement alone is enough." Composite improves TopK proxy but damages RankIC and lacks stable TopK-minus-nextK.
- "Liquidity filtering solves the clean baseline problem." Liquidity quality improves RankIC but does not create TopK edge.
- "Mid-rank should be deployed." Mid-rank direction exists, but yearly stability is insufficient.
- "High-liquidity, limit/state, or reversal conditions can be used as exclusion rules now." The D0-visible evidence is not stable enough for candidate use.
- "p98 is the clean gold standard." p98 / multi_equal_weight_v1 remain conditional reference only.
- "Trainval diagnosis is OOS." All cited evidence is not OOS.

## Allowed Paper-Only Future Questions

The following questions may be drafted only as paper-only pre-registration. They do not authorize implementation, candidate creation, portfolio, frozen test access, or v4.

1. Can fixed rank-band profiles be described without selecting bands based on validation outcomes?
2. Are extreme reversal exposures consistently linked to weak TopK outcomes after fixed D0-visible definitions are locked?
3. Does high-liquidity dilution explain TopK weakness independently from reversal extremity and limit/state exposure?
4. Are limit / state anomaly exposures explanatory after blocked fields remain excluded?
5. Can large-loser concentration be described using only pre-declared D0-visible proxies?
6. Is cross-model agreement stronger in nextK / rank31-100 than TopK under fixed descriptive bands?
7. Can feature interactions among reversal, liquidity, and state explain why RankIC improves without TopK conversion?
8. What evidence would be required to separate discovery verdicts from deployability verdicts without weakening promotion gates?
9. What source-chain repair would be needed before p98 or multi_equal_weight_v1 could be discussed beyond conditional reference status?
10. Which failure mechanisms remain after excluding composite and liquidity-quality routes as candidate sources?

## Final Statement

This document creates no strategy restart from this document.

It is a mechanism map and future paper-only question list. It does not approve alpha, does not create a candidate, does not design a trading rule, does not authorize portfolio or portfolio dry-run, does not open v4, does not read frozen test, and does not convert trainval diagnosis into OOS evidence.
