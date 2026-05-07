# Framework Redesign Shortlist

**Status:** Design only, not registered. No new rounds until a direction is chosen.

**Preceded by:** `framework_method_note.md` (frozen 2026-05-01) — established that execution feasibility gap (entry/exit limit-up under D1-D5 + TopK) is the primary bottleneck, not signal quality or cost model.

---

## The Problem (Recap)

> Perfect foresight (future 5d return) under tradeable-constrained execution still produces total loss (-0.999). Even with perfect information about which stocks will perform best, the D1-D5 + TopK framework cannot reliably enter winning positions (limit-up at buy) or exit them on schedule (limit-up at sell → delayed exit → mean reversion).

---

## Three Redesign Directions

### Direction A: Extend Holding Period

| Field | Value |
|---|---|
| Change | D5 → D10 or D20 (lengthen holding period from 5 to 10 or 20 trading days) |
| Mechanism | Longer hold → less frequent exit → lower delayed-exit-to-total-exits ratio → delayed exits' impact on alpha is diluted |
| Expected benefit | Reduced turnover, more time for mean reversion to work IN the strategy's favor (vs against it) |
| Cost | Changes constitutional-level execution contract (总纲 3.1). Slower signal-to-portfolio response. |
| Framework impact | High — touches holding period, cohort count, turnover model, entry/exit assumptions |
| Why it might work | The delayed exit problem is proportional to how frequently exits occur. D10 halves exit frequency vs D5. More importantly, a longer window gives the signal's alpha more time to overcome the initial execution friction. |

### Direction B: Widen Head Extraction (TopK / Broader Head)

| Field | Value |
|---|---|
| Change | TopK 10 → TopK 20-30, or replace hard TopK with rank-weighted extraction |
| Mechanism | More positions → less concentration in the "unstoppable" winners → fewer buy failures (more candidates to choose from on D1) → more diversified exit profile |
| Expected benefit | Higher fill rate, lower impact of any single stock's limit-up status |
| Cost | Dilutes signal per-name; may reduce gross alpha per unit capital |
| Framework impact | Medium — changes portfolio construction rule (总纲 9.2) but not execution semantics or holding period |
| Why it might work | The oracle's failure was partly because only ~10 tradeable names were available per day while it needed 10. With TopK=20, the buffer is larger even when many top names are limit-up. But the alpha per name drops. |
| Key risk | 10-cohort already showed topk_8/12 near zero (0.005) at TopK=10. Widening to 20 would make perturbation even worse. |

### Direction C: Adjust Evaluation — Accept Execution Infeasibility

| Field | Value |
|---|---|
| Change | Modify success rules or cost model to acknowledge that under A-share limit-up/down rules, perfect fill is not achievable for short-holding strategies |
| Mechanism | Adjust cost_stress model to use liquidity-dependent slippage, or add an "execution feasibility gearing factor" to gates |
| Expected benefit | More realistic gate thresholds for D1-D5 strategies in A-shares |
| Cost | Reduces comparability with prior framework rounds |
| Framework impact | Low — doesn't change strategy, only how success is measured |
| Key risk | May mask real problems under the guise of "adjusted expectations" |

---

## Recommended: Direction A — Extend Holding Period

**Argument:**

1. **Direction C (adjust evaluation)** is premature — we should first try to fix the problem before deciding it's unfixable and adjusting the target.

2. **Direction B (widen TopK)** was already partially explored through cohort-count changes, and 10-cohort showed topk_perturbation already near zero (0.005). Further widening would likely push it negative. The oracle's failure was not primarily about having too few candidates, but about the best candidates being systematically blocked by limit-up — a problem that widening doesn't address at the signal level.

3. **Direction A (longer holding period)** addresses the root cause directly: the delayed-exit problem is proportional to exit frequency. A D10 or D20 holding period:
   - Halves or quarters the exit frequency → halves or quarters the delayed-exit drag
   - Gives positions more time to realize their alpha before being forced out
   - Reduces turnover proportionally → improves cost_stress
   - Is a single-parameter change (holding period), keeping the rest of the framework intact

4. **The oracle result supports this:** the oracle's perfect stock selection was destroyed by forced exits at D5. If the holding period were D10, the same selections would have twice as long to realize their alpha, and forced exits would affect half as many positions per day.

### What D10 would change

| Parameter | D5 (current) | D10 | Effect |
|---|---|---|---|
| Holding period | 5 days | 10 days | +100% |
| Exit frequency | 1/5 per day | 1/10 per day | -50% |
| Active cohorts | 5 | 10 | +100% |
| Expected turnover (10-cohort) | ~0.20 | ~0.10 | -50% |
| Delayed exit impact | High | Reduced | Proportional to exit freq |

### Next step (if approved)

Design a D10 holding period round with the following specifications:
- changed_dimension: holding_period (framework parameter)
- single change: D5 → D10
- keep: TopK=10, 10-cohort, full refresh, same signal (intraday trend_bias)
- formal baseline: current D5 + 10-cohort full refresh
- success rules: same 9 gates (feasibility check first)
- expected outcome: turnover ~0.10, delayed exit ratio halved, cost_stress improved
