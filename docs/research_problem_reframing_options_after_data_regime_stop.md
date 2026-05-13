# Research Problem Reframing Options After Data Regime Stop

This document evaluates whether the project should continue by redefining the research problem after `current_data_regime_research_stopped`.

This is a paper-only governance record. It introduces no training, no backtest, no portfolio, no portfolio dry-run, no holdings generation, no new metrics/readout, and no frozen test access. It does not open v4 and does not define concrete trading rules.

## Boundary

- `current_data_regime_research_stopped`: clean baseline / TopK / mid-rank research under the current D0 OHLCV + state field regime has formally stopped.
- `no new information source`: there is no source beyond current daily OHLCV + state fields.
- `no new data modality`: there is no intraday, order-book, fundamental, alternative, text, or other new modality.
- `no portfolio`: no portfolio, portfolio dry-run, execution run, holdings generation, or backtest is authorized.
- `no frozen test`: frozen test remains unread and prohibited.
- `not OOS`: all existing evidence is train/validation diagnosis only, not OOS.
- `p98 conditional reference only`: `p98` and `multi_equal_weight_v1` remain conditional reference only, not clean gold standards and not deployment inputs.
- Trainval diagnosis must not be repackaged as strategy validation.
- No conclusion in this document claims that any strategy is effective.

## Prior Evidence Base

Current evidence supports only these statements:

- The clean baseline redesign found no portfolio-ready candidate.
- The composite route is rejected because TopK proxy improvement came with severe RankIC damage and unstable TopK-minus-nextK.
- The liquidity_quality route is rejected because its improvement is middle/tail shaped, not a stable TopK head improvement.
- Head-exclusion evidence is insufficient; no D0-visible exclusion condition passed cross-model and yearly stability requirements.
- Mid-rank edge is directionally present in some aggregate checks, but yearly stability is insufficient.
- Portfolio diagnostics did not provide strong enough clean evidence to authorize formal portfolio work.

Current evidence does not support:

- Restarting TopK alpha research under the same question.
- Treating wider rank bands as deployable.
- Treating 10d, 20d, or monthly holding periods as evidenced by 5d results.
- Landing any head-exclusion filter.
- Treating p98 or `multi_equal_weight_v1` as clean gold standards.
- Reading frozen test or calling trainval diagnosis OOS.

## Reframing Options

### Option 1. Wider Quantile Portfolio Instead of TopK

| field | assessment |
| --- | --- |
| Research question | Whether the current D0 OHLCV + state signals contain a more stable broad-rank effect outside the TopK head, such as rank 31-100, rank 31-200, or rank 101-300, without assuming TopK is the target. |
| Difference from original problem | The original problem asked whether the top-ranked names can form a clean alpha candidate. This reframing asks whether the signal is broader and weaker, and whether the head should no longer be privileged. |
| New label / execution contract | Likely yes for execution contract; possibly no for label if the return horizon remains unchanged. A band-level objective would need explicit population, weighting, liquidity, turnover, and cash treatment contracts before any implementation. |
| Independent pre-registration | Required. The rank bands, success criteria, admissible diagnostics, and stop rules must be registered before any analysis. |
| Existing evidence supports | Mid-rank may be directionally better than TopK in some aggregate trainval diagnostics. This supports only hypothesis generation. |
| Existing evidence does not support | It does not support portfolio resumption. Mid-rank yearly stability is insufficient, and existing diagnostics are not OOS. |
| Maximum risk | Band choice becomes another form of trainval-selected tuning, especially if rank ranges are expanded until a favorable readout appears. |
| Recommended as next stage | No implementation next. Paper-only hypothesis framing is acceptable. |
| Recommendation level | conditional |

### Option 2. Lower-Frequency / Longer-Holding Research

| field | assessment |
| --- | --- |
| Research question | Whether the same D0 OHLCV + state field regime has evidence at a lower-frequency or longer-holding target, such as 10d, 20d, or monthly evaluation, rather than the current 5d formulation. |
| Difference from original problem | The original problem is a 5d daily cross-sectional alpha question. A 10d, 20d, or monthly setup changes the prediction target, decay assumption, turnover profile, and execution timing. |
| New label / execution contract | Yes. A new horizon needs a new label definition and a new execution contract. The current 5d label and conclusions cannot be reused as evidence. |
| Independent pre-registration | Required. This is a new research problem and must be independently pre-registered before any data access or analysis. |
| Existing evidence supports | Existing evidence only suggests that 5d TopK / mid-rank deployment failed under current stability requirements. It may motivate asking whether horizon mismatch exists. |
| Existing evidence does not support | It does not support any 10d, 20d, or monthly edge. The 5d conclusions cannot be transferred to a new horizon. |
| Maximum risk | Horizon search can become implicit multiple testing if several holding periods are tried after failure. |
| Recommended as next stage | Not as implementation. Conditional only if the next work is a paper pre-registration with no training, no backtest, no portfolio, and no frozen test. |
| Recommendation level | conditional |

### Option 3. Risk-Control / Filter Research Instead of Alpha Selection

| field | assessment |
| --- | --- |
| Research question | Whether reversal, state, and liquidity fields can identify names that are unsuitable for inclusion in a separately defined portfolio, without claiming they create standalone alpha. |
| Difference from original problem | The original problem ranked stocks to maximize alpha in the selected head. This reframing treats the fields as risk controls or admission filters, not as primary alpha selectors. |
| New label / execution contract | Likely yes. A filter contract needs a base portfolio, rejection population, cost of false exclusions, and accepted risk objective. Without a base portfolio, the filter target is undefined. |
| Independent pre-registration | Required. The filter objective, base universe, allowed exclusions, and failure criteria must be registered independently. |
| Existing evidence supports | Existing diagnostics show certain D0-visible states help explain bad TopK behavior and large-loser concentration. |
| Existing evidence does not support | It does not support landing a filter. Current head-exclusion evidence is unstable, and no generic D0-visible exclusion condition passed cross-model and yearly stability checks. |
| Maximum risk | A filter can silently become a hard-coded alpha rule, using unstable trainval patterns to remove inconvenient names. |
| Recommended as next stage | Not recommended until there is an independently justified base portfolio or external risk objective. |
| Recommendation level | not recommended |

