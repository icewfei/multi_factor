# 项目状态总结 2026-05-07

## 研究线收口

2026-05-06 至 2026-05-07 完成了最后一轮系统性的信号工程探索。以下方向全部收口：

| 方向 | 轮次 | 结论 |
|---|---|---|
| 隔夜/日内收益拆解 + 反转交互 | overnight_intraday_decomposition | 隔夜正交但太弱(IC 0.014)，日内即 p98 本身 |
| Decile 非线性映射 | decile_nonlinear | 验证了非线性的存在，但不超越 p98 |
| Power transform | power_transform_v1-v4 | 数学上单调变换不改变排序，IC 提升是统计假象 |
| 行业/市值中性化 | neutralization_v1 | 验证 IC 提升，组合表现不转化 |
| 中性化 + 尾部切除 | neut_tail_combo | 验证 IC 提升 18%，组合表现略逊 p98 |
| 多信号 IC 加权复合 | multi_signal_composite | 验证 IC +93%，Sharpe +51%，成本 stress +32%，但年化收益仍为负 |

## 最终的探索性赢家

**`multi_equal_weight_v1`** — p98 + cord30 + vsumd60 + corr30 等权复合。

| 指标 | p98 (旧基线) | multi_equal_weight_v1 |
|---|---|---|
| 验证 IC | 0.0122 | **0.0235** |
| 年化相对收益 | -0.1293 | -0.1356 |
| 最大回撤 | -0.0867 | **-0.0670** |
| Sharpe | 13.59 | **20.57** |
| 成本 stress | -0.0610 | **-0.0413** |
| 日均换手 | 0.1245 | **0.1048** |

四个组成信号间 pairwise correlation 最低 0.07，最高 0.42，alpha 来源高度分散。

## 核心瓶颈

**所有真实信号的年化相对收益均为负。** Oracle（完美信息）在同一框架下产生 +2,888 的年化收益，证明框架本身不被执行封死。差距来自信号层——当前日频量价数据中可提取的预测信息，经最优组合后，仍不足以覆盖交易成本。

这不是方法问题，是信息源问题。

## 已归档的关键实验（可追溯、可复算）

- 12+ 轮研究，覆盖 5 个信号家族、3 个合同变体、3 个刷新规则
- 4 轮非线性探索（decile/power/neutralize/composite）
- Oracle 探针（V1 +2,888, Probe A +4,634）
- 所有失败证据保留在 failure_evidence_log.jsonl + candidate_scheme_registry.jsonl + research_round_registry.jsonl

## 项目当前状态

```
status: signal_engineering_phase_closed
exploratory_winner: multi_equal_weight_v1
strict_confirmatory_winner: none (annual_relative_return < 0)
next: awaiting new data modality or project scope change
```
