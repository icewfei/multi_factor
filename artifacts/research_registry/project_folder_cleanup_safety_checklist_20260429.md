# 项目文件夹安全清理清单

生成时间：`2026-04-29 15:53:05`

用途：

- 为当前项目提供一份**非破坏性优先**的目录清理清单
- 解决“项目目录过大、且有多代理同时工作”时，哪些目录应保留、哪些应先归档、哪些可直接删除的问题

当前体积判断：

- 项目总目录主要压力来自：
  - `/Users/wy/MiscProject/multi_factor/artifacts`
- 其中绝大部分来自：
  - `/Users/wy/MiscProject/multi_factor/artifacts/run_state`

关键体积分布：

- `artifacts/run_state = 158G`
- `signaldiag_* = 85.73G`
- `screendiag_* = 23.73G`
- `fullchain_* = 43.14G`
- `confirmatory_* = 11.48G`
- `project_panels_* = 0.61G`
- `artifacts/fixed_test = 106M`
- `artifacts/research_registry = 6M`

一句话原则：

**保留治理记录与当前主线证据，只归档旧 exploratory 运行态，只直接删除缓存和临时目录。**

---

## 1. 保留

以下目录建议继续放在项目内，不做移动，不做删除。

### 1.1 代码与制度层

- `/Users/wy/MiscProject/multi_factor/contracts`
- `/Users/wy/MiscProject/multi_factor/schemas`
- `/Users/wy/MiscProject/multi_factor/scripts`
- `/Users/wy/MiscProject/multi_factor/项目总纲及计划`

理由：

- 体积小
- 当前仍在持续迭代
- 是研究、执行、治理的真相源

### 1.2 治理与研究登记层

- `/Users/wy/MiscProject/multi_factor/artifacts/research_registry`

理由：

- 只有约 `6M`
- 承载 `research_round_registry(研究轮次登记册)`、`candidate_scheme_registry(候选方案登记册)`、`preregistration(预注册)`、阶段总结和治理审计
- 不应为了省空间删除

### 1.3 fixed test(固定测试) 层

- `/Users/wy/MiscProject/multi_factor/artifacts/fixed_test`

理由：

- 只有约 `106M`
- 是正式证据层，不建议清理

### 1.4 当前 trainval-only 研究基线

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/project_panels_research_trainval_20211231_20260429`

理由：

- 当前确认性研究默认依赖这套 `project panels(项目侧面板)`
- 体积约 `0.61G`
- 删除后会影响当前 confirmatory(确认性研究) 主线复现

### 1.5 当前 confirmatory(确认性研究) 活跃 run_state

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_baseline_v1_trainval_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_cord30_trainval_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_imxd5_trainval_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_reference_v18_trainval_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_vsumd60_trainval_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_vsumd60_seed_liquidity_guard70_trainval_20260429`

理由：

- 这是当前项目正式 confirmatory 证据链的活跃运行态
- 与当前 trainval-only snapshot(仅训练+验证快照) 和最新结论直接相关

---

## 2. 可归档

这一类目录建议**移出项目目录，但先不删除**。

推荐归档方式：

- 移到项目外独立归档目录，例如：
  - `/Users/wy/MiscProject/_archive/multi_factor_run_state_20260429/`

推荐动作：

- 先移动
- 观察 `2-7` 天
- 确认你和 Claude Code 都不再引用后，再做最终删除

### 2.1 全部旧 exploratory signaldiag(单信号诊断) run_state

目录模式：

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/signaldiag_*`

当前规模：

- `286` 个目录
- 约 `85.73G`

理由：

- 这是项目里最大的单类体积来源
- 多数属于已完成的探索性诊断
- 结论已沉淀到 `research_registry(研究登记层)`，原始 `run_state` 可优先归档

### 2.2 全部旧 screendiag(组合相容性筛查) run_state

目录模式：

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/screendiag_*`

当前规模：

- `38` 个目录
- 约 `23.73G`

理由：

- 主要用于 composability screening(组合相容性筛查)
- 当前阶段结论已写入 round 总结与 registry
- 不属于当前唯一活跃 confirmatory 主线

### 2.3 全部旧 exploratory fullchain run_state

目录模式：

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/fullchain_*`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/baseline_chain_20260417_105228`

当前规模：

- `25 + 1` 个目录
- 约 `43.14G + baseline_chain`

理由：

- 多数是历史 baseline / family / challenger 的 exploratory 全链路尝试
- 当前正式主线已切到 trainval-only confirmatory 口径
- 旧全量 snapshot 上的这些运行态不再作为独立 OOS(样本外) 证据使用

### 2.4 归档优先级建议

第一批先归档：

- `signaldiag_*`
- `screendiag_*`

原因：

- 释放空间最大
- 对当前 confirmatory 主线影响最小

第二批再归档：

- `fullchain_*`
- `baseline_chain_20260417_105228`

原因：

- 仍有一定历史参考价值
- 但对当前主线不是必需

---

## 3. 可删除

这一类目录或缓存可以直接删除，风险低。

### 3.1 明确的缓存目录

- `/Users/wy/MiscProject/multi_factor/.tmp`
- `/Users/wy/MiscProject/multi_factor/scripts/__pycache__`

理由：

- 属于缓存或临时目录
- 删除后可自动重建

### 3.2 小型临时归档目录

- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/sample_attempt_archive`

当前规模：

- 约 `360K`

理由：

- 体积很小
- 名称表明其为样例/临时归档性质
- 若你确认其中没有人工补录内容，可直接删除

---

## 4. 不建议现在动的目录

以下目录当前不建议清理：

- `/Users/wy/MiscProject/multi_factor/artifacts/fixed_test`
- `/Users/wy/MiscProject/multi_factor/artifacts/research_registry`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/project_panels_research_trainval_20211231_20260429`
- `/Users/wy/MiscProject/multi_factor/artifacts/run_state/confirmatory_*`

原因：

- 这些目录共同构成当前项目最重要的正式研究与治理证据层
- 现在清理它们，省不了多少空间，但会明显增加复现和审计成本

---

## 5. 建议执行顺序

### Phase 1

- 删除：
  - `.tmp`
  - `scripts/__pycache__`
  - `sample_attempt_archive`

### Phase 2

- 归档：
  - `artifacts/run_state/signaldiag_*`
  - `artifacts/run_state/screendiag_*`

### Phase 3

- 归档：
  - `artifacts/run_state/fullchain_*`
  - `artifacts/run_state/baseline_chain_20260417_105228`

### Phase 4

- 保留：
  - `research_registry`
  - `fixed_test`
  - `project_panels_research_trainval_20211231_20260429`
  - `confirmatory_*`

---

## 6. 当前最稳的一句话动作建议

如果你现在只想做一件事，就做这件事：

**先把 `artifacts/run_state/signaldiag_*` 和 `artifacts/run_state/screendiag_*` 整批移出项目目录归档，不要先删 confirmatory 与 fixed test。**

这一步最可能一次性释放出 `100G+` 空间，同时又基本不伤到当前主线。
