# Data-Layer Implementation Note: D10 Holding Period

**Status:** Design only, no new round registered. Preserved as future optional validation task.

**Current priority:** Low. Execution path recomputation would require ~3-5h of engineering. Expected insight is marginal (turnover ~0.20 → ~0.10) and unlikely to change the current 6/9 ceiling. Not recommended for immediate execution. If future reopening is needed, this is the first-priority task.

**Preceded by:** `rr_framework_d10_holding_period_20260501` — invalidated (run_state patch ineffective).

---

## 1. 为什么 run_state patch 不生效

`build_portfolio_artifacts.py` 的 `pre_holdings_positions_t` 视图使用以下数据源：

```sql
FROM execution_state_t e   ← 来自 run_state 生成的 execution_state_daily.parquet
INNER JOIN mapped_execution_targets_t t  ← 来自 run_state
INNER JOIN project_execution_panel_t p  ← 来自 project_execution_panel.parquet（数据层）
```

`project_execution_panel_t` 包含 `actual_exit_date`、`exit_delay_days`、`execution_delayed_realized_return` 等关键字段。portfolio builder 使用 `planned_exit_date` 来决定持仓生命周期（何时到期、退出、延迟），但这个字段实际上来自：

```
execution_state_daily.parquet.planned_exit_date
    ← 由 build_project_panels.py 在数据层预计算
    ← 公式: 基于 label_panel 中的 planned_exit_date 字段
```

我之前的补丁修改了 `execution_state_daily.parquet` 中的 `planned_exit_date`，但 portfolio builder 的 `pre_holdings_positions_t` 通过 JOIN `execution_state_t` 读取它。理论上应该生效。实际未生效的原因可能是：

1. `execution_state_t` 的 JOIN 条件（run_id, attempt_id, instrument, signal_date）与 `project_execution_panel_t` 的 `planned_exit_date` 存在覆盖关系
2. portfolio builder 使用了 `planned_exit_date` 字段来计算持仓周期，但 D10 的持仓在 D5-D10 期间的新 signal_date 上可能产生冲突

**实际上，所有指标完全一致的原因更可能是：D10 的补丁只改变了 planned_exit_date 的字符串值，但 portfolio builder 内部重新计算了 effective exit date 并覆盖了它。**

---

## 2. D10 要改哪些上游脚本

### 必须改的脚本

| 脚本 | 改动 | 原因 |
|---|---|---|
| `build_project_panels.py` | `planned_exit_date` 计算逻辑：从 `signal_date + 5` 改为 `signal_date + 10` | 这是 planned_exit_date 的唯一权威来源 |
| `build_run_state_skeleton.py` | execution_state 中的 `planned_exit_date` 继承 | 如果从 panel 继承，无需额外改动 |

### 不改的脚本

| 脚本 | 理由 |
|---|---|
| `build_portfolio_artifacts.py` | 已读取 execution_state 中的 planned_exit_date，无需改动 |
| `build_fixed_test_minimal.py` | 已读取 portfolio 产物的 exit_delay_days 等字段，无需改动 |
| `build_confirmatory_validation_readout.py` | 同上 |

### 构建流程

```
build_project_panels.py → 生成 project_execution_panel.parquet
  └─ planned_exit_date = signal_date + 10 (new)
  └─ label_5d_next_open_close (unchanged, tests D5→D10 consistency)
  
build_run_state_skeleton.py → 读取 execution_panel → generation_state
  └─ planned_exit_date 继承自 execution_panel (unchanged logic)
  
build_portfolio_artifacts.py → 使用 execution_state
  └─ 持仓生命周期自动延长 (unchanged)
```

---

## 3. 是否仍能视为单一 changed_dimension = holding_period

**是。** 改动 chain：

```
changed_dimension = holding_period
具体实现：build_project_panels.py 中 planned_exit_date 从 +5 改为 +10
```

虽然需要修改上游数据脚本，但这是实现单一概念改动的必要工程步骤。所有其他参数（TopK、cohort count、refresh、cost model、benchmark、signal）保持不变。

**类比：** 之前 `holding_cohort_count` 从 26 改为 5/10 时，也是通过 builder 参数实现的（`--holding-cohort-count 5/10`），不需要改数据层。但 holding_period 深入数据层面，因为它影响 label 定义和 execution panel 的预计算字段。

---

## 4. 对历史 D5 round 的可复现性影响

**无影响。** D10 改动只影响：
1. `build_project_panels.py` 中的 `planned_exit_date` 生成逻辑
2. 对于 D5 round，使用现有 snapshot 中的 D5 execution panel（不受 D10 builder 逻辑影响）

历史 D5 round 使用的是 **已冻结的 snapshot**（`warehouse_20260429_trainval_20211231`）中的执行面板。这些面板不会被新的 builder 逻辑覆盖。D10 round 需要使用新 snapshot。

---

## 5. 最小实现路径

```
1. 创建 D10 版本的项目面板：
   在 build_project_panels.py 中新增参数 --holding-period-days (default=5)
   当传入 --holding-period-days 10 时，planned_exit_date = signal_date + 10

2. 用新面板创建 run 目录：
   python build_project_panels.py --snapshot-id ... --holding-period-days 10 --run-id d10_panels
   
3. 使用新面板运行标准链路：
   build_baseline_model_scores.py (unchanged)
   build_run_state_skeleton.py (unchanged)
   build_portfolio_artifacts.py (unchanged)
   build_fixed_test_minimal.py (unchanged)
```

**总改动量：** 1 个文件（`build_project_panels.py`），约 5-10 行。

---

## 6. 建议

**值得继续做 data-layer D10 implementation。** 理由：

1. **实现成本极低**（1 个文件，5-10 行）。holding_period 是 framework redesign 的核心杠杆。
2. **不改任何下游脚本**。所有 pipeline 兼容 planned_exit_date 的任意值。
3. **对历史 round 无影响**。使用不同 snapshot 即可隔离。
4. **如果 D10 成功**，直接回答 execution-feasibility gap 问题。如果失败，可干净地关闭 framework redesign 方向。

### 风险等级：低

| 风险 | 等级 | 缓解 |
|---|---|---|
| 实现错误 | 低 | 5-10 行，可 code review |
| 历史 round 复现 | 无 | 不同 snapshot |
| 下游不兼容 | 无 | 已读 planned_exit_date，任意值 |
| signal 半衰期 | 中等 | 预期输出，由 Layer A 判定 |
