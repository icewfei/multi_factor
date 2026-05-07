# VSUMD60 family seed note

- `research_round_id(研究轮次ID) = rr_confirmatory_alpha158_vsumd60_family_seed_head_extraction_20260429`
- `candidate_scheme_id(候选方案ID) = confirmatory_alpha158_vsumd60_seed_linear_rank_decay_v1`
- `changed_dimension(变更维度) = portfolio_extraction`

本轮不是继续加更强的 `guard(护栏)`，而是测试另一条更干净的 restrained family seed(克制型家族种子线)：

- 分数本体保持 `alpha158_vsumd60_raw` 不变
- 排名方向保持不变
- `TopK = 10` 保持不变
- 只把持仓提取方式从 standalone reference(单信号参考) 的等权提取，改为 `linear_rank_decay(线性头部提取)`

目标问题：

- `portfolio_extraction_rule(组合提取规则)` 这一维，能否在不明显恶化 `turnover(换手)` / `cost drag(成本拖累)` 的前提下，提升相对 standalone `VSUMD60` 的头部质量？
