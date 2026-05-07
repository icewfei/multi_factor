# Design: Reversal + Cord30 Minimal Composite

**Status:** Design only. Not registered. No experiment running.

**Context:** p98 tail-handled reversal (IC 0.0459, spread +0.0049) passes all learnability + pipeline criteria. Cord30 (IC 0.0325, spread +0.0098) is the best positive-pass signal from the pv-corr family. They are mechanistically distinct: reversal captures anti-momentum in the cross-section, cord30 captures price-volume co-movement correlation. The question is whether combining them produces a signal strictly better than either alone.

---

## 1. Research Question

> Do tail-handled reversal (p98) and cord30 contain sufficiently orthogonal oracle-related information that a minimal equal-weight composite outperforms both standalone signals on IC and TopK pipeline compatibility?

This is NOT:
- A multi-signal search or feature engineering round
- A weighting optimization (no IC-IR, no shrinkage, no dynamic weights)
- A full portfolio pipeline run (IC-level + TopK only, same as tail-handling round)
- A data acquisition exploration

It is a single-candidate composite test: one formula, no tuning, pass/fail.

## 2. Baseline

**Primary baseline: p98 tail-handled reversal** — the strongest validated standalone signal.

| Signal | Median IC | CI | Top10 Label | Spread |
|---|---|---|---|---|
| **p98 reversal (primary)** | **0.0459** | [0.0422, 0.0499] | +0.0076 | +0.0049 |

**Secondary reference: cord30** — best positive-pass signal from pv-corr family.

| Signal | Median IC | CI | Top10 Label | Spread |
|---|---|---|---|---|
| cord30 (secondary) | 0.0325 | [0.0300, 0.0346] | +0.0076 | +0.0098 |

The round's real question is: **can we borrow cord30's pipeline compatibility (high spread) while preserving p98 reversal's IC lead?**

The composite must exceed p98 reversal on both IC and spread. Cord30 is the secondary reference — its spread (0.0098) sets an aspirational ceiling, but beating it is not a hard requirement.

## 3. Candidate (1 only)

### Composite: p98 reversal + cord30 equal-weight

**Candidate scheme ID:** `reversal_p98_cord30_ew_v1`

**Formula:**
```
composite_score = 0.5 * rank(p98_reversal_score) + 0.5 * rank(cord30_score)
```
where `rank()` is cross-sectional PERCENT_RANK per signal_date.

**Implementation:**
1. Compute p98 tail-handled reversal scores (negated reversal, exclude top 2%, from `nr_p98` view)
2. Compute cord30 scores (existing model_score_D0 from confirmatory_cord30 run)
3. Per signal_date, PERCENT_RANK each signal cross-sectionally
4. Average the two rank scores with equal weight
5. Re-rank the composite cross-sectionally (for TopK selection)
6. Measure IC and Top10/Bot10 labels

**Why equal-weight:**
Equal weight is the hardest test. If the signals are orthogonal, equal weight already captures the diversification benefit without needing optimized weights. If equal weight fails, optimized weights are unlikely to rescue it — the signals are too correlated or the weaker signal drags down the composite.

**Why not more signals:**
cord30 is the only positive-pass signal from pv-corr family with clean TopK direction. Adding marginal signals (pv_beta, corr30, imxd5) would add noise, not information — they share the same mechanism family as cord30 and would dilute rather than diversify. Two orthogonal mechanisms (reversal + price-volume correlation) is the right test.

## 4. Success Criteria

Primary baseline is p98 reversal. Both criteria must be met:

### A. IC: must exceed p98 reversal

| Criterion | Threshold | Rationale |
|---|---|---|
| Composite median daily IC | >= 0.040 | Preserve learnability threshold |
| Composite median daily IC | > p98 reversal (0.0459) | Composite must not degrade IC relative to the best standalone signal |
| Composite median daily IC | > cord30 (0.0325) | Floor check — implied by the above |

The composite is judged primarily against p98 reversal. If composite IC drops below 0.0459, the combination is destroying rather than aggregating information.

### B. Pipeline: must exceed p98 reversal

| Criterion | Threshold | Rationale |
|---|---|---|
| Composite Top10 avg label | > 0 | Basic direction check |
| Composite Top10-Bot10 spread | > p98 reversal spread (0.0049) | The round's thesis: cord30's pipeline strength can lift the composite's spread above p98 reversal's |

Cord30's spread (0.0098) is the aspirational ceiling but NOT a hard requirement. The question is whether adding cord30 to reversal improves spread at all — even a modest lift (e.g., 0.0049 → 0.0065) validates the compositing direction.

### Stop condition

Composite fails if EITHER:
- Composite median daily IC does not exceed p98 reversal IC (0.0459)
- Composite Top10-Bot10 spread does not exceed p98 reversal spread (0.0049)

In that case:
- p98 reversal remains the primary standalone baseline
- Cord30 is retired as a composite partner for reversal
- The next question: what other signal (beyond cord30) could be orthogonal to reversal?
- If no obvious candidate exists, the signal space has been maximally extracted from current data

## 5. Why Composite, Not Standalone Extension

| Path | Why skip / defer |
|---|---|
| p98 standalone portfolio run | Premature. Before running full fixed-test pipeline (9 gates, cost_stress, etc.), confirm that the IC + TopK advantage is real and that compositing with existing signals doesn't destroy it. One composite test is cheaper than a full pipeline run. |
| More reversal tail engineering | p98 is already a clean solution. Fiddling with p97/p96/p95 thresholds or regime-conditional cuts at this stage is diminishing returns. |
| New data sources | Reversal at 0.046 is the strongest signal found in current data. Combining it with the second-strongest (cord30 at 0.033) is the least-effort, highest-expected-value next move. If the composite fails, then we've exhausted the "combine existing signals" path and data acquisition becomes the clear next step. |

**What this single-candidate test resolves:**
- Whether the two best signals in the current feature space are orthogonal enough to composite
- Whether the pipeline's next baseline should be p98 reversal alone or p98+cord30 composite
- Whether "combine existing signals" is a viable path before data acquisition

## 6. IC Computation

Identical to all previous rounds:
- Spearman rank correlation: `CORR(score, label_5d_next_open_close)`
- Daily IC, >= 20 stocks per day
- Bootstrap CI: 10,000 resamples, seed=42
- Trainval-only snapshot, ranking_eligible_D0 filter

## 7. Execution Notes

- **Data:** Reversal scores from `exploratory_cross_horizon_c1_reversal_only/model_scores_D0.parquet`. Cord30 scores from `confirmatory_cord30_trainval_20260429/model_scores_D0.parquet`. Labels from `confirmatory_baseline_v1_trainval_20260429/project_label_panel.parquet`.
- **Contract:** `run_input_contract.research_trainval_20211231.json`
- **Computation:** Pure SQL in DuckDB. Negate reversal, apply p98 exclusion, rank both signals, average, re-rank, measure.
- **Expected effort:** ~1 script, ~1 composite score, ~1 diagnostic run.

## 8. References

- Reversal tail-handling results: `artifacts/fixed_test/reversal_tail_handling/reversal_tail_handling_results_20260502.md`
- pv-corr round 1 results: `artifacts/fixed_test/pv_corr_round1/pv_corr_round1_results_20260502.md`
- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md`
- Reversal tail-handling design: `项目总纲及计划/design_reversal_tail_handling_round.md`
