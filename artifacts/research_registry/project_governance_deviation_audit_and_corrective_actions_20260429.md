# 项目治理偏离审计结论 + 纠偏动作清单

审计日期：`2026-04-29`

审计范围：

- 研究治理执行状态
- 数据时间边界与 `snapshot(快照)` 使用
- `exploratory research(探索性研究)` 与 `confirmatory research(确认性研究)` 分层执行
- `fixed_test(固定测试)` / `walk_forward(滚动前推)` / `shadow_tracking(影子跟踪)` 的主线晋升准备度

---

## 一句话结论

当前项目已经形成了**较强的数据与工程基础设施**，但研究推进已经明显**超前于制度执行**。

正式审计结论是：

- 存在 `test-set visibility breach risk(测试集可见性违规风险)`，且这是当前最严重问题
- 存在 `search-space explosion(搜索空间爆炸)`，已显著超出总纲预算
- 存在 `zero confirmatory studies(确认性研究为零)`，导致当前所有优劣判断都不能用于主线晋升
- 存在 `Alpha158 bulk-pool governance drift(Alpha158 整包导入式治理偏移)`
- 因此，**当前阶段应立即停止继续扩 exploratory 候选池，先做治理纠偏，再恢复研究推进**

---

## 1. 已证实事实

### 1.1 `research_round_count(研究轮次数) = 67`

- 当前 `research_round_registry.jsonl` 中共有 `67` 个研究轮次
- `research_tier(研究层级) = exploratory(探索性)` 的轮次为 `67 / 67`
- 没有任何一轮被登记为 `confirmatory(确认性)`

### 1.2 `candidate_scheme_count(候选方案数) = 345`

- 当前 `candidate_scheme_registry.jsonl` 中共有 `345` 个候选方案
- 状态分布：
  - `signal_edge_positive(正向边际优势) = 54`
  - `signal_edge_mixed(混合边际优势) = 183`
  - `signal_edge_negative(负向边际优势) = 47`
  - `composability_screen_mixed(组合相容性混合) = 38`
  - `weak_candidate(弱候选) = 23`

### 1.3 主研究数据快照几乎都落在同一全量 `snapshot(快照)` 上

- 候选注册表中的 `snapshot_id` 分布：
  - `warehouse_20260418_181408 = 336`
  - `warehouse_20260413_165753 = 9`
- 当前运行合同默认指向：
  - `snapshot_id = warehouse_20260418_181408`
- 该快照覆盖到 `2026-04-10`，因此**包含总纲中定义的测试集区间 `2022-01 ~ 2025-12`**

### 1.4 `fixed_test(固定测试)` 产物已存在，但尚未形成合规主线证据

- `artifacts/fixed_test/` 目录下已有多次运行产物
- 但抽查 `fixed_test_manifest.json` 可见：
  - `candidate_scheme_id = None`
  - `research_round_id = None`
  - `run_type = None`
  - `snapshot_id = None`
- 这说明当前 `fixed_test` 更多是**探索性评估产物**，而不是已经治理绑定的正式主线晋升证据

### 1.5 `walk_forward(滚动前推)` 与 `shadow_tracking(影子跟踪)` 尚未真正启动

- `artifacts/walk_forward/` 当前只有 README
- `artifacts/shadow_tracking/` 当前只有 README
- 因此主线晋升所需的后两层正式证据链尚未建立

### 1.6 `Alpha158 exact canonical(Alpha158 精确定义线)` 已完整跑穿

- `Alpha158 exact 158` 已完成全量执行
- `30 / 30 standalone positive(30/30 个单信号正向 keeper)` 已全部完成相对 `v18` 的 `composability screening(组合相容性筛查)`
- 结果为：
  - `composability_screen_promising(组合相容性较有希望) = 0 / 30`
  - `composability_screen_mixed(组合相容性混合) = 30 / 30`

这条线的研究结论已经明确，应当冻结，不再继续 `Alpha158 -> v18 direct overlay(直接覆盖层)` 微调。

---

## 2. 与总纲的偏离项

### 2.1 `test-set visibility(测试集可见性)` 偏离  🔴 严重

总纲写死的制度边界：

- `训练集 = 2010-01 ~ 2018-12`
- `验证集 = 2019-01 ~ 2021-12`
- `测试集 = 2022-01 ~ 2025-12`
- 测试集主线冻结前不得查看
- 查看后永久失去 `OOS qualification(样本外资格)`
- 测试集必须物理隔离、加密托管

而当前实际情况是：

- 主体研究使用的 `snapshot` 已覆盖测试集区间
- 大多数探索性诊断、候选比较、family 微调、signal-edge 判断，都已经在这个全量快照上完成

审计判断：

- 不能再把当前 snapshot 上的任何测试区间结果表述为“独立样本外证明”
- 当前项目已经出现**实质性的测试集可见性问题**

