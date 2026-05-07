# tests 目录说明

## 当前状态

`tests/` 目前是标准审计骨架中的预留目录。

截至当前版本，仓库尚缺正式的 `pytest` 测试集合。这意味着项目虽然已经拥有较丰富的研究脚本、契约与结果 Schema，但在可持续工程审计层面，自动化测试仍明显不足。

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

## 本轮范围外事项

本轮不新增 pytest 代码，不运行新测试，只补测试骨架说明，作为后续工程化工作的入口。
