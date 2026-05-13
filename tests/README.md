# tests 目录说明

## 当前状态

`tests/` 目前已经开始承接第一批标准审计测试入口。

截至当前版本，这批测试主要是 **契约/文档级红线测试**。它们用于固定：

- 核心字段是否存在于 `contracts/` 与 `schemas/`
- 核心制度语义是否已经锚定到总纲与规格文档
- 排序、执行、标签、tradability 等关键边界是否有最小机器化入口

这意味着当前测试体系已经有入口，但距离完整的实现级审计还明显不够。

## 当前运行方式

安装依赖：

```bash
python -m pip install -r requirements-dev.txt
```

运行全部测试：

```bash
python -m pytest tests/
```

请确保安装依赖和运行测试使用同一个 Python 解释器。部分旧测试会通过 subprocess 调用脚本；如果解释器混用，可能出现当前 pytest 环境有依赖、子进程环境缺依赖的问题。

## 后续升级方向

这批测试后续应从当前的契约/文档级审计，逐步升级到：

- 函数级逻辑测试
- 小样本 DataFrame fixture 测试
- 小样本端到端执行语义测试
- feature timestamp / PIT freshness 机器化审计
- 依赖和 subprocess 环境一致性检查

## 本轮范围外事项

本轮不扩展到真实数据验证，不做收益验证，不做新的 fixed test / frozen test，也不修改任何策略实现。
