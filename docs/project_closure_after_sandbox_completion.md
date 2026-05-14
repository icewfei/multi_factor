# Project Closure After Sandbox Completion

This document records the project-level closure state after sandbox understanding is completed.

It is a governance and preservation record only. It does not train, backtest, run portfolio, generate holdings, generate formal metrics/readout, read frozen test, design trading rules, or claim strategy effectiveness.

## Current Status

The current state is:

```text
status: current_data_regime_research_stopped
strategy_research: paused
sandbox_understanding: completed
repository_role: audit asset and engineering asset
```

This means the current D0 OHLCV + state research question is no longer waiting for another strategy iteration. The local sandbox allowed zone has already served its purpose: it completed the descriptive mechanism understanding that was still missing after the original stop decision.

## Closure Judgment

The current project should now be treated as a closed research question under the existing D0 OHLCV + state regime.

The project is not unfinished. It is finished in the stronger sense that:

- the strategy line is paused;
- the sandbox understanding is completed;
- the current negative result is documented;
- the repository is preserved for audit and engineering reuse;
- no additional same-question sandbox expansion is recommended by default.

## What The Project Now Knows

The current understanding can be summarized as follows:

1. D0 OHLCV + state is not completely structureless.
2. The visible structure does not land stably on deployable TopK.
3. Rank-band profiles are non-monotonic.
4. Near-head / `nextK` / `rank31_100` structure is descriptively stronger than exact TopK in the completed sandbox diagnostics.
5. Exact TopK is more vulnerable to stress / extreme / limit-like contamination.
6. Cross-model common TopK is weak enough that model agreement does not rescue the head.
7. `p98` and `multi_equal_weight_v1` remain conditional reference only.

These conclusions are descriptive-only, not OOS, not candidate evidence, and not strategy approval.

## What Must Not Happen Next

The following remain prohibited:

- no candidate
- no portfolio
- no portfolio dry-run
- no frozen test
- no OOS claim
- no v4
- no training
- no backtest
- no trading rule design
- no restart of the same TopK / near-head question through minor threshold or field variations

In particular, the completed sandbox understanding must not be reinterpreted as permission to promote:

- a near-head candidate;
- a stress-exclusion candidate;
- a disagreement-based candidate;
- a conditional-reference-guided candidate.

## Allowed Future Use Of The Repository

The repository should now be used in two ways only:

1. audit asset
   - preserve the negative result, decision records, guardrails, diagnostics, and closure logic;
2. engineering asset
   - preserve reusable scripts, contracts, schemas, tests, and workflow guardrails for future independent work.

This is the main productive value of the repository in its current state.

## Restart Conditions

Future work should restart only if the problem changes materially, for example:

- a new information source;
- a new data modality;
- a new independently pre-registered research problem that does not reuse the stopped TopK / mid-rank claim as implicit evidence.

Without those conditions, further continuation would mostly become trainval repetition or post-hoc reframing.

## Final Recommendation

Final recommendation:

- keep `strategy_research: paused`;
- treat sandbox understanding as completed;
- preserve the repository as an audit asset and engineering asset;
- do not continue the same research question;
- do not create a candidate;
- do not run portfolio;
- do not read frozen test.

This is a closed-question preservation state, not an unfinished-strategy state.
