# no-p98 clean baseline score-layer decision record

## Scope

本记录用于收口 `no_p98_reversal_baseline_v1` 的 score-layer clean artifact gate。本文档只记录 clean projection 与 real trainval score gate 结果，不训练，不跑 portfolio，不生成 formal metrics/readout，不读取 frozen test，不做策略有效性声明。

## Decision

- clean projection 通过。
- `label_defined` / `backtest_executable_shared_proxy` 已剥离。
- clean sample panel 仅含白名单字段：`snapshot_id`、`instrument`、`signal_date`、`ranking_eligible_D0`。
- no-p98 `model_scores_D0` 已生成。
- `row_count = 11,198,074`
- `null_score_count = 421,656`
- `nonfinite_score_count = 0`
- `score_direction = ASC / reversal_rank`
- `p98_used=false`
- `label_diagnostics_used=false`
- `frozen_test_accessed=false`
- `D0 visibility audit pass`
- `leakage audit pass`
- `portfolio_ran=false`
- `formal_metrics_generated=false`

## Governance Statement

- no p98
- no label diagnostics
- frozen_test_accessed=false
- D0 visibility audit pass
- leakage audit pass
- portfolio_ran=false
- formal_metrics_generated=false
- not strategy approval

当前结论仅表示 score-layer clean artifact 通过，可用于后续 model-layer diagnosis 的输入治理基础。该结论不是 portfolio approval，不是策略有效性结论，不是 OOS 证明。
