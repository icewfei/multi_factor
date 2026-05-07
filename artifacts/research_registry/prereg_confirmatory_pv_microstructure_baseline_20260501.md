# Prereg: Confirmatory Price-Volume Microstructure Baseline — **SUPERSEDED / ABANDONED**

> 废弃原因：基于错误口径注册。v18 working reference 实际为 2 信号（momentum + liquidity_trend），
> 而非当时误以为的 5 信号。三个候选信号已在 exploratory 阶段以 v18 为 baseline 测过，
> composability screen 均返回 mixed。该方向已被 rounds 4-11b 系统性验证为走不通。
> 替代方案见 `prereg_confirmatory_intraday_microstructure_independent_baseline_20260501.md`。

- `research_round_id`: `rr_confirmatory_pv_microstructure_baseline_20260501`
- `registered_at`: `2026-05-01T09:54:02+08:00`
- `research_tier`: `confirmatory`
- `status`: `preregistration_abandoned`

## Research Question

在 D1-D5 短持有系统 + TopK + 现金保留 + 不补位合同下，以非 Alpha158 的量价协同信号（`volume_price_synchronicity`）、日内微观结构信号（`intraday_trend_bias`）、秩相关信号（`price_volume_rank_corr`）构建的线性多信号基线，能否在年化相对收益、相对 IR、TopK 扰动稳定性上不低于 working reference（`price_volume_v18_refresh_hysteresis`）50bp？

## 旧线诊断

旧线（Alpha158 confirmatory 微调线）终止原因：
- 信号来源过度集中：cord30/corr30/vsumd60 均来自 Alpha158 日频量价统计家族，信息增量有限
- D1-D5 短持有期下日频相关类信号换手率结构性偏高，换手控制工具不足以过治理门槛
- walk-forward 明确衰减：vsumd60 在 2024/2025 年相对 IR 转负
- 经济解释薄弱

新线与旧线的关键区别：

| 维度 | 旧线 | 新线 |
|---|---|---|
| 信号来源 | Alpha158 家族（corr/cord/vsumd） | 非 Alpha158 机制簇 |
| 经济机制 | 量价相关性 | 价格发现过程 + 量价协同确认 |
| 研究方式 | 单信号微调 | 多信号基线组合价值验证 |
| 与 v18 关系 | 替换成分 | 在 v18 成分外新增正交维度 |

## 诊断确认

此前 exploratory composability screen 对 `intraday_trend_bias` 和 `volume_price_synchronicity` 与 v18 核心家族的兼容性均返回 `mixed` 结论。本轮 confirmatory 阶段通过以下措施区分于 exploratory：
1. 固定验证集（2019-2021）vs. 之前 composability screen 使用训练集内部诊断
2. 预注册成功标准的布尔表达式，不允许事后解释
3. 验证集访问预算严格限制

## Baseline Reference

- `baseline_reference_candidate_scheme_id`: `price_volume_v18_refresh_hysteresis`
- `snapshot_id`: `warehouse_20260429_trainval_20211231`
- `contract`: `run_input_contract.research_trainval_20211231.json`
- `execution_logic_version`: `warehouse_execution_v3`

## 允许改动的核心维度

`score_family_composition` — 只允许在 baseline_reference 上新增指定信号。

## 不允许改动的维度

- TopK（固定 10）
- 执行语义（D0 收盘出信号、D1 开盘买、D5 收盘卖、不补位、现金保留）
- 成本合同（默认参数集）
- 基准（中证全指全收益）
- 持仓提取规则（等权 Top10）
- 组合刷新规则（v18 refresh hysteresis）
- purge gap（默认 5）
- 样本资格矩阵
- 信号预处理合同（统一使用 cross_sectional_robust_zscore, mad_clip_5, neutralization=none）

## 候选方案

三个候选为**递进式**：仅当前一候选在验证集上通过 success_rules 后，才允许推进到下一候选。

### c1: `confirmatory_pv_microstructure_c1_synchronicity_add`

- 信号集：`momentum_60_5_raw` + `liquidity_trend_20_60_raw` + `volume_price_synchronicity_20d_raw`
- 合成规则：等权 percentile_rank（DESC），min_feature_count >= 2
- 测试方向：量价协同信号在 v18 基础上是否有独立增量信息

### c2: `confirmatory_pv_microstructure_c2_synchronicity_trendbias`

- 信号集：c1 信号 + `intraday_trend_bias_20d_raw`
- 合成规则：等权 percentile_rank（DESC），min_feature_count >= 3
- 测试方向：日内微观结构信号（趋势偏向）在量价协同基础上是否还有独立增量

### c3: `confirmatory_pv_microstructure_c3_synchronicity_trendbias_rankcorr`

- 信号集：c2 信号 + `price_volume_rank_corr_20d_raw`
- 合成规则：等权 percentile_rank（DESC），min_feature_count >= 4
- 测试方向：秩相关信号在日内结构与量价协同组合上是否还有独立增量

## 信号预处理合同（所有候选统一）

| 步骤 | 规则 |
|---|---|
| 缺失值处理 | none（不做跨期填充） |
| 非有限值处理 | 排除 |
| 去极值 | mad_clip, param=5.0 |
| 标准化 | cross_sectional_robust_zscore |
| 中性化 | none |

## Success Rules（布尔表达式）

```
pass_validation_annual_relative_return: 
    annual_relative_return >= 0.01

pass_validation_relative_ir: 
    relative_ir >= 0.30

pass_not_worse_than_baseline: 
    annual_relative_return_delta_vs_v18 >= 0.005

pass_topk_perturbation: 
    topk_8_relative_return >= 0.00 
    AND topk_12_relative_return >= 0.00

pass_cost_stress: 
    cost_stress_annual_relative_return >= 0.00

pass_validation_turnover_not_materially_worse: 
    avg_turnover_daily_delta_vs_v18 <= 0.02
```

核心通过条件：
```
pass = pass_validation_annual_relative_return 
       AND pass_validation_relative_ir 
       AND pass_not_worse_than_baseline 
       AND pass_topk_perturbation 
       AND pass_cost_stress
```

`pass_validation_turnover_not_materially_worse` 为审计项，不直接阻止通过。

## 允许使用的数据分区

- 训练集：2010-01 ~ 2018-12（用于模型/合成规则拟合）
- 验证集：2019-01 ~ 2021-12（用于候选比较和正式 verdict，固定访问预算 = 2）

## 冻结保留的测试集

2022-01 ~ 2025-12（本轮不查看，仅当前 candidate 在验证集全通过后用于主线晋升 fixed test）

## 禁止事项

1. 不能新增第四个候选方案
2. 中途不能更换候选名单
3. 不能查看 2022-2025 测试集结果
4. 不能调整 v18 的 portfolio refresh hysteresis
5. 不能改变信号预处理合同
6. 不能新增中性化
7. 不能回看历史 Alpha158 confirmatory 结果来调整当前候选
8. 不能因为某一年特别好就放宽通过标准
9. 不能删除失败候选的实验记录

## 失败条件

若三个候选都未通过 success_rules，则：
- 本轮确认性研究归档为失败
- 该方向不得在未修改问题定义的前提下在同一 snapshot 上直接重试
- 失败证据保留在 registry 中

## 验证集查看预算

- 初始预算：2 次验证摘要生成
- 锁定 rerun 后同口径不重复消耗预算
- 每次新的验证摘要产物生成消耗 1 次预算
