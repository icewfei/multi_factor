# Round Note: pv-corr Family Engineering Round 1

**Status:** Preregistered. Not running.

## Round positioning

- Phase: signal/learnability
- Tier: exploratory
- Type: feature_engineering_within_existing_family
- Changed dimension: feature design (not contract, not data, not execution)

## Baseline

- **alpha158_cord30_v1**: median IC = 0.0325, 95% CI [0.0300, 0.0346]

## Candidates (2)

| ID | Direction | Method |
|---|---|---|
| pv_corr_ensemble_v1 | A. Window-Ensemble | mean(cord_rank_10d, cord_rank_30d, cord_rank_60d) |
| pv_corr_delta_v1 | B. Cross-Horizon Delta | mean(cord_rank_10d - cord_rank_30d, cord_rank_20d - cord_rank_60d) |

## Success Criteria (frozen)

- **Tier 1:** median IC >= 0.040, bootstrap 95% CI excluding zero
- **Tier 2:** median IC delta >= +0.005 over cord30

## Stop Condition

Both candidates fail Tier 1 AND Tier 2 → family saturated → re-open data acquisition.

## Exclusions

- No reversal sign-flip (post-round only)
- No new data sources
- No composite optimization
- No contract changes
- No D10
- Direction C held for round 2 (contingent on round 1 pass)

## References

- Design: `项目总纲及计划/design_signal_learnability_round1_pv_corr_family.md`
- Learnability diagnostic (frozen): `artifacts/fixed_test/learnability_diagnostic/learnability_diagnostic_20260502.md`
