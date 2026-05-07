# src 目录说明

## 当前状态

`src/` 目前是标准工程骨架中的预留目录。

当前项目的核心实现逻辑仍主要位于 [`scripts/`](/Users/wy/MiscProject/multi_factor/scripts)，包括：

- 特征构造
- 打分逻辑
- 组合构造
- 回测与组合产物生成
- 诊断与 reporting

这意味着：

- 当前仓库已经具备较完整的研究实现资产
- 但这些资产尚未被系统地抽取、收敛为最终模块化源码包

## 后续抽取方向

后续若推进工程化重构，应逐步从 `scripts/` 中抽取以下模块：

- `label`
- `tradability`
- `backtest`
- `features`
- `models`
- `reporting`

建议原则是：

- 先固化语义与测试边界
- 再做模块抽取
- 不在研究结论尚未稳定时进行大规模逻辑搬迁

## 本轮范围外事项

本轮补齐审计骨架不执行以下动作：

- 不重构 `scripts/` 为正式 Python package
- 不移动现有研究脚本
- 不改变任何策略逻辑或研究结论
