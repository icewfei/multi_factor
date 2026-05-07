# research_registry

本目录承载本项目的最小研究登记与失败证据骨架。

当前约定：

- `candidate_scheme_registry.jsonl`
  - 方案登记册
  - 每一行代表一个正式命名后的 `candidate_scheme_id`
  - 追加式维护，不得重写既有 `candidate_scheme_id` 的身份定义
- `research_round_registry.jsonl`
  - 研究轮次登记册
  - 每一行代表一个 `research_round_id`
- `scheme_attempt_log.jsonl`
  - 方案尝试日志
  - 以后每次 `run_state` 尝试都应自动追加一行
  - 不论成功还是失败，都应保留
- `failure_evidence_log.jsonl`
  - 失败证据日志
  - 只记录失败分支
- `research_rounds/<research_round_id>/preregistration.json`
  - 单轮研究的最小预注册 / 登记文件
  - 当前可以先作为治理骨架使用；进入确认性研究后必须补齐总纲 `7.5` 的全部字段
- `templates/single_signal_discovery_prereg_template_20260425.json`
  - 未来 `single-signal discovery(单信号发现)` 轮次的参考模板
  - 已内置 `dedup note(去重说明)` 字段
- `future_signal_naming_and_intake_rules_20260425.{md,json}`
  - 未来信号命名与立项检查规则
  - JSON 版本可供脚本读取
- `/Users/wy/MiscProject/multi_factor/scripts/preflight_single_signal_round.py`
  - 未来 `single-signal discovery(单信号发现)` round 的启动前预检入口
  - 会先调用 intake checker(立项检查器)，通过后才视为可启动
- `/Users/wy/MiscProject/multi_factor/scripts/create_single_signal_round_skeleton.py`
  - 未来 `single-signal discovery(单信号发现)` round 的骨架生成入口
  - 会从 canonical template(标准模板) 生成新的 preregistration，并在 round registry 追加一条 `registered_not_started`

使用原则：

- `candidate_scheme_id` 必须先注册，再进入正式 run-state 尝试
- `candidate_scheme_id` 一旦注册，不得重命名复用
- 正式 full-chain 运行必须同时提供：
  - `candidate_scheme_id`
  - `research_round_id`
- 对应 `research_round_id` 的 `preregistration.json` 必须至少声明：
  - `changed_dimension`
  - `change_control_rule = single_dimension_only`
- 若缺少注册、缺少 preregistration、或未声明单维改动，正式 full-chain 必须拒跑
- 未来新的 `single-signal discovery(单信号发现)` prereg 应先通过：
  - `/Users/wy/MiscProject/multi_factor/scripts/check_preregistration_intake.py`
- 更推荐直接用启动前预检入口：
  - `/Users/wy/MiscProject/multi_factor/scripts/preflight_single_signal_round.py --research-round-id <round_id>`
- 新 round 更推荐先用骨架生成入口：
  - `/Users/wy/MiscProject/multi_factor/scripts/create_single_signal_round_skeleton.py --research-round-id <round_id>`
- 之后填完 `signal_pool(信号池)` 和 `planned_candidate_scheme_ids(计划候选)`，再跑启动前预检
- 现有 round4/5/6 的 batch runner 现在也会在脚本开头自动执行同一套预检
- `scheme_attempt_log.jsonl` 是“尝试历史”
- `failure_evidence_log.jsonl` 是“失败分支摘要”
- 两者都不能替代正式 fixed test / walk-forward 报告
