# multi_equal_weight_v1 Baseline Mechanism Audit

## Scope

本文档是 `trainval diagnostic-only` 审计记录，不是 `OOS`，不是 `frozen test`，不是 formal strategy readout。本文档不训练模型，不跑新策略回测，不读取 `frozen test`，不修改 `baseline / confirmed5 / v2 / v3`，也不为 `v4` 设计任何参数。

## Audit Question

当前需要复核的是：`multi_equal_weight_v1` 为什么持续强于所有 nonlinear challenger，以及这种优势是否可能来自隐性口径优势、数据泄漏、执行不公平或组合构造偏差，而不是来自更好的 baseline selection。

## Evidence Reviewed

- [build_multi_equal_weight_v1_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_multi_equal_weight_v1_scores.py)
- [build_reversal_tail_composite_model_scores.py](/Users/wy/MiscProject/multi_factor/scripts/build_reversal_tail_composite_model_scores.py)
- [model_scores_D0_audit.json](/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_reversal_p98_trainval_20260506/model_scores_D0_audit.json)
- [current_project_status_after_confirmed5.md](/Users/wy/MiscProject/multi_factor/docs/current_project_status_after_confirmed5.md)
- [nonlinear_confirmed5_challenger_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_confirmed5_challenger_decision_record.md)
- [nonlinear_challenger_v2_decision_record.md](/Users/wy/MiscProject/multi_factor/docs/nonlinear_challenger_v2_decision_record.md)
- [confirmed5_vs_baseline_same_contract_readout.json](/private/tmp/confirmed5_vs_baseline_same_contract_readout.json)
- [nlc_v2_vs_baseline_same_contract_v3_readout.json](/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.json)
- [combined_same_contract_terminal_approval.json](/private/tmp/combined_same_contract_terminal_approval.json)
- [combined_same_contract_repaired_candidate_v2plus.json](/private/tmp/combined_same_contract_repaired_candidate_v2plus.json)

## 1. Baseline Score Construction Audit

- `multi_equal_weight_v1` 的可见构造链是固定的：
  - `0.25 * p98`
  - `0.25 * cord30`
  - `0.25 * corr30`
  - `0.25 * vsumd60`
- 可见代码路径只读取：
  - `project_sample_panel`
  - `ranking_eligible_D0`
  - `vw_bars_daily.adj_close`
  - `vw_bars_daily.amount`
  - `vw_bars_daily.vol`
  - `vw_bars_daily.pct_chg`
- rolling 计算窗口都以 `CURRENT ROW` 结束，没有看到 `D1+` 字段、未来标签、或 realized return 参与 baseline score 构造。
- `p98` 固定组件的可见构造链是：
  - 先对 reversal score 取负
  - 再做 per-day cross-sectional `p98` tail exclusion
  - 最后在剩余股票内重新排序

当前结论：

- 在当前可访问代码链上，没有发现 baseline score construction 直接使用未来信息。
- 在当前可访问代码链上，没有发现 baseline score construction 直接读取 label 或 realized return。

## 2. D0 Visibility Audit

- `trade_date` 被映射为当日 `signal_date`。
- `cord30 / corr30 / vsumd60` 的 rolling 统计都来自历史序列并止于 `CURRENT ROW`。
- 横截面排序只在 `ranking_eligible_D0` 内执行。
- 因此，当前可见 baseline builder 输入字段都属于 `D0` 可见字段或截止 `D0` 的历史滚动统计。

当前结论：

- baseline 的当前可见输入字段满足 `D0 visibility` 要求。

## 3. Leakage Risk Audit

- 在 `build_multi_equal_weight_v1_scores.py` 中，没有发现：
  - `forward_label`
  - `execution_delayed_realized_return`
  - `actual_exit_date`
  - `actual_sell_price`
  - `next_open / next_close`
- 在 `build_reversal_tail_composite_model_scores.py` 中，也没有发现上述字段进入 `p98` tail-handled score builder。
- 已有 same-contract readout 明确写明：
  - `frozen_test_accessed = false`
  - `formal_metrics_generated = false`

当前结论：

