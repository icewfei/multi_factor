# v7 / v9 低流动性暴露根因诊断

生成时间：`2026-04-18`

适用范围：
- `baseline_momentum_v7_liquidity_guard70`
- `baseline_momentum_v9_liquidity_weight_penalty`

相关产物：
- `v7` run-state: [/Users/wy/MiscProject/multi_factor/artifacts/run_state/fullchain_baseline_liquidity_guard70_20260418_1620/attempts/attempt_20260418_154945](/Users/wy/MiscProject/multi_factor/artifacts/run_state/fullchain_baseline_liquidity_guard70_20260418_1620/attempts/attempt_20260418_154945)
- `v7` fixed test: [/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_guard70_20260418_1620](/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_guard70_20260418_1620)
- `v9` run-state: [/Users/wy/MiscProject/multi_factor/artifacts/run_state/fullchain_baseline_liquidity_weight_penalty_20260418_1818/attempts/attempt_20260418_173752](/Users/wy/MiscProject/multi_factor/artifacts/run_state/fullchain_baseline_liquidity_weight_penalty_20260418_1818/attempts/attempt_20260418_173752)
- `v9` fixed test: [/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_weight_penalty_20260418_1818](/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_weight_penalty_20260418_1818)

## 结论摘要

这次诊断得到 3 个核心结论：

1. `liquidity_rank` 的方向与前几轮 `guard / penalty` 的使用方向是反的。  
   在当前实现里，`liquidity_rank` 是通过 `PERCENT_RANK() OVER (ORDER BY liquidity_20d_raw DESC)` 得到的，这意味着：
   - 更高流动性的样本得到更小的 `liquidity_rank`
   - 更低流动性的样本得到更大的 `liquidity_rank`
   
   因此：
   - `v7` 的 `liquidity_rank >= 0.70` 实际上是在**保留更低流动性的样本**
   - `v9` 的 `weight_mapping_multiplier = 0.5 + 0.5 * liquidity_rank` 实际上是在**给更低流动性的样本更高权重**

2. fixed test 里的 `low_liquidity_flag_t` 口径存在明显单位错配。  
   `Tushare Pro` 的 `amount` 单位是`千元`。共享数据源当前把 `low_liquidity_flag_t` 定义为 `amount < 5_000_000`，这实际等价于“成交额低于 50 亿元就算低流动性”。在当前 snapshot 下：
   - 全部 `vw_tradability_daily` 行里，大约 `96.25%` 被标记为低流动性
   - `ranking_eligible_D0` 行里，大约 `99.86%` 被标记为低流动性
   
   因此 `low_liquidity_weight_share ≈ 1.0` 不能直接被解释为“策略只挑到了极端差流动性尾部”，因为审计 flag 自身已经覆盖了绝大多数样本。

3. `v7 -> v9` 没有改善，是因为 `v9` 的权重惩罚方向也反了。  
   `v9` 试图“在冻结 `v7` 选股边界的前提下，惩罚低流动性权重”，但当前公式实际上在**上调**低流动性样本权重，所以结果略差并不意外。

一句话总结：

当前看到的“低流动性暴露极高”，并不只是策略问题；它同时反映了：
- 研究侧 `liquidity_rank` 的方向误用
- 审计侧 `low_liquidity_flag_t` 的绝对阈值存在单位错配

## 证据 1：`liquidity_rank` 方向被反着用了

相关实现：
- [build_baseline_model_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_baseline_model_scores.py:276)

当前定义：

```sql
PERCENT_RANK() OVER (
    PARTITION BY snapshot_id, signal_date
    ORDER BY liquidity_20d_raw DESC, instrument ASC
) AS liquidity_rank
```

这会导致：
- `liquidity_20d_raw` 越大，`liquidity_rank` 越接近 `0`
- `liquidity_20d_raw` 越小，`liquidity_rank` 越接近 `1`

而前几轮方案的使用方式是：
- `v7`：`liquidity_rank >= 0.70`
- `v9`：`0.5 + 0.5 * liquidity_rank`

这两者都在偏向 **更低流动性**，而不是更高流动性。

## 证据 2：`v7` / `v9` 的持仓本身确实落在较低流动性分位

针对持仓与冻结 `TopK` 的检查结果：

- `v7` 持仓：
  - 持仓条数：`60,526`
  - `liquidity_rank` 平均值：约 `0.8327`
  - 最小值：`0.70`
  - 最大值：`1.00`
- `v7` 冻结 `TopK`：
  - 条数：`63,020`
  - `liquidity_rank` 平均值：约 `0.8354`

- `v9` 持仓：
  - 持仓条数：`60,526`
  - `liquidity_rank` 平均值：约 `0.8327`
  - 最小值：`0.70`
  - 最大值：`1.00`

这与 `v7` 的 guard 定义完全一致：它保留的是 **`liquidity_rank >= 0.70`** 的样本，也就是当前定义下更低流动性的后 30% 区域。

## 证据 3：fixed test 的 `low_liquidity_flag_t` 口径存在单位错配

相关实现：
- [build_fixed_test_minimal.py](/Users/wy/MiscProject/multi_factor/scripts/build_fixed_test_minimal.py:977)
- [/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:1018)
- [/Users/wy/MiscProject/tushare_data/parquet_duckdb/benchmark_config.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/benchmark_config.py:38)

