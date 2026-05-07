# Design Note: Regime-Conditioned Intraday Trend Bias

**Status:** Design only, not yet registered.

**Previous rounds:**
- `rr_exploratory_intraday_microstructure_independent_baseline_20260501` — 26-cohort, 5/9, closed
- `rr_exploratory_intraday_cohort5_contract_design_20260501` — 5-cohort, 6/9, closed

---

## 1. Problem Redefinition

### What is regime-conditioned trend bias?

裸的 `intraday_trend_bias_20d_raw` = `AVG(intraday_ret) OVER w20`，测度的是过去 20 天 "收盘相对于开盘的方向性漂移" 的平均值。

Regime-conditioned 版本不再平等对待所有样本的 trend_bias 信号，而是引入一个 regime 条件——**只在特定市场状态下启用或加权该信号**。

### 与裸 trend_bias 的本质区别

| 维度 | 裸 trend_bias | Regime-conditioned |
|---|---|---|
| 信号作用域 | 所有 ranking_eligible 股票 | 仅满足 regime 条件的子集 |
| 对低质量信号的处理 | 平等参与排名 | 被 gate 排除，不进入 TopK |
| 费用压力来源 | 所有交易均产生成本 | 过滤段高费用样本 |
| 投资仓位 | 随信号覆盖自然分布 | 集中在高质量 regime 时段 |

### 为什么有希望改善 absolute return / cost_stress

两轮失败的核心原因不是 trend_bias 无信息，而是它的 alpha 厚度不足以覆盖所有环境下的交易成本。**不是信号错了，而是信号在一些 regime 下被稀释了。**

以成交量为对照维度：
- 高成交量日的 intraday drift 更可能是真实订单流不平衡（不是噪音）
- 高成交量股票的买卖价差和滑点更低
- 如果只在高成交量 regime 下启用 trend_bias，等于同时做了两件事：
  - 提升信号的信噪比（alpha 上升）
  - 降低交易成本（cost 下降）
  - 两者都指向 cost_stress 改善

---

## 2. Regime 维度候选

### 候选 A：Volume regime（推荐首选）

| 字段 | 值 |
|---|---|
| 条件变量 | 个股日成交额 `amount` 相对自身 20 日中位数的比率 |
| 条件规则 | `amount > median(amount_over_20d)` → signal active |
| 经济含义 | 成交活跃日的 intraday trend 更可靠、交易成本更低 |
| 预期效果 | 排除低成交噪音样本，降低费用压力，提升信号质量 |

### 候选 B：Volatility regime

| 字段 | 值 |
|---|---|
| 条件变量 | 个股 20 日 realized volatility |
| 条件规则 | `volatility_20d < median(volatility_over_longer)` → signal active |
| 经济含义 | 低波动环境下 intraday drift 更可能持续、反转更少 |
| 预期效果 | 减少高波动的噪音交易，但可能过度排除信号 |

### 候选 C：Volume expansion regime

| 字段 | 值 |
|---|---|
| 条件变量 | 日间成交额变化率（类似 vsumd 的扩张方向） |
| 条件规则 | `amount_t > amount_t-1 × 1.2` + `intraday_ret > 0` → signal active |
| 经济含义 | 放量上涨日的 intraday drift 最具持续性 |
| 预期效果 | 最强信号子集，但样本量可能过小 |

### 为什么选 Volume regime（候选 A）

1. **直接作用于 cost_stress**：高成交量 = 低滑点 + 低买卖价差。这是成本端改善。
2. **经济解释最干净**：成交活跃 + intraday drift = 订单流不平衡。不活跃 = 噪音。
3. **实现简单**：不需要新数据，`amount` 已在 serving.vw_bars_daily 中。
4. **风险最低**：gate 条件是连续变量（amount 比率），可以通过调整阈值来控制样本保留率，不会像候选 C 那样过度收缩样本。

---

## 3. 单一优先方案

### 推荐：Volume-confirmed intraday trend bias

**Conditioning rule：**
```
signal_active_t = amount_t > median(amount_t-20,...,amount_t-1)
```
即：当日成交额大于过去 20 日成交额中位数的股票，才允许进入 trend_bias 排名。

**实现方式：**
不是二阶段筛选，而是**在排名阶段直接添加 WHERE 条件**：
```sql
WHERE ranking_eligible_D0
  AND intraday_trend_bias_20d_raw IS NOT NULL
  AND volume_ratio_20d > 1.0   -- 新增
```

当某股票不满足 volume gate 时，其 `model_score_D0` 为 NULL，永远不会进入 TopK。

**对 invested_weight 的影响：**
不满足 volume gate 的股票被排除后，可选的候选池缩小。但在 5-cohort 合同下（avg_invested_weight 0.81），候选池有足够缓冲。如果 gate 排除了 30-40% 的候选，invested_weight 可能回落到 0.50-0.60——仍高于 0.15 门槛。

**对 cost_stress 的预期影响：**
这是最直接的改善路径。低成交量股票的费用压力来源（大滑点、大冲击成本）被 gate 排除，剩余的高成交量股票的成本结构更健康。

### 为什么比继续微调合同更值得做

