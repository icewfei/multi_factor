# Method Review: Why All Signal Families Failed Under 5-Cohort

**Status:** Analysis only, not registered. No experiments, no code changes.

---

## 问题陈述

在 5-cohort 合同下，5 轮独立信号族测试全部失败（最佳 6/9）。失败高度一致地集中在 3 个同一门槛：**absolute return、relative_IR、cost_stress**。而所有候选都通过了 delta-vs-v18、invested_weight、drawdown 门槛。

这种"相对改善但绝对不足"的失败模式，暗示问题可能不在信号本身，而在**研究框架层**。

---

## 层面 1：Percentile-Rank + TopK 提取机制

### 当前机制

```
信号值 → 横截面 percent_rank → 等权平均 → 选 TopK=10 → D1 开盘买入
```

核心特征：
- 每个 signal_date 重新计算全宇宙排名
- 排名变化率（换手）不受信号自身频率影响，受**宇宙构成变化**和**横截面相对位置变化**影响

### 问题

即使在基本面信号（季度频率）下，换手率仍然高达 0.39/日，与动量信号完全相同。这意味着：

- 每日排名中，虽然标的 A 的 ROE 没变，但因为标 B 新进入 universe、标 C 的 ROE 被 winsorization 更新、标 D 的 ROE 因新财报数据刷新——所有标的的相对排名都在变动
- TopK=10 只取头部 10 只，每日顶部 10 名的构成变化率极高
- **结论：percentile-rank + TopK 系统自身是一个高换手系统，信号频率对此影响极为有限**

### 可检验的假设

**假设 H1：在当前 percentile-rank + TopK 系统下，任何信号族都不可能实现足够低的换手来通过 cost_stress 门槛。**

检验方法：用白噪声信号（随机均匀分布）跑一遍，如果换手率仍然 ≈ 0.35-0.40，则 H1 成立。

---

## 层面 2：5-Cohort Portfolio Extraction 是否放大噪声

### 当前机制

5-cohort 下，26 个重叠 cohort → 5 个 cohort。`cohort_capital_fraction = 1/5 = 20%`。每个 signal_date 产生 10 只 TopK 标的。

### 问题

从 26-cohort 到 5-cohort 的切换提高了 invested_weight（16% → 81%），但同时也放大了以下问题：

- 每个 cohort 的持仓权重大幅增加（每个标的从 0.385% → 2%）
- 当 TopK 头部选错时，惩罚也相应放大（drawdown 从 -0.40 恶化到 -0.94 for v18）
- 5-cohort 的 invested_weight 提高并不创造 alpha，只是放大了已有的 alpha 和 noise

### 可检验的假设

**假设 H2：5-cohort 合同下，portfolio extraction 在每个 signal_date 的 rank 排序中放大了顶部 10 名的 cutoff 噪声，导致 topk 扰动普遍为负或接近 0。**

检验方法：对比每个 signal_date 上 rank=10 和 rank=11 的 score 差异。如果差异极薄（< 0.01），则 H2 成立。

---

## 层面 3：Cost_Stress 模型与信号/流动性的结构性错配

### 当前模型

```
cost_stress_annual_relative_return:
  固定 20bp open slippage + 20bp close slippage + 标准佣金费率
```

### 问题

- cost_stress 使用固定滑点（20bp），**不区分个股成交量水平**
- 这意味着流动性 gate（volume > median）无法降低 stress 模型中的假设成本
- 基本面信号（低换手）也无法降低 stress 模型中的假设成本——因为 stress 模型假设每次交易都有固定成本，与信号频率无关
- 最终：**cost_stress 在当前模型下基本等价于对策略换手率 × 固定成本的惩罚**。如果换手率 ≥ 0.35，cost_stress 几乎必然为负

### 可检验的假设

**假设 H3：在固定 20bp 滑点 + 至少 0.35 日换手的条件下，没有任何信号族可以通过 cost_stress >= 0.00 的门槛。**

检验方法：用一个理想化信号（假设已知未来收益，perfect foresight）跑固定测试，观察 cost_stress 值。如果 perfect foresight 信号仍然无法通过 cost_stress，则 H3 成立——当前 cost_stress 模型在 5-cohort + TopK 系统下是一个不可能通过的门槛。

---

## 层面 4：Success Rules 的严格度

### 当前 setup

9 gates，全部必须通过。包括：
- 绝对收益门（annual_relative_return >= 0.01）——在 benchmark 验证期总收益 82% 时极为苛刻
- 扰动门（topk_8/12 >= 0.00）——非对称（正值通过，轻微负值即失败）
- 费用门（cost_stress >= 0.00）——在固定滑点模型下等价于换手率门

### 问题

如果单个 exploratory round 不能假设候选能找到正 alpha（这正是它需要去发现的），那么 annual_relative_return >= 0.01 在 benchmark 年化收益 20%+ 的验证期下，几乎必然是负的。

**分层判断标准可能更合理：**

| 层 | 目标 | 门槛 | 当前 5 轮最佳 |
|---|---|---|---|
| Layer 1: 相对 baseline | 是否比随机/v18 更好 | delta >= 0 | ✅ 全部通过 |
| Layer 2: 绝对收益 | 是否正 alpha | ann_rel_ret > 0 | ❌ 全部失败 |
| Layer 3: 扰动稳健性 | 组合是否稳定 | topk >= 0, cost >= 0 | ❌ 全部失败 |

5 轮全部通过了 Layer 1，全部在 Layer 2-3 失败。Layer 1 证明这些信号确实有非随机信息。Layer 2-3 证明在当前合同下，**没有一个信号族的信息含量足以覆盖系统固有噪声和成本**。

---

## 最优先检验的根因假设

### 推荐：H3 — Cost_Stress 模型的结构性不可通过性

**理由：**

1. **H1（percentile-rank 高换手）和 H2（cutoff 噪声）** 更多是诊断性的——知晓后可以解释"为什么不行"但难以直接修复
2. **H3（cost_stress 结构性不可通过）** 如果被验证，将直接影响后续研究方向的选择。如果 perfect foresight 信号都无法通过 cost_stress，则 cost_stress >= 0.00 在当前 5-cohort + TopK 合同下本质上是一个不可能通过的门槛。这将意味着：
   - **不是信号族的失败，而是框架层设定的问题**
   - 后续要么调整 cost_stress 模型参数（改为与流动性挂钩），要么降低该门槛到合理水平

### H3 检验的 minimal experiment（先不跑）

```
1. 用 v18_5cohort 的 holdings 提取全部交易记录
2. 将每笔交易假设为以 D1 开盘实现"收益最大化"的理想成交
3. （或者更激进：直接以未来 5 日收益作为排序信号）
4. 跑 fixed test 看 cost_stress
```

如果 ideal signal 也无法通过 cost_stress，则该门槛在当前系统设置下不可能通过，应优先修正框架层设定而非继续迭代信号。

---

## 下一步行动

| 优先级 | 行动 | 工作量 |
|---|---|---|
| P0 | 验证 H3：用理想化信号检验 cost_stress 门槛的可通过性 | 1 天 |
| P1 | 如果 H3 成立，重新评估 success rules 的分层结构 | 设计 |
| P2 | 根据 H3 结果，决定是否修复 cost_stress 模型或调整研究框架 | 待定 |