- 没有发现 baseline 对 label / realized return 的直接或显式间接泄漏证据。
- 但本次只能做 `conditional pass`，不能给 unconditional pass。

Blocker:

- 上游 `exploratory_cross_horizon_c1_reversal_only` 的独立 run-state audit 产物当前不在本地可用，因此 raw reversal source 的最上游 provenance 还没有被这次审计重新逐层复核。

## 4. Universe / Mask / Tradability Alignment Audit

- baseline builder 以 shared `project_sample_panel` 为 anchor。
- baseline 排序显式使用 `ranking_eligible_D0`。
- 当前项目决策文档已把 same-contract comparison 写死为：
  - 同 split
  - 同 execution contract
  - 同 terminal exit policy
  - 同 portfolio construction rules
  - 同 cash / invested capital 口径
- 当前没有证据表明 baseline 使用了更宽的 universe、更松的 tradability mask，或单独享受了不同的 D0 可交易定义。

当前结论：

- 没有发现 baseline 的 universe / mask / tradability hidden advantage。

## 5. Execution / Terminal / Portfolio Rule Alignment Audit

- shared terminal approval 只决定 repaired candidate 是否有资格进入上游 execution 修复链。
- approval audit 明确写明：
  - 不回填 `actual_exit_date`
  - 不回填 `actual_sell_price`
  - 不回填 `execution_delayed_realized_return`
- merged repaired candidate 也明确写明：
  - 这些行仍然是 hard blocker
  - 在 execution path 产出正式 actual exit 字段前，不会被当成已定价退出
- confirmed5 / v2 的 decision record 都明确声明 baseline comparison 必须在同一 execution contract、同一 terminal exit policy、同一 portfolio rule 下完成。

当前结论：

- 没有发现 baseline 享受更宽松的 terminal exit handling。
- 没有发现 baseline 享受 baseline-only execution concession。

## 6. Cash / Invested / Turnover Explanation

baseline 的优势不能简单归因于某一个“更舒服的资金口径”。

- 对 `confirmed5`：
  - baseline 平均 cash 更高
  - baseline 平均 invested capital 更低
  - baseline 平均 turnover 更低
  - baseline 仍然赢
- 对 `v2`：
  - baseline 平均 cash 更低
  - baseline 平均 invested capital 更高
  - baseline 平均 turnover 略高
  - baseline 仍然赢

这意味着：

- baseline 不是因为永远持有更多现金才显得更稳。
- baseline 也不是因为永远持有更高投资仓位才显得更强。
- baseline 更像是在同 contract 下，对 selected names 的选择质量更高，而不是单靠 cash / invested / turnover accounting 获胜。

## 7. Hidden Advantage Judgment

当前综合判断：

- 未发现 baseline hidden advantage 的直接证据。
- 未发现 baseline future function / label leakage 的直接证据。
- 未发现 baseline same-contract comparison 的明显不公平口径。
- baseline 当前最可信的优势解释仍然是：
  - selected-head realized return 更强
  - divergence selection 更强

但这仍然只是 `trainval diagnostic-only` 结论，不是策略有效性声明，不是 `OOS`，不是 `frozen test` 结论。

## 8. Minimum Hurdle Decision

当前结论：

- 继续允许 `multi_equal_weight_v1` 作为最低门槛。
- 审计结论是 `conditional pass`，不是 unconditional pass。

原因：

- 当前可访问 baseline 机制链没有暴露出未来函数、标签泄漏、terminal 特判、portfolio contract 特判或明显 universe 偏置。
- 仍存在一个 blocker：
  - 上游 raw reversal source audit artifact 当前不可本地重验。

## 9. What This Audit Does Not Claim

本文档明确不做以下声明：

- 不宣称 `baseline 策略有效`
- 不宣称 `baseline OOS 通过`
- 不宣称 `baseline 可以实盘`
- 不把 `trainval diagnosis` 当成 `OOS`
- 不把 `same-contract dry-run` 当成 `frozen test`

## Final Record

- baseline mechanism audit 当前结论：`conditional pass`
- hidden advantage: `not found from accessible evidence`
- baseline minimum hurdle: `retain`
- `frozen test`：仍禁止读取
