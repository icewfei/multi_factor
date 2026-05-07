# Design Note: Fundamental Signal Family (Quality / Profitability)

**Status:** Design only, not yet registered.

**Previous closures:**
- Intraday standalone (3 rounds): 26-cohort → 5-cohort → volume-gated — all failed
- Cross-horizon price technical (1 round): reversal + momentum under 5-cohort — all failed

---

## 1. Why Fundamental Signals Now

### 项目历史概览

从项目开始至今，所有研究尝试都集中在**价格类技术信号**（price-volume technicals）：
- Intraday microstructure（trend_bias, upside_share, reversal_asymmetry）
- Short-term reversal（reversal_5d）
- Medium-term momentum（momentum_60_5）
- Liquidity trend（liquidity_trend_20_60）

这些信号经过 **4 轮、7 个候选、2 个合同变体** 的测试，全部失败。根本原因是：**在 5-cohort 高仓位（~80% invested_weight）下，价格类技术信号在持有期内产生的 alpha 不足以覆盖基准收益和交易成本。**

### 总纲的研究顺序

总纲 14.5 明确推荐的第一批研究方向是：

> 1. quality / profitability
> 2. investment
> 3. value
> 4. liquidity / trading frictions（已完成并失败）
> 5. low-risk / volatility
> 6. momentum as challenger（已完成并失败）

项目跳过了 quality/profitability、investment、value，直接进入了 4 和 6。现在是回到第 1 位的时候。

### 基本面信号与价格信号的本质区别

| 维度 | 价格类技术信号（已关闭） | 基本面信号（新方向） |
|---|---|---|
| 数据来源 | bars_daily（OHLC + amount） | **PIT 财务数据（fina_indicator_pit）** |
| 信号频率 | 日频，高换手 | 季频/月频，**低换手** |
| alpha 来源 | 市场微观结构、趋势、反转 | **公司盈利、质量、估值** |
| 换手率 | ~0.35-0.40 | **预期显著更低** |
| cost_stress | 系统性失败（固定滑点） | **天然优势**（交易频率低） |
| 与已测试信号的关系 | 已被充分探索 | **完全正交**（信息集不重叠） |

---

## 2. Quality / Profitability / Value 优先级

### 候选 A：Quality / Profitability（推荐首选）

| 字段 | 值 |
|---|---|
| 核心指标 | ROE、gross margin、profitability proxies |
| 经济含义 | 高质量/高盈利公司更可能持续产生超额收益 |
| 数据可得性 | warehouse 已有 `fina_indicator_pit` 视图 |
| PIT 约束 | 已有 `ann_date → next_trade_date` 滞后规则 |
| 预期换手 | 极低（季度变化，非日频） |
| 总纲位置 | **14.5 第 1 位** |

### 候选 B：Value

| 字段 | 值 |
|---|---|
| 核心指标 | EP、BP、CFP |
| 经济含义 | 低估值的公司获得均值回复收益 |
| 优先级 | 在 quality 之后（总纲第 3 位） |

### 候选 C：Investment

| 字段 | 值 |
|---|---|
| 核心指标 | asset growth、investment-to-asset |
| 经济含义 | 低投资/保守扩张的公司表现更好 |
| 优先级 | 在 quality 之后（总纲第 2 位） |

### 为什么选 Quality / Profitability

1. **总纲推荐的第 1 位**——不是随意选择
2. **ROE 因子在 A 股的短期持有系统中已有正向证据**
3. **低换手天然缓解 cost_stress**——这是之前所有方向最卡脖子的瓶颈
4. **PIT 数据架构已完备**——`fina_indicator_pit` 视图和 `ann_date → next_trade_date` 滞后规则已在总纲 5.4 中定义好

---

## 3. 单一优先方案

### 推荐：Quality / Profitability 单因子基线

**信号定义：**

`quality_score = standardized_roe`（或类似 proxy）

基于 `fina_indicator_pit.roe`（净资产收益率），使用 `ann_date → next_trade_date` 的 PIT 可见性约束。

**经济含义：** 高 ROE 公司在未来 5 天持有期内有正向预期收益。ROE 变化比 ROE 水平更具预测性。

**预期换手率：** 约 0.02-0.05（季度重算 vs 日内 intraday 信号的 0.35+），这将直接改善 cost_stress。

**为什么比继续做价格类技术信号更值得：**

