# Current Project Status After Confirmed5

## Status Summary

在 `nlc_v1_confirmed5_lgbm_depth3_seed42` 完成当前轮研究评估后，项目状态可以收敛为：

```text
status: confirmed5_closed_without_promotion
confirmed5_model_layer: positive_edge
confirmed5_execution_layer: passed
confirmed5_portfolio_dry_run: passed
confirmed5_same_contract_vs_baseline: weaker_than_baseline
promotion_decision: do_not_enter_confirmatory_or_shadow
next: new_challenger_only_under_new_research_round
```

本文档只整理当前已经形成的研究状态，不新增实验，不生成新的 metrics/readout，不读取 frozen test。

## Confirmed5 Evaluation Conclusion

当前轮 `confirmed5` 的结论已经固定：

- `model-layer 有正 edge`
- `execution-layer 通过`
- `portfolio dry-run 通过`
- `same-contract baseline comparison 弱于 baseline`
- 决策：`不晋级 confirmatory / shadow`

这里的关键含义是：

- confirmed5 不是因为工程链路没打通而停下。
- confirmed5 也不是因为 model-layer 完全失效而停下。
- confirmed5 停下的原因是：在同口径 portfolio comparison 下，结果弱于 `multi_equal_weight_v1`，因此不满足晋级条件。

## Prohibited Actions

confirmed5 收口后，当前项目明确禁止以下事项：

- 不允许继续调 `confirmed5`
- 不允许围绕 validation 结果反复筛优
- 不允许读取 frozen test
- 不允许把 trainval dry-run 当 OOS
- 不允许宣称策略有效

进一步说：

- 不允许把 model-layer 正 edge 包装成 portfolio-layer 胜出。
- 不允许把 execution unblock 包装成 strategy approval。
- 不允许把一次 trainval 相对弱势结果，再通过局部调参重新叙述成候选仍可晋级。

## Mature Infrastructure

截至 confirmed5 收口，本轮已经成熟并可复用的基础设施包括：

### 1. Terminal Exit Blocker Resolution

- terminal exit blocker 已经有正式 resolution 路径。
- 该路径支持在同一 execution contract 下处理 terminal event unresolved rows。
- 该路径已经用于同口径 confirmed5 / baseline portfolio unblock。

### 2. Repaired Terminal Event Candidate

- repaired terminal event candidate 已具备独立审计与审批链路。
- candidate 不等于直接补价，而是为 execution path 提供受控上游输入。
- 该机制已经与 terminal policy、approval flags、audit breadcrumb 对齐。

### 3. Run-State Acceptance

- run_state acceptance 已具备 formal validation 能力。
- 可检查 ranking / execution row alignment、TopK cap、entry fill contract、一致性约束。
- 这使得 challenger 和 baseline 都可以在相同 contract 下进入后续组合层。

### 4. Portfolio Dry-Run Artifacts

- portfolio dry-run artifacts 已形成稳定输出。
- 包括 holdings、daily summary、turnover、cash / invested capital 路径。
- 组合层 guard 已经能在不绕过 unresolved blocker 的前提下自然判定通过或失败。

### 5. Model Edge Diagnosis

- model edge diagnosis 已经独立于 portfolio readout 固化。
- 它可以回答 model-score 层是否存在可审计 edge。
- 它不会自动推导 portfolio valid，也不会替代 portfolio comparison。

### 6. Baseline Same-Contract Comparison

- baseline same-contract comparison 已经成为标准比较层。
- 这一步要求同 split、同 execution contract、同 terminal exit policy、同 portfolio rule。
- 现在它不再是可选分析，而是 challenger 晋级前的正式门槛之一。

## What The Project Knows Now

confirmed5 收口后，项目当前已经知道：

- 非线性 challenger 可以在受控 manifest 下完成训练与审计。
- model-layer 的正 edge 不足以推出 portfolio-layer 晋级。
- execution-layer 闭环后，portfolio-layer 才能被同口径比较。
- same-contract comparison 才是判断 challenger 是否真正优于 baseline 的关键闸门。
- `multi_equal_weight_v1` 仍然是当前需要被 challenger 正面超过的最低组合层基线。

## Entry Conditions For The Next Challenger

如果要继续下一轮 challenger，进入条件必须重新满足，而不是沿用 confirmed5：

- 必须新建 `research_round_id`
- 必须新建 manifests
- 必须预注册变更维度
- 必须完成 same-contract comparison
- 必须在 same-contract comparison 中优于 baseline，才允许讨论晋级

这意味着：

- 不能在 `confirmed5` 旧 round 上续写研究。
- 不能在 `confirmed5` 旧 manifest 上继续改参数。
- 不能跳过 baseline comparison 直接谈 confirmatory / shadow。

## Final Project Status

当前项目状态不是“confirmed5 成功晋级”，而是：

- confirmed5 作为一个研究 challenger，完成了从 manifest 到 portfolio comparison 的完整评估链路。
- 这条链路产出了可复用基础设施和清晰的研究边界。
- confirmed5 本身不晋级。
- 后续如要继续 nonlinear research，必须以新 challenger 的形式重新立项。
