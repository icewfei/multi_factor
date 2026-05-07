# Self-Audit: 2026-05-01 Research Session

**Purpose:** Strict review of conclusions, evidence chains, and overstatements made during the full-day research session.

**Result:** Partially reliable with one critical oracle flaw, now corrected. Observation-level results from the non-oracle rounds remain usable; oracle-based framework conclusions required major rollback and rewrite.

### Critical Finding (2026-05-02): Oracle Score-Direction Bug

The oracle score builder used `PERCENT_RANK() OVER (ORDER BY label DESC)` combined with `TopK selects model_score_D0 DESC`. `PERCENT_RANK` assigns 0 to the first row (highest label) and 1 to the last row (lowest label). `TopK DESC` then selects the stocks with score closest to 1 — the worst-label stocks, systematically. This bug was present in both V1 and Probe A.

**Consequence:** all oracle-based conclusions from 2026-05-01 were invalid and had to be re-evaluated from scratch.

**Corrected oracle results (post-bugfix):**
- V1 oracle: annual_relative_return = +2,888 (was -0.998)
- Probe A: annual_relative_return = +4,634 (was -0.999)

**Project-level impact:**
- `"execution-feasibility gap is primary bottleneck"` — retracted as an oracle-backed conclusion
- `"framework is execution-blocked"` — retracted
- signal/learnability layer is newly elevated by corrected oracle evidence

---

## A. Conclusion Audit

### 1. execution-feasibility gap is the primary hypothesis
**Not supported as a current top-line conclusion.**

This was plausible before oracle correction, but the corrected oracle reverses the supporting evidence. Execution constraints may still matter, but they are no longer the strongest oracle-backed explanation.

### 2. Oracle probe
**Fully supported after correction, but only as an upper-bound diagnostic.**

Proven now:
- corrected oracle under the same execution semantics and cost model can generate extremely large positive returns
- the framework is not execution-blocked under this oracle diagnostic

Not proven:
- that signal quality is the unique bottleneck
- that execution, extraction, or evaluation layers no longer matter
- that any real strategy can approach the oracle upper bound

### 3. 10-cohort / retain15 / retain50
**Fully supported at the observation level. Causal interpretations remain downgraded.**

- 10-cohort reduces turnover → verified
- retain15/50 improve return/drawdown → verified
- retain50 worsens cost_stress → verified as correlation, not as causal mechanism

### 4. D10 holding period redesign
**Partially supported — implementation boundary found, strategic claim still untested.**

What was proven:
- `planned_exit_date` can be patched in the project layer
- this patch alone does not change strategy metrics

What was **not** proven:
- whether D10 would work if execution path were recomputed

### 5. Project freeze status
**Fully supported in corrected form.**

The corrected freeze state is:
`framework_diagnosis_strongly_suggestive_not_conclusive`

---

## B. Evidence Chain Gaps

### Still-open causal chains
1. Why is the oracle-to-real gap so large?
2. What part of retain50 drives worse `cost_stress`?
3. Do different signal families fail for the same reason or for different reasons?
4. Would D10 behave differently after a true execution-path recomputation?

### Overstatements that were corrected
1. `"framework fully exhausted"` → corrected to `"strongly suggestive, not conclusive"`
2. `"holding period direction closed"` → corrected to `"D10 hypothesis unvalidated"`
3. `"execution-feasibility gap is primary bottleneck"` → retracted as an oracle-backed conclusion
4. `"oracle proves framework is blocked"` → retracted

---

## C. Corrected Position

**Reliable (fully supported by data / experiments):**
- All 5 signal families capped at 6/9
- 10-cohort reduces turnover to about 0.20
- retain15/50 improve return/drawdown in observed runs
- corrected oracle is strongly positive under the same execution and cost framework
- D10 patch changes `planned_exit_date` but does not recompute real execution path

**Deferred (requires new work to verify):**
- Why corrected oracle is so far above real signals
- D10 holding-period effectiveness
- Retain50 `cost_stress` causal mechanism
- Per-family root-cause decomposition

**Retracted (no longer acceptable as current project conclusions):**
- `"oracle produces total loss under execution constraints"`
- `"execution-feasibility gap is the primary bottleneck"`
- `"framework fully exhausted"`
- `"holding period direction closed"`