### 2.2 `search-space budget breach(搜索空间预算突破)`  🔴 严重

总纲预算上限写明：

- `exploratory_max_raw_candidate_factors(探索性原始候选因子上限) = 30`
- `exploratory_factor_pool_max(探索性因子池上限) = 30`
- `exploratory_max_strategy_variants(探索性策略变体上限) = 12`

而当前实际情况：

- `candidate_scheme_count(候选方案数) = 345`
- `2026-04-28` 单日新增候选 `235`
- `2026-04-28` 单日新增研究轮次 `30`

审计判断：

- 当前搜索空间已经远超总纲预算
- 当前所有 `signal_edge_positive(正向边际优势)` 结果都面临明显的 `multiple-testing risk(多重比较风险)`
- 在未做研究空间调整审计前，不能把这些结果视为“足够稳健”

### 2.3 `confirmatory-research absence(确认性研究缺位)`  🟡 中高风险

总纲要求确认性研究必须同时满足：

- `must preregister(必须预注册)`
- `single_dimension_only(必须单维改动)`
- `fixed boolean success rule(必须固定布尔表达式通过标准)`
- `fixed_test_run_id binding(必须绑定固定测试运行主键)`

而当前实际情况：

- `67 / 67` 轮次全部仍处在 `exploratory`
- 没有任何一轮满足完整的确认性研究门槛

审计判断：

- 当前所有“某方案优于某方案”的结论，都只能算探索性证据
- 这些证据可用于收缩候选池，但不能用于主线晋升

### 2.4 `Alpha158 bulk-pool governance drift(Alpha158 整包导入式治理偏移)`  🟡 中风险

总纲写明：

- `Alpha158` 等大因子池不得整包进入主线候选池

而当前实际情况：

- `round11b` 以 `qlib Alpha158 exact 158` 为目标执行全量扫描
- 随后又对其正向 keeper 池做了全覆盖 `composability screening`

审计判断：

- 这属于**探索层大规模白名单外扫矿**
- 虽然它没有真正晋升为主线，但已经构成明显治理偏移
- 后续若继续使用 Alpha158，只能作为 `standalone reserve cards(单信号储备卡片)` 或新独立 family seed，不得再整包扩展主线

### 2.5 `research-over-institution(研究超前于制度)`  🔴 核心病灶

框架设计顺序应当是：

1. 建可信基础设施
2. 控制规模的探索
3. 收缩候选池
4. 确认性研究
5. `fixed_test + walk_forward + shadow_tracking`
6. 主线晋升

当前实际顺序更接近：

1. 基础设施做到可用
2. 大规模 exploratory 扫描迅速展开
3. 研究池膨胀到数百候选
4. 确认性研究 / `walk_forward` / `shadow_tracking` 仍为空

审计判断：

**核心问题不是某个因子方向研究错了，而是治理次序被打乱了。**

---

## 3. 风险等级汇总

| 风险项 | 严重度 | 审计结论 |
|---|---|---|
| `test-set visibility(测试集可见性)` | `🔴` | 已实质触碰，必须先处理 |
| `search-space explosion(搜索空间爆炸)` | `🔴` | 明确超预算 |
| `zero confirmatory studies(确认性研究为零)` | `🟡` | 目前所有结果都只能停留在 exploratory |
| `Alpha158 bulk import drift(Alpha158 整包导入偏移)` | `🟡` | 已发生，需停止扩张 |
| `walk_forward / shadow missing(滚动前推与影子跟踪缺失)` | `🟡` | 主线晋升证据链未建立 |
| `fixed_test governance binding weak(固定测试治理绑定不足)` | `🟡` | 有产物，但不够正式 |

---

## 4. 正式纠偏动作清单

### 4.1 `P0(最高优先级)` 立即冻结新增 exploratory 候选扩张

立即执行：

- 停止新的 `single-signal discovery(单信号发现)` 批量开跑
- 停止新的 `Alpha158` 扩池、overlay、family 微调线
- 停止任何会继续放大搜索空间的 exploratory 大批量诊断

冻结范围：

- 新候选注册
- 新 discovery round 注册
- 新 Alpha158 扫描
- 新 direct overlay screen

允许保留：

- 对已有证据做整理、归并、审计、治理修复
- 对已有 `reserve cards(储备卡片)` 做去重与规范化

### 4.2 `P0(最高优先级)` 处理测试集可见性问题

推荐走 `retro-split snapshot(回溯划分新快照)` 路线：

1. 新建一个**不含测试集**的研究快照
   - 仅包含：
     - `训练集 = 2010-01 ~ 2018-12`
     - `验证集 = 2019-01 ~ 2021-12`
   - 不包含：
     - `测试集 = 2022-01 ~ 2025-12`
     - `观察区 = 2026-至今`

