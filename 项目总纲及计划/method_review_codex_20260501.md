# Codex Method Review: 5-Cohort Research Bottleneck

Status: analysis only. No registration, no code change, no new experiment.

## Executive Conclusion

The repeated failures under the 5-cohort contract are no longer best explained as "we have not found the right signal yet." The stronger diagnosis is that the current research stack turns very different signals into a similar portfolio behavior: high invested weight, daily TopK churn, near-identical turnover, and a fixed-cost stress gate that consumes weak-to-moderate alpha.

The central bottleneck is the portfolio formation method, not the data source. In particular, daily percentile-rank plus hard TopK selection appears to dominate the realized behavior of the strategy more than the economic frequency of the underlying signal.

## Evidence Snapshot

| Family / run | annual_relative_return | relative_ir | avg_turnover_daily | avg_invested_weight | cost_stress |
|---|---:|---:|---:|---:|---:|
| v18 5-cohort baseline | -0.571 | -2.867 | 0.394 | 0.803 | -0.139 |
| intraday best, c3 | -0.157 | -0.800 | 0.397 | 0.829 | -0.089 |
| volume-gated trend bias | -0.171 | -0.901 | 0.397 | 0.814 | -0.113 |
| cross-horizon best, c3 | -0.397 | -2.100 | 0.385 | 0.777 | -0.430 |
| fundamental best return, c2 ROA | -0.293 | -1.327 | 0.394 | 0.799 | -0.179 |
| fundamental best gate count, c1 ROE | -0.325 | -1.692 | 0.394 | 0.811 | -0.159 |

The striking fact is not that the signals differ. They do. The striking fact is that turnover converges to roughly 0.39/day for v18, intraday, volume-gated intraday, and fundamental signals. That means the realized trading behavior is being set largely by the daily TopK extraction system.

## Hypothesis Review

### H1: Daily percentile-rank + hard TopK is creating structural turnover

Assessment: strong evidence.

The fundamental family was expected to reduce turnover because ROE/ROA update slowly. It did not. ROE, ROA, intraday, and v18 all landed near the same turnover band. This is the cleanest clue in the whole review.

Likely mechanism: each signal date recomputes a full cross-sectional rank, then takes a narrow TopK=10 slice. Even if a raw fundamental value is stale or stable, its percentile rank can move as the eligible universe, missingness, PIT updates, and neighboring names change. A narrow head selection converts small rank changes into full entry/exit events.

Implication: more signal discovery will keep inheriting the same turnover profile unless the extraction or refresh rule changes.

### H2: 5-cohort fixed capital allocation amplifies head-selection noise

Assessment: partly true, but not the first root cause.

The 5-cohort change solved one real problem: invested weight rose from roughly 0.16 to roughly 0.80. It also fixed topk perturbation for the intraday family. So 5-cohort was not simply bad.

But once the system is 80% invested, every TopK mistake matters more. A narrow Top10 head with roughly 2% name weights has little room for noisy rank edges. The v18 baseline becoming much worse under 5-cohort is the warning label here: higher invested weight exposes whether the head signal is genuinely strong.

Implication: 5-cohort should not be abandoned immediately, but it needs a portfolio formation rule that dampens rank churn.

### H3: Cost stress is structurally hostile to the current turnover regime

Assessment: strong but should be tested with a break-even analysis, not only a perfect-foresight toy.

The stress model subtracts fixed 20bp open and 20bp close slippage based on buy/sell notional. Because the cost is fixed, volume gating cannot improve the stress cost unless it also reduces turnover or changes traded notional. This exactly matches the volume-gated result: the gate removed 52.72% of stock-days, but cost_stress worsened.

At roughly 0.39 daily turnover, the strategy needs a large gross edge just to survive the stress layer. The current signals may have information, but not enough information per unit turnover.

Implication: before more signal-family rounds, estimate the break-even required gross annual relative return implied by observed turnover and the stress formula. If the needed edge is far above all observed candidates, further standalone signal exploration is low-probability.

### H4: Success rules may be too confirmatory for exploratory standalone baselines

Assessment: partly true, but not an excuse to relax them casually.

The 9-gate rule usefully prevented weak positives from being promoted. That is good governance. But the current rule mixes two purposes:

- Discovery question: does the signal contain non-random information relative to a matched baseline?
- Deployment question: can the whole strategy pass absolute return, IR, robustness, and stress costs?

Several candidates passed the discovery layer but failed the deployment layer. That is not a contradiction. It says the signals are informative but not deployable under the current portfolio contract.

Implication: future exploratory rounds should report two verdicts: signal information verdict and deployable strategy verdict. Promotion should still require deployment gates, but research direction triage should not erase signal information just because deployment failed.

## My Root Cause Ranking

1. Daily hard TopK extraction is the highest-priority root cause. It makes realized turnover nearly invariant across signal families.
2. Fixed-cost stress then punishes that turnover regime. The cost model is doing what it was designed to do, but it reveals that current portfolio construction is too expensive.
3. 5-cohort capital allocation exposes weak head selection. It is not the main flaw by itself.
4. Success rules are strict, but they are mostly revealing the above mechanics rather than causing false failures.

## Recommended Next Hypothesis

Priority hypothesis:

Daily hard TopK extraction, not signal family choice, is the binding bottleneck under the 5-cohort contract.

Minimal test design:

Use an already-run signal with the best evidence, preferably intraday c3 or fundamental c1, and change only the portfolio extraction / refresh mechanism. Do not introduce a new signal. The test should ask whether turnover and cost_stress improve when the same score is mapped into a more stable portfolio.

Candidate mechanisms to design, not run yet:

| Mechanism | Changed dimension | Why it tests the root cause |
|---|---|---|
| Incumbent retention band | portfolio_refresh_rule | Tests whether reducing rank churn improves cost_stress without changing signal information |
| Broader TopK with rank decay | portfolio_extraction | Tests whether less brittle head selection improves TopK perturbation and drawdown |
| Score-change threshold before replacement | portfolio_refresh_rule | Tests whether small percentile-rank noise is causing unnecessary turnover |

The first one I would test is incumbent retention band, because it directly targets the observed invariant turnover while preserving the signal, universe, cost model, and 5-cohort contract.

## What Not To Do Next

Do not open another standalone signal family as the next step. The project has now tested price technical, intraday, cross-horizon, and fundamental families, and the realized portfolio mechanics keep converging to the same failure shape.

Do not relax cost_stress before measuring the break-even cost budget. The cost gate may be strict, but it is pointing at a real tradeability problem.

Do not treat volume/liquidity conditioning as a cost fix unless the cost model itself is liquidity-sensitive or the conditioning demonstrably reduces turnover.

## Final Recommendation

Pause new signal-family discovery. Register a method round only after a design note freezes a single portfolio-construction hypothesis:

Can an incumbent-retention refresh rule, applied to one already-tested 5-cohort signal, reduce daily turnover enough to move cost_stress materially closer to zero without destroying return, IR, and invested weight?

If yes, the project bottleneck is portfolio formation. If no, the current 5-cohort standalone framework likely requires either a much stronger signal source or a more fundamental rewrite of the deployability rules.
