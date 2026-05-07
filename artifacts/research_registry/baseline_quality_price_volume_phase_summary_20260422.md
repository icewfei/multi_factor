# baseline / quality / price-volume families 阶段性总总结与下一阶段方向建议

日期：2026-04-22  
范围：校准后的 baseline family（`v7-v11`）、quality/profitability family（`v12`）、price-volume family（`v13-v14`）

## 1. 结论先行

- **当前唯一有效 operational reference 仍然是校准后的 `v7`。**
- **baseline family 已经不值得继续微调。**
- **quality/profitability family 当前最小版本不值得继续深挖。**
- **最近两条 price-volume family（`v13`、`v14`）在当前固定形式下不值得继续。**
- **下一阶段不建议直接开 `v15`，而应先切换到“单信号发现 -> 再组 family”的研究方式。**

## 2. 当前 reference：校准后的 `v7`

Reference:

- `candidate_scheme_id = baseline_momentum_v7_liquidity_guard70`
- `research_round_id = rr_baseline_liquidity_guard70_20260418`
- `snapshot_id = warehouse_20260418_181408`

关键指标：

- `annual_relative_return = -0.06976572569304007`
- `relative_ir = -0.5287021621315882`
- `max_drawdown = -0.3968114993586318`
- `avg_cash_weight = 0.7919965084907071`
- `avg_invested_weight = 0.2080034915092814`
- `avg_turnover_daily = 0.09811299793683326`
- `low_liquidity_weight_share = 0.020450724262800736`
- `topk_perturbation_pass = false`
- `cost_stress_pass = false`

这条 reference 的意义是：

- 它已经经过 `amount` 单位修正、`low_liquidity_flag_t` 阈值修正、`liquidity_rank` 方向修正。
- 它是当前所有后续 challenger 最公平的比较基准。
- 它仍然只是 `weak_candidate`，不能晋级，但它是目前已知 family 中信息量最大的 operational baseline。

## 3. baseline family（`v7-v11`）总结

对应正式收口文件：

- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/baseline_family_v7_to_v11_direction_decision_20260419.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/baseline_family_v7_to_v11_direction_decision_20260419.md)

### 3.1 研究过的单维方向

- `v7`：更强 liquidity guard
- `v8`：same-threshold universe guard
- `v9`：liquidity weight penalty
- `v10`：broadened head extraction
- `v11`：turnover suppression / sticky refresh rule

### 3.2 统一判断

- 这条 family **不是完全没信号**。
- 但它的 gross edge **太薄**，并且：
  - `TopK=10` 提取很脆
  - turnover / cost 拖累明显
  - 微调 guard / extraction / refresh rule 都没有把它推到可晋级状态

### 3.3 为什么应停止继续微调

- `v7-v11` 已覆盖这条 family 最自然的一批单维改动。
- 剩余问题不再像某一个局部参数没调对。
- 继续做：
  - 更多 guard 阈值
  - 更多 extraction 公式
  - 更多 refresh rule
  只会明显扩大研究空间，提高过拟合风险。

结论：

- **baseline family 已停止继续微调。**
- **校准后的 `v7` 保留为 reference，但不再继续围绕它开局部微调候选。**

## 4. quality/profitability family（`v12`）总结

关键对照：

- `annual_relative_return`: `-0.069766 -> -0.075695`
- `relative_ir`: `-0.528702 -> -0.491747`
- `max_drawdown`: `-0.396811 -> -0.194233`
- `avg_invested_weight`: `0.208003 -> 0.104997`
- `avg_turnover_daily`: `0.098113 -> 0.047313`
- `topk_perturbation_pass`: `false -> false`
- `cost_stress_pass`: `false -> false`

对应文件：

- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_quality_profitability_family_20260419/challenger_vs_v7_summary.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_quality_profitability_family_20260419/challenger_vs_v7_summary.md)
- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_quality_profitability_family_20260419/v12_signal_edge_diagnosis_20260419.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_quality_profitability_family_20260419/v12_signal_edge_diagnosis_20260419.md)

### 4.1 已知优点

- drawdown 更低
- turnover 更低

### 4.2 已知问题

- 收益没有改善，`annual_relative_return` 更差
- signal edge 很浅：
  - full-sample IC 只有 `0.002484`
  - 平均日 IC 为负
- broad decile ordering 仍有一点信息，但头部提取明显不好：
  - `top10` 不优于 `rank 11-20`
  - 甚至也不优于尾部

### 4.3 阶段判断

- `v12` **不是完全随机**，但当前最小版本的 edge 太弱。
- 这条 family 若继续深挖，合理前提应该是先证明它存在足够强的单信号或更清晰的头部 edge。
- 在当前证据下，**不建议继续直接做 `v12` extraction 微调或家族内小修小补。**

结论：

- **quality/profitability family 当前不是下一阶段优先方向。**

## 5. price-volume families（`v13-v14`）总结

### 5.1 `v13 = price_volume_multisignal_core`

对照结果：

