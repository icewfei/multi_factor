# clean baseline family decision record

## Scope

本记录用于收口 clean baseline family 的 score-layer gate 与 model-layer trainval diagnosis 结论。本文档不训练，不跑 portfolio，不生成 metrics/readout，不读取 frozen test，不修改 baseline / challenger，不把 trainval diagnosis 当 OOS，不做策略有效性声明。

## Score-Layer Record

- clean baseline family score-layer gate 4/4 通过。
- 4/4 score gate passed。
- 所有 clean baseline 均 no p98。
- 所有 clean baseline 均 no label diagnostics。
- 所有 clean baseline 均 no frozen test access。
- D0 visibility audit passed。
- leakage audit passed。
- clean sample panel projection 通过。
- clean sample panel 仅含白名单字段：`snapshot_id`、`instrument`、`signal_date`、`ranking_eligible_D0`。

## Model-Layer Record

- model-layer diagnosis completed。
- `no_p98_reversal_baseline_v1` 有 full-cross-section edge 但没有 TopK head quality。
- `clean_liquidity_adjusted_reversal_baseline_v1` 有 full-cross-section edge 但没有 TopK head quality。
- `clean_momentum_20d_baseline_v1` 没有可用 model-layer edge。
- `clean_equal_weight_random_eligible_baseline_v1` 不适合作为晋级 baseline。
- recommended_same_contract_portfolio_dry_run_candidates = []。
- no portfolio dry-run。
- 不进入 portfolio dry-run。

## Governance Conclusion

- clean baseline family score-layer clean，但 TopK head quality 不足。
- 当前没有 clean baseline candidate 推荐进入 same-contract portfolio dry-run 准备。
- 不替代 p98 conditional baseline。
- 不并列 p98 conditional baseline。
- cannot replace or parallel p98 conditional baseline。
- `p98` / `multi_equal_weight_v1` 仍只能作为 conditional reference only。
- conditional reference only。
- not OOS。
- not strategy approval。
- 这不是策略有效性结论。
- 不把 trainval diagnosis 当 OOS。

## Per-Baseline Final Read

### 1. no_p98_reversal_baseline_v1

- score-layer clean。
- full-cross-section model-layer edge 存在。
- validation TopK head quality 不足。
- 不进入 portfolio dry-run。

### 2. clean_momentum_20d_baseline_v1

- score-layer clean。
- 没有可用 model-layer edge。
- 不进入 portfolio dry-run。

### 3. clean_liquidity_adjusted_reversal_baseline_v1

- score-layer clean。
- full-cross-section model-layer edge 存在。
- liquidity proxy 使用 `20d median amount`，真实字段契约为 `vol + amount`。
- validation TopK head quality 不足。
- 不进入 portfolio dry-run。

### 4. clean_equal_weight_random_eligible_baseline_v1

- score-layer clean。
- 不适合作为晋级 baseline。
- 不进入 portfolio dry-run。

## Next Step

- 下一步不应跑 portfolio。
- 下一步应考虑 clean baseline family redesign 或数据字段补全。
- 当前不应把 clean baseline family diagnosis 升格为 portfolio 准备结论。

## Final Decision

clean baseline family 当前可以保留为 clean score-layer / model-layer diagnosis 参考簇，但只能说明“clean baseline family score-layer clean，model-layer head quality 不足”。它不说明 portfolio 可行，不说明策略有效，不说明可以替代或并列当前 `p98 conditional baseline`，也不说明 trainval diagnosis 可以当作 OOS。
