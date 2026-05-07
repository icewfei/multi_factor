# Alpha158 Exact 158 全量执行阶段性总总结

## 一句话决策

冻结 `price_volume_v18_refresh_hysteresis` 继续作为 `working_reference(工作基准)`；**不直接开新的大而全 family(家族)**，先对 Alpha158 exact keepers 做 `keeper consolidation(保留信号归并)`，再进入一轮更克制的 `composability screening(组合相容性筛查)`。

## 执行范围与总结果

- 本轮执行范围：`qlib Alpha158 exact canonical 158`，全部按本项目自己的数据口径独立实现。
- 执行完成度：`exact_executed_candidate_count(精确定义已执行数) = 158 / 158`，`exact_remaining_candidate_count(剩余精确定义数) = 0`
- 总分类结果：
  - `signal_edge_positive(正向边际优势) = 30`
  - `signal_edge_mixed(混合边际优势) = 120`
  - `signal_edge_negative(负向边际优势) = 8`
- 总体 keeper 命中率：`30 / 158 = 18.99%`

## 分段观察

- `1-60`：`signal_edge_positive(正向边际优势) = 2 / 60 = 3.33%`
  - 这一段以价格形态、趋势平滑和基础波动定义为主，命中率很低。
- `61-120`：`signal_edge_positive(正向边际优势) = 12 / 60 = 20.00%`
  - 这一段开始进入价格-成交量相关与路径时序，明显转强。
- `121-158`：`signal_edge_positive(正向边际优势) = 16 / 38 = 42.11%`
  - 这一段以相对成交量、成交量变化分解为主，是最强的 tranche(特征分段)。

结论很直接：**本项目的数据优势更明显地体现在量价与成交量动态，而不是纯价格形态。**

## 主要发现

- `CORR/CORD` 整段表现强。
  - 最强代表包括：
    - `alpha158_corr20`: `full_sample_corr_ic(全样本IC) = 0.018514`
    - `alpha158_corr10`: `full_sample_corr_ic(全样本IC) = 0.018240`
    - `alpha158_cord30`: `avg_daily_ic(平均日IC) = 0.031407`
    - `alpha158_cord20`: `full_sample_corr_ic(全样本IC) = 0.016534`
- `VMA` 相对量族整段正向。
  - `vma5/10/20/30/60` 全部 keeper，且 `VMA60` 最强：
    - `full_sample_corr_ic(全样本IC) = 0.012987`
    - `avg_daily_ic(平均日IC) = 0.022111`
- `VSUMP / VSUMN / VSUMD` 中长窗成交量变化分解很强。
  - `20/30/60` 窗口基本整段 keeper。
  - `VSUMD60`:
    - `full_sample_corr_ic(全样本IC) = 0.014043`
    - `avg_daily_ic(平均日IC) = 0.023207`
    - `avg_label_bottom10(后10平均标签) = -0.008018`
- `WVMA` 整段负向。
  - `wvma5/10/20/30/60` 都不值得继续，属于本轮最清楚的 rejected cluster(拒绝簇)。
- 纯价格方向分解没有过关。
  - `CNTP/CNTN/CNTD/SUMP/SUMN/SUMD` 这几组大多 `signal_edge_mixed(混合边际优势)`，说明“价格方向计数/分解”在本项目数据里没有像“成交量方向分解”那样形成硬优势。

## Keeper Consolidation

### 归并原则

- 同一机制不同窗口，只保留 `1-2` 个代表，不把整串近邻窗口一起带进下一轮。
- 代数近等价或高度同构的信号，只保留一个标准代表。
- 下一轮优先保留“机制不同”的代表，而不是“指标都还不错”的代表。

### 建议保留的 canonical keeper map

- `close_location_support`
  - keeper: `price_volume_single_signal_alpha158_low0_v1`
  - 含义：收盘相对当日低点位置
  - 角色：弱但可能正交，放入 reserve(备选池)

- `trend_fit_quality_short`
  - keeper: `price_volume_single_signal_alpha158_rsqr10_v1`
  - 含义：短窗趋势拟合质量
  - 角色：弱但可能正交，放入 reserve

- `path_ordering_breakout`
  - keeper: `price_volume_single_signal_alpha158_imxd5_v1`
  - 备选：`price_volume_single_signal_alpha158_imax20_v1`
  - 决策：优先保留 `imxd5`
  - 原因：指标更强，表达的是“高点在低点之后”的路径顺序，而不是单纯高点新近性

- `price_volume_level_corr`
  - keeper cluster:
    - `corr5/10/20/30/60`
  - canonical representative(标准代表): `price_volume_single_signal_alpha158_corr20_v1`
  - 备选：`corr10`
  - 原因：`corr20` 的 `full_sample_corr_ic(全样本IC)` 全簇最高，同时窗口不算过短

- `price_volume_change_corr`
  - keeper cluster:
    - `cord5/10/20/30/60`
  - canonical representative: `price_volume_single_signal_alpha158_cord30_v1`
  - 备选：`cord20`
  - 原因：`cord30` 的 `avg_daily_ic(平均日IC)` 全簇最高，稳定性和强度兼顾

