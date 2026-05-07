# Research Snapshot 方案：Train+Validation Only（不含测试集）

方案日期：`2026-04-29`

用途：

- 为项目创建一个**不含测试集 `2022-01 ~ 2025-12`** 的正式 research snapshot(研究快照)
- 让后续 `exploratory freeze(探索冻结后整理)`、`confirmatory research(确认性研究)`、`fixed_test(固定测试)` 的时间边界重新恢复可治理状态

---

## 一句话决策

新 research snapshot 应采用：

- `market/raw data cutoff(市场原始数据截止日) = 20211231`
- `research signal cutoff(研究信号截止日) = calendar 中满足 next_trade_date_5 <= 20211231 的最后一个 trade_date`

在当前交易历法下，这个 `research signal cutoff` 应为：

- `expected_last_signal_date_with_full_D5_horizon(预期最后完整D5窗口信号日) = 20211224`

因此，新的 research snapshot 不是简单地“把数据截到 2021-12-31”，而是要同时满足：

1. `bars / benchmark / tradability / status / calendar` 等基础表不含 `2022-01-01` 及以后的数据
2. `labels / execution_path / sample_eligibility` 等前视研究表，不含任何会把 `D1/D5/actual_exit` 推进到 `2022` 的研究行

---

## 1. 为什么不能只做“日期硬截到 20211231”

如果只是把上游 `bars_daily` 截到 `20211231`，但不重新治理研究层的行边界，会有两个问题：

1. `label_5d_next_open_close(5日开收到收标签)` 需要未来 `D1` 和 `D5`
2. `execution_path_daily(执行路径表)` 需要 `planned_exit_date_D5`，并且真实退出可能存在 `retry open(延迟到后续开盘)`

这意味着：

- `trade_date = 20211229` 的研究行，即使本身落在 2021，也会引用 2022 的未来价格
- 这类行若被保留，本质上仍然消耗测试区间信息

所以 research snapshot 的边界必须分两层：

### 1.1 `source cutoff(源数据截止日)`

- 所有源级市场与状态数据：
  - `raw/*`
  - `warehouse/market/*`
  - `warehouse/state/*`
  - `warehouse/industry/*`
  - `warehouse/fundamental/*`
- 统一要求：
  - 不得包含 `trade_date > 20211231`

### 1.2 `research row cutoff(研究行截止日)`

- 对所有前视研究表：
  - `serving.vw_labels_daily`
  - `serving.vw_execution_path_daily`
  - `serving.vw_sample_eligibility_daily`
- 统一要求：
  - 仅保留 `trade_date <= last_signal_date_with_full_D5_horizon`
  - 其中：
    - `last_signal_date_with_full_D5_horizon = max(trade_date where next_trade_date_5 <= 20211231)`

---

## 2. 新 snapshot 的正式定义

### 2.1 命名建议

建议命名：

- `snapshot_id = warehouse_20260429_trainval_20211231`

命名含义：

- `20260429`：方案生成日 / 新快照建立日
- `trainval`：只用于训练+验证研究
- `20211231`：源级市场数据截止日

### 2.2 时间边界

正式边界：

- `train_window(训练窗口) = 2010-01-01 ~ 2018-12-31`
- `validation_window(验证窗口) = 2019-01-01 ~ 2021-12-31`
- `test_window(测试窗口) = 完全不进入此 snapshot`
- `observation_window(观察区) = 完全不进入此 snapshot`

### 2.3 研究表有效截止规则

对 `labels/execution/eligibility`：

- `market_cutoff_date(市场截止日) = 20211231`
- `signal_cutoff_rule(信号截止规则) = next_trade_date_5 <= 20211231`
- `expected_last_signal_date(预期最后信号日) = 20211224`

这条规则优先于“自然日期 <= 20211231”。

---

## 3. 必须裁剪的对象

### 3.1 上游 snapshot 内部必须重新生成或重裁剪的对象

#### `raw/`

- 保留到 `trade_date / ann_date / end_date / namechange effective date <= 20211231`
- 原则：
  - 所有会影响 `warehouse` 层结果的原始 parquet，都必须从源头裁剪

#### `warehouse/market/`

- `bars_daily`
- `benchmark_daily`
- `benchmark_aux_daily`
- `limit_rules_daily`
- `tradability_daily`

要求：

- 不得出现 `trade_date > 20211231`

#### `warehouse/state/`

- `instrument_status_daily`
- `st_status_interval`
- `terminal_event_daily`

要求：

- `daily` 表不含 `trade_date > 20211231`
- `interval` 表允许存在跨期区间原始定义，但在 `serving` 层映射到日频时不得穿过 `20211231`

#### `warehouse/research/`

- `labels_daily`
- `execution_path_daily`
- `sample_eligibility_daily`

要求：

- `trade_date <= last_signal_date_with_full_D5_horizon`
- `planned_exit_date_D5 <= 20211231`
- `actual_exit_date <= 20211231` 或为空

### 3.2 项目侧必须切换的对象

项目侧不应继续使用：

