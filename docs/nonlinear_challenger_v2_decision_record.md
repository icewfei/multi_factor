# Nonlinear Challenger v2 Decision Record

## Scope

本记录用于固定 `nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42` 在当前研究轮的决策结论。本文档只汇总已经生成的 trainval 研究证据，不新增实验，不跑回测，不生成新的 metrics/readout，不读取 frozen test。

## Locked Candidate

- Research round: `rr_nonlinear_challenger_v2_cs_volatility_discount_20260509`
- Candidate: [candidate_nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v2/candidates/candidate_nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42.json)
- Feature set: [feature_set_nlc_v2_fset01_confirmed5_locked_inputs.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v2/feature_sets/feature_set_nlc_v2_fset01_confirmed5_locked_inputs.json)
- Model config: [model_config_nlc_v2_lgbm_depth3_seed42_cs_volatility_discount_v1.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v2/model_configs/model_config_nlc_v2_lgbm_depth3_seed42_cs_volatility_discount_v1.json)
- Frozen-test access: `false`

## Single Primary Change Dimension

`v2` 的单一主变更维度是：

- `portfolio_aware_cross_sectional_score_transformation`

固定合同为：

- `adjusted_score_D0 = raw_model_score_percentile_rank_D0 * (1.0 - volatility_20d_percentile_rank_D0)`

该变更维度的含义是：

- 不重训 confirmed5 LightGBM
- 不修改 confirmed5 feature set
- 不修改 execution / portfolio guard
- 只在 post-score 层引入固定、不可调参的 cross-sectional volatility discount

## Evaluation Chain

### 1. Design / Manifest Guardrails

- `v2` 是新 challenger，不是 confirmed5 续调。
- candidate / feature_set / model_config 已预注册，并且显式绑定 `frozen_test_access=false`。
- `v2` 的晋级门槛已写死：same-contract portfolio comparison 必须优于 `multi_equal_weight_v1`，否则不得晋级。

### 2. Score Transformation

- 证据文件：
  [score_transform_audit.json](/private/tmp/local_nlc_v2_confirmed5_locked_cs_volatility_discount_20260509/score_transform_audit.json)
- 本轮执行的是 fixed transformer，不是重新训练。
- `training_performed=false`
- `frozen_test_accessed=false`
- transformed score 生成后：
  - `row_count=10558258`
  - `null_score_rows=0`
  - `nonfinite_score_rows=0`

### 3. Model-Layer Diagnosis

- 证据文件：
  [nonlinear_challenger_v2_model_edge_diagnosis.json](/private/tmp/nonlinear_challenger_v2_model_edge_diagnosis.json)
  [nonlinear_challenger_v2_model_edge_diagnosis.md](/private/tmp/nonlinear_challenger_v2_model_edge_diagnosis.md)
- 当前轮模型层结论是：`v2 model-layer 结果为正`。
- 关键结论：
  - validation `RankIC=0.0692`
  - validation `ICIR=0.5198`
  - `materially_damages_confirmed5_model_edge=false`
  - `eligible_for_portfolio_dry_run`
- 这说明 `v2` 没有明显损坏 confirmed5 的 model-layer edge。

### 4. Portfolio Dry-Run

- `v2` 在 exact shared panel 上自然通过 portfolio guard。
- 证据文件：
  [nlc_v2_vs_baseline_same_contract_v3_readout.json](/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.json)
  [nlc_v2_vs_baseline_same_contract_v3_readout.md](/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.md)
  [nonlinear_challenger_v2_same_contract_portfolio_status.json](/private/tmp/nonlinear_challenger_v2_same_contract_portfolio_status.json)
  [nonlinear_challenger_v2_same_contract_portfolio_status.md](/private/tmp/nonlinear_challenger_v2_same_contract_portfolio_status.md)
- 读数标签仍然属于 trainval portfolio dry-run，不是 frozen test，不是 formal strategy readout。

### 5. Same-Panel Same-Contract Baseline Comparison

- 比较口径为：
  - 同 train / validation split
  - 同 execution contract
  - 同 terminal exit policy
  - 同 portfolio construction rules
  - 同 cash / invested capital 口径
- 当前轮组合层结论是：`v2 portfolio-layer 未超过 baseline`。

| Window | Metric | v2 | Baseline |
| --- | --- | ---: | ---: |
| Train | final total equity | 1.8865 | 9.8817 |
| Train | invested capital | 21.6173 | 24370.4685 |
| Train | avg invested weight | 0.2136 | 0.2214 |
| Train | relative return | 0.0047 | 0.1114 |
| Train | relative IR | -0.1216 | 0.4539 |
| Validation | final total equity | 2.1394 | 11.7977 |
| Validation | invested capital | 39.8618 | 52850.4274 |
| Validation | avg invested weight | 0.2004 | 0.2104 |
| Validation | relative return | -0.1511 | -0.1359 |
| Validation | relative IR | -1.0644 | -1.0600 |

- validation drawdown 虽然略好于 baseline，但这不构成晋级依据。
- 按预注册门槛，`v2` 没有超过 baseline，因此不能晋级。

### 6. Confirmed5 Blocker Note

- confirmed5 在当前 exact shared panel 上仍有 `6` 个 hard blocker。
- 这件事需要单独记录，但它不改变 `v2` 自身的晋级判断。
- `v2` 的决策依据仍然是：model-layer 正向，但 portfolio-layer same-contract comparison 未超过 baseline。

## Decision

- `v2 model-layer 结果为正`
- `v2 portfolio dry-run 自然通过`
- `v2 portfolio-layer 未超过 baseline`
- `v2 不晋级`
- `v2 不建议进入 confirmatory / shadow`
- `不允许继续围绕 validation 调 v2 formula`

当前 research decision 到此冻结。`v2` 可以保留为一个完成过 model-layer 与 portfolio-layer 审计的 challenger，但不能继续被包装成晋升候选。

## Prohibited Statements

本文档明确禁止以下表述：

- 不能说 `策略有效`
- 不能说 `OOS 通过`
- 不能说 `可以实盘`
- 不能把 `trainval dry-run` 当 `OOS`
- 不能把 `trainval dry-run` 当 `fixed/frozen test`
- 不能把 model-layer 正结果改写成 portfolio-layer 胜出
- 不能因为 confirmed5 当前 shared-panel blocker 就弱化 `v2 未超过 baseline` 这一结论

## Next-Step Boundary

- 不允许继续围绕 validation 调 `v2` formula。
- 不允许继续在 `v2` 上做 validation 结果驱动的反复筛优。
- 不允许读取 frozen test。
- 如果继续 nonlinear research，必须新建 challenger。
- 如果继续 nonlinear research，必须新建 research round。
- 如果继续 nonlinear research，必须新建 manifest。
- 后续 challenger 仍然必须通过 same-contract baseline comparison，并且结果必须优于 baseline。

## Final Status

- 本轮结论是负向研究收口结论，不是策略宣传材料。
- 本轮证据全部属于 trainval 研究层，不是 OOS，不是 frozen test 结论。
- `v2` 在本轮到此止步，不进入 confirmatory / shadow。
