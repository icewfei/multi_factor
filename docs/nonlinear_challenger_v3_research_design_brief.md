# Nonlinear Challenger v3 Research Design Brief

## Scope

本文档只定义 `nonlinear_challenger_v3` 的研究设计 brief。本文档不写实现代码，不训练模型，不跑回测，不生成新的 metrics/readout，不读取 frozen test，也不设计具体 `v3` 参数。

## Why v3 Exists

`confirmed5` 与 `v2` 的研究结论已经固定：

- 两者都在 model-layer 看到了正向 edge
- 两者都没有在 same-contract portfolio comparison 中超过 baseline
- 已有 failure analysis 和 portfolio construction gap summary 都指向同一个问题：
  `model-layer edge 没有转化成 TopK portfolio edge`

因此，`v3` 的研究目标不应再是“做一个更复杂的模型”，而应直接针对：

- deployed TopK head quality
- capital deployment efficiency

## Relation To Previous Rounds

`v3` 是新的 challenger，不是 `confirmed5` 或 `v2` 的续调版本。

`v3` 与上一轮的关系必须明确：

- 不继续微调 `confirmed5`
- 不继续围绕 `v2` 的 volatility discount 做 validation 驱动的回抠
- 不把更高 RankIC 当成足够条件
- 不再默认“模型更复杂就会自然赢 baseline”

## Single Primary Change Dimension

`v3` 的单一主变更维度应定义为：

- `topk_head_quality_conditioned_capital_deployment`

这个维度的含义是：

- `v3` 只研究“如何把同一套 model score 更有效地转化为 deployed TopK portfolio”
- `v3` 只允许在 portfolio construction / capital deployment 这一层引入新的主变更
- `v3` 不以追求更高 full cross-section RankIC 为目标

更直接地说，`v3` 研究的是：

- 当 TopK head quality 足够强时，如何更有效部署资本
- 当 TopK head quality 不足时，如何避免把弱 head 机械部署成低质量持仓

这一定义只保留一个自由度：  
`capital deployment should be conditioned on deployed head quality rather than assumed from model complexity alone`

## Why This Dimension Directly Targets The Failure

这个单一主变更维度直接针对前两轮的失败原因：

### 1. 它针对的不是 RankIC 不足，而是 TopK head conversion 失败

`confirmed5` 和 `v2` 的共同问题不是“完全没有模型 edge”，而是：

- 排序统计为正
- 但 selected-head realized return 没有形成足够优势
- 最终 total equity / relative return 仍然输给 baseline

所以 `v3` 不应该继续去优化“更漂亮的 model-layer 指标”，而应直接研究：

- score 如何进入 deployed head
- deployed head quality 如何决定 capital deployment

### 2. 它直接针对 confirmed5 的失败模式

`confirmed5` 的失败模式更像：

- 高 churn
- head quality 不够强
- invested weight 不低，但 total equity 仍明显弱于 baseline

这说明问题不在“投得太少”，而在“投出去的 head 不够好”。  
因此 `v3` 需要围绕 head quality 与 deployment 的连接方式，而不是继续堆模型。

### 3. 它直接针对 v2 的失败模式

`v2` 的失败模式更像：

- 降低了一部分风险
- 降低了一部分换手
- 但也牺牲了收益捕获

这说明简单的 score discount 并没有解决 deployed head quality 问题。  
因此 `v3` 需要研究的不是“再换一个折扣公式”，而是：

- 资本部署是否应该显式围绕 head quality 条件来决定

## What v3 Is Trying To Improve

`v3` 的目标不是只提高 RankIC。  
`v3` 的目标是改善以下对象中的至少一个，并且最终体现为 same-contract portfolio gain：

- TopK head realized return quality
- deployed capital efficiency
- head quality 与持仓部署的一致性
- 资本部署后的 total equity conversion

换句话说，`v3` 的成功标准不是：

- “模型分数更好看”

而是：

- “同样的 model family，在 deployed TopK portfolio 上更有效”

## What v3 Must Not Change

`v3` 必须明确不改变以下内容：

- 不改变 model input features
- 不改变 LightGBM hyperparameters
- 不改变 execution semantics
- 不改变 terminal exit policy
- 不改变 portfolio guard

这几个边界的目的很明确：

- 把研究焦点锁死在 portfolio construction / capital deployment
- 避免把多个自由度重新混在一起
- 防止又回到“边调模型边解释组合结果”的路径

## Why This Is Not “More Model Complexity”

`v3` 不应继续堆模型复杂度，原因很直接：

- `v2` 的 validation RankIC / ICIR 已经明显强于 confirmed5
- 但 `v2` 的 deployed head realized return 仍然低于 baseline
- 这说明当前主要瓶颈不是模型表达能力，而是 portfolio conversion

因此再增加复杂度，最可能发生的是：

- model-layer 数字继续变化
- portfolio-layer 问题仍未被直接处理
- 研究自由度增加
- 解释空间变大

这不符合当前轮的研究结论，也不符合下一轮应降低自由度的原则。

## Promotion Gate

如果未来正式启动 `v3`，最低晋级门槛必须提前写死：

- model-layer 不明显劣化
- same-contract portfolio comparison 必须优于 baseline
- total equity 必须报告
- invested capital 必须报告
- cash 必须报告
- turnover 必须报告

其中“优于 baseline”必须在以下同口径条件下成立：

- 同 split
- 同 execution contract
- 同 terminal exit policy
- 同 portfolio construction comparison contract
- 同 cash / invested capital 口径

## Fail-Fast Conditions

`v3` 必须在以下情况下直接 fail-fast：

- 没有 baseline same-contract comparison，不晋级
- 高现金口径未披露，不晋级
- TopK head quality 未改善，不晋级
- frozen test 被读取，直接作废

这些条件的含义是：

- 如果不能证明 portfolio conversion 比 baseline 更好，就不允许推进
- 如果 cash / invested capital 没披露清楚，就不允许用 total equity 做片面叙事
- 如果 head quality 没改善，就不允许声称部署机制改进有效
- 如果触碰 frozen test，整个研究轮治理失效

## What v3 Is Not

`v3` 不是：

- confirmed5 的续调
- v2 的公式微调版
- 一个新的模型复杂度竞赛
- 一个 validation 驱动的筛优轮次
- 一个可以绕过 same-contract baseline comparison 的候选

## Final Brief

`v3` 的研究问题应被固定为：

- 在不改变特征、不改变 LightGBM 超参、不改变 execution / terminal / guard 的前提下，
- 只围绕 `topk_head_quality_conditioned_capital_deployment` 这一单一主变更维度，
- 研究如何让 deployed TopK head quality 与 capital deployment efficiency 改善，
- 并且只以 same-contract portfolio comparison 是否超过 baseline 作为最终晋级判断。
