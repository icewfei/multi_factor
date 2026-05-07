# Design: Signal/Learnability Round 1 — Price-Volume Correlation Family Engineering

**Status:** Design only. Not registered. No experiment running.

**Context:** Learnability diagnostic (2026-05-02, frozen) identified 4 positive_pass signals all from the price-volume correlation family: alpha158_cord30 (+0.0325), alpha158_corr30 (+0.0313), alpha158_imxd5 (+0.0316), pv_beta_rank (+0.0303). Median ICs are consistently 0.030-0.033 with CIs excluding zero. No other family shows this consistency. Reversal is a separate sign-inverted candidate (-0.0442), to be evaluated independently.

---

## 1. Round Goal

**Research question:**

> In the price-volume correlation family — the only family where all members pass the learnability diagnostic — can targeted feature engineering lift the median daily IC against the oracle label from the current ~0.032 ceiling to a meaningfully higher level?

"Meaningfully higher" is defined quantitatively in the success criterion (section 4).

This is NOT:
- A search across families
- A parameter sweep over window sizes
- An attempt to build a new composite score
- A test of D10, new data, or contract changes

## 2. Baseline

**alpha158_cord30_v1** — the strongest canonical cluster representative in the family.

| Metric | Value |
|---|---|
| Median daily IC vs oracle | 0.0325 |
| 95% CI | [0.0300, 0.0346] |
| Mechanism | Change-correlation of price and volume over 30 days |

Any new candidate must be compared against this baseline on the same trainval-only snapshot (`warehouse_20260429_trainval_20211231`), using the same IC computation method.

## 3. Candidate Feature Directions (2 directions)

### Direction A: Window-Ensemble Correlation

**Hypothesis:** The oracle label is sensitive to price-volume co-movement at multiple time scales simultaneously. A single 30d window discards horizon-specific information that could be recovered by combining short, medium, and long windows.

**What it is:**
- Compute cord (change-correlation) at 3 windows: 10d, 30d, 60d
- Rank-normalize each window's cord value cross-sectionally
- Output: `cord_ensemble = mean(cord_rank_10d, cord_rank_30d, cord_rank_60d)`

**Why not just test windows separately:**
The cluster registry already records cord5/cord10/cord20/cord30/cord60 as horizon variants in the same cluster. Testing them individually is a parameter search and unlikely to yield new information — if cord30 is best at 0.0325, cord10 or cord60 alone are unlikely to jump to 0.04. The ensemble hypothesis is that the interaction across horizons carries information that single windows don't.

**What success looks like:** median IC > 0.035 with CI excluding zero. A 10% lift over baseline suggests horizon ensemble adds value beyond the best single window.

### Direction B: Cross-Horizon Correlation Delta

**Hypothesis:** The *change* in price-volume correlation across time scales — not the correlation level itself — captures whether the relationship is accelerating or decelerating. This is structurally absent from all current family members.

**What it is:**
- `cord_delta_short = cord_rank_10d - cord_rank_30d` (recent acceleration)
- `cord_delta_long = cord_rank_20d - cord_rank_60d` (medium-term shift)
- Output: `cord_delta = mean(cord_delta_short, cord_delta_long)`

**Why this could work:** If a stock's price-volume correlation has recently increased (positive delta), it may indicate a regime change that the oracle label rewards. If correlation is stable across windows (zero delta), the stock is in a steady state. The magnitude of cord itself doesn't capture this dynamic.

**What success looks like:** median IC > 0.035 with CI excluding zero. If delta has any predictive power, even weak, it captures information orthogonal to cord level, making it a valuable composite input even before it beats cord30 standalone.

### What is intentionally excluded

- **Direction C (Correlation Quality / Stability):** Held for a future round. A and B are the highest-priority structural extensions; quality/stability is a natural follow-up but should not dilute the first round's focus.
- **Single-window variants of cord/corr:** Already in cluster registry as horizon variants. Testing them is parameter search, not feature engineering.
- **New data sources:** Out of scope for this round. The learnability diagnostic showed information exists in current features; the question is whether we can extract more of it.
- **Composite scoring / weighting optimization:** Premature. First find features, then combine.
- **Reversal:** Evaluated separately after the main round completes (section 5). Not mixed into this round.

