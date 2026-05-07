# configs 目录说明

## 当前状态

`configs/` 目前是标准审计骨架中的预留目录。

当前项目的正式配置、契约与结果结构定义并不在本目录，而主要位于：

- [`contracts/`](/Users/wy/MiscProject/multi_factor/contracts)
- [`schemas/`](/Users/wy/MiscProject/multi_factor/schemas)

因此，当前阶段不应把 `configs/` 误理解为真实配置真相源。

## 当前正式来源

### `contracts/`

负责保存：

- 运行输入契约
- 来源表与字段映射
- 主键规则
- 项目字段字典

### `schemas/`

负责保存：

- 中间表结构
- 结果产物结构
- 审计摘要结构

## 后续定位

后续 `configs/` 只应承担轻量职责：

- 运行配置索引
- 环境差异说明
- 配置入口文档

不应在本目录中：

- 复制 `artifacts/` 产物
- 复制大体量运行结果
- 复制 `contracts/` 与 `schemas/` 的正式定义并制造多份真相源

## 本轮范围外事项

本轮只新增配置说明文档，不迁移现有契约，不创建新的运行参数体系。
