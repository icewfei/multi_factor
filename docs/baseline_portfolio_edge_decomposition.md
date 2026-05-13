# Baseline Portfolio Edge Decomposition

## Scope

本文档只记录 `baseline vs confirmed5 / v2` 的 trainval research diagnosis。本文档不训练，不回测，不读取 frozen test，不把 trainval 当 OOS，不生成正式策略结论，也不直接推出任何 `v4` 方案。

## Boundary

- 这是 `trainval research diagnosis`，不是 `OOS`
- 不读取 frozen test
- 不生成 formal metrics/readout
- 不把 trainval 当 OOS
- 不训练
- 不回测

## What The Diagnosis Can Explain

这轮 baseline 的优势，至少有几条可观察证据已经比较清楚。

### 1. Baseline 更像赢在 selected-head quality

validation TopK realized return 诊断里，baseline 的头部收益分布整体强于两条 nonlinear：

- baseline validation TopK realized return mean 约 `0.51%`
- confirmed5 validation TopK realized return mean 约 `0.49%`
- v2 validation TopK realized return mean 约 `0.30%`
- baseline 的 validation median / positive-rate 也强于 confirmed5

这说明 baseline 不是单纯靠 full-cross-section 排序统计在赢，更像是：

- `TopK deployed head` 更稳定
- 中位数更好
- 头部 realized return 更容易转成组合层结果

### 2. Confirmed5 更像输在高 churn + 左尾更重

confirmed5 的可观察特征是：

- validation TopK replacement ratio 约 `0.96`
- baseline validation TopK replacement ratio 约 `0.66`
- confirmed5 与 baseline 的 validation 同日 TopK overlap 很低，平均只有约 `0.24 / 10`
- confirmed5 有更大的单笔大盈利，但同时也伴随更重的亏损左尾和更弱的中位数

这更像：

- `head quality` 不够稳
- `churn` 很高
- `tail loss` 更重

而不是“只要再多投一些资金就能赢”。现有 same-contract readout 里，confirmed5 的 `avg_invested_weight` 还高于 baseline，但仍然输给 baseline。

### 3. v2 更像输在保守化后的收益捕获不足

v2 的可观察特征和 confirmed5 不同：

- validation TopK replacement ratio 约 `0.19`，显著低于 baseline
- validation 与 baseline 的同日 TopK overlap 更低，约 `0.05 / 10`
- v2 的头部波动、流动性和 turnover proxy 都被压得更低
- same-contract readout 显示 v2 validation `avg_invested_weight` 低于 baseline

所以 v2 的失败不像主要来自 `churn`，更像：

- `selected-head quality` 仍弱于 baseline
- `cash deployment / invested_weight` 更保守
- score-to-TopK 转化没有补足收益捕获

这也解释了为什么“更低 churn”本身并没有让 v2 打赢 baseline。

### 4. Daily relative win/loss 只提供弱正向支持，不足以包装成稳定 OOS edge

validation 日度对比里：

- baseline 对 confirmed5 的胜率只略高于 `50%`
- baseline 对 v2 的胜率也只略高于 `50%`
- 但 baseline 的日均相对优势仍为正

这说明 baseline 的优势更像：

- `持续但不极端`
- 能在头部 realized return 上积累出正的平均差

但现有 trainval 证据还不足以把它包装成稳定 OOS 组合优势结论。

## Observable Exposure Differences

当前 trainval 诊断里，以下字段是可观察的：

- `market_cap`
- `liquidity`
- `volatility`

可观察结论大致是：

- confirmed5 头部更偏高波动、高成交、高换手名字
- baseline 头部更偏更大市值、较低波动名字
- v2 被 volatility discount 压向了更低波动、低换手、低成交的一侧

这些暴露差异能解释部分 portfolio-layer 结果，但还不能单独证明 baseline 存在完整而稳定的 portfolio construction edge。

## Not Enough Evidence Yet

以下证据当前仍然不足或不可得：

- `industry` 暴露：当前输入不可得
- `concentration` 证据：当前任务未读取 holdings/weights/concentration artifacts，因此不可得
- 纯粹由 portfolio construction 而非 selected-head quality 独立贡献的定量拆分：证据仍不足
- 把当前 trainval 诊断直接上升为正式策略判断：不允许

## Research Implication

当前更合理的下一步问题是：

- 是否还需要继续研究 `portfolio construction / capital deployment`

在当前证据下，答案是：`如果继续 nonlinear 研究，这仍然值得继续查`。  
但这只意味着研究问题还存在，不意味着现在就应该直接设计新 challenger。

本文档明确不推出 `v4`，也不把这份 diagnosis 当成新的 challenger 立项说明。
