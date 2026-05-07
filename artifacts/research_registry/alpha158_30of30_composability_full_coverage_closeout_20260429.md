# Alpha158 30/30 Composability 全覆盖收口总结

## 一句话决策

`Alpha158 exact canonical` 的 `30 / 30 standalone positive(30/30 个单信号正向 keeper)`，现在已经全部完成相对 `price_volume_v18_refresh_hysteresis` 的 `composability screening(组合相容性筛查)`。

结论是：

- `composability_screen_promising(组合相容性较有希望) = 0 / 30`
- `composability_screen_mixed(组合相容性混合) = 30 / 30`

因此，**后续应停止这条“Alpha158 keeper 直接 overlay(覆盖层) 到 v18” 的微调线**。这些信号继续保留为 `standalone keepers(单信号保留)`，但不再进入当前 `v18` family 的下一轮 direct overlay 立项。

## 覆盖范围

三轮 composability screening 已全部完成：

1. `rr_alpha158_exact_keeper_composability_screen_20260428`
2. `rr_alpha158_exact_keeper_composability_screen_round2_20260428`
3. `rr_alpha158_exact_keeper_composability_screen_round3_20260429`

合计覆盖 `30` 个 exact Alpha158 positive keepers，已经实现对当前 canonical positive 池的 `100%` 全覆盖。

## 总结果概览

### 结果计数

- `screened_positive_keepers(已筛正向keeper数) = 30`
- `promising_count(较有希望数量) = 0`
- `mixed_count(混合数量) = 30`

### 四项核心门槛通过情况

- `hard_gate_pass(重叠硬门槛通过数) = 4 / 30`
- `top_spread_pass(头部分层改善通过数) = 27 / 30`
- `liquidity_proxy_pass(流动性代理通过数) = 18 / 30`
- `bucket_monotonicity_pass(高核心区加法单调性通过数) = 9 / 30`
- `all_four_pass(四项同时通过数) = 0 / 30`

### 全样本汇总统计

- `avg_overlap_delta(平均次日前10重叠变化) = -2.180899`
- `median_overlap_delta(次日前10重叠变化中位数) = -2.227289`
- `avg_top_spread_delta(平均前10减11-20变化) = +0.000866`
- `median_top_spread_delta(前10减11-20变化中位数) = +0.000839`
- `avg_liquidity_delta(平均前10流动性分位变化) = -0.015277`
- `median_liquidity_delta(前10流动性分位变化中位数) = -0.014792`
- `avg_same_day_top10_overlap_vs_v18(与v18同日前10平均重叠) = 3.216177`

## 为什么 30/30 全都过不了 v18

### 1. 最大问题不是“静态排序没用”，而是“头部稳定性被打坏”

这一批 Alpha158 positive keepers 的共同特征不是没有 `signal-edge(边际优势)`，而是它们一旦进入三因子静态 overlay 后，**会显著改变 v18 的头部持仓身份**。

证据很直接：

- `hard_gate_pass(重叠硬门槛通过数)` 只有 `4 / 30`
- `avg_overlap_delta(平均次日前10重叠变化) = -2.180899`
- `median_overlap_delta(次日前10重叠变化中位数) = -2.227289`
- `avg_same_day_top10_overlap_vs_v18(与v18同日前10平均重叠) = 3.216177`

这说明绝大多数 Alpha158 keeper 进入 tri-signal overlay 后，不是在“轻微优化 v18 的头部排序”，而是在**换掉一大半头部名字**。这和当前 `v18` 的 `refresh hysteresis(刷新滞后)`、`head extraction(头部提取)`、`TopK=10` 运行契约是冲突的。

### 2. 大部分信号其实能改善静态头部分层，但这种改善不是“可执行改善”

如果只看静态横截面 readout，这批信号并不弱：

- `top_spread_pass(头部分层改善通过数) = 27 / 30`
- `avg_top_spread_delta(平均前10减11-20变化) = +0.000866`

也就是说，大多数候选都能让：

- `top10_minus_rank11_20(前10减11-20名标签差)` 变好
- `full_sample_corr_ic(全样本IC)` 也常常高于参考

但它们仍然失败，原因是：

**当前问题已经不是“会不会挑到更强的名字”，而是“是否还能维持 v18 那套稳定、可交易、低扰动的头部提取机制”。**

所以这条线失败的根因不是 `signal edge(单信号边际)` 不足，而是：

**“静态排序增益” 无法转化成 “相容的组合层增益”。**

### 3. 很多接近通过的候选，最后死在流动性代理或加法单调性

最接近的一组其实是 `CORR / CORD` 中长窗：

- `alpha158_corr30_raw`
- `alpha158_corr60_raw`
- `alpha158_cord30_raw`
- `alpha158_cord60_raw`

它们的共同特点是：

- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠)` 接近甚至高于参考
- `screen_top10_minus_rank11_20(筛查前10减11-20)` 大多也改善

但最后仍然没过，原因分两类：

- `corr30 / cord30 / cord60` 主要死在 `avg_top10_liquidity_rank_mean(前10平均流动性分位)` 恶化过阈值
- `corr60` 主要死在 `core_high_signal_high` 没能高于 `core_high_signal_mid`，也就是加法单调性不够干净

最典型的 near-miss(接近通过但仍失败)：

- `alpha158_corr30_raw`
  - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 7.194936`
  - `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
  - `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.002368`
  - 但 `liquidity_delta(流动性变化) = -0.022071`，略差于容忍阈值 `-0.02`

- `alpha158_corr60_raw`
  - `overlap_delta(重叠变化) = +0.519494`
  - `liquidity_delta(流动性变化) = +0.022330`
  - 但 `bucket_delta(高核心区加法单调性差) = -0.000094`

这说明连最接近通过的候选，也不是“只差一点点就能开 family”，而是**各自在不同维度上与 v18 契约发生冲突**。

### 4. 这批信号更像“替代型头部选择器”，不是“低扰动补充因子”

从组合行为看，Alpha158 positive keepers 更像是在表达一套**不同的头部选择偏好**，而不是在现有 v18 核心双因子上做小幅增强。

这也是为什么：

- standalone 时它们可以是 `signal_edge_positive(正向边际优势)`
- 但一旦被等权并入 `v18` 核心双因子，就会把头部身份重排得过于激进

换句话说：

**它们不是“v18 的第三条平滑补充轴”，更像“另一套独立排序器”。**

对于当前 `v18` 这条以头部稳定性为核心约束的 family 来说，这种候选天然不适合直接用 `equal-weight overlay(等权覆盖层)` 的方式接进去。

## 分簇观察

### `CORR / CORD`

这是三轮里最接近通过的一簇，也是唯一值得保留“将来可能重访”的一簇。

特点：

- 静态 `IC(信息系数)` 强
- `top_spread(头部分层差)` 强
- 中长窗版本的 `overlap(次日重叠)` 也不差

但结论仍然是：

- `corr20 / corr30 / cord20 / cord30 / cord60 / corr60` 全部 `mixed`
- 当前失败点集中在 `liquidity proxy(流动性代理)` 或 `bucket monotonicity(加法单调性)`

因此，这一簇不应再继续做直接 overlay 微调。

### `VMA / VSUM* / VSTD`

这一簇的共性更明显：

- standalone 通常正向
- overlay 后重叠下降明显
- 很多候选与 v18 的同日前10重叠虽然不算特别低，但次日前10连续性明显变差

尤其 `VMA` 家族最典型：

- `vma5 / vma10 / vma20 / vma30 / vma60` 全部是 `mixed`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠)` 普遍明显低于参考

因此，这一簇可以正式视为：

**“单信号可保留，但不适合作为当前 v18 的 direct overlay 候选”。**

### `IMAX / IMXD / LOW0 / RSQR10`

这组更偏路径或形态微结构，在 standalone 里有一定正向性，但 overlay 失败得更直接：

- `imxd5`
- `imax20`
- `low0`
- `rsqr10`

主要问题是：

- `overlap(重叠)` 大幅下降
- 少数还伴随 `top_spread(头部分层差)` 反而变差

这组可以视为：

**更适合做独立单信号记录，不再适合围绕 v18 做 composability 微调。**

## 后续是否停止这条 overlay 线

结论：**是，应该停止。**

更准确地说，是停止下面这条特定研究线：

- `Alpha158 standalone keeper -> equal-weight tri-signal overlay on frozen v18`

停止理由已经足够充分：

1. `30 / 30` 已经全覆盖，不存在“还没筛到真正好用那只”的空间。
2. `all_four_pass(四项同时通过数) = 0 / 30`，不是偶然失败。
3. 失败模式高度一致，主因都是 `head stability(头部稳定性)` 与 `family contract(家族契约)` 不相容。
4. 继续在这条线局部微调，预期信息增量已经很低。

## 建议的后续动作

### 应该做

- 冻结 `price_volume_v18_refresh_hysteresis` 继续作为 `working_reference(工作基准)`
- 保留 `Alpha158` positive keepers 作为 `standalone reserve cards(单信号储备卡片)`
- 把 `Alpha158` 研究成果沉淀为：
  - 哪些簇 standalone 强
  - 哪些簇与 `v18` 不相容
  - 哪些簇若要重访，只能在**完全不同的组合层设计**里重访

### 不应该做

- 不再开新的 `Alpha158 -> v18` direct overlay round
- 不再围绕 `corr / cord / vma / vsumd` 做更多等权 family 微调
- 不把 “standalone positive 很强” 误判成 “适合并入当前 working family”

## 如果未来还要重访，只能换问题定义

只有在下面这些前提改变时，才值得重访 `Alpha158`：

- 不再是 `equal-weight overlay(等权覆盖层)`，而是 `gated / sparse / veto-style overlay(门控/稀疏/否决式覆盖层)`
- 不再要求强保留 `v18` 头部身份，而是允许更换参考 family
- 或者直接把某个 `Alpha158` 簇当成**新 family 的核心轴**，而不是作为 `v18` 的第三因子

也就是说，未来若重开，不应是：

- “这只 Alpha158 keeper 能不能塞进 v18”

而应是：

- “这只 Alpha158 keeper 能不能作为另一条独立 family 的核心排序轴”

## 最终收口判断

`Alpha158 exact canonical` 这条研究线是有效的，但它给出的有效信息不是：

- “找到了可以直接加到 v18 上的 overlay 候选”

而是：

- “找到了若干 standalone 上有效、但与当前 v18 family 契约不相容的原子信号簇”

因此，这轮全覆盖收口后的正式决策是：

**停止 Alpha158 -> v18 overlay 微调线。保留信号知识，不再继续这条组合相容性微调路径。**
