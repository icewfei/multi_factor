# 多因子项目 v1 实施计划

用途：
- 作为 `/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md` 的配套执行文件
- 记录当前周期与下一阶段的实施安排、优先级、节流规则与推进节奏

权威关系：
- 总纲负责长期稳定、可复现、可审计的制度边界
- 本文件负责当前阶段的执行安排
- 若本文件与总纲冲突，以总纲为准

适用时间点：
- 截至 `2026-04-30`

---

## 1. 当前周期定位

当前周期已从“治理纠偏 + 确认性收缩”推进到“确认性收口 + reserve 池治理 + 新问题定义准备”阶段。

当前周期目标不是：
- 恢复大规模 exploratory(探索性研究) 扩张
- 继续整包扫描大因子池
- 在已看过的全量 snapshot(快照) 上继续声称 OOS(样本外) 结论
- 同时并行推进多条 family(家族) 微调线

当前周期目标是：
- 保持总纲正文不动，只修正执行安排
- 把 research snapshot(研究快照) 切换到不含测试集的 trainval-only 口径
- 冻结 exploratory archive(探索性档案) 与 working reference(工作基准)
- 固化 reserve atomic keeper(储备原子信号) 池并完成 canonical 因子去重口径
- 只允许先立项后执行的新问题定义推进，不恢复已暂停的微调线

---

## 2. 当前冻结边界

本周期默认纪律：

- `/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md` 是唯一权威主文档
- 本文件只更新当前执行安排，不回写总纲原则
- 暂停新的大批量 exploratory(探索性研究) 候选扩张
- 暂停新的 Alpha158 整包扫描、overlay(覆盖层) 扩张与多线 family 微调
- 不再把旧全量 snapshot 上的结果表述为独立 OOS(样本外) 证据
- 不新增任何绕开 snapshot / prereg / fixed boolean rule(固定布尔通过规则) 的研究流程

工作方式：

- 所有问题先映射到总纲正文、附录 C、附录 D
- 研究层默认先看 registry(登记册) 与既有 prereg(预注册)
- 若需要新增临时安排，优先更新本文件，而不是回写总纲
- 允许继续整理既有 exploratory evidence(探索性证据)、去重、归档、治理修复

---

## 3. 数据基线与研究快照

当前正式确认：

- `/Users/wy/MiscProject/tushare_data/parquet_duckdb` 是跨项目共享的独立数据源
- 开发检查可读取 `data/current`
- 正式研究、fixed test、`walk-forward`、影子跟踪必须冻结到 `data/snapshots/<snapshot_id>`
- `current` 仅用于开发便利，不得作为正式审计主键
- 项目默认运行环境固定为 `/opt/anaconda3/envs/quant_trade`

当前 research snapshot(研究快照) 执行口径：

- trainval-only snapshot(仅训练+验证快照)：
  - `snapshot_id = warehouse_20260429_trainval_20211231`
- 项目侧正式 research contract(研究合同)：
  - `/Users/wy/MiscProject/multi_factor/contracts/run_input_contract.research_trainval_20211231.json`
- trainval project panels(项目侧面板)：
  - `/Users/wy/MiscProject/multi_factor/artifacts/run_state/project_panels_research_trainval_20211231_20260429`

口径说明：

- 当前 confirmatory(确认性研究) 与后续治理修复，默认基于 trainval-only snapshot 继续
- 历史全量 snapshot 上形成的结果，统一降级为 exploratory archive(探索性档案)，不再声称具备独立 OOS(样本外) 资格

与总纲的对应关系：

- 数据源边界定义见总纲 `5.1A`
- 运行环境基线见总纲 `5.2A`
- `snapshot_id`、PIT、执行语义与正式评估约束以总纲正文为准

---

## 4. 已完成的关键基础设施与治理修复

当前已完成：

- `tradability`、标签、样本资格矩阵、真实清算收益链路
- `TopK + 现金保留 + 不补位` 与标准持仓产物
- fixed test(固定测试) 的最小产物骨架
- research registry(研究登记册) / prereg / intake / round skeleton(轮次骨架) / preflight(预检) 基础治理
- trainval-only snapshot(仅训练+验证快照) 与项目侧 contract 切换
- Alpha158 confirmatory shortlist 与 strict recheck 收口
- `walk-forward` 最小闭环运行（用于继续投入判断）
- `54` 只正向信号物理去重收口为 `25` 个 canonical clusters(标准机制簇)

当前仍未完成或未正式启用：

- `shadow tracking(影子跟踪)`
- 主线晋升所需的完整正式证据链
- 更系统的 research-space audit(研究空间审计) 自动化

明确禁止：