## 4. Success Criterion

Two-tier, both evaluated against alpha158_cord30 on the same trainval-only snapshot:

**Tier 1 — Absolute threshold:**
At least one candidate achieves median daily IC >= 0.040 with bootstrap 95% CI excluding zero.

**Tier 2 — Relative to baseline:**
The same candidate shows median daily IC delta >= +0.005 over alpha158_cord30 (i.e., candidate_median_IC - 0.0325 >= 0.005). This ensures the improvement is not just absolute-threshold noise but a meaningful step beyond the current best-known signal in the family.

**Stop condition:**
If both candidates have median IC <= 0.035 with CIs overlapping cord30's CI [0.0300, 0.0346], and neither clears the +0.005 delta, the family is likely saturated at the ~0.03 level. In that case, do NOT expand to Direction C or more cord variants — instead conclude that current data modalities have hit their ceiling and re-open the data acquisition question.

**What "don't stop" looks like:**
If any candidate meets both Tier 1 and Tier 2, the family has more information to give. The next step would be a second narrow round: Direction C (correlation quality) as a follow-up, plus combining the best structural directions into a family-level composite. Reversal sign-flip can then be evaluated as a cheap standalone check.

## 5. Reversal: Deferred to Post-Round Check

Reversal is a sign-inverted candidate (median IC = -0.0442, CI [-0.0479, -0.0405]). It is NOT included in this round.

**Timing:** Run only after the pv-corr main round completes and produces a conclusion (pass or stop). This keeps the first round to a single narrative.

**One-line test (for later):**
Produce `model_score_D0` where reversal score is negated (`-1 * reversal_score`), compute median daily IC against oracle label. Success: median IC >= +0.04 with CI excluding zero.

**Constraint (for later):**
Do NOT mix negated reversal into a composite with pv-corr signals until the standalone sign-flip test confirms the sign-inverted IC is real and stable.

## 6. Why This Is the Right Next Step

**The learnability diagnostic eliminated the alternatives:**

| Path | Why skip for now |
|---|---|
| Massive feature mining | Only 1 family shows consistent signal. 4/4 positive_pass candidates are pv-corr. Broad search over families with zero signal (momentum 0.007, ROE 0.006, ROA 0.002) is negative-expected-value. |
| Data acquisition | The diagnostic proved information EXISTS in current features. The bottleneck is extraction quality, not data availability. Acquire new data only if this family plateaus. |
| Composite/weight optimization | Premature. The best single signal is cord30 at 0.0325; baseline composite is 0.0297. Composite before better components = averaging noise into signal. |
| D10 / contract changes | Not a signal problem. Returns to scope only if signal quality materially improves. |
| Reversal-as-composite-input | Must pass standalone sign-inversion test first. Don't mix uncertain polarities. |

**What this round resolves:**
- Whether the pv-corr family's ~0.03 IC is a feature design ceiling or a data ceiling
- Whether structural extensions (ensemble, delta) extract more information than single-window correlation
- Whether to continue investing in current data or pivot to acquisition

## 7. Execution Notes (for implementation, not now)

- **Data contract:** `contracts/run_input_contract.research_trainval_20211231.json`
- **Oracle label:** `label_5d_next_open_close` from `project_label_panel.parquet`
- **IC computation:** Same method as learnability diagnostic (Spearman rank correlation, bootstrap CI, 10k resamples)
- **Feature computation:** Requires access to daily bar data (vw_bars_daily) to compute raw cord values at multiple windows. Existing `build_baseline_model_scores.py` already has bar-level feature computation — the cord variants can be added as new SQL expressions in the same DuckDB view.
- **No new builder needed.** Both directions are SQL-computable from daily bars. No model training. No parameter tuning. Each direction produces a single score column.
- **Expected effort:** ~1 script, ~2 score columns, ~1 diagnostic run.

## 8. References

- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md`
- Canonical cluster registry: `artifacts/research_registry/canonical_cluster_registry_20260430.json`
- Phase transition review: this conversation, 2026-05-02
- Framework summary (frozen): `项目总纲及计划/final_summary.md`
