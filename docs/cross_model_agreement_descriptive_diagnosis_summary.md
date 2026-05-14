# Cross-Model Agreement Descriptive Diagnosis Summary

This summary records the implemented cross-model agreement / disagreement diagnosis.

The round is exploratory descriptive research only. It is descriptive-only, not alpha, not a candidate, not a new baseline, not portfolio, not OOS, and Frozen test remains unread. It does not restart strategy research.

## Outputs

The implemented script writes:

- `/private/tmp/cross_model_agreement_descriptive_diagnosis.json`
- `/private/tmp/cross_model_agreement_descriptive_diagnosis.md`

## Scope

The diagnosis reports:

- TopK agreement_count buckets `0..N`
- common TopK vs model-specific TopK
- common `nextK` / `rank_31_100` / `rank_31_200` / `rank_101_300` descriptive structure
- cross-band migration between TopK, `nextK`, `mid_head`, and `middle`
- amount bucket, board / exchange, limit / tradability, and `listing_age_days` bucket exposure decomposition
- train / validation direction checks
- validation yearly consistency checks

Cross-band migration uses exclusive bands so the implementation can separate `nextK` from 61-100 while still keeping aggregated `rank_31_100` outputs.

## Conditional References

`p98` and `multi_equal_weight_v1` are conditional reference only. They are not clean evidence, not clean gold standards, and not promotion anchors.

## Boundary

agreement_count cannot directly form any trading rule. The diagnosis does not make an alpha claim, does not create a candidate, does not run portfolio, does not read frozen test, and does not treat trainval diagnosis as OOS.

## Future Paper-Only Hypotheses

The implementation may emit future paper-only hypotheses about:

- whether common TopK consensus crowds into low-liquidity or limit-like names;
- whether stronger near-head names come from disagreement rather than exact TopK consensus;
- whether `p98` conditional reference aligns more with clean near-head consensus than with clean common TopK.

These remain paper-only hypothesis candidates, not strategy restart conditions.

## Insufficient Evidence Boundary

If train / validation direction or validation yearly direction is unstable, the output must say insufficient evidence. It does not authorize candidate creation, validation tuning, portfolio recommendation, or trading rule design.