之前 4+ 轮的全部失败共同证明了一个结论：在 5-cohort 合同下，价格类技术信号无法产生足够的 alpha 来覆盖交易成本。这不是参数问题，是信息集的问题。基本面信号使用完全不同的数据源（财务报表 vs OHLC），其 alpha 来源与价格信号正交。

---

## 4. Shortlist 建议

### 候选 c1：单因子 Quality（推荐首发）

| 字段 | 值 |
|---|---|
| 信号 | `roe_ttm_raw`（或类似 ROE proxy from fina_indicator_pit）|
| min_feature_count | 1 |
| 数据处理 | PIT 对齐：`ann_date → next_trade_date` |
| 预处理 | cross_sectional_robust_zscore，中性化：行业 |
| 角色 | 单因子对照，测试基本面因子在 5-cohort 下的基本可行性 |

### 候选 c2：单因子 Profitability

| 字段 | 值 |
|---|---|
| 信号 | `gross_margin_ttm_raw` 或 `profitability` proxy |
| 角色 | 与 quality 互补：gross margin 度量经营效率 |

### 候选 c3：Quality + Profitability 组合

| 字段 | 值 |
|---|---|
| 信号 | quality + profitability 等权 |
| min_feature_count | 2 |
| 角色 | 主测试候选，测试复合基本面因子的叠加效应 |

---

## 5. Prereg 草案

```yaml
research_round_id: rr_exploratory_fundamental_quality_profitability_20260501

research_tier: exploratory
round_type: family_construction

research_question: >
  在 5-cohort 合同下，以基本面 quality/profitability 信号（基于 PIT 财务数据）
  构建的独立基线，能否在验证集上通过 prereg success rules？
  基本面信号的低换手特性是否能解决 cost_stress 瓶颈？

baseline_reference_candidate_scheme_id: exploratory_cohort5_v18_ref
  (注：基本面信号与价格信号信息集正交，baseline 仅作为项目统一参考系)

snapshot_id: warehouse_20260429_trainval_20211231
contract_path: /Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json
execution_logic_version: warehouse_execution_v3

score_builder: （新建或扩展，需新增基本面信号 SQL）
  build_fundamental_model_scores.py 或扩展 build_baseline_model_scores.py

contract_param:
  holding_cohort_count: 5

changed_dimension: score_family
change_control_rule: single_dimension_only
change_detail: >
  从价格类技术信号完全替换为基本面 quality/profitability 信号。
  不允许改变：TopK(10)、执行语义、成本合同、基准、持仓提取、
  组合刷新规则、purge gap、样本资格矩阵、流动性 guard、holding_cohort_count(5)。

success_rules:
  保持与之前轮次一致的 9 道 gates：

  pass_validation_annual_relative_return: annual_relative_return >= 0.01
  pass_validation_relative_ir: relative_ir >= 0.30
  pass_not_worse_than_baseline: annual_relative_return_delta_vs_v18_5cohort >= -0.005
  pass_avg_invested_weight: avg_invested_weight >= 0.15
  pass_max_drawdown_not_worse: max_drawdown_delta_vs_v18_5cohort >= -0.05
  pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
  pass_cost_stress: cost_stress_annual_relative_return >= 0.00
  pass_turnover_not_materially_worse: avg_turnover_daily_delta_vs_v18_5cohort <= 0.04

  core_pass_condition: all 9 gates must pass

forbidden:
  - 不能加入任何价格类技术信号（该方向已关闭）
  - 不能中途更换前瞻/后顾 PIT 口径
  - 不能混合不同财年的数据
  - 不能改动 5-cohort 合同参数

需要预先解决的实施问题:
  1. 确认 fina_indicator_pit 视图的可用性
  2. 确认 PIT 对齐（ann_date → next_trade_date）的实现状态
  3. 确认行业中性化的数据可用性
  4. 确认基本面代理变量的覆盖率
```

---

## 6. 待确认的实施前提（注册前需要核实的）

| # | 事项 | 状态 |
|---|---|---|
| 1 | `serving.vw_fina_indicator_pit` 是否存在 | 需确认 |
| 2 | PIT 日期对齐逻辑（`ann_date → next_trade_date`）是否已实现 | 需确认 |
| 3 | ROE / gross_margin 在 ranking_eligible 宇宙中的覆盖率 | 需确认 |
| 4 | 行业归属数据是否可用于中性化 | 需确认 |
| 5 | 现有 builder 是否容易扩展基本面 SQL | 需确认 |
