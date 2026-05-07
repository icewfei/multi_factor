# Phase Summary: Exploratory Intraday Microstructure Independent Baseline

- `research_round_id`: `rr_exploratory_intraday_microstructure_independent_baseline_20260501`
- `status`: `completed_intraday_family_not_viable`
- `completed_at`: `2026-05-01T11:20:00+08:00`

---

## Verdict

**All 3 candidates failed prereg success rules. Round archived as `completed_intraday_family_not_viable`.**

No candidate passes the core pass condition. None qualifies as `reasonable_candidate`.

---

## Gate-by-Gate Results

| # | Gate | c1 | c2 | c3 |
|---|------|:--:|:--:|:--:|
| 1 | `annual_relative_return >= 0.01` | -0.182 ❌ | -0.196 ❌ | -0.177 ❌ |
| 2 | `relative_ir >= 0.30` | -1.334 ❌ | -1.424 ❌ | -1.246 ❌ |
| 3 | `annual_relative_return_delta >= -0.005` | +0.093 ✅ | +0.079 ✅ | +0.098 ✅ |
| 4 | `avg_invested_weight >= 0.15` | 0.185 ✅ | 0.185 ✅ | 0.156 ✅ |
| 5 | `max_drawdown_delta >= -0.05` | +0.236 ✅ | +0.240 ✅ | +0.277 ✅ |
| 6 | `topk_8 >= 0 AND topk_12 >= 0` | -0.059/-0.056 ❌ | -0.067/-0.065 ❌ | -0.071/-0.068 ❌ |
| 7 | `cost_stress_return >= 0.00` | -0.097 ❌ | -0.107 ❌ | -0.103 ❌ |
| 8 | `avg_turnover_daily_delta <= 0.04` | +0.015 ✅ | +0.015 ✅ | -0.002 ✅ |
| **core_pass** | **all 8 must pass** | **FAIL** | **FAIL** | **FAIL** |

Core pass condition: 8 gates (gate 6 counts as one gate with two sub-conditions).

### Gate Pattern

**4 passed by all 3 candidates:** delta-vs-v18 return, delta-vs-v18 drawdown, delta-vs-v18 turnover, invested_weight floor.

**4 failed by all 3 candidates:** absolute annual_relative_return, relative_ir, topk_perturbation, cost_stress.

---

## Failure Analysis

The failure pattern is identical across all three candidates—different signal counts do not change the outcome, only the magnitude.

**c3 is the best of the three**, improving on c1/c2 in return (-0.177 vs -0.182/-0.196), drawdown (-0.122 vs -0.163/-0.159), and turnover (0.073 vs 0.090/0.090). But it still fails the same gates.

**Root cause:** Systemic low-invested-weight under the current D1-D5 + TopK + cash-retention contract. All candidates held 81-84% cash during the 2019-2021 validation window (benchmark total return +82%). When a strategy carries 80%+ cash during a strong bull market, absolute relative return is structurally negative regardless of signal quality.

**Important caveat:** The intraday signals consistently improved upon v18 reference across all delta-based gates (return delta +0.08~+0.10, drawdown delta +0.24~+0.28, turnover delta within 0.015 or better). This is not a signal-quality failure—it is a contract-interaction failure. V18 itself has the same problem (avg_invested_weight 0.155, validation annual_relative_return -0.275).

---

## Recommendations for Future Direction

**Do not re-litigate this exact question.** The intraday independent baseline as a standalone family under the current portfolio contract has been formally tested and does not work.

**Candidate directions for future consideration (not yet registered):**

1. **Higher invested-weight contract design** — Test intraday signals under a portfolio contract that allocates more capital (e.g., single cohort, weight-mapping rules, or higher TopK). The signal-level evidence (positive deltas vs v18) may be exploitable if the portfolio layer is the binding constraint.

2. **Intraday signals as additive layer** — Re-test intraday signals not as a standalone family but as additions to a higher-invested-weight baseline (e.g., add intraday_trend_bias to a contract with avg_invested_weight >= 0.50).

3. **Portfolio extraction / refresh interaction** — Investigate whether different head-extraction geometry or refresh hysteresis reduces cash drag enough for intraday signals to pass perturbation and cost-stress gates.

These directions are noted for reference only. No new round has been opened.

---

## Interpretation Note

> 本轮失败不应被解读为 intraday microstructure signals 无信息，而应被解读为：在当前 D1-D5 + TopK + 现金保留 + 不补位合同下，intraday independent baseline 未满足 prereg success rules。
