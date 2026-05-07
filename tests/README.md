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

## 后续必须补齐的测试

后续应优先补齐以下测试文件：

- `test_label_semantics.py`
- `test_execution_semantics.py`
- `test_tradability_rules.py`
- `test_no_future_leakage.py`
- `test_ranking_entry_separation.py`

## 各测试的目标

### `test_label_semantics.py`

验证标签定义与持有期口径是否与项目正式语义一致，避免训练标签与真实清算语义漂移。

### `test_execution_semantics.py`

验证 `D0` 出信号、`D1` 开盘买入、持有到 `D5` 收盘卖出及延迟退出规则是否保持一致。

### `test_tradability_rules.py`

验证涨停不能买、跌停不能卖、停牌不可交易、低成交审计旗标等规则的实现边界。

### `test_no_future_leakage.py`

验证特征、标签、评分与组合构造过程中不存在未来信息泄漏。

### `test_ranking_entry_separation.py`

验证“排名形成”和“实际入场执行”这两个层次没有被混写，避免用可执行结果倒灌排名层逻辑。

## 后续升级方向

这批测试后续应从当前的契约/文档级审计，逐步升级到：

- 函数级逻辑测试
- 小样本 DataFrame fixture 测试
- 小样本端到端执行语义测试
- feature timestamp / PIT freshness 机器化审计

## 本轮范围外事项

本轮不扩展到真实数据验证，不做收益验证，不做新的 fixed test / frozen test，也不修改任何策略实现。
