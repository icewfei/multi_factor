# Multi-Factor Project — Final Summary

**Status:** Corrected oracle exposes massive gap between oracle upper bound and current real signals. Signal/learnability layer strongly elevated. D10 unvalidated.

**Frozen at:** 2026-05-02

---

## 1. Scope Completed

### Signal Families (5 rounds)

| Round | Direction | Best Result |
|---|---|---|
| `rr_exploratory_intraday_microstructure_independent_baseline_20260501` | Intraday microstructure | 6/9 |
| `rr_exploratory_intraday_cohort5_contract_design_20260501` | Intraday + 5-cohort | 6/9 |
| `rr_exploratory_trend_bias_volume_confirmed_20260501` | Volume-conditioned | 6/9 |
| `rr_exploratory_cross_horizon_reversal_momentum_20260501` | Cross-horizon (reversal+momentum) | 3/9 |
| `rr_exploratory_fundamental_quality_profitability_20260501` | Quality/profitability (ROE/ROA) | 6/9 |

**All 5 signal families converged on the same ceiling:** 3 failing gates (annual_relative_return, relative_ir, cost_stress). No signal family could break through.

### Contract Parameters (2 rounds)

| Round | Change | Outcome |
|---|---|---|
| 26-cohort → 5-cohort | holding_cohort_count: auto(26) → 5 | Solved invested_weight problem (0.81). Turnover ~0.40. |
| 5-cohort → 10-cohort | holding_cohort_count: 5 → 10 | Solved turnover feasibility (0.20). Inv_wt dropped to 0.41. |

**Best found:** 10-cohort + full refresh (6/9). Contract parameters alone couldn't break through.

### Refresh Rules (3 rounds)

| Round | Rule | Outcome |
|---|---|---|
| `retain15` | retain_if_rank_leq = 15 | Return/drawdown improved. Turnover unchanged. |
| `retain50` | retain_if_rank_leq = 50 | Further return/drawdown improvement. Cost_stress worsened. |
| `cohort_entry_locked` | (prereg) | Found infeasible — current turnover metric floor > 0.20. |
| `retain50 + 10-cohort` | Combined | Same 6/9. Cost_stress still negative. |

**Best method combination found:** 10-cohort + retain50 gives drawdown of -0.255 (best) but still 6/9.

### Framework Redesign (2 probes + 1 incomplete redesign attempt)

| Probe | Result | Status |
|---|---|---|
| Oracle v1 (corrected 2026-05-02) | annual_relative_return = +2888. Execution NOT an impossible barrier. Massive gap between oracle and real signals. | ✅ Completed (post-bugfix) |
| Probe A (corrected 2026-05-02) | annual_relative_return = +4634. Tradeable-constrained better than unconstrained. | ✅ Completed (post-bugfix) |
| D10 holding period | **planned_exit_date patched. actual_exit_date / actual_sell_price / execution_delayed_realized_return unchanged (still from D5).** Strategy metrics identical to D5. | ⚠️ Implementation-incomplete — execution path not recomputed |

---

## 2. Final Conclusion

> **经过 12+ 轮研究、5 个信号家族、3 个合同变体、3 个刷新规则的测试，所有配置最高成绩 6/9，始终卡在相同的 3 个门槛。** 2026-05-02 发现并修复 oracle probe 的 score-direction bug（PERCENT_RANK + ORDER BY DESC 与 TopK DESC 方向冲突）。修正后的 V1 oracle 在同一执行约束下产生年化相对收益 +2,888，Probe A 产生 +4,634。这证明：(a) corrected oracle proves the framework is not execution-blocked under this oracle diagnostic — 完美信息可以在同一执行语义和成本模型下产生巨量正收益；(b) corrected oracle reveals an extremely large gap between oracle upper bound and current real signals (~15,000× in magnitude), which strongly elevates the priority of the **signal/learnability layer** — 但不排除 other layers (evaluation model, extraction mechanics) 也可能 contribute。信号/可学习层被修正后的 oracle 证据新提为优先级的核心问题。D10 持有期改动未验证。retain15/50 改善 return/drawdown 但恶化 cost_stress——因果机制未经验证。Probe A > V1 成立但机制解释保持开放（"限制在可买卖宇宙本身就不是净负面" vs."可买卖宇宙恰好与高预期收益重叠"）。

### 关键证据链

1. **Corrected oracle proves framework is not execution-blocked (under this oracle diagnostic)** — V1 +2,888, Probe A +4,634 under same execution and cost model
2. **Massive oracle-to-real gap strongly elevates signal/learnability layer** — best real signal (-0.181) vs oracle upper bound reveals a very large information gap. Does not yet rule out contributions from other layers
3. **D10: `planned_exit_date` 正确修改但策略指标 unchanged** — `planned_exit_date` 不是当前 pipeline 的真实控制变量
4. **Cost_stress unchanged across 0.40 → 0.20 turnover** — cost model structural calibration question remains, but is now secondary to signal quality

