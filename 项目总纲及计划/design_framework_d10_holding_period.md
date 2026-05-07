# Framework Redesign: D10 Holding Period

**Status:** Design only, not registered. Framework-level redesign, not a parameter round.

**Preceded by:** `framework_method_note.md` (frozen 2026-05-01) — established that execution feasibility gap is the primary bottleneck. `framework_redesign_shortlist.md` — recommended Direction A (extend holding period) over widening TopK or adjusting evaluation.

---

## 1. Problem Definition

> 在保持 TopK(10)、执行语义（D0 信号 → D1 开盘买入）、成本模型、benchmark、10-cohort full refresh 不变的前提下，仅将 holding period 从 D5 延长到 D10，是否能显著缓解当前 framework 的 primary bottleneck——execution-feasibility gap（entry limit-up + exit limit-up → delayed exit → mean reversion）？

### 为什么这是 framework redesign，不是参数轮

| 维度 | 普通参数轮 | 这轮 |
|---|---|---|
| 改动层级 | 总纲附录 A（参数级） | **总纲 3.1（执行语义——宪法级）** |
| 影响范围 | score family / contract / refresh | **持有期、cohort 数、换手率、退出分布** |
| 与前序方法轮的关系 | 同一框架下的局部搜索 | **框架层重新设计** |
| 杠杆 | 有限（~10-20% 改善） | **高（~50%+ 潜在改善）** |

总纲 3.1 定义 "D0 收盘后出信号 → D1 开盘买入 → 持有到 D5 收盘 → D5 收盘优先卖出"。D5 → D10 是修改这个宪法级定义，因此是 framework redesign。

---

## 2. Changed Dimension

```
changed_dimension = holding_period
变化：holding period 从 D5 → D10
具体：D0 出信号 → D1 开盘买入 → 持有到 D10 收盘 → D10 收盘优先卖出
```

### 不改变的其他要素

| 要素 | 状态 |
|---|---|
| TopK | 10（不变） |
| 执行语义 | D0 信号 → D1 开盘买入（不变）|
| 卖出机制 | 收盘优先卖出，跌停/停牌延迟（不变） |
| 成本模型 | 标准 + stress（不变） |
| benchmark | 中证全指全收益（不变）|
| signal family | intraday trend_bias only（不变）|
| refresh rule | full refresh（不变）|
| holding_cohort_count | 10（不变）|
| cash retention | no replacement（不变）|

### 需要同步更新的

- `build_portfolio_artifacts.py` 中的 `planned_exit_date` 计算逻辑需要从 D5 改为 D10
- `execution_state_daily.parquet` 中的 `planned_exit_date` 字段（由 `build_run_state_skeleton.py` 生成）
- 这些改动影响所有 downstream 计算（holdings period、cohort overlap、delayed exit tracking）

---

## 3. Anchor Signal

**Intraday trend_bias (c1)** — 与前面所有方法轮一致。

理由：
- 所有方法轮中诊断最干净的 anchor
- 与 D5 history 直接可比
- cost_stress 最接近 0（-0.076），最适合观察 D10 的改善效果

---

## 4. Baseline

```
formal baseline: exploratory_cohort10_c1_trendbias_only
  - D5 holding period
  - 10-cohort full refresh
  - intraday trend_bias (same signal)
  - TopK=10, standard execution, standard cost model
```

---

## 5. Expected Impact Analysis

### Mechanism

| 参数 | D5（当前） | D10 | 变化 |
|---|---|---|---|
| Holding period | 5 天 | 10 天 | +100% |
| 单 cohort 生命周期 | T+0 → T+5 | T+0 → T+10 | +100% |
| 每日到期 cohort 数 | 1/5 = 20% | 1/10 = 10% | -50% |
| 活跃 cohort 数（稳态） | 5 | 10 | +100% |
| 预期 avg_invested_weight | ~0.41 | **~0.41（相同）** | 0% |
| 预期 turnover (10-cohort) | ~0.20 | **~0.10** | -50% |
| 预期 delayed_exit 比例 | ~基准 | **~减半** | -50% |

### 预期效果

**正面：**
- Turnover 从 ~0.20 降至 ~0.10（结构性到期减少）
- 延迟退出占总持仓比例下降（退出频率减半）
- cost_stress 从 ~-0.08 向 0 方向改善
- 信号有更多时间实现 alpha（5 天 → 10 天）

