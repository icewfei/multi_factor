# Round Note: Reversal Tail-Handling

**Status:** Preregistered. Not running.

## Round positioning

- Phase: signal/learnability
- Tier: exploratory
- Type: tail_handling_structural_fix
- Changed dimension: score tail truncation (single-dimension)

## Candidates (2)

| ID | Method | Threshold |
|---|---|---|
| reversal_tail_exclude_p99_v1 | Per-day exclude top 1% of raw scores, re-rank | p99 cross-sectional |
| reversal_tail_exclude_p98_v1 | Per-day exclude top 2% of raw scores, re-rank | p98 cross-sectional |

**Implementation semantics (fixed):**
1. Per signal_date, rank by negated reversal raw score descending
2. Compute p99/p98 on raw scores for that date (cross-sectional)
3. Exclude stocks with raw score > daily threshold
4. Re-rank remaining stocks descending
5. TopK=10 from re-ranked universe; no gap-filling

## Baseline

- Primary: raw negated reversal (IC 0.0442, spread -0.0045)
- Secondary: alpha158_cord30 (IC 0.0325, spread +0.0098)

## Success Criteria (4 criteria, all must pass for at least one candidate)

**A. Learnability:**
- Median daily IC >= 0.040
- Bootstrap 95% CI excludes zero

**B. Pipeline compatibility:**
- Top10 avg oracle label > 0
- Top10-Bot10 spread > 0.003

## Decision tree

- Both pass → preferred = higher spread
- One passes → that method is the path forward
- Neither passes → reversal not salvageable with simple tail truncation; reopen data acquisition discussion

## References

- Design: `项目总纲及计划/design_reversal_tail_handling_round.md`
- Tail diagnosis: `scripts/run_reversal_tail_diagnosis.py`
- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md`
