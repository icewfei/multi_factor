# parquet_duckdb Trainval-Only Snapshot Build Runbook

## 目的

把上游 `parquet_duckdb` 数据仓真正产出一个**不含测试集**的 research snapshot(研究快照)，用于后续 `confirmatory research(确认性研究)`。

本 runbook 对应的项目侧治理规格是：

- 方案文档：[research_snapshot_trainval_only_plan_20260429.md](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_snapshot_trainval_only_plan_20260429.md)
- 机器规格：[research_snapshot_trainval_only_spec_20260429.json](/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_snapshot_trainval_only_spec_20260429.json)
- 校验脚本：[validate_research_snapshot_trainval.py](/Users/wy/MiscProject/multi_factor/scripts/validate_research_snapshot_trainval.py)

目标 snapshot：

- `proposed_snapshot_id(建议快照ID) = warehouse_20260429_trainval_20211231`
- `source_market_cutoff_date(源级市场数据截止日) = 20211231`
- `expected_last_signal_date_with_full_D5_horizon(预期最后完整D5窗口信号日) = 20211224`

## 先说结论

上游当前的 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py) 还**不能直接**产出这个 snapshot，因为它目前：

- 只有 `--sqlite-db` 参数
- 自动生成 `snapshot_id`
- 构建完成后会自动 `activate_current_snapshot`
- 没有任何 `cutoff_date(截断日期)` 或 `trainval_only` 逻辑

所以正确路径不是手工删文件，而是先在上游 builder 里补一组最小治理参数，再按下面步骤构建。

## 代码改动清单

### 1. CLI 参数

在 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:2194) 的 `main()` 里新增这些参数：

- `--snapshot-id`
- `--snapshot-purpose`
  - 建议取值：`full` / `trainval_only`
- `--source-market-cutoff-date`
  - 本次固定为 `20211231`
- `--skip-activate-current`
  - 本次必须启用

建议行为：

- 未传 `--snapshot-id` 时，保持原来的时间戳命名
- `snapshot-purpose=full` 时，保持现有全量行为
- `snapshot-purpose=trainval_only` 时，启用下面的裁切逻辑

### 2. 先裁基础市场/状态表，再生成 research 表

最稳的实现方式是：

1. 先照常构建 `mart.calendar / mart.bars_daily / mart.benchmark_daily / mart.benchmark_aux_daily / mart.limit_rules_daily / mart.tradability_daily / mart.instrument_status_daily / mart.terminal_event_daily`
2. 在生成 `labels_daily / execution_path_daily / sample_eligibility_daily` 之前，统一按 `source_market_cutoff_date = 20211231` 裁切

建议新增一个 helper，例如：

```python
def apply_trainval_cutoffs(con: duckdb.DuckDBPyConnection, market_cutoff_date: str) -> str:
    signal_cutoff_date = con.execute(
        f"""
        SELECT MAX(trade_date)
        FROM mart.calendar
        WHERE next_trade_date_5 <= '{market_cutoff_date}'
        """
    ).fetchone()[0]
    if signal_cutoff_date is None:
        raise ValueError("无法从 mart.calendar 推导 signal_cutoff_date")

    con.execute(f"DELETE FROM mart.calendar WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.bars_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.benchmark_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.benchmark_aux_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.limit_rules_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.tradability_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.instrument_status_daily WHERE trade_date > '{market_cutoff_date}'")
    con.execute(f"DELETE FROM mart.terminal_event_daily WHERE trade_date > '{market_cutoff_date}'")

    return signal_cutoff_date
```

这一步的目的，是保证所有 `D0/D1/D5` 依赖的底层日期窗先被切干净。

### 3. `labels_daily` 需要额外限制

当前定义在 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:1274)。

需要在末尾补一个 `WHERE`，确保：

- `b.trade_date <= signal_cutoff_date`
- `cal.next_trade_date_5 <= source_market_cutoff_date`

也就是：

```sql
...
FROM mart.bars_daily b
LEFT JOIN mart.calendar cal
    ON b.trade_date = cal.trade_date
LEFT JOIN mart.bars_daily d1
    ON b.ts_code = d1.ts_code AND cal.next_trade_date_1 = d1.trade_date
LEFT JOIN mart.bars_daily d5
    ON b.ts_code = d5.ts_code AND cal.next_trade_date_5 = d5.trade_date
WHERE b.trade_date <= '{signal_cutoff_date}'
  AND cal.next_trade_date_5 <= '{source_market_cutoff_date}'
```

### 4. `execution_path_daily` 需要多一道 `actual_exit_date` 保护

当前定义在 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:1338)。

这张表不能只切 `trade_date`，因为我们已经验证过：

- 即使 `trade_date <= 20211224`
- `actual_exit_date(实际退出日)` 仍可能延到 `2022`

所以最终 `SELECT` 外层必须再加：

```sql
WHERE terminal_event_base.trade_date <= '{signal_cutoff_date}'
  AND terminal_event_base.planned_exit_date_D5 <= '{source_market_cutoff_date}'
  AND (
      terminal_event_base.actual_exit_date IS NULL
      OR terminal_event_base.actual_exit_date <= '{source_market_cutoff_date}'
  )
```