- `relative_volume_level`
  - keeper cluster:
    - `vma5/10/20/30/60`
  - canonical representative: `price_volume_single_signal_alpha158_vma60_v1`
  - 备选：`vma30`
  - 原因：长窗代表更强，且更适合作为 family 中的慢变量

- `volume_stability`
  - keeper cluster:
    - `vstd30/60`
  - canonical representative: `price_volume_single_signal_alpha158_vstd60_v1`
  - 原因：`vstd60` 显著强于 `vstd30`

- `volume_expansion_balance`
  - keeper cluster:
    - `vsump20/30/60`
    - `vsumn20/30/60`
    - `vsumd20/30/60`
  - canonical representative: `price_volume_single_signal_alpha158_vsumd60_v1`
  - 备选：`vsump60`
  - 原因：
    - `VSUMP / VSUMN / VSUMD` 本质上高度同构
    - `VSUMD60` 是最对称、最适合作为组合层输入的净量变化代表

### 归并后建议保留的 8 个核心代表

- `price_volume_single_signal_alpha158_corr20_v1`
- `price_volume_single_signal_alpha158_cord30_v1`
- `price_volume_single_signal_alpha158_vma60_v1`
- `price_volume_single_signal_alpha158_vstd60_v1`
- `price_volume_single_signal_alpha158_vsumd60_v1`
- `price_volume_single_signal_alpha158_imxd5_v1`
- `price_volume_single_signal_alpha158_low0_v1`
- `price_volume_single_signal_alpha158_rsqr10_v1`

其中建议分层：

- `primary composability pool(一级组合筛查池)`
  - `corr20`
  - `cord30`
  - `vma60`
  - `vsumd60`

- `secondary reserve pool(二级备选池)`
  - `vstd60`
  - `imxd5`
  - `low0`
  - `rsqr10`

## 下一阶段 Family / Composability 建议

### 不建议直接做的事

- 不建议把 30 个 keepers 直接拼成新 family。
- 不建议把 `CORR` 和 `CORD` 的多窗口版本一起并入。
- 不建议把 `VSUMP / VSUMN / VSUMD` 三条等价链同时带入组合层。
- 不建议现在就从 Alpha158 keepers 直接替换掉 `v18`。

### 建议的推进顺序

1. 先开一轮 `composability screening(组合相容性筛查)`，对象只放 4 个一级代表：
   - `price_volume_single_signal_alpha158_corr20_v1`
   - `price_volume_single_signal_alpha158_cord30_v1`
   - `price_volume_single_signal_alpha158_vma60_v1`
   - `price_volume_single_signal_alpha158_vsumd60_v1`

2. 每只信号都先相对于 `v18` 做单独 overlay(覆盖层) 筛查，而不是直接开 mixed family。

3. composability 硬门槛继续沿用并加严：
   - `annual_relative_return(年化超额收益)` 不能明显恶化
   - `max_drawdown(最大回撤)` 不能明显恶化
   - `turnover(换手率)` 与 `cost drag(成本拖累)` 不能失控
   - `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠)` 不能比参考下降超过阈值

4. 只有单只 overlay 过筛后，才开下一步 restrained family(克制型家族)。

### 如果要开下一条最小 family，建议从这两个方向二选一

- 方向 A：`cord30 + vma60`
  - 逻辑：一个反映价格变化与量变化联动，一个反映相对量水平
  - 优点：机制区分度较高，比较像“动态联动 + 慢变量确认”

- 方向 B：`corr20 + vsumd60`
  - 逻辑：一个反映价格与量水平相关，一个反映净量变化方向
  - 优点：都来自量价，但一个偏 level coupling(层级耦合)，一个偏 flow balance(流量平衡)

在这两个方向里，**优先级更高的是方向 A：`cord30 + vma60`**。

## 最终阶段判断

- Alpha158 exact 158 全量执行是有效的，且确实带来了新信息。
- 但这些信息不是“可以立刻开大杂烩 family”，而是把下一阶段研究重点**进一步推向量价 / 成交量动态机制**。
- 因此，下一步最合理的不是“再扩 Alpha158 池”，而是：
  - 先做 keeper consolidation 后的 composability screening
  - 再决定是否基于 `cord30 / vma60 / vsumd60 / corr20` 打开一条新的 restrained family 设计线

## 附：本轮最强 exact keepers

- `alpha158_corr20`: `full_sample_corr_ic(全样本IC) = 0.018514`
- `alpha158_corr10`: `full_sample_corr_ic(全样本IC) = 0.018240`
- `alpha158_cord30`: `avg_daily_ic(平均日IC) = 0.031407`
- `alpha158_imxd5`: `avg_daily_ic(平均日IC) = 0.031425`
- `alpha158_vsumd60`: `avg_daily_ic(平均日IC) = 0.023207`
- `alpha158_vsump60`: `avg_daily_ic(平均日IC) = 0.023205`
- `alpha158_vsumn60`: `avg_daily_ic(平均日IC) = 0.023203`
- `alpha158_vma60`: `avg_daily_ic(平均日IC) = 0.022111`
