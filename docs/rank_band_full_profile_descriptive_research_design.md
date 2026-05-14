# Rank-Band Full Profile Descriptive Research Design

This document defines the first exploratory sandbox research design after `current_data_regime_research_stopped`.

This is descriptive mechanism research only. It is not alpha research, not a candidate design, not a strategy restart, not a portfolio dry-run, and not OOS evidence.

## Governance Boundary

This design operates under [exploratory_sandbox_policy_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/exploratory_sandbox_policy_after_data_regime_stop.md).

Allowed status:

- `exploratory descriptive`;
- descriptive mechanism research allowed;
- train/validation evidence may be summarized only as trainval diagnostic evidence;
- output is a failure mechanism summary and rank-band profile, not a promotion decision.

Hard prohibitions:

- no alpha claim;
- no candidate;
- no portfolio;
- no portfolio dry-run;
- no holdings generation;
- no training;
- no backtest;
- no frozen test;
- trainval not OOS;
- no validation tuning;
- no p98 as clean gold standard;
- no concrete trading rule.

## Research Question

The descriptive question is:

> Across existing clean scores and conditional references, what does the full rank-band return and exposure profile look like after the current data regime stop?

The goal is to understand whether observed TopK and mid-rank failures are shaped by head concentration, middle-rank structure, tail behavior, market-state exposure, cross-model disagreement, or feature interaction patterns.

This question does not ask whether any rank band is deployable. It does not choose a new band for portfolio use.

## Allowed Descriptive Scope

The design may describe the following:

- rank-band full profile across fixed rank bands;
- TopK, nextK, rank 31-100, rank 101-200, rank 201-300, and tail behavior;
- market-state conditional diagnostics within rank bands;
- long/short asymmetry of rank-band behavior;
- cross-model agreement/disagreement across existing score families;
- feature interaction description for existing D0-visible state and exposure fields;
- failure mechanism summary for why TopK or mid-rank evidence did not become deployable.

All rank bands must be fixed before analysis. The design may not expand, contract, or rename rank bands after viewing validation results.

## Inputs

Allowed inputs are existing governed artifacts and existing train/validation diagnostic outputs already inside the repository.

No new information source is introduced. No new data modality is introduced. Frozen test remains unread.

`p98` and `multi_equal_weight_v1` may appear only as conditional references. They must not be used as clean gold standards, clean components, or promotion anchors.

## Expected Output

Allowed outputs:

- a descriptive rank-band profile;
- a table or summary of fixed-band behavior;
- market-state and cross-model descriptive summaries;
- a failure mechanism summary;
- a list of unresolved questions for paper-only pre-registration.

Forbidden outputs:

- candidate name;
- score formula change;
- portfolio construction rule;
- backtest or portfolio metrics/readout;
- holdings;
- pass/fail promotion decision;
- OOS claim.

## Stop Rule

This descriptive round stops after producing a mechanism summary.

If the summary suggests a future implementable idea, the next allowed step is paper-only pre-registration. No implementation may start from this document alone.

## Decision Boundary

This design can conclude only:

- what the existing rank-band profile appears to explain;
- which mechanisms remain plausible;
- which future questions need paper-only pre-registration.

It cannot conclude:

- that any alpha exists;
- that any rank band is deployable;
- that any candidate should be opened;
- that portfolio work should resume;
- that trainval evidence is OOS.
