# Framework-Level Method Note

**Status:** FINAL — frozen as of 2026-05-02. This document represents the project's current framework-level conclusion after the oracle score-direction bug was found and corrected.

**No new signal rounds, contract rounds, or refresh rounds will be opened until a future reopening decision is made.**

**Preceding evidence:** 12+ method rounds across signal families, contract parameters, and refresh rules all converged on the same 3 failing gates.

**Corrected oracle evidence (2026-05-02):** Prior oracle results (-1.0 total loss) were invalidated by a score-direction bug. Corrected V1 oracle produces annual_relative_return = +2,888; corrected Probe A (tradeable-constrained) produces +4,634. This shows the framework is not execution-blocked under this oracle diagnostic. The massive gap between oracle and the best real signal strongly elevates the signal/learnability layer as the leading hypothesis. Other layers are not ruled out.

---

## 1. Current State

After 12+ rounds of signal families, contract parameters, and refresh rules:

| Layer | Action | Outcome |
|---|---|---|
| Signal families | intraday, cross-horizon, fundamental | All capped at 6/9 |
| Contract (cohort count) | 26 → 5 → 10 | Solved invested_weight and turnover feasibility |
| Refresh rule | daily-recheck, retain15, retain50 | Improved return/drawdown but cost_stress remained negative |
| Oracle diagnostic | corrected V1 + Probe A | Framework not execution-blocked under oracle diagnostic |
| D10 redesign | data-layer patch only | `planned_exit_date` changed; execution path not recomputed |

**余下的 3 道门槛（annual_relative_return >= 0.01, relative_ir >= 0.30, cost_stress >= 0.00）在所有完成的真实信号配置下都不可达。** 需要 framework-level 分析，而非继续调局部参数。

---

## 2. Three Layers After Oracle Correction

### Layer 1: Signal / Learnability

**当前优先级最高。**

Corrected oracle shows that the same execution semantics and the same cost model can support extremely large positive returns when ranking information is perfect. Therefore, the largest remaining gap is no longer best explained by "execution impossibility."

What the corrected evidence supports:
- Real signals are far below the oracle upper bound
- Current score mapping is unlikely to be the dominant loss by itself
- Signal/learnability is now the leading hypothesis for why real strategies remain stuck at 6/9

What it does **not** prove:
- Signal quality is the unique bottleneck
- Execution, extraction mechanics, or evaluation calibration are irrelevant

### Layer 2: Portfolio Construction / Turnover

**Important, but no longer the leading story.**

Observed facts remain valid:
- cohort_count 调整（5→10）将 turnover 从 0.40 降至 0.20
- retain15/retain50 在多个配置下改善了 return/drawdown
- retain50 在多个配置下与更差的 cost_stress 同时出现

What remains open:
- retain50 恶化 cost_stress 的因果机制尚未分解
- `planned_exit_date` 不是当前 pipeline 的真实控制变量，但 D10 redesign 仍未被正确检验

### Layer 3: Evaluation / Cost-Model

**仍然需要保留，但优先级下降。**

Before the oracle bugfix, one possible story was that `cost_stress >= 0` might be structurally unreachable. Corrected oracle no longer supports that story. A perfect-information diagnostic can pass the same stress gate with a wide margin.

What remains open:
- 20bp open + 20bp close stress 的校准是否过严
- cost_stress 对不同持仓结构是否存在系统性偏差

So the evaluation layer remains a calibration question, but it is no longer the best explanation for the project-wide 6/9 ceiling.

---

## 3. Updated Hypothesis Priority

| Priority | Hypothesis | Status | Next Step if Reopened |
|---|---|---|---|
| P0 | Signal / learnability gap | Strongly elevated by corrected oracle | Information-content audit / feature engineering as a new research phase |
| P1 | Evaluation / cost-model calibration | Open | Revisit only after signal layer is better understood |
| P2 | Execution semantics / D10 redesign | Open but secondary | Requires execution-path recomputation before any real test |

Key downgrade from the pre-bug narrative:
- `execution-feasibility gap is the primary bottleneck` is **retracted**
- `framework is execution-blocked` is **retracted**
- execution-related questions remain open, but no longer lead the narrative

---

## 4. Framework-Level Final Conclusion

经过 12+ 轮信号家族、合同参数、刷新规则的方法轮，以及修正后的 oracle diagnostic，当前项目最稳健的框架级判断是：

**corrected oracle shows the current framework is not execution-blocked under this oracle diagnostic, and the very large gap between oracle upper bound and current real signals strongly elevates the signal/learnability layer as the leading explanation for current results.**

This conclusion should be read carefully:
- it **does** rule out the old "execution impossibility" story as the main oracle-backed conclusion
- it **does not** prove signal quality is the only remaining issue
- it leaves D10 redesign unvalidated because execution path was never recomputed under the new holding-period semantics

Therefore, if the project is ever reopened, it should reopen as a **new signal/learnability phase**, not as a continuation of the earlier execution-blocked narrative.
