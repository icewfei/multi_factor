# Design: Reversal Tail-Handling Round

**Status:** Design only. Not registered. No experiment running.

**Context:** Reversal tail-failure diagnosis (2026-05-02) showed:
- Negated reversal has the strongest IC of any tested signal (median 0.0442, CI [0.0405, 0.0479])
- But Top10 label is negative (-0.0018), spread inverted (-0.0045)
- The failure is extremely narrow: Top20 label already positive (+0.0019)
- Excluding top 1% of scores restores positive spread (+0.0040) and lifts IC to 0.0470
- Excluding top 2% gives best spread (+0.0049) with IC 0.0459
- Tail failure is concentrated in recent market regimes (2017-2021)

---

## 1. Research Question

> Given that the strongest known signal (negated reversal, IC 0.044) fails only at the extreme score tail (Top ~10-15 stocks), can a minimal per-day score-tail truncation simultaneously preserve the signal's high IC and restore correct TopK direction?

This is NOT:
- A new feature engineering round
- A composite construction round
- A data acquisition exploration
- A modeling or parameter sweep

It is a structural fix validation: proving that tail pathology is separable from signal quality.

## 2. Baseline

**Primary baseline: raw negated reversal** (no tail handling).

| Metric | Value |
|---|---|
| Median daily IC | 0.0442 |
| 95% CI | [0.0405, 0.0479] |
| Top10 avg label | -0.0018 |
| Top10-Bot10 spread | -0.0045 |

**Secondary reference: alpha158_cord30** — the best positive-pass signal from learnability diagnostic.

| Metric | Value |
|---|---|
| Median daily IC | 0.0325 |
| 95% CI | [0.0300, 0.0346] |
| Top10 avg label | +0.0076 |
| Top10-Bot10 spread | +0.0098 |

## 3. Candidates (2 methods)

### Method 1: Exclude top 1%

**Candidate scheme ID:** `reversal_tail_exclude_p99_v1`

**Rule (precise implementation semantics):**
1. Per signal_date, rank all stocks by negated reversal raw score descending
2. Compute the 99th percentile of negated reversal raw scores for that signal_date (cross-sectional)
3. Exclude all stocks with raw score strictly above this daily p99
4. Re-rank remaining stocks by negated reversal raw score descending
5. Select TopK=10 from the re-ranked remaining universe

**Key constraints:**
- Percentile is computed on raw negated reversal score (not rank score, not composite)
- Threshold is per signal_date cross-sectional (not global, not rolling)
- Exclusion removes stocks from the eligible pool entirely on that date
- After exclusion, ranking restarts from rank 1 on the remaining universe
- No gap-filling: excluded slots are not replaced from lower ranks

**Rationale:** Minimal intervention. Removes ~1% of stocks per day (~30-50 names). Diagnosis showed IC 0.0470, spread +0.0040.

### Method 2: Exclude top 2%

**Candidate scheme ID:** `reversal_tail_exclude_p98_v1`

**Rule:** Same as Method 1, but using the 98th percentile cross-sectionally per signal_date. Exclude stocks with raw score above daily p98, then re-rank.

**Rationale:** Slightly more aggressive cut. Diagnosis showed best spread (+0.0049) with IC 0.0459. Trade-off: more stocks excluded but cleaner top tail.

### What is intentionally excluded

- **Winsorization (clip at percentiles):** Diagnosis showed it restores direction but with weaker spread (+0.0015). Included in diagnosis but excluded from formal candidates: exclusion is strictly better on both IC and spread.
- **Exclude top 5%:** Over-kill. Spread degrades (+0.0041) relative to 2% exclusion, and IC is similar. The sweet spot is 1-2%.
- **Per-year or regime-conditional thresholds:** Adds complexity without clear benefit. Simpler is better for a first validation round.
- **Reversal in composite with cord30:** Premature. First prove tail handling works standalone.

## 4. Success Criteria

Two independent dimensions, both must pass. Evaluated on trainval-only snapshot (`warehouse_20260429_trainval_20211231`).

### A. Learnability (IC quality)

| Criterion | Threshold | Rationale |
|---|---|---|
| Median daily IC | >= 0.040 | Preserve the learnability diagnostic threshold; reversal must remain the strongest signal |
| Bootstrap 95% CI | Excludes zero | Signal must be directionally reliable |

### B. Pipeline compatibility (TopK direction)

| Criterion | Threshold | Rationale |
|---|---|---|
| Top10 avg oracle label | > 0 | The portfolio actually buys stocks with positive expected return |
| Top10-Bot10 oracle label spread | > 0.003 | Top picks are meaningfully better than bottom picks |

(Spread > 0.003 already implies spread > 0 — the weaker condition is redundant.)

### Pass condition

**At least one method must pass all four criteria.** If both pass, the method with higher Top10-Bot10 spread is preferred for subsequent rounds.

If only one of {A, B} passes (e.g., IC > 0.040 but spread still negative), the round is a partial failure: tail handling can't simultaneously preserve IC and restore direction. This would reopen the question of whether reversal can be used in the current pipeline at all.

### Stop condition

If neither method achieves both learnability AND pipeline compatibility, reversal is not salvageable with simple tail truncation alone. In that case, either:
- Accept reversal as a "ranking signal only" (useful for broad ranking, not for TopK selection), or
- Defer reversal to a later phase after more sophisticated tail modeling

## 5. IC Computation Method

Identical to learnability diagnostic (frozen):
- Spearman rank correlation: `CORR(score, label_5d_next_open_close)`
- Daily IC aggregated over all trading days where >= 20 stocks have non-null scores and labels
- Bootstrap CI: 10,000 resamples, seed=42
- Trainval-only snapshot, ranking_eligible_D0 filter

Top10/Bot10 labels computed per day, then averaged across days.

## 6. Why This Round, Not Data Acquisition

| Path | Why skip for now |
|---|---|
| Data acquisition | The best signal (reversal, IC 0.044 > cord30 0.033) is broken by a narrow tail pathology, not by insufficient data. Fix the pathology first. Acquiring new data while a known-fixable signal sits unused is negative-expected-value. |
| pv-corr family round 2 | Round 1 showed saturation at ~0.03. Direction C (correlation quality) is held but unlikely to break the ceiling. Reversal at 0.044 is a better use of the next round. |
| Composite construction | Premature. First prove tail-handled reversal works standalone. Then composite with cord30 in a subsequent round. |

**What this round resolves:**
- Whether the strongest known signal can be made pipeline-compatible with a one-line exclusion rule
- Whether "tail pathology" and "signal quality" are separable problems
- Whether the next phase should be "tail-aware signal construction within existing feature space" or "data acquisition"

## 7. Execution Notes (for implementation, not now)

- **Data:** Reversal scores from `exploratory_cross_horizon_c1_reversal_only/model_scores_D0.parquet`. Oracle labels from `confirmatory_baseline_v1_trainval_20260429/project_label_panel.parquet`.
- **Contract:** `run_input_contract.research_trainval_20211231.json`
- **Implementation:** Negate reversal score. Per signal_date, compute 99th (or 98th) percentile, filter, re-rank. Pure SQL. No new builder.
- **Expected effort:** ~1 script, ~10 lines of SQL change from reversal diagnosis.

## 8. References

- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md`
- Reversal tail diagnosis (this session): `scripts/run_reversal_tail_diagnosis.py`
- pv-corr round 1 results: `artifacts/fixed_test/pv_corr_round1/pv_corr_round1_results_20260502.md`
- Design round 1: `项目总纲及计划/design_signal_learnability_round1_pv_corr_family.md`
