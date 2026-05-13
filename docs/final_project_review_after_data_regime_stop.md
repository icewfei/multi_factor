# Final Project Review After Data Regime Stop

This document is the current entry-point project review after `current_data_regime_research_stopped`. It summarizes the research path, engineering implementation, project progress, root causes for stopping, and recommended next actions.

This is a governance and engineering review only. It does not train, backtest, run portfolio, generate holdings, generate formal metrics/readout, read frozen test, design trading rules, or claim strategy effectiveness.

## Executive Judgment

The project should pause strategy research under the current D0 OHLCV + state field regime.

The project is not blocked by a missing final implementation step. The current research question has been answered negatively under the available data regime: no clean, stable, portfolio-ready candidate emerged from the clean baseline / TopK / mid-rank line.

The repository should be retained as an audit asset and engineering asset. Future research should resume only with a new information source, a new data modality, or an independently pre-registered research problem that does not reuse the stopped TopK / mid-rank question.

## Research Path Review

The research path has been broad and mostly disciplined:

- Early daily price-volume signal engineering found exploratory improvements but no strict confirmatory winner.
- `multi_equal_weight_v1` became an exploratory/conditional reference, not a clean gold standard.
- Nonlinear confirmed5 / v2 / v3 did not convert model-layer edge into robust portfolio-layer edge.
- `p98` and `multi_equal_weight_v1` were downgraded to conditional reference only because they are not clean baseline components.
- no-p98 and clean baseline families improved governance cleanliness but did not solve TopK head quality.
- clean baseline redesign produced six candidates and no portfolio-ready candidate.
- composite, liquidity_quality, head-exclusion, and mid-rank routes were each decomposed and closed.
- `current_data_regime_research_stop_decision` stopped clean baseline / TopK / mid-rank research under current D0 OHLCV + state fields.

The important interpretation is that the project did not fail due to a single weak experiment. It exhausted a defined local research space and recorded why each branch did not justify portfolio continuation.

## Engineering Implementation Review

The repository contains valuable engineering assets:

- `scripts/` contains the core research implementation and diagnostics.
- `contracts/` defines run input, source mapping, exit policy, and blocker resolution semantics.
- `schemas/` defines structured outputs for scores, panels, portfolio artifacts, audits, and guardrail requests.
- `configs/` stores clean baseline and nonlinear challenger manifests.
- `docs/` records current governance decisions and audit boundaries.
- `tests/` contains contract-level audit tests and selected fixture-level implementation tests.
- guarded workflow and data enrichment next-use guardrails are implemented.

The main engineering weaknesses are:

- Core implementation remains script-heavy; `src/` is not yet the true module layer.
- Some scripts are large and difficult to reuse safely.
- Test dependencies were underdeclared before this review.
- Some older tests used subprocess interpreter assumptions that can diverge from the pytest environment.
- Documentation had stale current-stage references after the final stop decision.
- `artifacts/` is large and needs clearer audit-asset versus rebuildable-output classification.

These weaknesses are manageable engineering debt. They do not justify continuing strategy research, but they should be fixed before any future restart.

## Project Progress Review

The project has reached a valid stop point:

- Signal engineering phase: closed.
- Nonlinear challenger phase: closed.
- Clean baseline governance: completed enough to reject p98 as a clean gold standard and identify clean baseline weakness.
- Data enrichment guardrail: implemented.
- Clean baseline / TopK / mid-rank under current D0 OHLCV + state regime: stopped.
- Current recommendation: pause strategy research and preserve audit / engineering assets.

This is a research closure state, not an unfinished implementation state.

## Why The Project Cannot Continue On The Same Path

The current path cannot continue for five reasons:

1. The available information source is too limited. Existing D0 OHLCV + state fields can explain some failures but have not produced a clean deployable edge.
2. Model-layer edge did not reliably convert into TopK portfolio edge. RankIC / ICIR improvements are not enough when the deployed head is weak.
3. The strongest references are conditional, while the cleaner candidates are weak. This creates a clean-versus-strong gap.
4. Stability checks failed. Composite, liquidity_quality, head-exclusion, and mid-rank routes each failed a different stability or target-alignment requirement.
5. Further iteration would likely become trainval tuning. Without new data or a new pre-registered problem, additional rules would mostly increase overfitting risk.

## Recommended Actions

### Immediate Actions

- Keep strategy research paused.
- Keep no portfolio, no frozen test, no v4, no training, no backtest, no formal metrics/readout, and no concrete trading rules.
- Treat this repository as audit and engineering infrastructure.
- Commit the current stop/reframing/review documents and tests.
- Keep `p98` and `multi_equal_weight_v1` as conditional reference only.

### Engineering Cleanup

- Keep [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md) aligned with `current_data_regime_research_stopped`.
- Keep this review as the top-level narrative entry after README.
- Maintain complete development dependencies in `requirements-dev.txt`.
- Prefer `sys.executable` for subprocess tests so child processes use the same Python environment as pytest.
- Gradually extract reusable logic from long scripts into `src/` only after strategy research is paused and requirements are stable.
- Classify `artifacts/` into audit-retained records versus rebuildable outputs before any cleanup.

### Future Restart Conditions

Research may restart only if at least one condition is met:

- A new information source becomes available.
- A new data modality becomes available.
- A new research problem is independently pre-registered and does not reuse the stopped TopK / mid-rank claim as evidence.

Possible paper-only reframings include wider quantile, longer horizon, or risk-objective research, but none should enter code implementation from the current evidence.

## Final Recommendation

Final recommendation: pause strategy research, preserve the repository as an audit asset and engineering asset, and do not resume implementation until the restart conditions are satisfied.

The current project is valuable because it has a documented negative result, clear governance boundaries, and reusable infrastructure. Its next productive phase is cleanup and preservation, not another strategy round.
