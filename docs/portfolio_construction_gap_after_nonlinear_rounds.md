# Portfolio Construction Gap After Nonlinear Rounds

## Scope

本文档用于总结 `confirmed5`、`nonlinear_challenger_v2` 与 `multi_equal_weight_v1` 在 nonlinear rounds 结束后的 portfolio construction gap 研究结论。本文档只汇总已有 trainval dry-run 与 gap diagnosis 证据，不跑新实验，不生成新的 metrics/readout，不读取 frozen test，不设计具体 `v3` 参数。

## Round Summary

当前 nonlinear rounds 的收口状态已经固定：

- `confirmed5` 已拒绝晋级
- `v2` 已拒绝晋级
- 两条 nonlinear challenger 都不是“模型完全没信号”
- 真正失败的位置在 `model score -> TopK portfolio` 的转化机制

## Core Comparison

### Model-Layer

模型层结论并不差：

| Candidate | Validation RankIC | Validation ICIR | Validation Spread |
| --- | ---: | ---: | ---: |
| confirmed5 | 0.0343 | 0.2835 | 0.0037 |
| v2 | 0.0692 | 0.5198 | 0.0043 |
| baseline | 0.0564 | 0.5246 | 0.0048 |

直接含义：

- `confirmed5 model-layer 有正 edge`
- `v2 model-layer 结果为正`
- `v2` 的 validation model-layer 甚至强于 confirmed5

### Portfolio-Layer

组合层结论完全不同：

| Candidate | Validation Total Equity | Validation Relative Return | Validation Relative IR | Avg Cash Weight | Avg Invested Weight | Avg Turnover Daily |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| confirmed5 | 2.0093 | -0.2156 | -1.7221 | 0.7526 | 0.2474 | 0.1218 |
| v2 | 2.1394 | -0.1511 | -1.0644 | 0.7996 | 0.2004 | 0.0997 |
| baseline | 11.7977 | -0.1359 | -1.0600 | 0.7896 | 0.2104 | 0.1048 |

selected-head realized return 也说明 baseline 更强：

- confirmed5 validation selected-head realized return mean: `0.4888%`
- v2 validation selected-head realized return mean: `0.3606%`
- baseline validation selected-head realized return mean: `0.5073%`

## Failure Summary

### 1. Nonlinear model-layer edge 没有转成 TopK portfolio edge

这是本轮最重要的研究结论。

- RankIC / ICIR 是 full cross-section 排序统计
- portfolio 只消费 TopK head
- full cross-section 的排序改善，没有自动变成 deployed head 的 realized return 优势

所以本轮失败不是“模型没有信号”，而是：

- `nonlinear model-layer edge 没有转成 TopK portfolio edge`

### 2. confirmed5 高 churn 且 head quality 不够强

confirmed5 的验证期特点是：

- `avg_turnover_daily = 0.1218`
- TopK set turnover 高于 baseline
- validation selected-head realized return mean 低于 baseline
- relative return / relative IR 明显弱于 baseline

因此 confirmed5 的失败更像：

- `高 churn`
- `head quality 不够强`

而不是单纯因为 invested weight 不够。

### 3. v2 降低风险但牺牲收益捕获

`v2` 的 volatility discount 确实带来了一些效果：

- 换手低于 confirmed5
- validation drawdown 明显好于 confirmed5
- relative return 也比 confirmed5 好

但它的问题是：

- validation `avg_invested_weight` 下降到 `0.2004`
- validation selected-head realized return mean 下降到三者最低
- 最终仍然没有超过 baseline

所以 `v2` 的更准确描述是：

- `降低风险`
- `降低 churn`
- `但牺牲了收益捕获`

### 4. baseline 的 selected-head realized return 更强

这轮 baseline 的优势更像是 deployed head quality，而不是简单的资金占用。

原因很明确：

- confirmed5 validation `avg_invested_weight` 比 baseline 更高
- 但 confirmed5 的 total equity 和 relative return 更差
- baseline validation selected-head realized return mean 仍然更高

这说明 baseline 不是靠“投得更多”在赢，而是更像靠：

- `selected-head realized return 更强`
- `portfolio conversion 更有效`

## Research Implication

当前证据不支持下一轮继续堆模型复杂度。

更合理的解释是：

- baseline 的优势主要在 portfolio construction / capital deployment 转化
- nonlinear challenger 的主要短板不是缺少 RankIC
- 而是缺少把 ranking edge 变成 deployed TopK alpha 的机制

因此，下一轮如果启动 `v3`：

- 不应继续盲目增加模型复杂度
- 不应继续围绕 confirmed5 或 v2 做 validation 驱动的微调
- 应优先围绕 `portfolio construction / capital deployment`

## Boundary

本文档明确固定以下边界：

- 不跑回测
- 不生成 metrics/readout
- 不读取 frozen test
- 不把 trainval dry-run 当 OOS
- 不设计具体 `v3` 参数

如果未来启动 `v3`：

- 必须新建 challenger
- 必须新建 research round
- 必须预注册单一主变更维度
- 必须把 same-contract baseline comparison 作为最低门槛

## Final Status

- nonlinear rounds 的主要失败已经定位到 `portfolio construction gap`
- `confirmed5` 和 `v2` 都不应继续沿模型复杂度方向微调
- 若继续研究，优先方向应是 `portfolio construction / capital deployment`
