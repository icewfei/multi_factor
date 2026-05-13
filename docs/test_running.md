# 审计测试运行说明

## 当前测试的定位

当前 `tests/` 目录中的测试，主要是 **contract-level audit tests**。

它们的目标是固定以下内容：

- 核心字段是否在 `contracts/` 与 `schemas/` 中正式存在
- 核心制度语义是否已经写入总纲、模块规格或项目文档
- 研究流程中的红线边界是否有最小机器化入口

当前这些测试：

- 不连接真实数据
- 不读取本地大体量数据文件
- 不运行新的回测
- 不验证收益好坏
- 部分测试会采用 source-level guardrail 方式，直接检查关键脚本中是否仍保留审计护栏

## 安装方式

在项目根目录执行：

```bash
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` 记录的是当前审计测试和小样本 fixture 测试需要的最小开发依赖。测试运行时应使用同一个 Python 解释器安装依赖并启动 pytest，避免 `pytest` 与 subprocess 调用的 `python` / `python3` 指向不同环境。

## 运行方式

在项目根目录执行：

```bash
python -m pytest tests/
```

如果本机同时存在系统 Python 与 conda/venv Python，优先使用当前环境的显式解释器：

```bash
$(python -c "import sys; print(sys.executable)") -m pytest tests/
```

如果只想单独检查当前 `Nonlinear Challenger v1` draft manifests 是否满足基础治理约束，也可以执行：

```bash
python scripts/validate_nonlinear_challenger_manifests.py \
  --feature-set configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json \
  --model-config configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json \
  --candidate configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json
```

当前这条命令预期会因为 `baseline_candidate_scheme_id` 仍是 placeholder 而失败。这不是 bug，而是说明 baseline 尚未正式绑定，因此当前仍不允许进入训练阶段。

如果只想运行当前第一批制度红线测试，也可以指定单个文件或小集合。

## 当前可能出现的 xfail

当前测试中可能包含 `xfail` 占位项。

当前已知的占位原因是：

- `feature timestamp / PIT freshness audit` 还没有被沉淀为可直接机器检查的正式契约或函数级实现

因此，`xfail` 的含义是：

- 该红线已经被文档确认需要审计
- 但当前仓库尚未具备完整的可执行实现级检查入口

## 这些测试不是什么

这些测试目前 **不是**：

- 收益验证
- 因子优劣比较
- 完整实现审计
- 端到端数据质量验收
- 新的 fixed test / frozen test
- 策略研究重启授权
- portfolio 或 backtest 入口

它们只是第一层机器化审计入口，用来确保核心研究语义、字段边界和治理红线不会在工程整理过程中被静默漂移。

## 后续升级方向

后续测试体系应逐步从当前的契约/文档级审计，升级到：

- 函数级逻辑测试
- 小样本 DataFrame fixture 测试
- 排序与执行语义的最小端到端测试
- feature timestamp / PIT freshness 机器化审计
