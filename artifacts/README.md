# Artifacts Directory Contract

本目录承载研究运行产物、治理登记、阶段证据和审计摘要。

当前项目已经进入 `current_data_regime_research_stopped`，因此 `artifacts/` 的下一步职责不是继续生成策略证据，而是明确哪些内容必须保留、哪些内容只适合归档、哪些内容属于可重建输出。

本目录不承载共享数据源真相源，也不承载未来新研究的自由写入入口。

固定子目录：

- `fixed_test/`
- `research_registry/`
- `walk_forward/`
- `shadow_tracking/`
- `run_state/`

规则：

- 共享数据源视图和 parquet 不得复制到本目录冒充真相源
- 本目录只保存 run-level 结果、项目运行态状态和项目审计摘要
- 所有子目录产物都应绑定 `run_id + snapshot_id`；其中 `run_state` 的运行态输出还必须绑定 `attempt_id`
- 研究登记、方案主键和失败证据骨架位于 `artifacts/research_registry/`

## 证据边界

当前仓库中的许多历史产物虽然位于 `fixed_test/` 或名称中包含 `fixed_test`，但实际绑定的是 trainval-only 研究快照。

因此：

- `artifacts/` 中的历史产物可以作为过程审计、研究治理、失败解释和阶段性决策证据。
- 绑定 trainval-only 快照的产物不得被表述为独立 OOS 证据。
- 历史路径名不在本轮重命名，但引用时必须说明其 trainval-only 属性和证据等级。
- 当前不应从本目录继续挑选 candidate、跑 portfolio、读取 frozen test、生成新的 formal metrics/readout 或包装策略有效性。

详细审计口径见：

- [`docs/audit_boundary.md`](/Users/wy/MiscProject/multi_factor/docs/audit_boundary.md)
- [`docs/research_freeze_policy.md`](/Users/wy/MiscProject/multi_factor/docs/research_freeze_policy.md)
- [`docs/current_stage.md`](/Users/wy/MiscProject/multi_factor/docs/current_stage.md)

## 保留分类

### 必须保留在项目内

这些内容体积相对可控，或直接承载当前结论、治理主键、审计路径和可复查摘要。

- `artifacts/research_registry/`
  - 研究轮次登记、候选方案登记、失败证据、预注册、阶段总结和治理审计。
  - 这是当前项目最重要的过程证据层之一，不应为节省空间删除。
- `artifacts/fixed_test/`
  - 历史固定测试、trainval-only 读数、诊断摘要和阶段性评估产物。
  - 保留路径名，但解释时必须披露其证据等级；不能自动视为 OOS。
- `artifacts/run_state/project_panels_research_trainval_20211231_20260429/`
  - 当前 trainval-only 研究快照的项目侧面板。
  - 删除会提高复验成本。
- 当前仍被文档和测试引用的 `artifacts/run_state/confirmatory_*`、`artifacts/run_state/exploratory_*`、`artifacts/run_state/reversal_*` 等小规模或结论绑定运行态。
  - 保留标准是是否被当前 decision record、source-chain audit、测试 fixture 或阶段总结直接引用。

### 优先归档到项目外

这些内容主要是大体量历史运行态。它们对追溯过程有价值，但不应长期压在当前工作目录里。

- `artifacts/run_state/signaldiag_*`
  - 旧单信号诊断运行态。
  - 结论应以 `research_registry/` 中的 round 总结和阶段记录为准。
- `artifacts/run_state/screendiag_*`
  - 旧组合相容性筛查运行态。
  - 适合整体移出项目目录后保留一段观察期。
- `artifacts/run_state/fullchain_*`
  - 旧探索性 full-chain 尝试。
  - 当前不作为独立 OOS 证据，归档前应确认对应阶段总结已存在。
- `artifacts/run_state/baseline_chain_20260417_105228`
  - 历史 baseline chain 运行态。

推荐归档方式：

- 移到项目外独立归档目录，例如 `/Users/wy/MiscProject/_archive/multi_factor_run_state_<date>/`。
- 先移动，不直接删除。
- 观察 `2-7` 天，确认没有当前文档、测试、脚本或审计任务引用后，再决定是否长期冷存或删除。

### 可重建或可删除

这些内容不是当前证据主干，删除前仍应先确认没有人工补录内容。

- `.tmp/`
  - 临时目录，可删除。
- `scripts/__pycache__/`
  - Python 缓存，可删除。
- `artifacts/run_state/sample_attempt_archive/`
  - 仅保存少量样例 attempt；如果没有人工补录的 acceptance report，可删除或转入外部归档。

## 清理顺序

推荐顺序：

1. 先清理缓存和临时目录。
2. 再外部归档 `signaldiag_*` 与 `screendiag_*`。
3. 再外部归档旧 `fullchain_*` 与 `baseline_chain_20260417_105228`。
4. 保留 `research_registry/`、`fixed_test/`、当前 trainval project panels 和仍被当前审计链引用的 run_state。

任何清理动作都不应改变研究结论，也不应把历史 trainval-only 证据提升为 OOS 证据。