- `annual_relative_return`: `-0.069766 -> -0.124733`
- `relative_ir`: `-0.528702 -> -0.828565`
- `max_drawdown`: `-0.396811 -> -0.662927`
- `avg_turnover_daily`: `0.098113 -> 0.088353`
- `low_liquidity_weight_share`: `0.020451 -> 0.009514`

signal-edge 诊断：

- full-sample IC：`-0.021984`
- 平均日 IC：`-0.038414`
- 正 IC 日占比：`35.57%`
- decile 方向反了，高分更差、低分更好

对应文件：

- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_price_volume_multisignal_family_20260419/challenger_vs_v7_summary.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_price_volume_multisignal_family_20260419/challenger_vs_v7_summary.md)
- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_price_volume_multisignal_family_20260419/v13_signal_edge_diagnosis_20260419.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_price_volume_multisignal_family_20260419/v13_signal_edge_diagnosis_20260419.md)

判断：

- `v13` 不是“提取方式没调对”，而是 score 方向本身就不对。

### 5.2 `v14 = trend_quality_price_volume_core`

对照结果：

- `annual_relative_return`: `-0.069766 -> -0.074637`
- `relative_ir`: `-0.528702 -> -0.554869`
- `max_drawdown`: `-0.396811 -> -0.346044`
- `avg_turnover_daily`: `0.098113 -> 0.089080`
- `low_liquidity_weight_share`: `0.020451 -> 0.021163`

signal-edge 诊断：

- full-sample IC：`-0.009235`
- 平均日 IC：`-0.013902`
- 正 IC 日占比：`39.71%`
- decile 方向仍反，高分仍不优于低分

对应文件：

- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_trend_quality_price_volume_family_20260419/challenger_vs_v7_summary.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_trend_quality_price_volume_family_20260419/challenger_vs_v7_summary.md)
- [/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_trend_quality_price_volume_family_20260419/v14_signal_edge_diagnosis_20260422.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_trend_quality_price_volume_family_20260419/v14_signal_edge_diagnosis_20260422.md)

判断：

- `v14` 相比 `v13` 更干净，但方向仍不对。
- 说明问题不是“加入了短期反转导致打架”这么简单，而是当前这条新量价 family 的固定构造本身没有正 edge。

### 5.3 阶段判断

- **`v13` 和 `v14` 都不值得继续。**
- 当前 price-volume family 的问题不是 extraction 或 turnover，而是 score 层本身已经负 edge。
- 因此不建议：
  - 再在 `v13/v14` 上做 extraction 微调
  - 再在同一批量价特征上混更多组合

## 6. 三条研究线的统一判断

### 6.1 已有信息

- baseline family：有弱正 edge，但太薄，且已被微调到收益递减区
- quality family：可能有很浅的 broad ordering，但头部 edge 不成立
- price-volume 新 families：当前固定构造下 score 方向直接为负

### 6.2 目前不该做的事

- 不要直接开 `v15` 去继续 baseline family 微调
- 不要继续修 `v12` 的 extraction
- 不要继续在 `v13/v14` 上混更多量价组合
- 不要同时扩大 score family 和组合层自由度

## 7. 下一阶段方向建议

### 7.1 建议先做什么

**下一阶段优先做“单信号发现”，而不是直接再开一个新的混合 family。**

建议的工作方式：

1. 从当前最成熟的数据源里，预注册一批**单信号候选**  
   例如分成三组：
   - 量价趋势类
   - 估值/投资类
   - 质量/盈利类

2. 每次只测**单一原始信号**或**极小的单一变体**  
   先看：
   - full-sample IC
   - 平均日 IC
   - decile 单调性
   - top10 / 11-20 / bottom10 对比

3. 只有当单信号本身显示出**明确的正 edge**，再进入 family 组合阶段

### 7.2 为什么这样更合理

- 现在已经知道：盲目把多个信号混成一个 family，可能在方向上直接搞反。
- 先做单信号发现，可以更快回答：
  - 哪些信号根本没 edge
  - 哪些信号有弱正 edge
  - 哪些信号只在 broad ordering 上有效
- 这能显著降低下一阶段的研究自由度和过拟合风险。

### 7.3 推荐的下一阶段主题

优先顺序建议：

1. **量价单信号发现**
   因为数据覆盖最全、管线最成熟、实验反馈最快

2. **value / investment 单信号发现**
   因为这条线还没有真正被测过 family 以外的“更基础原子信号”

3. **quality / profitability 单信号发现**
   作为补充线，而不是当前主线

## 8. 最终建议

当前阶段最合理的决策是：

- **正式停止继续微调 baseline family**
- **不继续深挖 `v12`**
- **不继续深挖 `v13/v14`**
- **下一阶段转为“单信号发现 -> 再组 family”的研究流程**

若要开下一轮，不建议直接命名为新的混合 family，而应先用更原子的 research round 去验证：

- 哪一个单信号方向确实有可提取的正 edge

在这一步完成前，继续开新的混合 `score family`，研究价值低、过拟合风险高。