### Option 4. Stability / Risk-Control Objective Instead of Return Maximization

| field | assessment |
| --- | --- |
| Research question | Whether current fields can reduce left-tail outcomes, extreme losses, untradable exposures, or instability, rather than maximize average return or TopK alpha. |
| Difference from original problem | This is not the original TopK alpha target. It changes the objective from return maximization to stability and risk control. |
| New label / execution contract | Yes. A left-tail or tradability-risk target needs a new label or target statistic and a new execution contract defining the risk unit being controlled. |
| Independent pre-registration | Required. Risk objective, target statistic, allowed evidence, and minimum practical relevance must be registered before analysis. |
| Existing evidence supports | Some diagnostics indicate worse large-loser concentration, limit-like exposure, and tradability/state patterns in problematic heads. |
| Existing evidence does not support | It does not support a risk-control strategy or a deployable rule. It also does not prove risk reduction survives a new target, new horizon, or portfolio construction. |
| Maximum risk | The project may redefine success after alpha failure and overstate diagnostic explanations as risk-management evidence. |
| Recommended as next stage | Conditional as paper research only. It is a different problem and cannot inherit the TopK alpha evidence. |
| Recommendation level | conditional |

### Option 5. Portfolio Construction Research Instead of Daily Cross-Sectional Ranking

| field | assessment |
| --- | --- |
| Research question | Whether portfolio construction choices such as weighting, cash deployment, turnover control, and risk budget can improve the use of an already justified signal. |
| Difference from original problem | The original problem was daily cross-sectional signal ranking. This reframing studies construction mechanics, not signal discovery. |
| New label / execution contract | Yes for execution contract. It may not need a new label if the signal target is unchanged, but it needs a clean approved input signal before portfolio construction can be meaningful. |
| Independent pre-registration | Required. Portfolio construction objectives, allowed inputs, constraints, and diagnostics must be registered before any run. |
| Existing evidence supports | Prior portfolio diagnostic work identified construction gaps and made clear that construction choices matter. |
| Existing evidence does not support | It does not support opening formal portfolio work now. Previous portfolio diagnostic did not find strong enough clean evidence, and no current clean signal is portfolio-ready. |
| Maximum risk | Construction research could mask weak signal evidence and turn into portfolio search over unstable trainval artifacts. |
| Recommended as next stage | Not recommended now. A clean input signal or separately justified research target is required first. |
| Recommendation level | not recommended |

### Option 6. Pause A-Share Daily Clean Alpha Research

| field | assessment |
| --- | --- |
| Research question | Whether the correct next action is to stop strategy research under the current A-share daily clean alpha regime and retain the repository as audit and engineering infrastructure. |
| Difference from original problem | This is not an alpha problem. It is a governance decision to avoid continuing after the current data regime failed to produce a stable clean candidate. |
| New label / execution contract | No. Pausing needs no new label and no execution contract. |
| Independent pre-registration | No for the pause itself. Any future restart would require independent pre-registration. |
| Existing evidence supports | The current data regime has no portfolio-ready clean candidate; composite and liquidity_quality routes are rejected; head-exclusion and mid-rank evidence are unstable; trainval is not OOS; p98 is conditional reference only. |
| Existing evidence does not support | It does not support a claim that no A-share strategy can exist. It supports only pausing this clean daily OHLCV + state alpha program until new data or a genuinely new problem definition exists. |
| Maximum risk | Opportunity cost if a valid reframing could have been pre-registered later. This is lower than the risk of continuing implementation without clean evidence. |
| Recommended as next stage | Yes. Preserve engineering assets, documentation, audits, guardrails, and reproducibility records; do not continue strategy research. |
| Recommendation level | recommended |

## Cross-Option Ranking

| option | recommendation level | next allowable action |
| --- | --- | --- |
| Wider quantile portfolio | conditional | Paper-only hypothesis definition; no implementation. |
| Lower-frequency / longer-holding research | conditional | Paper-only pre-registration draft; no data run. |
| Risk-control / filter research | not recommended | Wait for an independently justified base portfolio or external risk objective. |
| Stability / risk-control objective | conditional | Paper-only objective definition; no implementation. |
| Portfolio construction research | not recommended | Blocked until a clean input signal or separate approved target exists. |
| Pause A-share daily clean alpha research | recommended | Preserve repository as audit and engineering asset. |

## Final Recommendation

Final recommendation: **B. Do not continue strategy research; pause A-share daily clean alpha research under the current D0 OHLCV + state field regime.**

The only recommended next action is to preserve the repository as an auditable engineering and research-governance asset. Conditional paper-only pre-registration may be drafted later for wider quantile, longer horizon, or risk-objective reframings, but none should enter code implementation, training, backtest, portfolio, metrics/readout, or frozen test access from the current evidence.

Current prohibitions remain active:

- No training.
- No backtest.
- No portfolio or portfolio dry-run.
- No holdings generation.
- No formal metrics/readout.
- No frozen test.
- No v4.
- No concrete trading rules.
- No treating trainval diagnosis as OOS.
- No treating p98 or `multi_equal_weight_v1` as clean gold standards.
- No claim of strategy effectiveness.