### 5. `sample_eligibility_daily` 跟随 `signal_cutoff_date`

当前定义在 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:1507)。

末尾补：

```sql
WHERE b.trade_date <= '{signal_cutoff_date}'
```

### 6. manifest 里补治理字段

在 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:1784) 的 `collect_metadata()` 返回结果里，建议追加：

- `snapshot_purpose`
- `source_market_cutoff_date`
- `signal_cutoff_date`
- `trainval_only = true/false`
- `activation_policy = activated_current / registry_only`

这样后续项目侧就能直接验证这个 snapshot 是否真的是“治理隔离版”。

### 7. trainval snapshot 不得顶掉 full snapshot 的 `current`

当前 [build_warehouse.py](/Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py:2246) 之后总会执行：

- `activate_current_snapshot(final_snapshot_root)`
- `update_snapshot_registry(...)`

这次必须改成：

- `trainval_only` 只执行 `update_snapshot_registry(...)`
- 不执行 `activate_current_snapshot(...)`

建议逻辑：

```python
if not args.skip_activate_current:
    activate_current_snapshot(final_snapshot_root)
update_snapshot_registry(snapshot_id, final_snapshot_root, manifest)
```

本次构建必须使用 `--skip-activate-current`。

## 上游实际执行步骤

### 步骤 1. 先备份上游当前指针

备份这两个文件：

- `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/meta/latest_snapshot.json`
- `/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/meta/snapshot_registry.json`

目的：

- 防止 trainval-only snapshot 误覆盖 full snapshot 的日常入口

### 步骤 2. 在上游 `build_warehouse.py` 落地上面的最小改动

这次改动的核心触点只有 5 处：

- `main()` 参数区
- 基础表裁切 helper
- `labels_daily`
- `execution_path_daily`
- `sample_eligibility_daily`

### 步骤 3. 生成 snapshot

修改完上游后，执行：

```bash
python /Users/wy/MiscProject/tushare_data/parquet_duckdb/build_warehouse.py \
  --sqlite-db /Users/wy/MiscProject/tushare_data/SQLite/tushare.db \
  --snapshot-id warehouse_20260429_trainval_20211231 \
  --snapshot-purpose trainval_only \
  --source-market-cutoff-date 20211231 \
  --skip-activate-current
```

预期产物目录：

`/Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/warehouse_20260429_trainval_20211231`

### 步骤 4. 用项目侧 validator 做硬校验

执行：

```bash
python /Users/wy/MiscProject/multi_factor/scripts/validate_research_snapshot_trainval.py \
  /Users/wy/MiscProject/tushare_data/parquet_duckdb/data/snapshots/warehouse_20260429_trainval_20211231
```

必须全部通过这 7 条：

- `calendar_max_trade_date <= 20211231`
- `bars_max_trade_date <= 20211231`
- `labels_max_trade_date <= 20211224`
- `labels_max_planned_exit_date_D5 <= 20211231`
- `execution_max_trade_date <= 20211224`
- `execution_max_actual_exit_date <= 20211231`
- `eligibility_max_trade_date <= 20211224`

### 步骤 5. 人工 spot check(抽查)

建议再手工查 4 件事：

1. `build_manifest.json` 里已经写入：
   - `snapshot_purpose = trainval_only`
   - `source_market_cutoff_date = 20211231`
   - `signal_cutoff_date = 20211224`
2. `latest_snapshot.json` 仍然指向原来的 full snapshot，而不是 trainval-only snapshot
3. `snapshot_registry.json` 新增了 trainval-only snapshot 条目
4. `duckdb/warehouse.duckdb` 可以正常查询 `serving.vw_*`

### 步骤 6. 项目侧切换新 contract

校验通过后，再在本项目生成新的 research contract：

- 文件名：`run_input_contract.research_trainval_20211231.json`

至少更新这些字段：

- `generated_at`
- `snapshot_id`
- `source_root.snapshot_path`
- `notes`

并明确写入：

- `trainval_only research snapshot`
- `test window 2022-01 to 2025-12 excluded by construction`
- `not eligible to be overwritten by current full snapshot contract`

## 通过标准

只有同时满足下面 4 条，这次构建才算完成：

1. 上游生成了 `warehouse_20260429_trainval_20211231`
2. validator 返回 `ok = true`
3. full snapshot 的 `current` 指针没有被覆盖
4. 本项目已切到新的 trainval-only contract

## 当前限制

我这边已经把上游实际构建路径收成可执行清单，但**当前沙箱不能直接改写** `/Users/wy/MiscProject/tushare_data/parquet_duckdb` 仓库本身，所以这份 runbook 现在是“上游落地的精确施工图”。

如果后面你要我继续推进，最顺的下一步是：

- 要么你在上游仓库按这份 runbook 落 patch
- 要么把上游仓库放进可写范围，我就直接把 `build_warehouse.py` 改完