### 未验证的假设

- **D10 延长持有期能否改善执行层摩擦或持有期表现** — 未验证。需要重算 execution path 后才可判断。
- **更根本的 execution-semantics redesign**（如修改涨跌停处理方式）— 未探索。

---

## 3. Current Project State

```
status: framework_diagnosis_strongly_suggestive_not_conclusive
rounds_completed: 12+
signal_families_tested: 5 (intraday, cross-horizon, fundamental) — all 6/9
contract_variants_tested: 3 (26-cohort, 5-cohort, 10-cohort)
refresh_rules_tested: 3 (full, retain15, retain50)
framework_redesigns_tested: oracle probe (complete), D10 (incomplete)
current_best_result: 6/9 (multiple configurations)
strongest_hypothesis: signal/learnability layer strongly elevated; other layers not ruled out
unvalidated_hypothesis: D10 holding period (requires execution path recompute)
recommendation: no further local parameter search
```

---

## 4. Caveats & Limitations

**Evidence boundaries noted during self-audit (2026-05-01):**

1. **Old oracle-loss narrative is invalidated.** The original oracle `-1.0` result was caused by a score-direction bug and should not be used as evidence for entry/exit constraint stories. Any future mechanism decomposition must start from the corrected oracle runs, not the invalidated ones.

2. **"Leading layer" is not a uniqueness claim.** Corrected oracle strongly elevates signal/learnability, but it does not mathematically rule out contributions from evaluation calibration, extraction mechanics, or other layers.

3. **Retain50 + cost_stress: correlation ≠ causation.** Retain50 is observed to worsen cost_stress in both 5-cohort and 10-cohort. The causal mechanism (higher trading costs from retained lower-ranked positions) has not been verified via per-position cost analysis.

4. **6/9 consensus across signal families does not guarantee identical failure modes.** Intraday c1, v18, and fundamental c1 may fail the same 3 gates for different underlying reasons. No per-configuration failure decomposition has been performed.

5. **Oracle probe tests only one type of future information (5d return).** It does not test whether other oracle formulations (e.g., future turnover, future rank stability) could pass.

---

## 5. Next Phase Recommendation

> **若未来重启本项目，应从 signal/learnability phase 重新立项，而不是继续沿用旧的 execution-blocked 叙事。** 修正后的 oracle 说明当前框架在该 diagnostic 下并未被 execution impossibility 封死；当前最优先的问题是，为什么真实特征与 oracle upper bound 之间仍存在巨大的信息差距。在此之前，继续做局部 contract / refresh 搜索 unlikely 突破 6/9 的 ceiling。
>
> 具体可选方向包括：signal/learnability diagnostics 或新的 feature engineering phase；D10 仍可作为 secondary validation task，但前提是先重算 execution path。

---

## 6. Appendix: Still-Open Questions

**For future reopening reference. Priority-ordered.**

| Priority | Question | What's Needed |
|---|---|---|
| P0 | Rerun oracle probes (DONE 2026-05-02) | ✅ V1 = +2,888, Probe A = +4,634 |
| P1 | What drives the ~15,000× gap between oracle and best real signal? | Per-signal family information content audit |
| P2 | D10 holding period | Execution path recomputation (3-5h) |
| P2 | D10: does extended holding period improve execution feasibility? | Recompute execution_path in project layer for D10, rerun full-chain |
| P3 | Retain50: does cost_stress worsen because of retained-position costs or another mechanism? | Per-position cost decomposition (retained vs. replaced) |
| P4 | Do different signal families fail for genuinely different root causes despite the same gate scores? | Per-configuration failure decomposition (return decomposition, exit delay decomposition, cost decomposition) |
| P5 | Is the oracle conclusion sensitive to the choice of oracle signal (5d return vs. other formulations)? | Test alternative oracle signals (e.g., future rank stability, future turnover) |

---

## 7. Final Note

本项目完成了 12+ 轮研究轮次、5 个信号家族、3 个合同变体、3 个刷新规则、2 个框架层设计（1 个完成探针、1 个未完成重算）的系统性探索。修正后的 oracle 将项目主叙事从 execution-blocked 回滚为：当前框架在该 oracle diagnostic 下并未被 execution impossibility 封死，而 signal/learnability layer 被显著抬升为领先解释。D10 的完整验证仍需要 execution path 重算，超出本轮实现范围。项目当前状态为 **framework diagnosis strongly suggestive, not conclusively closed**。所有产物、registry、和文档保留在 `/Users/wy/MiscProject/multi_factor/` 目录下。