- [run_input_contract.current.json](/Users/wy/MiscProject/multi_factor/contracts/run_input_contract.current.json)
  中当前指向的 `warehouse_20260418_181408`

项目侧应新增一份 research-only 合同，例如：

- `run_input_contract.research_trainval_20211231.json`

并满足：

- `snapshot_id = warehouse_20260429_trainval_20211231`
- `source_root.snapshot_path = .../data/snapshots/warehouse_20260429_trainval_20211231`

---

## 4. 建议的生成流程

### Step 1. 复制当前 full snapshot 的构建血缘

以当前 full snapshot 为基线：

- `warehouse_20260418_181408`

读取：

- `meta/build_manifest.json`
- `duckdb/warehouse.duckdb`
- `warehouse/*`
- `raw/*`

### Step 2. 重新生成一个 trainval-only snapshot

目标不是在项目侧“读时过滤”，而是在上游 `parquet_duckdb` 仓库里生成一个新的不可变 snapshot：

- `snapshots/warehouse_20260429_trainval_20211231/`

### Step 3. 在上游 snapshot 内做两层裁剪

#### Layer A：源表与市场表按 `20211231` 裁剪

- 所有日频 `trade_date` 表直接截断到 `20211231`
- 所有区间型表在映射到日频或 serving 前保证不穿过 `20211231`

#### Layer B：研究表按 `last_signal_date_with_full_D5_horizon` 裁剪

计算规则：

```sql
SELECT max(trade_date)
FROM serving.vw_calendar
WHERE next_trade_date_5 <= '20211231';
```

该结果即：

- `last_signal_date_with_full_D5_horizon`

随后要求：

```sql
trade_date <= last_signal_date_with_full_D5_horizon
AND planned_exit_date_D5 <= '20211231'
AND (actual_exit_date IS NULL OR actual_exit_date <= '20211231')
```

### Step 4. 生成新 snapshot 的 DuckDB serving 入口

新 snapshot 内必须保留同名 serving views：

- `serving.vw_calendar`
- `serving.vw_bars_daily`
- `serving.vw_labels_daily`
- `serving.vw_execution_path_daily`
- `serving.vw_sample_eligibility_daily`

这样项目侧脚本可以继续无侵入切换，只靠 `run_input_contract` 变更 `snapshot_path`

### Step 5. 运行边界校验

新 snapshot 建成后，必须跑专门的 validator：

- `scripts/validate_research_snapshot_trainval.py`

只有全部通过后，才允许它成为确认性研究的默认输入。

---

## 5. 验收标准

### 5.1 `calendar / bars / benchmark` 验收

- `max(trade_date) <= 20211231`

### 5.2 `labels / eligibility / execution` 验收

- `max(trade_date) <= last_signal_date_with_full_D5_horizon`
- `max(planned_exit_date_D5) <= 20211231`
- `max(actual_exit_date) <= 20211231`（忽略空值）

### 5.3 `snapshot contract` 验收

新 run input contract 必须包含：

- `snapshot_id`
- `snapshot_path`
- `generated_at`
- `data_contract_version`
- `execution_logic_version`
- `field_mapping_version`
- `notes` 中明确写明：
  - `trainval_only research snapshot`
  - `test window excluded by construction`

### 5.4 `project-side panel rebuild` 验收

项目侧重建后的：

- `project_sample_panel`
- `project_label_panel`
- `project_execution_panel`

必须全部绑定新 `snapshot_id`。

---

## 6. 与当前全量 snapshot 的角色分工

### `warehouse_20260418_181408`

保留角色：

- exploratory archive(探索历史档案)
- 历史 full-range run-state 复查
- 已完成 fixed test / diagnosis / family trace 的证据归档

不再允许的角色：

- 作为新的确认性研究默认输入
- 作为未来主线晋升的“未污染 OOS”依据

### `warehouse_20260429_trainval_20211231`

新角色：

- 确认性研究默认输入
- 候选收缩后的 train+validation 正式工作底座
- 未来 `fixed_test` 前的唯一 research snapshot

---

## 7. 后续紧接动作

新 research snapshot 方案定义完成后，建议按以下顺序推进：

1. 在上游 `parquet_duckdb` 仓库生成 `warehouse_20260429_trainval_20211231`
2. 跑 `validate_research_snapshot_trainval.py`
3. 新增项目侧 `run_input_contract.research_trainval_20211231.json`
4. 用新 snapshot 重建项目 panels
5. 从当前 `345` 个候选中收缩出 `3-5` 个 `confirmatory shortlist`
6. 只在新 snapshot 上启动第一轮真正确认性研究

---

## 最终方案判断

这次 research snapshot 方案的关键，不是“再建一个旧快照副本”，而是：

- 明确切断测试集时间边界
- 明确切断研究表的前视窗口
- 明确把当前 full snapshot 降级为历史档案
- 让后续确认性研究重新回到制度轨道

正式结论：

**应立即建立 `warehouse_20260429_trainval_20211231` 这类 trainval-only research snapshot，并把它设为后续确认性研究的唯一默认研究输入。**
