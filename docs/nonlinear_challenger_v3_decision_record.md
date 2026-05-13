# Nonlinear Challenger v3 Negative Decision Record

## Scope

本记录用于固定 `nonlinear_challenger_v3` 的负向决策结论。本文档只汇总已经存在的 trainval research evidence，不训练模型，不跑 portfolio，不生成新的 formal metrics/readout，不读取 frozen test，不把 trainval diagnosis 当 OOS。

## Locked Scope

- Candidate: `nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42`
- Evidence package: `score builder` + `source binding` + `real trainval score-layer gate` + `model-layer diagnosis`
- Frozen-test access: `false`
- Portfolio dry-run executed: `false`

## Evidence Chain

### 1. v3 Score Builder 通过

- `v3_score_builder_audit` 已确认：
  - `training_performed=false`
  - `frozen_test_accessed=false`
  - `portfolio_outputs_generated=false`
- 当前结论固定为：`v3 score builder 通过`

### 2. Source Binding 通过

- `source_binding_id = nlc_v3_score_source_binding_v1`
- source binding disclosure 已明确：
  - 该 binding 只授权 `score-layer inputs`
  - 不授权 `portfolio / holdings / metrics / readout / frozen test`
- 当前结论固定为：`source binding 通过`

### 3. Real Score-Layer Gate 通过

- `conditioning_source` 已存在并完成 trainval score-layer gate 审计。
- 当前轮 gate 的作用只是确认：
  - score-layer package 可被审计
  - trainval-only conditioning source 可被披露
  - 不存在 frozen test 消耗
- 当前结论固定为：`real score-layer gate 通过`

### 4. Model-Layer Diagnosis 失败

`v3` 的失败发生在 model-layer diagnosis，而不是 score builder / source binding / score-layer gate。

validation 关键读数如下：

| Candidate | RankIC | ICIR | Top-Bottom Spread |
| --- | ---: | ---: | ---: |
| v3 | 0.0042 | 0.0960 | -0.0010 |
| confirmed5 | 0.0117 | 0.1201 | 0.0064 |
| v2 | 0.0692 | 0.5199 | 0.0043 |
| baseline | 0.0564 | 0.5246 | 0.0049 |

固定结论：

- `model-layer diagnosis 失败`
- `validation RankIC / ICIR 明显低于 v2 / baseline`
- `validation top-bottom spread 为负`

这说明：

- `v3` 没有把 score-layer 包装转化成可接受的 validation model-layer edge
- `v3` 不能被表述为相对 `v2` 或 `baseline` 的改进

## Decision

当前轮负向决策必须固定为：

- `v3 score builder 通过`
- `source binding 通过`
- `real score-layer gate 通过`
- `model-layer diagnosis 失败`
- `validation RankIC / ICIR 明显低于 v2 / baseline`
- `validation top-bottom spread 为负`
- `不进入 portfolio dry-run`
- `不进入 confirmatory / shadow`

`v3` 到此收口，不允许再把它包装成等待 portfolio 验证的候选。

## Prohibited Moves

本文档明确禁止以下动作和表述：

- `不允许围绕 validation 调 v3 formula`
- `不允许读取 frozen test`
- `不允许把 trainval diagnosis 当 OOS`
- 不能说 `v3 只差 portfolio 验证`
- 不能说 `v3 可以进入 confirmatory / shadow`
- 不能把 score-layer gate 通过改写成 model-layer 通过

## Boundary

当前边界固定如下：

- `不训练`
- `不回测`
- `不读取 frozen test`
- `不把 trainval diagnosis 当 OOS`
- `不围绕 validation 调 v3 formula`
- `不进入 portfolio dry-run`
- `不进入 confirmatory / shadow`

## Final Status

- `v3` 是一次完成了 score builder / source binding / score-layer gate 审计，但在 model-layer diagnosis 明确失败的 challenger。
- 本记录是负向研究收口，不是 OOS，不是 frozen test，不是 formal strategy conclusion。
