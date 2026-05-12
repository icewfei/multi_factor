# Nonlinear Challenger v3 Manifest Notes

## Purpose

本文档只记录 `nonlinear_challenger_v3` draft manifests 的治理边界。本文档不授权实现、不授权训练、不授权回测，也不生成任何新的 metrics/readout。

## Bound IDs

- `research_round_id`: `rr_nonlinear_challenger_v3_topk_head_quality_conditioned_capital_deployment_20260512`
- `candidate_scheme_id`: `nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42`
- `feature_set_id`: `nlc_v3_fset01_confirmed5_locked_inputs`
- `model_config_id`: `nlc_v3_lgbm_regressor_depth3_seed42_locked_hparams_topk_head_quality_conditioned_capital_deployment`

## Governance Position

- `confirmed5` 已封口，不允许续调。
- `v2` 已封口，不允许续调。
- `v3` 是新的 research round，不是 `confirmed5` 或 `v2` 的延伸改参。
- `v3` 当前只建立 manifest 框架和测试守卫，后续若要实现，必须先通过治理审查。

## Single Primary Change Dimension

`v3` 只允许一个主变更维度：

- `topk_head_quality_conditioned_capital_deployment`

该定义意味着：

- 不改 model input features
- 不改 LightGBM hyperparameters
- 不改 execution semantics
- 不改 terminal exit policy
- 不改 portfolio guard

## Promotion Gates

未来若进入实现后评估，晋级门槛必须同时满足：

- model-layer 不明显劣化
- TopK head quality 必须改善
- same-contract portfolio comparison 必须优于 baseline
- total equity / invested capital / cash / turnover 必须同时报告

## Fail-Fast Guardrails

以下任一情况出现，`v3` 不得推进：

- 无 baseline same-contract comparison
- TopK head quality 未改善
- 高现金口径未披露
- terminal exit flags 不完整
- 读取 `frozen_test` 或 `fixed_test`
- manifest validator 或 pytest manifest checks 未通过

## Allowed Readouts

`allowed_readouts` 只允许：

- `train_*`
- `validation_*`

不允许：

- `test_*`
- `frozen_test_*`
- 任何脱离 train/validation 口径的 readout