2. 在这个新 snapshot 上重建：
   - `project_sample_panel`
   - `project_label_panel`
   - `execution_path / tradability / eligibility` 相关项目侧面板

3. 明确治理声明：
   - 当前全量 snapshot 上形成的结果，均不再声称具备独立 `OOS(样本外)` 资格
   - 它们只作为 exploratory evidence archive

### 4.3 `P0(最高优先级)` 收缩候选池，形成 `confirmatory shortlist(确认性短名单)`

目标：

- 从当前 `345` 个候选中，收缩到 `3-5` 个非冗余候选

短名单筛选原则：

- 必须来自不同机制簇
- 必须有较清晰的经济解释
- 必须已有较充分 exploratory 证据
- 必须避免近邻窗口簇重复入围

建议动作：

- 建一份 `keeper consolidation v2(保留信号归并 v2)` 清单
- 每个机制簇只保留 `1` 个 canonical representative
- 明确：
  - `keep for confirmatory`
  - `keep as reserve only`
  - `archive as explored but not promoted`

### 4.4 `P1(高优先级)` 预注册第一轮真正的 `confirmatory research(确认性研究)`

要求一次只回答一个问题：

- 只允许 `single_dimension_only(单维改动)`
- 必须提前冻结：
  - `candidate_scheme_id`
  - 候选列表
  - 时间分区
  - 成功布尔表达式
  - `fixed_test_run_id`
  - `snapshot_id`

通过标准必须写成布尔表达式，例如：

- `(annual_relative_return > X) AND (max_drawdown < Y) AND (turnover < Z)`

不得再使用：

- “看起来更好”
- “接近通过”
- “静态诊断较强”

作为确认性通过依据。

### 4.5 `P1(高优先级)` 补正式 `fixed_test(固定测试)` 治理绑定

当前 `fixed_test` 已有丰富产物，但需要补齐治理字段：

- `candidate_scheme_id`
- `research_round_id`
- `run_type = fixed_test`
- `snapshot_id`
- `code_hash`
- `execution_logic_version`

否则这些产物只能算“探索性固定格式回测”，不能算正式固定测试证据。

### 4.6 `P1(高优先级)` 启动 `walk_forward(滚动前推)` 最小闭环

当前 `walk_forward` 目录为空，必须补第一版最小闭环：

- 固定窗口生成协议
- 固定 `purge_gap(清洗间隔)`
- 固定产物 schema
- 固定 audit summary

目标不是立刻跑很多版本，而是让主线晋升所需的第二条正式证据链先存在。

### 4.7 `P2(中优先级)` 补 `shadow_tracking(影子跟踪)` 骨架，但暂不拉长线

当前不需要立即进入长周期 shadow 运行，但应先补：

- `shadow_run_id`
- 持仓对照 schema
- 日级偏差审计 schema
- 相对收益与执行偏差摘要

这样未来进入观察区时，不会再次出现“研究先跑，制度后补”的问题。

---

## 5. 当前研究线的正式处理建议

### 5.1 `v18 family line`

- 继续冻结 `price_volume_v18_refresh_hysteresis`
- 仅作为 `working_reference(工作基准)`
- 暂不继续做新的组合层微调

### 5.2 `Alpha158 line`

- 停止 `Alpha158 -> v18 direct overlay(直接覆盖层)` 微调线
- 保留 `Alpha158 keepers` 为 `standalone reserve cards(单信号储备卡片)`
- 未来若重启，只能改成：
  - 新独立 family seed
  - 或门控型、稀疏型、否决型 overlay 问题

### 5.3 `exploratory discovery line`

- 暂停继续扩池
- 等 snapshot 边界与 confirmatory 短名单建立后，再决定是否重开

---

## 6. 正式阶段判断

当前项目并不是“研究无效”，而是：

- `infrastructure(基础设施)` 已经做到了可用且相当强
- `exploratory evidence(探索性证据)` 已经大量积累
- 但 `governance execution(治理执行)` 明显落后于研究推进速度

因此，当前最合理的项目动作不是继续找新信号，而是：

1. 冻结探索扩张
2. 修复 `snapshot` 边界
3. 收缩候选池
4. 启动第一轮真正合规的确认性研究
5. 再进入正式 `fixed_test / walk_forward / shadow_tracking`

---

## 最终审计结论

本次审计的最终结论是：

**项目当前确实存在重大治理偏离，但仍处于可纠偏、可恢复制度可信度的阶段。**

前提是必须立刻执行以下三件事：

- 停止继续扩大 exploratory 搜索空间
- 正式处理测试集可见性问题
- 从“继续找更多候选”切换到“收缩候选并启动确认性研究”

如果不做这三件事，后续新增结果的研究价值会快速下降，且主线晋升证据将越来越难恢复可信度。