共享源定义：

```sql
CASE
    WHEN b.amount IS NULL THEN FALSE
    ELSE b.amount < 5000000.0
END AS low_liquidity_flag_t
```

如果 `amount` 单位是`千元`，那么这条规则实际上是在判断：

```text
成交额 < 50亿元
```

当前 snapshot 的全局统计：
- `vw_tradability_daily` 全部行中，`low_liquidity_flag_t = true` 的比例约 `96.25%`
- `ranking_eligible_D0` 行中，`low_liquidity_flag_t = true` 的比例约 `99.86%`

这意味着：
- 这个 flag 当前更像“绝大多数样本都会被打上的广义低流动性标志”
- 它不适合直接拿来解释“为什么某个策略的 low_liquidity_weight_share 接近 1.0”

## 证据 4：`v7` / `v9` 持仓在 `signal_date` 的成交额并不支持“极端低流动性”解读

针对持仓当日 `amount` 的统计：

- `v7` 与 `v9` 基本完全一致：
  - 平均 `amount`：约 `34,176.83`
  - 中位数 `amount`：约 `18,109.30`
  - 最大 `amount`：约 `3,302,548.98`
  - `< 5,000,000` 的持仓比例：`100%`

如果 `amount` 单位是`千元`，这些数对应的大致成交额规模是：
- 平均成交额约 `3,417.68 万元`
- 中位成交额约 `1,810.93 万元`
- 最大成交额约 `33.03 亿元`

这说明至少在当前数据口径下：
- 持仓样本确实全部落在 `5,000,000` 阈值以下
- 但这个阈值按 `千元` 单位解释时本来就是 `50 亿元`
- 因此“全部低于阈值”不能被解读为“策略只挑了极端差流动性样本”

这里可以明确下结论：
- `amount` 的量纲与 `5,000,000` 阈值不匹配
- 共享源当前 `low_liquidity_flag_t` 阈值应按 `千元` 单位重设

## 证据 5：`v9` 的权重惩罚没有解决问题，原因是方向错了

`v9` 的固定公式是：

```text
weight_mapping_multiplier = 0.5 + 0.5 * liquidity_rank
```

如果 `liquidity_rank` 越大代表越低流动性，那么这条公式实际上会：
- 给低流动性样本更大的 multiplier
- 给高流动性样本更小的 multiplier

这与“流动性惩罚”的目标是反着的。

这和 fixed test 结果一致：
- `v9` 相比 `v7`
  - `annual_relative_return` 略差
  - `relative_ir` 略差
  - `max_drawdown` 略差
  - `low_liquidity_alpha_contribution_share` 从 `0.5991` 升到 `0.6080`

参考文件：
- [v7 metrics.json](/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_guard70_20260418_1620/metrics.json)
- [v9 metrics.json](/Users/wy/MiscProject/multi_factor/artifacts/fixed_test/fullchain_baseline_liquidity_weight_penalty_20260418_1818/metrics.json)
- [v9 vs v7 summary](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_rounds/rr_baseline_liquidity_weight_penalty_20260418/challenger_vs_v7_summary.json)

## 诊断结论

当前“低流动性暴露高”的根因，不应简单归因为“策略太差”，而应拆成两层：

### A. 研究实现层问题
- `liquidity_rank` 的语义被反着用了
- `v7` guard 实际在保留低流动性样本
- `v9` penalty 实际在上调低流动性样本权重

### B. 审计口径层问题
- `low_liquidity_flag_t` 是基于绝对阈值 `amount < 5,000,000`
- 但 `amount` 单位是`千元`，所以当前阈值实际等价于 `50 亿元`
- 在当前 snapshot 下，这个 flag 覆盖了绝大多数样本
- 因此它可以作为 warning，但不应在当前口径下被过度解读为“策略只持有极端差流动性标的”

## 建议的下一步

1. 暂停继续开新 `candidate_scheme_id`  
   在修正流动性语义前，不建议继续推进 `v10`。

2. 先修正研究实现口径  
   二选一即可：
   - 把 `liquidity_rank` 改成“更高流动性 -> 更大 rank”
   - 或保持 rank 定义不变，但所有 guard / penalty 条件改成与当前 rank 方向一致的比较方式

3. 修正共享源 `low_liquidity_flag_t`  
   由于 `amount` 单位是`千元`，若目标口径是“成交额低于 500 万元视为低流动性”，阈值应改为：
   - `5_000`
   而不是：
   - `5_000_000`

4. 修正后先做“校准 rerun”，不要直接记为新研究轮次  
   最合理的是先把当前最好的 `v7` 作为校准参考，在修正口径后重跑一次，确认：
   - guard 的方向真正按预期工作
   - `low_liquidity_weight_share` 和 `low_liquidity_alpha_contribution_share` 是否显著回落

## 当前最重要的一句话

在继续研究前，必须先修正：
- `liquidity_rank` 的方向使用
- 以及 `low_liquidity_flag_t` 的单位阈值口径

否则后续所有“流动性 guard / penalty”实验，都会夹杂明显的实现语义偏差，研究结论不够可靠。
