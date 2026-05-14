# Final Audit Entry Package

本文档是当前仓库的最终审计入口包。

它不新增研究结论，不训练，不回测，不跑 portfolio，不生成 formal metrics/readout，不读取 frozen test，也不宣称策略有效性。它只把当前项目的最小复查路径固定下来，方便后来审阅者快速判断：

- 项目当前处于什么状态；
- 为什么当前研究问题已经停止；
- 哪些证据可以如何引用；
- 哪些历史产物不能被误读为 OOS；
- 后续什么时候才允许重新立项。

## 当前结论

当前状态为：

```text
status: current_data_regime_research_stopped
strategy_research: paused
sandbox_understanding: completed
repository_role: audit asset and engineering asset
```

当前 D0 OHLCV + state 数据范式下，clean baseline / TopK / mid-rank 研究已经停止。仓库当前价值是保留负结果、治理边界、审计证据和可复用工程资产，而不是继续追加同一问题下的新策略变体。

## 最小阅读路径

外部审阅者只需要先读以下五份材料，即可建立当前仓库的正确证据口径：

1. [README.md](/Users/wy/MiscProject/multi_factor/README.md)
   - 仓库总入口，说明项目目标、当前阶段、目录结构和禁止事项。
2. [docs/current_stage.md](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)
   - 当前真相源，固定 `current_data_regime_research_stopped`、`strategy_research: paused` 和 no-portfolio 结论。
3. [docs/final_project_review_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/final_project_review_after_data_regime_stop.md)
   - 最终项目复盘，解释研究路径、工程状态、停止原因、工程清理方向和重启条件。
4. [docs/audit_boundary.md](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md)
   - 证据边界说明，明确 trainval-only 结果、`fixed_test` 历史命名和 OOS 口径限制。
5. [artifacts/README.md](/Users/wy/MiscProject/multi_factor/artifacts/README.md)
   - 产物保留与归档规则，区分必须保留、优先外部归档、可重建或可删除内容。

## 补充阅读

需要理解 sandbox 为什么已经完成时，读：

- [docs/project_closure_after_sandbox_completion.md](/Users/wy/MiscProject/multi_factor/docs/project_closure_after_sandbox_completion.md)

需要理解当前 D0 OHLCV + state 路线为什么停止时，读：

- [docs/current_data_regime_research_stop_decision.md](/Users/wy/MiscProject/multi_factor/docs/current_data_regime_research_stop_decision.md)

需要理解历史探索边界和冻结政策时，读：

- [docs/exploratory_sandbox_policy_after_data_regime_stop.md](/Users/wy/MiscProject/multi_factor/docs/exploratory_sandbox_policy_after_data_regime_stop.md)
- [docs/research_freeze_policy.md](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)

需要理解工程目录职责时，读：

- [docs/repo_map.md](/Users/wy/MiscProject/multi_factor/docs/repo_map.md)
- [docs/test_running.md](/Users/wy/MiscProject/multi_factor/docs/test_running.md)

## 禁止误读

当前审计入口包固定以下边界：

- 不把 `p98` / `multi_equal_weight_v1` 当作 unconditional gold standard。
- 不把 clean baseline family 解释为 portfolio-ready。
- 不把 trainval diagnosis 或 trainval-only readout 当作 OOS。
- 不把历史 `fixed_test` 路径名自动解释为独立样本外证据。
- 不用已经完成的 sandbox understanding 推出 near-head、stress-exclusion、agreement-based 或 conditional-reference-guided candidate。
- 不继续当前 D0 OHLCV + state 下的同一 TopK / mid-rank 问题变体。

## 重启条件

未来研究只有在至少满足以下条件之一时才应重新立项：

- 出现新的信息源；
- 出现新的数据模态；
- 出现独立预注册的新研究问题，且不复用已停止的 TopK / mid-rank claim 作为隐含证据。

在这些条件满足前，仓库的合理工作是保留、审计、归档、测试和工程整理。
