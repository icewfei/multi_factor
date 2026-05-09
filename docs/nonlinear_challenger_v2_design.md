# Nonlinear Challenger v2 Design

## Scope

本文档只定义 `nonlinear_challenger_v2` 的设计、draft manifests 与 fail-fast guardrails。

本文档不做以下事情：

- 不训练模型
- 不跑 portfolio
- 不生成 metrics/readout
- 不读取 frozen test
- 不修改 confirmed5 文件
- 不修改 confirmed5 `model_config` / `feature_set` / `candidate`

## Why v2 Exists

`confirmed5` 的收口结论已经固定：

- model-layer 有正 edge
- execution-layer 通过
- portfolio dry-run 通过
- same-contract baseline comparison 弱于 baseline
- 不进入 confirmatory / shadow
- 不允许继续围绕 validation 调 confirmed5

因此，`nonlinear_challenger_v2` 的目标不是继续微调 confirmed5，也不是以“提高 validation 回测”为目标。  
`v2` 的目标是：在不改 confirmed5 基础特征和不调模型超参的前提下，降低“模型分数 edge 无法转化为组合层相对优势”的问题。

## Relation To Confirmed5

`v2` 与 `confirmed5` 的关系必须明确：

- `v2` 是一个全新的 challenger，不是 confirmed5 的继续调参版。
- `v2` 保持 confirmed5 的五个输入特征不变。
- `v2` 保持 confirmed5 的 LightGBM 深度、叶子数、学习率、估计器数量不变。
- `v2` 不修改 execution contract，不修改 portfolio guard。
- `v2` 唯一改变的是分数到选股排序之间的单一主变更维度。

## Locked IDs

- `research_round_id = rr_nonlinear_challenger_v2_cs_volatility_discount_20260509`
- `candidate_scheme_id = nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42`
- `feature_set_id = nlc_v2_fset01_confirmed5_locked_inputs`
- `model_config_id = nlc_v2_lgbm_regressor_depth3_seed42_cs_volatility_discount_v1`

## Single Primary Change Dimension

`v2` 的单一主变更维度为：

- `portfolio_aware_cross_sectional_score_transformation`

具体采用的预注册设计是：

- 在保留 confirmed5 原始模型训练配置不变的前提下，
- 对 D0 截面的原始模型分数引入一个固定、不可调参的 `volatility_20d` 折扣变换，
- 让高波动状态下的高分名字在最终排序中受到一致的、预先声明的折扣，
- 以减少“模型 edge 在组合层转化时被高波动部署状态稀释”的问题。

本设计选择该维度的原因是：

- 它不改变 confirmed5 的输入特征集合。
- 它不改变 confirmed5 的模型超参。
- 它不触碰 execution / portfolio guard。
- 它直接针对组合层转化损失，而不是继续围绕 validation 做特征和参数筛优。

## Transformation Contract

`v2` 的 score transformation 合同固定为：

- raw score source: `raw_model_score_D0`
- auxiliary state input: `volatility_20d`
- cross-sectional objects:
  - `raw_model_score_percentile_rank_D0`
  - `volatility_20d_percentile_rank_D0`
- fixed transformation:
  - `adjusted_score_D0 = raw_model_score_percentile_rank_D0 * (1.0 - volatility_20d_percentile_rank_D0)`
- transformation intent:
  - 保留模型排序信息
  - 对高波动部署状态做统一折扣
  - 不引入新的可调系数
  - 不允许依据 validation 结果重写折扣公式

这一定义是参数冻结、规则先验、不可调优的主变更维度。  
如果未来需要换公式、换辅助状态、换折扣结构，必须开新 challenger，而不是在 `v2` 上继续改。

## Prohibited Actions

`v2` 设计阶段明确禁止：

- 不调 confirmed5
- 不用 validation 反复筛优
- 不碰 frozen test
- 不把 trainval dry-run 当 OOS
- 不改 execution / portfolio guard
- 不在 `v2` 上引入第二个主变更维度

## Promotion Gate

`v2` 后续若进入训练与评估，晋级门槛必须提前写死：

- model-layer 不能明显差于 confirmed5
- same-contract portfolio comparison 必须优于 baseline
- total equity 必须报告
- invested capital 必须报告
- average invested_weight 必须报告
- average cash_weight 必须报告
- terminal exit flags 必须完整

这里的“优于 baseline”指的是：

- 同 split
- 同 execution contract
- 同 portfolio construction rules
- 同 cash / invested capital 口径
- 同 terminal exit policy

## Fail-Fast Guardrails

`v2` 在任何训练授权前必须满足以下 fail-fast 条件：

- source mapping 未确认则不能训练
- baseline comparison 未绑定则不能训练
- manifest 未通过 validator 则不能训练

更具体地说：

- 如果 `volatility_20d` 或 raw score transform 所需字段没有完成 source mapping 复核，训练禁止启动。
- 如果 `baseline_candidate_scheme_id` 没有绑定到当前基线，训练禁止启动。
- 如果 feature_set / model_config / candidate manifest 任一未通过 validator，训练禁止启动。

## Expected Manifest Semantics

`v2` draft manifests 必须表达以下含义：

- `feature_set` 不是新选特征，而是 `confirmed5` 输入锁定版。
- `model_config` 不是新调参，而是 `confirmed5` 超参锁定版加一个 post-score transformation contract。
- `candidate` 必须声明：
  - 相对 confirmed5 的关系
  - 单一主变更维度
  - 不允许 validation 反复筛优
  - baseline same-contract comparison 是晋级必要条件

## What v2 Is Not

`v2` 不是：

- confirmed5 的续调版本
- 一个为了追 validation readout 的参数优化轮次
- 一个已经训练过的 challenger
- 一个已经证明策略有效的候选
- 一个 OOS / frozen test 结论
