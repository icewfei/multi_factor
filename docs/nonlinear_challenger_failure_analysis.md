# Nonlinear Challenger Failure Analysis

## Scope

本文档只解释为什么 `confirmed5` 与 `nonlinear_challenger_v2` 都能在 model-layer 看到正向 edge，但在 portfolio-layer same-contract comparison 中没有超过 `multi_equal_weight_v1`。本文档不做新实验，不跑回测，不生成新的 metrics/readout，不读取 frozen test。

## Evidence Boundary

- `confirmed5` 的 portfolio-layer 证据来自已经完成的 same-contract baseline comparison。
- `v2` 的 portfolio-layer 证据来自 exact shared panel 上的 same-panel same-contract comparison。
- `confirmed5` 在当前 exact shared panel 上还有 `6` 个 hard blocker，但这不改变本分析的主结论。
- 本文档讨论的是 trainval research evidence，不是 OOS，不是 frozen test。

## Result Summary

### Model-Layer

模型层读数说明，两条 nonlinear challenger 都不是“完全没有预测信息”的失败。

| Candidate | Window | RankIC | ICIR | Top-Bottom Spread | Coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| confirmed5 | Train | 0.0573 | 0.4143 | 0.0062 | 0.9453 |
| confirmed5 | Validation | 0.0343 | 0.2835 | 0.0037 | 0.9295 |
| v2 | Train | 0.0623 | 0.4559 | 0.0034 | 0.9453 |
| v2 | Validation | 0.0692 | 0.5198 | 0.0043 | 0.9295 |
| baseline | Train | 0.0685 | 0.5944 | 0.0078 | 0.9453 |
| baseline | Validation | 0.0564 | 0.5246 | 0.0048 | 0.9295 |

直接结论：

- `confirmed5 model-layer 有正 edge`
- `v2 model-layer 结果为正`
- `v2` 没有明显损坏 confirmed5 的 model-layer edge
- 但 baseline 在 model-layer 也并不弱，尤其 train RankIC / ICIR / spread 更强

### Portfolio-Layer

组合层读数说明，model-layer 的正向信息没有自然转化成比 baseline 更强的 TopK portfolio outcome。

| Candidate | Window | Total Equity | Relative Return | Relative IR | Avg Cash Weight | Avg Invested Weight | Avg Turnover Daily |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| confirmed5 | Train | 2.2273 | 0.0935 | 0.3835 | 0.7502 | 0.2498 | 0.1178 |
| confirmed5 | Validation | 2.0093 | -0.2156 | -1.7221 | 0.7526 | 0.2474 | 0.1218 |
| v2 | Train | 1.8865 | 0.0047 | -0.1216 | 0.7864 | 0.2136 | 0.0991 |
| v2 | Validation | 2.1394 | -0.1511 | -1.0644 | 0.7996 | 0.2004 | 0.0997 |
| baseline | Train | 9.8817 | 0.1114 | 0.4539 | 0.7786 | 0.2214 | 0.1043 |
| baseline | Validation | 11.7977 | -0.1359 | -1.0600 | 0.7896 | 0.2104 | 0.1048 |

直接结论：

- `confirmed5 portfolio-layer same-contract comparison 弱于 baseline`
- `v2 portfolio-layer 未超过 baseline`
- `v2` 虽然把 validation drawdown 稍微压低，但没有把组合层相对收益推到 baseline 之上
- 因此两条 challenger 都不能晋级

## Failure Analysis

### 1. Model Edge 没有自然转化成 TopK Portfolio Edge

这件事也可以直接表述为：`model edge 不能自然转化成 TopK Portfolio Edge`。

这里最核心的问题不是“模型完全没信号”，而是“有信号，但信号没有在 TopK portfolio contract 下变成更强的组合层结果”。

- RankIC / ICIR 是全截面排序统计，不等于 TopK 持仓收益统计。
- decile spread 为正，说明排序有方向性，但 TopK 只消费排序最前端的很小一段。
- 一旦最前端名字的收益密度、换手路径、退出路径、持仓重叠形态不如 baseline，组合层就可能输掉。

也就是说，`score 排序改善不等于持仓收益改善`。  
这正是 confirmed5 与 v2 的共同失败模式。

### 2. Positive RankIC 不保证 Top Decile Head 足够强

`confirmed5` 和 `v2` 的 model-layer 正结果更多说明“平均排序方向正确”，但不自动说明：

- TopK 头部名字比 baseline 更强
- TopK 头部名字更稳定
- TopK 头部名字在 portfolio contract 下更容易被有效部署

尤其是：

- `v2` validation RankIC 明显高于 confirmed5
- 但 `v2` validation portfolio relative return 仍然低于 baseline

这说明 improvement 更可能发生在 broader ranking shape，而不是足以压过 baseline 的 deployed head quality。

### 3. High Cash / Low Deployed Capital 会压缩 Edge 转化

两条 nonlinear challenger 的平均现金权重都不低：

