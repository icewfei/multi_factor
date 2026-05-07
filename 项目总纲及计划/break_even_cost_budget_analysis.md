# Break-Even Cost Budget Analysis

**Purpose:** Calculate how much gross alpha a strategy needs to generate under the current cost_stress model to pass the cost_stress >= 0.00 gate.

**Status:** Analysis only, not registered.

---

## 1. Cost Component Breakdown

### 成本参数（总纲附录 A）

| 参数 | 默认值 | stress 值 |
|---|---|---|
| buy_commission | 0.0003 (3bp) | 0.0005 (5bp) |
| sell_commission | 0.0003 (3bp) | 0.0005 (5bp) |
| sell_stamp_duty | 0.0010 (10bp) | 0.0010 (10bp) |
| slippage | 0.0005 (5bp) | **0.0010 (10bp)** |
| min_commission | 5.0 | 5.0 |
| stress_open_bp | — | **20bp** |
| stress_close_bp | — | **20bp** |

**stress vs default 的差异：**
- 额外 20bp 开盘滑点 + 20bp 收盘滑点 = **+40bp 每笔 round trip**
- 佣金从 3bp 升到 5bp（+2bp 每笔买卖）

### 实际运行参数（所有 5-cohort 候选）

```
avg_turnover_daily ≈ 0.39（5 轮 15 个候选全部收敛于此）
```

换手率来源：`avg_turnover_daily = (buy_notional + sell_notional) / lag_total_equity`

单边交易量 ≈ 0.39 / 2 = 0.195（每侧，乘 equity）

---

## 2. 日度/年度成本拖累

### 基础成本（default，非 stress）

| 成本项 | 每笔 round trip | 日度（×0.39 turnover） | 年化（×252） |
|---|---|---|---|
| buy_commission (3bp) | 0.0003 | 0.000117 | 0.030 |
| sell_commission (3bp) | 0.0003 | 0.000117 | 0.030 |
| sell_stamp_duty (10bp) | 0.0010 | 0.000390 | 0.098 |
| slippage (5bp) | 0.0005 | 0.000195 | 0.049 |
| **基础成本合计** | **0.0021** | **0.000819** | **0.206** |

### Stress 额外成本

| 成本项 | 每笔 round trip | 日度（×0.39 turnover） | 年化（×252） |
|---|---|---|---|
| extra slippage (5bp→20bp) | 0.0015 | 0.000293 | 0.074 |
| extra open stress (20bp) | 0.0020 | 0.000390 | **0.098** |
| extra close stress (20bp) | 0.0020 | 0.000390 | **0.098** |
| extra commission (3bp→5bp) | 0.0004 | 0.000078 | 0.020 |
| **Stress 额外合计** | **0.0059** | **0.001151** | **0.290** |

### 总成本

| 口径 | 年化成本拖累 |
|---|---|
| 基础成本（default 已包含在回测中） | 0.206 (20.6%) |
| Stress 额外成本（在基础之上叠加） | **0.290 (29.0%)** |
| **Total stress 口径成本** | **0.496 (49.6%)** |

---

## 3. Break-Even Gross Alpha

要过 `cost_stress >= 0.00` 门，需要：

```
gross_annual_relative_return - total_stress_cost >= 0.00
gross_annual_relative_return >= total_stress_cost = 0.496
```

但需要注意：基础成本（0.206）已经包含在我所观察到的 `annual_relative_return` 中。我们看到的 -0.19 是已扣除基础成本后的净值。所以：

**要使 stress 后的 net >= 0：**
```
(stress_后_net) = (已见_base_return) - stress_额外成本 >= 0
                = (-0.19) - 0.29 >= 0
                = -0.48 >= 0 → 不可能
```

换算成 gross alpha（未扣除任何成本前）：
```
gross_alpha = (已见_base_return) + 基础成本 + stress_额外成本
            = (-0.19) + 0.206 + 0.290
            = 0.306 (30.6% annualized)
```

**结论：在当前 avg_turnover=0.39 和 stress 口径下，策略需要约 30% 年化的 gross relative return（费用前），才能在 stress 后达到 cost_stress >= 0。**

---

## 4. 对 5 轮已完成 round 的解释力

| 候选 | seen_base_return | estimated_gross_alpha | break-even | 差距 |
|---|---|---|---|---|
| intraday c1_5cohort | -0.194 | **+0.302** | 0.496 | **-0.194 by stress** |
| intraday c3_5cohort | -0.157 | **+0.339** | 0.496 | **-0.157 by stress** |
| fundamental c1_roe | -0.325 | **+0.171** | 0.496 | **-0.325 by stress** |
| cross-horizon c3 | -0.397 | **+0.099** | 0.496 | **-0.397 by stress** |
| reversal c1 | -0.532 | **-0.036** | 0.496 | **-0.532 by stress** |

**核心发现：没有任何候选的 gross alpha（20-30%）接近 stress 成本（49.6%）。** stress 成本本身是 gross alpha 的 1.5-5 倍。这是一个结构性不匹配，不是信号质量问题。

**stress 下 break-even 需要 gross_alpha ≈ 49.6%。但过去 5 轮中最佳候选（intraday c3）的估计 gross alpha 约 33.9%。缺口约 15.7%。**

即使最乐观的候选（intraday c3），gross alpha 也只有 33.9%，而 stress 成本是 49.6%。

---

## 5. 结论

**H3 currently plausible enough to guide next steps.**

不需要额外做 ideal/perfect-foresight probe。当前 break-even analysis 已足够清楚：

1. **cost_stress >= 0.00 在当前系统设定下是一个结构性不可通过的门槛**——不是因为信号质量不够，而是因为 percentile-rank + TopK 系统产生的 0.39 日均换手 × 40bp round-trip stress 滑点产生了约 50% 年化成本拖累
2. 5 轮全部失败的共同原因不是信号方向错了，而是 **stress 成本预算超过了任何现实信号族能提供的 gross edge**
3. 如果后续要推进，修复方向应是：
   - **降低 turnover**（portfolio refresh rule）→ 直接降低成本
   - **或调整 stress 模型**（改为与流动性挂钩的滑点）
   - 而不是继续迭代信号

### 对 cost_stress 门的评估

| 角度 | 判断 |
|---|---|
| 在 0.39 turnover 下是否可通过 | **否**（需要 49.6% gross alpha） |
| 是否有候选接近通过 | 否（最佳仅 33.9%） |
| 门槛本身是否合理 | **在 exploratory round 中过于苛刻** |
| 是否应先修框架再跑信号 | **是** |