**负面/风险：**
- 信号半衰期：intraday trend_bias 作为 short-horizon 信号，其预测力在 10 天持有期内可能衰减。前 5 天可能有效，后 5 天可能回归均值。
- Alpha 被拉平：如果信号的 alpha 主要集中在持有期的前 3-5 天，延长持有期不会增加 gross alpha，只会增加持有期间的无谓波动。gross alpha 可能持平，但 turnover 下降带来的 cost 改善直接提升 net alpha。

### 关键 tradeoff

```
D5:  更高的 exit 频率 × 更高的 delayed-exit 损耗 × 更高的 turnover × 更高的 cost
       vs.
     信号在有效期内被强制退出 → 错过后半段 alpha

D10: 更低的 exit 频率 × 更低的 delayed-exit 损耗 × 更低的 cost
       vs.
     信号可能在持有期后段失效 → 尾段 alpha 被浪费
```

如果 intraday trend_bias 的 alpha 半衰期 > 5 天，D10 净赢。
如果半衰期 < 5 天，D10 可能 neutral 或净输。

---

## 6. Success Focus

### Layer A: Framework Feasibility

| 指标 | 目标 | 衡量标准 |
|---|---|---|
| avg_turnover_daily | 显著下降（从 ~0.20 降至 ~0.12 以下）| ≤ 0.15 |
| avg_invested_weight | 不崩溃 | ≥ 0.30 |
| delayed_exit 比例 | 较 D5 下降 | 对比 D5 的延迟退出占比 |
| cost_stress | 向 0 方向改善 | 比 D5 的 -0.082 更高 |

### Layer B: Strategy Viability

| 指标 | 目标 |
|---|---|
| annual_relative_return | ≥ D5 baseline 的 90%（接受适度下降）|
| relative_ir | 不显著恶化 |
| topk_8 / topk_12 | ≥ 0（保持正值）|
| cost_stress | 比 D5 baseline 更接近 0 |

### 门数暂不定义

这轮不预先冻结 9 道 gates。原因是 framework redesign round 的预期产出是"判断 D10 是否缓解 execution-feasibility gap"，而不是"是否通过所有 strategy gates"。Design 阶段确认 Layer A 的结果后，再决定是否继续到 Layer B。

---

## 7. Implementation Impact

| 文件 | 改动 | 难度 |
|---|---|---|
| `build_run_state_skeleton.py` | `planned_exit_date` 从 `signal_date + 5` 改为 `signal_date + 10` | 低（1 行） |
| `build_portfolio_artifacts.py` | 持仓计划退出日期计算 | 低（1 行） |
| `build_fixed_test_minimal.py` | 持有期相关计算（如有硬编码 D5）| 低 |
| 下游 validation | 无 | — |

D10 是宪法级改动但实现面极小——主要影响 planned_exit_date 的计算逻辑。大部分 pipeline 使用这个字段自动推导退出行为。

---

## 8. Recommendation

**D10 值得进入注册阶段。** 理由：

1. **Probe A 已经钉死：当前 execution-feasibility gap 是 primary bottleneck**，而且 D5 本身是 gap 的重要来源（退出频率 × 延迟退出损耗）。
2. **D10 是 single-parameter framework change**，不改变执行语义的其他部分，不影响成本模型，不影响 signal family。改动面虽属宪法级但实现成本极低。
3. **turnover 从 0.20 降到 0.10 是确定的**，cost_stress 改善是高概率的。即使 signal 半衰期风险存在，D10 的 cost 改善大概率超过 alpha 衰减。
4. **如果 D10 也失败**（cost_stress 仍 < 0），则可以进入 Direction C（调整评估标准），因为此时已有充足证据表明 D1-D10 + TopK 在 A 股涨跌停制度下确实存在不可消除的结构性成本。

### 注册条件

同意注册后：
- 1 个候选（D10 + 10-cohort + intraday trend_bias + full refresh）
- formal baseline: exploratory_cohort10_c1_trendbias_only (D5)
- Layer A feasibility 为首要判断
- Layer B strategy 为次级判断
- 不改 cost model、benchmark、TopK、signal family
