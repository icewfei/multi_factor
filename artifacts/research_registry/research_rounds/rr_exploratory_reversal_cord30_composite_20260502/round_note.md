# Round Note: Reversal + Cord30 Minimal Composite

**Status:** Preregistered. Not running.

## Round positioning

- Phase: signal/learnability
- Tier: exploratory
- Type: minimal_composite_check
- Changed dimension: two-signal equal-weight composite

## Baseline

- **Primary:** p98 tail-handled reversal (IC 0.0459, spread +0.0049)
- **Secondary (aspirational):** alpha158_cord30 (IC 0.0325, spread +0.0098)

## Candidate (1 only)

**reversal_p98_cord30_ew_v1**

```
composite = 0.5 × rank(p98_reversal) + 0.5 × rank(cord30)
```

Equal-weight rank composite. No tuning.

## Success Criteria (frozen)

**A. Learnability:**
- median IC >= 0.040
- median IC > p98 reversal (0.0459)

**B. Pipeline compatibility:**
- Top10 avg label > 0
- Top10-Bot10 spread > p98 reversal (0.0049)

## Stop Condition

If composite IC does NOT exceed p98 reversal IC (0.0459)
OR composite spread does NOT exceed p98 reversal spread (0.0049):
- Composite fails
- p98 reversal remains primary standalone baseline
- Cord30 retired as composite partner

## References

- Design: `项目总纲及计划/design_reversal_cord30_composite.md`
- Tail-handling results: `artifacts/fixed_test/reversal_tail_handling/`
- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/`
