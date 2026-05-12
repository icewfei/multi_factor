# Nonlinear Challenger v3 Implementation Design Spec

## Scope

本文档只定义 `nonlinear_challenger_v3` 的 implementation design spec。本文档不写实现脚本，不训练，不跑 portfolio，不生成新的 metrics/readout，不读取 frozen test，也不修改 `confirmed5` / `v2`。

本文档只回答未来若进入实现阶段，`topk_head_quality_conditioned_capital_deployment` 应该如何被计算、约束和审计。

## Locked Objective

`v3` 的单一主变更维度固定为：

- `topk_head_quality_conditioned_capital_deployment`

它的目标不是改善 full cross-section 指标，而是改善：

- deployed TopK head quality
- capital deployment efficiency
- model-layer edge 到 deployed TopK head portfolio edge 的转化

## Unchanged Items

`v3` implementation design 必须锁死以下不变项：

- 不改 feature list
- 不改 LightGBM 参数
- 不改 execution semantics
- 不改 terminal exit policy
- 不改 portfolio guard

## Base Score Source

`v3` 必须先声明唯一 base score source，然后才允许做 head-quality conditioning。

允许的 base score source 只有两类：

- `confirmed5 raw_score_D0`
- `v2 adjusted_score_D0`

禁止：

- 同时混合 `confirmed5` 和 `v2` 做 ensemble
- 重新训练新的 base model
- 在 `v3` 内改写 `confirmed5` / `v2` 的 score 定义

实现含义必须固定为：

- `raw_score_D0` = 已锁定 base score source 在 `signal_date = D0` 的原始部署输入分数
- base score source 一旦在 manifest 中声明，就不能再用 validation 结果切换

## Required Inputs

`v3` 未来实现若启动，允许且需要的输入如下：

### 1. Base score inputs

- `confirmed5` 或 `v2` 的已存在 `D0` scores
- 当前 `signal_date` 截面的 score rank
- 按未调整 raw score 先得到的 provisional `TopK membership`

### 2. Historical head-quality estimates

- `historical train-only head-quality estimates` 是允许且必需的
- 这些估计只能来自：
  - 固定 train window
  - 或 expanding past data
- 任何一种模式都必须保证只使用当前 `signal_date` 之前的信息

### 3. State inputs

- `volatility` 允许，但必须是 `D0` 可见、来自既有项目数据源的状态输入
- `liquidity` 允许，但必须是 `D0` 可见、来自既有项目数据源的状态输入
- `turnover` 只允许使用 `ex-ante turnover proxy`
- `realized turnover outcome` 不允许
- `realized label proxy` 只允许用于 historical head-quality estimation
- `realized label proxy` 不允许作为当前 `signal_date` 的直接输入

这里的边界是：

- 允许使用历史聚合统计
- 不允许把未来 realized outcome 直接喂给当前日部署决策

## Prohibited Inputs

以下输入在 `v3` implementation design 中必须明确禁止：

- `validation outcome`
- `frozen test`
- `future realized return`
- `portfolio result feedback`
- `current signal_date` 之后才知道的信息
- `same-contract comparison` 的结果数值本身
- 任何由 portfolio equity / cash / turnover 反推出来的反馈信号

更具体地说：

- 不能用 validation 结果调门槛
- 不能用 validation 结果切换 conditioning source
- 不能用 frozen test 决定 multiplier
- 不能用未来 realized return 决定当前日 head quality
- 不能用 portfolio result feedback 反复重写条件规则

## Conditioning Calculation Contract

`v3` 的 conditioning 计算必须采用固定、可审计、不可围绕 validation 改写的合同。

### Step 1. Define provisional head from raw score

先用声明好的 `raw_score_D0` 在 `D0` 截面上做未调整排序：

- 得到 `raw_score_rank_pct_D0`
- 得到 `TopK membership`

这一步是 `v3` 的原始 head 定义。  
后续 conditioning 只能在这个 provisional head 之上工作，不能先看未来结果再反推 head。

### Step 2. Build historical head-quality cells

对每个历史样本，允许构造以下 conditioning keys：

- `base_score_source`
- `topk_rank_bucket`
- `volatility_bucket`
- `liquidity_bucket`
- `turnover_proxy_bucket`

其中：

- `topk_rank_bucket` 必须来自 raw TopK 内部位置，而不是未来结果
- `volatility_bucket` / `liquidity_bucket` / `turnover_proxy_bucket` 必须只由 `D0` 可见输入或更早信息构造
- bucket 方案必须预先写死，不能用 validation 筛选

历史 `head_quality_estimate` 的允许定义为：

- train-only 平均 `label_5d_next_open_close`
- 或 train-only TopK head hit-rate proxy
- 或 expanding past 的同口径历史聚合值

但它们都只能作为历史聚合统计，不能把未来 realized return 直接用于当前日输入。

### Step 3. Historical source modes

`v3` 只允许两种 `head_quality_conditioning_source`：

- `train_window_frozen_calibration`
- `expanding_past_calibration`

具体约束为：

- `train_window_frozen_calibration`：整个 validation 期间都使用训练窗口冻结得到的 calibration table
- `expanding_past_calibration`：每个 `signal_date` 只能使用 `< signal_date` 的过去观测更新 calibration table

禁止：

- `validation_tuned_calibration`
- `frozen_test_calibration`
- `portfolio_feedback_calibration`

### Step 4. Convert historical head quality to multiplier

`capital_deployment_multiplier` 必须由历史 cell quality 映射得到，且范围预设、单调、不可调。

推荐固定合同如下：