- confirmed5 validation `avg_cash_weight=0.7526`
- v2 validation `avg_cash_weight=0.7996`
- baseline validation `avg_cash_weight=0.7896`

这意味着：

- 大部分资金时间并没有部署在风险资产上
- model edge 只能作用在较小的 deployed sleeve 上
- 即使 selection 有正向信息，传导到 total equity 的幅度也会被现金占比稀释

因此，这不是单纯的“模型会不会排序”的问题，还包含一个更本质的问题：  
`deployed capital 口径下的 edge capture 是否足够强`

### 4. Volatility Discount 降低了回撤，但也降低了收益捕获

`v2` 的固定 volatility discount 针对的是组合层转化损失。结果显示：

- validation max drawdown 从 confirmed5 的更差状态改善到接近 baseline
- validation turnover 也下降
- 但 validation relative return 仍然没有超过 baseline

这说明 volatility discount 的主要效果更像：

- 削弱高波动名字的暴露
- 平滑一部分组合路径
- 降低一部分 downside

但同时它也可能：

- 压低本来能提供更高收益弹性的高波动名字
- 让风险压缩快于 alpha 提升
- 最终变成“回撤稍好，但收益捕获也更弱”

因此，`v2` 没有解决根问题，只是把失败模式从“高波动部署下的弱转化”变成了“更保守但仍未超过 baseline”。

### 5. Baseline 本身在 Portfolio-Layer 很强

这轮 nonlinear challenger 的对手不是一个脆弱基线，而是一个组合层很强的 baseline。

baseline 的特点是：

- model-layer 本身不弱
- portfolio-layer total equity 显著更高
- relative return / relative IR 也更好
- invested capital 口径下的放大更明显

所以这不是“challenger 轻微落后于一个普通基线”，而是：

- baseline 自身就已经是高门槛
- challenger 必须在 portfolio construction contract 下给出更强的 deployed alpha capture
- 仅靠模型复杂度或轻量 score transformation，并不足以自然越过这个门槛

### 6. TopK / Holding Cohort / Capital Deployment 可能比模型更重要

当前证据更支持一个方向：  
下一轮的主要研究对象不应优先是“再把模型做复杂一点”，而应优先是：

- TopK 头部如何形成
- holding cohort 如何分摊和重叠
- capital deployment 如何决定 total equity 传导效率

原因很直接：

- confirmed5 和 v2 都证明“模型可以有 edge”
- 但它们也同时证明“模型 edge 不足以自动赢 portfolio”
- baseline 在 deployed capital 转化上更强

这说明当前瓶颈更像 portfolio construction / capital deployment contract，而不是模型表达能力本身。

## Wrong Moves To Avoid

接下来明确不能做的错误动作：

- 不围绕 validation 调 `v2` formula
- 不继续微调 `confirmed5`
- 不读取 frozen test
- 不把 `trainval dry-run` 当 `OOS`
- 不把 model-layer 正结果包装成 strategy approval

这些动作的问题在于，它们只会把当前失败解释成“再调一轮也许能过”，而不是承认研究结论已经足够清楚：  
当前 nonlinear challenger 的主要问题在 portfolio conversion，不在继续回抠 validation。

## Principles For A Future v3

这里不设计具体 `v3`，只固定下一轮应遵守的原则。

### 1. 先研究 Portfolio Construction / Capital Deployment

下一轮应优先研究：

- portfolio construction
- capital deployment
- TopK head formation
- holding cohort overlap

而不是先默认“模型更复杂就会更好”。

### 2. 不要盲目增加模型复杂度

当前证据并不支持“再加复杂度就能自然赢 baseline”。

更合理的方向是：

- 先理解组合层转化损失
- 再决定是否需要新的 model-layer 变化

### 3. 新 Challenger 必须预注册单一变更维度

如果继续 nonlinear research：

- 必须新建 challenger
- 必须新建 research round
- 必须新建 manifest
- 必须预注册单一主变更维度

不能再把多个变更维度混在一起做事后解释。

### 4. Same-Contract Baseline Comparison 是最低门槛

这条边界也可以直接写成：`same-contract baseline comparison 是最低门槛`。

后续任何 challenger：

- 都必须完成 same-contract baseline comparison
- 都必须在同 split、同 execution contract、同 terminal exit policy、同 portfolio construction rules 下比较
- 都必须优于 baseline，才有资格讨论晋级

## Final Status

- `confirmed5` 证明了 model-layer 正 edge 不足以推出 portfolio-layer 胜出。
- `v2` 证明了轻量 portfolio-aware score transformation 也不足以自然超过 baseline。
- 当前 nonlinear challenger family 的失败不是“完全没信号”，而是“信号没有成功转化为更强的组合层优势”。
- 因此，下一轮如果继续，应把主要研究重心放在 portfolio construction / capital deployment，而不是继续围绕 confirmed5 或 v2 做 validation 驱动的微调。