两轮合同设计（26-cohort → 5-cohort）已经做了极限：从 16% 仓位到 81% 仓位。进一步提升仓位的空间不存在（81% 已经接近 TopK=10+5-cohort 的上限）。剩下的瓶颈是信号层面。

### 为什么比 additive layer 更值得做

Additive layer 需要多个信号组合，引入 composability 风险（上一轮的 c2/c3 已经部分证明这种风险存在）。Regime conditioning 是在**单信号内部**做改进，不引入组合自由度，判定更干净。

---

## 4. Prereg 草案

```yaml
research_round_id: rr_exploratory_trend_bias_volume_confirmed_20260501

research_tier: exploratory
round_type: signal_conditioning_investigation

research_question: >
  intraday_trend_bias 在高成交量 regime 下（amount > 20d median）
  是否比无条件的 trend_bias 具有更好的 cost_stress 和绝对收益表现？
  或者说，对 trend_bias 施加成交量 gate 是否能缩小从 6/9 到 9/9 的缺口？

baseline_reference_candidate_scheme_id: exploratory_cohort5_c1_trendbias_only
  (注：使用 c1_5cohort 作为同一合同下的对照系，不分合同差异)

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

score_builder: build_baseline_model_scores.py
  (需新增 volume_ratio_20d 中间字段 + 在 feature_frame 中新增 volume gate)
  注：不改现有 presets，新增一个 preset

changed_dimension: signal_conditioning_regime
change_control_rule: single_dimension_only
change_detail: >
  只添加一个 conditioning condition：当日 amount > 过去 20 日中位数。
  所有其他要素不变：score family（intraday_trend_bias 单信号）、
  TopK(10)、执行语义、成本合同、基准、持仓提取、组合刷新、purge gap、
  流动性 guard、holding_cohort_count(5)。

contract_param:
  holding_cohort_count: 5
  (与上一轮 c1_5cohort 相同，保证合同口径一致)

planned_candidates:
  - candidate_scheme_id: exploratory_trend_bias_volume_gated_v1
    feature_preset: single_signal_intraday_trend_bias_volume_gated
    base_signal: intraday_trend_bias_20d_raw
    conditioning_variable: amount 20d median ratio
    conditioning_rule: amount > median_20d (gate in ranking eligibility)
    score_rule: >
      percentile_rank(intraday_trend_bias_20d_raw DESC);
      WHERE ranking_eligible_D0 AND trend_bias IS NOT NULL AND volume_ratio_20d > 1.0;
      min_feature_count >= 1
    description: >
      Intraday trend bias conditioned on above-median daily volume.
      Stocks with below-median volume on signal date are excluded from
      ranking (model_score_D0 = NULL).

success_rules:
  与上一轮完全一致（保证跨候选可比性）：
    pass_validation_annual_relative_return: annual_relative_return >= 0.01
    pass_validation_relative_ir: relative_ir >= 0.30
    pass_not_worse_than_c1_5cohort: annual_relative_return_delta_vs_c1_5cohort >= -0.005
    pass_avg_invested_weight: avg_invested_weight >= 0.15
    pass_max_drawdown_not_worse: max_drawdown_delta_vs_c1_5cohort >= -0.05
    pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
    pass_cost_stress: cost_stress_annual_relative_return >= 0.00
    pass_turnover_not_materially_worse: avg_turnover_daily_delta_vs_c1_5cohort <= 0.04

  core_pass_condition: all 9 gates must pass

  补充诊断指标（不进入 pass/fail，用于分析 gate 效果）:
    - volume_gate_exclusion_rate: 被 gate 排除的 stock-day 占比
    - avg_invested_weight_post_gate: gate 后的实际投资仓位
    - total_turnover_comparison: gate 前后的换手变化

forbidden:
  - 不能新增第二个候选
  - 中途不能更换 gate 条件或阈值
  - 不能查看 2022-2025 测试集
  - 不能改动 Trend_bias 信号本身（只加 gate，不改信号公式）
  - 不能改动任何合同参数（holding_cohort_count 固定 = 5）
  - 不能将 volume gate 与其他 regime 维度组合
  - 不能在 volume gate 之外再加第二层 gate

serial_execution:
  single_candidate_only: true
  rule: 只运行 1 个候选（volume-gated trend_bias）。完成后统一判断。不并行，不中途开新分支。

relationship_to_previous_rounds:
  previous_contract_round: rr_exploratory_intraday_cohort5_contract_design_20260501
  previous_baseline_candidate: exploratory_cohort5_c1_trendbias_only
  relationship: same contract (5-cohort), same base signal, added volume conditioning gate
```

---

## 5. 预期与判断

| 场景 | 解读 |
|---|---|
| cost_stress > 0（突破性改善） | Volume gate 解决了费用压力 → signal conditioning 方向成立 |
| cost_stress 改善但 absolute return 仍 < 0 | Volume gate 降低了成本，但 alpha 仍不足 → 需研究更强的 regime 条件 |
| cost_stress 和 return 均无明显改善 | Volume 不是正确的 regime 维度 → 关停该方向 |

如果 volume-gated trend_bias 通过 success rules：
→ 可以进入 confirmatory 候选，考虑正式主线评估

如果 volume-gated trend_bias 仍失败：
→ 这将是 intraday microstructure 方向的第三次失败，建议关停该研究方向