1. 对所有历史 conditioning cells 计算 `head_quality_estimate`
2. 在历史 cells 内对 `head_quality_estimate` 计算 percentile rank
3. 定义：

`capital_deployment_multiplier = clip(0.50 + 0.50 * head_quality_cell_percentile_rank, 0.50, 1.00)`

这一定义的含义是：

- 历史 head quality 越差，multiplier 越接近 `0.50`
- 历史 head quality 越好，multiplier 越接近 `1.00`
- `v3` 只允许 downweight，不允许 leverage up
- multiplier 的上下界是预设范围，不允许用 validation 调整

### Step 5. Fallback chain

如果细粒度 conditioning cell 没有足够历史支持，回退顺序必须预先写死：

1. `topk_rank_bucket + volatility_bucket + liquidity_bucket + turnover_proxy_bucket`
2. `topk_rank_bucket + volatility_bucket + liquidity_bucket`
3. `topk_rank_bucket + volatility_bucket`
4. `topk_rank_bucket`
5. `global_topk_train_reference`

如果连 `global_topk_train_reference` 都不存在：

- `conditioning source 缺失`
- 必须 fail-fast

### Step 6. Produce adjusted deployment score

未来实现必须保留两套分数字段：

- `raw_score_D0`
- `adjusted_score_D0`

固定定义为：

- 对 `TopK membership = true` 的名字：
  - `adjusted_score_D0 = raw_score_D0 * capital_deployment_multiplier`
- 对 `TopK membership = false` 的名字：
  - `adjusted_score_D0 = 0.0`
  - `capital_deployment_multiplier = 0.0`

这样定义的目的很明确：

- provisional TopK 先由 raw score 决定
- conditioning 只改变 deployed capital intensity
- 不允许非 TopK 名字因为后处理而回流进入 head

## Leakage Prevention

`v3` implementation design 必须明确以下 leakage 防护：

### 1. head-quality conditioning 只能由 train window 或 expanding past data 产生

- `head-quality conditioning 只能由 train window 或 expanding past data 产生`
- 不能从 validation summary 反推 calibration
- 不能从 frozen test 反推 calibration

### 2. 不能用当前 signal_date 之后的信息

- `不能用当前 signal_date 之后的信息`
- `不能用当前 signal_date` 的 future realized return
- `不能用 D1/D5` 之后才知道的 outcome 做当前日输入

### 3. 不能用 validation 结果调门槛

- `不能用 validation 结果调门槛`
- `不能用 validation 结果改 bucket`
- `不能用 validation 结果改 multiplier range`
- `不能用 validation 结果选择 confirmed5 或 v2`

### 4. leakage audit 必须显式输出

`leakage_audit_flags` 至少必须包含：

- `train_only_or_expanding_past_only`
- `no_validation_lookup`
- `no_frozen_test_lookup`
- `no_future_signal_date_lookup`
- `no_portfolio_feedback_lookup`
- `state_inputs_d0_visible`

## Output Fields

未来若实现，输出中必须显式包含以下字段：

- `raw_score_D0`
- `adjusted_score_D0`
- `capital_deployment_multiplier`
- `head_quality_conditioning_source`
- `conditioning_policy_version`
- `leakage_audit_flags`

推荐固定：

- `conditioning_policy_version = nlc_v3_hqcd_v1`

字段含义必须写死：

- `raw_score_D0`：来自预声明 base score source 的未调整分数
- `adjusted_score_D0`：应用 conditioning 后的部署分数
- `capital_deployment_multiplier`：由历史 head quality 映射得到且受上下界限制的部署强度
- `head_quality_conditioning_source`：`train_window_frozen_calibration` 或 `expanding_past_calibration`
- `conditioning_policy_version`：当前 conditioning 合同版本
- `leakage_audit_flags`：用于证明没有读取 validation / frozen / future / portfolio feedback

## Fail-Fast Guardrails

未来实现前和未来运行时，以下情况都必须直接 fail-fast：

- `conditioning source 缺失`
- `使用 validation/frozen 信息`
- `multiplier 超出预设范围`
- `TopK head quality 未改善`
- `baseline same-contract comparison 缺失`

更具体地说：

- 如果 calibration table 无法构造，直接失败
- 如果发现读取 validation outcome 或 frozen test，直接失败
- 如果任一 `capital_deployment_multiplier` 不在 `[0.50, 1.00]` 内，直接失败
- 如果后续评估时 `TopK head quality 未改善`，不晋级
- 如果后续评估时 `baseline same-contract comparison 缺失`，不晋级

## What v3 Implementation Design Must Not Do

本文档完成后，仍然不代表现在可以开始实现脚本、训练、回测或生成 readout。

本文档不授权以下动作：

- 不准写实现脚本
- 不准训练
- 不准跑 portfolio
- 不准生成 metrics/readout
- 不准读取 frozen test
- 不准调参
- 不准改 confirmed5 / v2
- 不准围绕 validation 筛优

## Final Design Position

`v3` 的 implementation design 应被固定为：

- 先用锁定 base score source 定义 provisional TopK head
- 再用 `train window` 或 `expanding past data` 构造 historical head-quality estimates
- 再把历史 head quality 映射成有上界和下界的 `capital_deployment_multiplier`
- 最后输出 `raw_score_D0 / adjusted_score_D0 / capital_deployment_multiplier / head_quality_conditioning_source / conditioning_policy_version / leakage_audit_flags`

并且整个过程必须同时满足：

- 不改 feature list
- 不改 LightGBM 参数
- 不改 execution semantics
- 不改 terminal exit policy
- 不改 portfolio guard
