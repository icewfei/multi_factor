# Turnover Floor Analysis — Refresh-Rule-Only Feasibility

---

## 1. Structural Turnover Floor

### 当前合同参数

| 参数 | 值 |
|---|---|
| holding_cohort_count | 5 |
| holding_period | 5 days (D1-D5) |
| avg_invested_weight | ~0.81 |
| turnover formula | `(buy_notional + sell_notional) / lag_total_equity` |

### 理论下限

在 5-cohort 稳态下：

```
每日有 1/5 的持有资本到期（D5 强制卖出）
sell_flow = avg_invested_weight / holding_cohort_count = 0.81 / 5 = 0.162

为维持 ~0.81 invested weight，每日须买入等额：
buy_flow ≈ sell_flow = 0.162

turnover_floor = buy_flow + sell_flow = 0.162 + 0.162 = 0.324
```

**结论：在任何 refresh rule（不改变 holding period / cohort count）下，avg_turnover_daily 的下限是 ~0.324。**

如果达到满仓（invested_weight = 1.0），下限为 `2 × 1.0 / 5 = 0.40`。

### 为什么 full refresh / retain15 / retain50 都收敛在 ~0.40

三者的 turnover（0.397-0.399）非常接近理论满仓下限 0.40。说明在 5-cohort + 5 天持有下，turnover 几乎完全由结构性到期决定，refresh rule 的优化空间极小。

---

## 2. 各方法轮的 turnover 变动拆解

```
                  full_refresh    retain15    retain50    locked
结构性到期            0.324         0.324       0.324      0.324
每日 rank 替换         0.073         0.075       0.075      0.000
                     ───────       ───────     ───────    ──────
合计                   0.397        0.399       0.399      0.324

注：cohort_entry_locked 的理论值 = 0.324。
实际值可能略高（约 0.33-0.35），因退市/停牌等特殊退出。
```

---

## 3. Refresh-Rule-Only 的可达目标

### 原来：`avg_turnover_daily <= 0.20`

**不可达**。结构性下限 0.324 > 0.20，没有纯 refresh rule 改变能在不修改 holding period 或 cohort count 的情况下达到 0.20。

### 实际上可达的目标

| 目标 | 是否可达 | 如何达成 |
|---|---|---|
| `avg_turnover_daily <= 0.35` | ✅ | 任何 retention（已达成） |
| `avg_turnover_daily <= 0.33` | ⚠️ | cohort-entry locked（理论下限 0.324，接近） |
| `avg_turnover_daily <= 0.20` | ❌ | 需要改 holding period / cohort count |

### 降低 turnover 的三种路径

| 路径 | 预期 turnover | 改动维度 | 备注 |
|---|---|---|---|
| **保持 5-cohort，仅改 refresh rule** | 0.33-0.35 | portfolio_refresh_rule | 影响空间极小 |
| **增加 cohort_count（如 5→10）** | 0.20-0.25 | holding_cohort_count | 降低结构性到期比例，但降低 invested_weight |
| **延长 holding period（如 D5→D10）** | 0.20-0.25 | 执行语义（宪法级） | 更长的持有期降低每日到期率 |
| **改 turnover 口径** | — | — | 不属于方法改进 |

---

## 4. 建议

### 方向 1（推荐）：改 cohort_count

将 `holding_cohort_count` 从 5 改为 **10**，其他不变。

```
new_sell_flow = avg_inv / 10 = 0.81 / 10 = 0.081
turnover_floor = 2 × 0.081 = 0.162
```

预期 turnover 约 0.16-0.20，**≤ 0.20 可达**。

但 invested_weight 会下降（从 0.81 到约 0.50-0.60），因为每 cohort 的资本份额从 20% 降到 10%。

### 方向 2：改 holding period

将 holding period 从 D5 延长到 **D10**。但这是总纲宪法级规则（Section 3.1），改动成本高。

### 方向 3：接受 turnover 下限，重新设定方法轮目标

不再以 `avg_turnover_daily <= 0.20` 为目标。
改为 `avg_turnover_daily <= 0.33`（结构性下限 + 少量 margin）。
但这只能确认 cohort-entry locked 是否达到理论下限，收益不够明确。

---

## 5. 单一推荐

### 方向 1：holding_cohort_count = 10

与前几轮方法轮不同，这次**不再仅改 portfolio_refresh_rule**，而是扩展 changed_dimension 为 **portfolio_capital_allocation**（cohort_count + refresh_rule 联动）。

但这引入了两个自由度的联动。更干净的做法是：

**只改 holding_cohort_count = 10，保留 full refresh**，先看单独的 cohort_count 变化是否能把 turnover 压到 ≤0.20，再决定是否加 retention。

| 改动 | changed_dimension | 预期 turnover |
|---|---|---|
| `holding_cohort_count: 5→10` | contract_parameter | ~0.18-0.22 |

如果 10-cohort 就能压到 ≤0.20，则不需要再引入 retention。如果不行，再在 10-cohort 上加 retention。

这回到了项目早期做过的 26-cohort → 5-cohort 的合同参数研究，但这次是反方向：5 → 10（增加 cohort 数量）。

---

## 6. 最终结论

```
1. avg_turnover_daily <= 0.20 在 5-cohort + 5-day hold + 0.81 inv_wt 下不可达
2. 结构性下限 = 0.324（2 × 0.81 / 5）
3. 过去 5 轮方法轮的 turnover 收敛在 0.40 附近，几乎都由结构性到期决定
4. 要继续压 turnover：
   优先：holding_cohort_count 5→10，预期 turnover ~0.18-0.22
   备选：延长 holding period（宪法级改动，成本更高）
   已关闭：仅改 refresh rule 不改以上参数
```