- 在未补齐 `walk-forward` 前，把 confirmatory 结果直接表述为主线晋升完成
- 在 trainval-only 之外重开大规模 exploratory 扫描
- 跳过当前治理修复，直接恢复多线 family 扩张

---

## 5. 当前研究状态与冻结线

当前正式研究判断：

- `price_volume_v18_refresh_hysteresis` 冻结为 `working_reference(工作基准)`
- `Alpha158 -> v18 direct overlay(直接覆盖层)` 研究线正式关闭
- `Alpha158 exact 158` 全量扫描结果仅保留为 `standalone reserve cards(单信号储备卡片)`
- 既有 exploratory discovery / family / composability 结果统一保留在 registry 中，作为证据档案，不再继续扩池

当前 confirmatory(确认性研究) 主结论：

- `price_volume_single_signal_alpha158_vsumd60_v1 = reserve atomic keeper(储备原子信号)`
- `price_volume_single_signal_alpha158_corr30_v1 = reserve atomic keeper(储备原子信号)`
- `price_volume_single_signal_alpha158_cord30_v1 = high-quality reserve atomic keeper(高质量储备原子信号)`
- `active_confirmatory_winner(活跃确认性赢家) = none`
- `strict_confirmatory_winner(严格确认性赢家) = none`
- `Alpha158 confirmatory fine-tuning line(确认性微调线) = pause`

因此当前冻结线是：

- 不恢复 Alpha158 direct overlay(直接覆盖层)
- 不新增 Alpha158 confirmatory shortlist
- 不继续 `corr30 / cord30 / vsumd60` 微调线扩展
- 不重开已暂停的 Alpha158 confirmatory fine-tuning(确认性微调)分支
- 不在旧全量 snapshot 上追加新的正式晋级判断

## 6. 当前允许推进的研究与实现顺序

除非后续再次更新本文件，当前默认推进顺序为：

1. 保持 trainval-only snapshot(仅训练+验证快照) 作为研究默认入口
2. 维护 registry / prereg / fixed test 的治理闭环
3. 围绕 canonical 因子池维护命名、去重、因子卡与登记口径一致性
4. 只允许“新问题定义”先 prereg(预注册) 后执行
5. 在不放松总纲硬规则前提下，再决定是否允许下一阶段正式主线晋升

当前不允许：

- 继续 `vsumd60 / corr30 / cord30` 的 confirmatory 微调迭代
- 未 prereg 就启动新 round
- 在 canonical 池之外用别名或近重复信号重复立项

---

## 7. Codex 节流规则

在低额度周期内，Codex 默认只承担高价值低消耗任务：

- 审阅
- 归纳
- 映射
- 排序
- 治理修复
- 单维 confirmatory 推进

协作纪律：

- 每次只问一个清晰模块
- 优先做单维闭环，避免并行开太多线
- 所有问题都优先引用总纲章节或附录编号
- 优先复用已有 registry / round / fixed test 产物

若后续进入实现周期，则仍应遵守：

- 先做最小可交付物
- 每次改动后先做自审
- 任何新实现都不得绕开总纲既有治理边界

---

## 8. 本周期基础完成标准

- 能明确区分 exploratory archive(探索性档案) 与 confirmatory line(确认性主线)
- 能默认使用 trainval-only snapshot(仅训练+验证快照) 继续推进
- 能明确说明当前 `strict_confirmatory_winner(严格确认性赢家) = none`
- 能明确说明 `Alpha158 confirmatory fine-tuning line(确认性微调线) = pause`
- 能明确说明哪些研究线已冻结、哪些仍允许继续
- 任何新问题都能先映射到总纲某一节，而不是重新从头讨论

---

## 9. 文档引用关系

优先查看顺序：

1. `/Users/wy/MiscProject/multi_factor/项目总纲及计划/项目总纲/new_multifactor_project_framework_v1.md`
2. 本文件

按问题类型查阅：

- 制度边界、评估纪律、字段口径、审计要求：看总纲
- 当前周期安排、下周期优先级、Codex 使用节奏：看本文件
- `tradability + 标签 + 样本资格矩阵 + 真实清算收益` 的可编码规格：看模块规格书
- 新增条款实施检查：看总纲附录 C
- 新增条款 schema：看总纲附录 D

当前执行时的关键补充入口：

- research snapshot 方案：
  - `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/research_snapshot_trainval_only_plan_20260429.md`
- 治理偏离审计：
  - `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/project_governance_deviation_audit_and_corrective_actions_20260429.md`
- Alpha158 微调线暂停收口：
  - `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_cord30_turnover_control_seed_closeout_and_pause_decision_20260430.md`
- 正向因子 canonical 去重清单：
  - `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/positive_signal_canonical_inventory_20260430.md`
