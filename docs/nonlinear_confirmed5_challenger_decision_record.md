# Nonlinear Confirmed5 Challenger Decision Record

## Scope

本记录用于固定 `nlc_v1_confirmed5_lgbm_depth3_seed42` 在当前研究轮的结论边界。本文档只总结已经生成的 trainval 研究证据，不新增实验，不生成新的 metrics/readout，不读取 frozen test。

## Locked Candidate

- Research round: `rr_nonlinear_challenger_v1_confirmed5`
- Candidate: [candidate_nlc_v1_confirmed5_lgbm_depth3_seed42.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_confirmed5_lgbm_depth3_seed42.json)
- Feature set: [feature_set_nlc_v1_fset01_confirmed5.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01_confirmed5.json)
- Model config: [model_config_nlc_v1_lgbm_depth3_seed42.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json)
- Confirmed5 feature list: `reversal_5d`, `cord30`, `corr30`, `vsumd60`, `volatility_20d`
- Frozen-test access: `false`

## Evaluation Chain

### 1. Manifest / Confirmed5 Feature Set

- `confirmed5` 是受限 challenger，不是开放搜索配置。
- 候选和 feature set 预注册在同一 research round 下，并且显式绑定 `frozen_test_access=false`。
- 当前 candidate 允许的证据层级是 train / validation 研究读数，不允许把本轮证据上升为 frozen/fixed test 结论。

### 2. Model Score Training

- 训练配置固定在 [model_config_nlc_v1_lgbm_depth3_seed42.json](/Users/wy/MiscProject/multi_factor/configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json)。
- 当前轮的 model score 训练与审计产物为：
  [model_scores_D0.parquet](/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_reversal_p98_trainval_20260506/model_scores_D0.parquet)
  [model_scores_D0_audit.json](/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_reversal_p98_trainval_20260506/model_scores_D0_audit.json)
- 本记录接受该训练链路已完成且可审计，不在 confirmed5 上继续做围绕 validation 的参数回抠。

### 3. Model Edge Diagnosis

- 证据文件：
  [model_edge_diagnosis.json](/private/tmp/model_edge_diagnosis.json)
  [model_edge_diagnosis.md](/private/tmp/model_edge_diagnosis.md)
- 当前轮模型层结论是：`confirmed5 model-layer 有正 edge`。
- 直接证据包括：
  - train RankIC `0.0573`
  - validation RankIC `0.0343`
  - train ICIR `0.41`
  - validation ICIR `0.28`
  - 诊断结论中 `has_model_edge=true`
- 该结论只属于 model-score 层，不等于 portfolio 层胜出。

### 4. Execution Blocker Resolution

- terminal blocker 处理沿用了与 baseline 相同的 terminal policy / approval / repaired candidate 路径，不存在 confirmed5 特判。
- 证据文件：
  [combined_same_contract_terminal_approval.json](/private/tmp/combined_same_contract_terminal_approval.json)
  [combined_same_contract_repaired_candidate.json](/private/tmp/combined_same_contract_repaired_candidate.json)
- 本轮 shared approval 摘要：
  - total rows `33`
  - candidate rows `33`
  - approval passed `33`
  - bridge-required rows `14`
  - zero-recovery approved `0`
- 本记录接受执行层结论为：`execution-layer 已通过`。含义是 portfolio dry-run 所需的 terminal exit resolution 已经在同一套 contract 下闭环，不需要再把 unresolved rows 下推给组合层兜底。

### 5. Portfolio Dry-Run Validation Readout

- 证据文件：
  [nonlinear_confirmed5_validation_readout.json](/private/tmp/nonlinear_confirmed5_validation_readout.json)
  [nonlinear_confirmed5_validation_readout.md](/private/tmp/nonlinear_confirmed5_validation_readout.md)
- 读数标签已明确写明：
  `TRAINVAL PORTFOLIO DRY-RUN ESTIMATE ONLY — NOT FROZEN TEST — NOT A FORMAL STRATEGY CONCLUSION`
- 当前轮 portfolio-layer 读数显示：
  - validation `final_total_equity_estimate=2.0093`
  - validation `annual_relative_return_trainval_dry_run_estimate=-0.2156`
  - validation `relative_ir_estimate=-1.7221`
  - overall average invested weight `0.2492`
  - overall average cash weight `0.7508`
- 该读数说明 confirmed5 在 portfolio 层不是零收益失效，但 validation 相对 benchmark 明显偏弱。

### 6. Same-Contract Baseline Comparison

- 证据文件：
  [confirmed5_vs_baseline_same_contract_readout.json](/private/tmp/confirmed5_vs_baseline_same_contract_readout.json)
  [confirmed5_vs_baseline_same_contract_readout.md](/private/tmp/confirmed5_vs_baseline_same_contract_readout.md)
- 当前轮最终比较口径是：
  - 同 train / validation split
  - 同 execution contract
  - 同 portfolio construction rules
  - 同 cash / invested capital 口径
  - 同 terminal exit policy
- 结果上，confirmed5 在 same-contract portfolio comparison 中弱于 `multi_equal_weight_v1`。

| Window | Metric | Confirmed5 | Baseline |
| --- | --- | ---: | ---: |
| Train | final total equity | 2.2273 | 9.8817 |
| Train | avg invested weight | 0.2498 | 0.2214 |
| Train | avg turnover daily | 0.1178 | 0.1043 |
| Train | relative return | 0.0935 | 0.1114 |
| Train | relative IR | 0.3835 | 0.4539 |
| Validation | final total equity | 2.0093 | 11.7977 |
| Validation | avg invested weight | 0.2474 | 0.2104 |
| Validation | avg turnover daily | 0.1218 | 0.1048 |
| Validation | relative return | -0.2156 | -0.1359 |
| Validation | relative IR | -1.7221 | -1.0600 |

## Decision

- `confirmed5 model-layer 有正 edge`
- `execution-layer 已通过`
- `portfolio-layer same-contract comparison 弱于 baseline`
- `不建议进入 confirmatory / shadow`
- `不允许围绕 validation 继续调 confirmed5 参数`

当前 research decision 到此冻结。confirmed5 可以被保留为一个已经完成研究审计的 challenger，但不能继续被包装成晋升候选。

## Prohibited Statements

本文档明确禁止以下表述：

- 不能说 `策略有效`
- 不能说 `OOS 通过`
- 不能说 `可以实盘`
- 不能把 `trainval dry-run` 当 `fixed/frozen test`
- 不能把 model-layer 正 edge 改写成 portfolio-layer 胜出
- 不能把 execution unblock 改写成 strategy approval

## Next-Step Boundary

- 若继续 nonlinear research，必须新建 challenger。
- 若继续 nonlinear research，必须新建 research round。
- 若继续 nonlinear research，必须新建 manifest。
- 不能在 `confirmed5` 上继续围绕 validation 结果调参。
- 后续 challenger 至少要完成 same-contract baseline comparison。
- `multi_equal_weight_v1` 的 same-contract portfolio comparison 结果，已经成为后续 challenger 的最低门槛。

## Final Status

- 本轮结论是研究收口结论，不是策略宣传材料。
- 本轮证据全部属于 trainval 研究层，不是 frozen test 结论。
- confirmed5 在本轮到此止步，不进入 confirmatory / shadow。
