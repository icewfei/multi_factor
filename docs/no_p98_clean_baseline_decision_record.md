# no-p98 clean baseline decision record

## Scope

本记录用于收口 `no_p98_reversal_baseline_v1` 的 score-layer 与 model-layer trainval diagnosis 结论。本文档不训练，不跑 portfolio，不生成 metrics/readout，不读取 frozen test，不把 trainval diagnosis 当 OOS，不做策略有效性声明。

## Score-Layer Record

- no-p98 clean baseline score-layer clean。
- no p98。
- no label diagnostics。
- no frozen test access。
- D0 visibility audit passed。
- leakage audit passed。
- clean projection 通过。
- `label_defined` / `backtest_executable_shared_proxy` 已剥离。
- clean sample panel 仅含白名单字段：`snapshot_id`、`instrument`、`signal_date`、`ranking_eligible_D0`。

## Model-Layer Record

- no-p98 clean baseline clean but weak。
- model-layer 仍有弱正 edge，但明显弱于当前基线簇。
- validation `RankIC=0.0287`
- validation `ICIR=0.2350`
- validation `top-bottom spread=0.00246`
- validation `TopK head realized return proxy=-0.00543`
- validation `TopK minus nextK=-0.00844`
- no portfolio dry-run。
- 不建议进入 portfolio dry-run。

## Governance Conclusion

- p98 conditional baseline stronger but not clean。
- no-p98 clean baseline 干净但弱。
- no-p98 不替代 `multi_equal_weight_v1` / p98 conditional baseline。
- 当前不建议把 `no_p98_reversal_baseline_v1` 作为 portfolio dry-run 候选推进。
- 下一步应 rebuild clean baseline family，而不是简单去掉 p98。
- 这不是策略有效性结论。
- not strategy approval。
- 不把 trainval diagnosis 当 OOS。

## Final Decision

`no_p98_reversal_baseline_v1` 当前可保留为 clean baseline candidate 的治理参考，但仅限 score-layer / model-layer clean diagnosis 语境。它说明“clean but weak”，不说明 portfolio 可行，不说明策略有效，不说明可以替代当前 `multi_equal_weight_v1` 或 p98 conditional baseline。
