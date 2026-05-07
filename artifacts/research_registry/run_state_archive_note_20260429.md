# run_state 归档记录

归档日期：`2026-04-29`

本次执行的是**非破坏性归档**，未删除数据，只将旧的 exploratory run-state(探索性运行态) 移出项目目录。

归档位置：

- `/Users/wy/MiscProject/_archive/multi_factor_run_state_archive_20260429_1600_signaldiag_screendiag`

本次归档内容：

- `signaldiag_*`：`286` 个目录
- `screendiag_*`：`38` 个目录

归档后状态：

- 项目内 `artifacts/run_state` 下：
  - `signaldiag_* = 0`
  - `screendiag_* = 0`

体积摘要：

- `signaldiag archive size(单信号诊断归档体积) ≈ 86G`
- `screendiag archive size(筛查诊断归档体积) ≈ 24G`
- 归档后项目内 `artifacts/run_state ≈ 48G`

说明：

- 当前 confirmatory(确认性研究) 主线 run-state 未移动
- `research_registry(研究登记层)` 与 `fixed_test(固定测试)` 未移动
- 历史文档中若引用旧 `signaldiag_*` / `screendiag_*` 的项目内原路径，需要改为到归档目录中查找

---

## 第二次归档：`fullchain_*`

归档日期：`2026-04-29`

归档位置：

- `/Users/wy/MiscProject/_archive/multi_factor_run_state_archive_20260429_1610_fullchain`

本次归档内容：

- `fullchain_*`：`25` 个目录

归档后状态：

- 项目内 `artifacts/run_state` 下：
  - `fullchain_* = 0`

体积摘要：

- `fullchain archive size(全链路归档体积) ≈ 38G`
- 第二次归档后项目内 `artifacts/run_state ≈ 11G`

补充说明：

- 本次仍为**非破坏性归档**
- `baseline_chain_20260417_105228` 未随本次一起移动
- 当前 confirmatory(确认性研究) 主线 run-state 仍保留在项目目录内

---

## 第三次归档：`baseline_chain_20260417_105228`

归档日期：`2026-04-29`

归档位置：

- `/Users/wy/MiscProject/_archive/multi_factor_run_state_archive_20260429_1615_baseline_chain`

本次归档内容：

- `baseline_chain_20260417_105228`

归档后状态：

- 项目内 `artifacts/run_state` 下：
  - `baseline_chain_20260417_105228 = 0`

体积摘要：

- `baseline_chain archive size(基线链路归档体积) ≈ 1.5G`
- 第三次归档后项目内 `artifacts/run_state ≈ 9.0G`

补充说明：

- 本次仍为**非破坏性归档**
- 到此为止，旧的 `signaldiag_*`、`screendiag_*`、`fullchain_*`、`baseline_chain_20260417_105228` 都已移出项目目录
- 项目内 `run_state` 现阶段主要保留的是当前 confirmatory(确认性研究) 主线与 trainval panels
