# clean baseline family score gate summary

## Scope

本记录用于汇总 clean baseline family 在真实 trainval 数据上的 score-layer gate 结果。本文档只记录 clean sample panel projection 与 `model_scores_D0` / audit 产物，不训练，不跑 portfolio，不生成 holdings / backtest_daily / formal metrics/readout，不读取 frozen test，不做策略有效性声明。

## Clean Projection

- clean sample panel path: `/private/tmp/clean_baseline_family_score_gate_20260513/clean_sample_panel.parquet`
- clean sample panel audit path: `/private/tmp/clean_baseline_family_score_gate_20260513/clean_sample_panel_audit.json`
- clean sample panel 仅含白名单字段：`snapshot_id`、`instrument`、`signal_date`、`ranking_eligible_D0`
- projection row_count = `11,198,074`
- stripped forbidden columns: `label_defined`、`backtest_executable_shared_proxy`
- frozen_test_accessed=false

## Gate Result

- 4/4 clean baseline score-layer gate 通过
- 每个 baseline 都成功生成 `model_scores_D0.parquet`
- 每个 baseline 都成功生成 `model_scores_D0_audit.json`
- 每个 baseline 都成功生成 `source_chain_audit.json`
- 每个 baseline 都成功生成 `run_state_attempt_manifest.json`
- 这不是 portfolio approval
- 这不是策略有效性结论
- not portfolio approval
- not strategy approval
- 下一步才是 clean baseline family model-layer diagnosis

## Baselines

### no_p98_reversal_baseline_v1

- output path: `/private/tmp/clean_baseline_family_score_gate_20260513/no_p98_reversal_baseline_v1/model_scores_D0.parquet`
- candidate_scheme_id / baseline_id: `no_p98_reversal_baseline_v1` / `no_p98_reversal_baseline_v1`
- row_count = `11,198,074`
- null_score_count = `421,656`
- nonfinite_score_count = `0`
- score_direction = `ASC / reversal_rank`
- p98_used=false
- label_diagnostics_used=false
- frozen_test_accessed=false
- D0 visibility audit: `pass`
- leakage audit: `pass`
- score-layer gate: `pass`

### clean_momentum_20d_baseline_v1

- output path: `/private/tmp/clean_baseline_family_score_gate_20260513/clean_momentum_20d_baseline_v1/model_scores_D0.parquet`
- candidate_scheme_id / baseline_id: `clean_momentum_20d_baseline_v1` / `clean_momentum_20d_baseline_v1`
- row_count = `11,198,074`
- null_score_count = `435,357`
- nonfinite_score_count = `0`
- score_direction = `descending 20d cumulative return / stronger momentum first`
- p98_used=false
- label_diagnostics_used=false
- frozen_test_accessed=false
- D0 visibility audit: `pass`
- leakage audit: `pass`
- score-layer gate: `pass`

### clean_liquidity_adjusted_reversal_baseline_v1

- output path: `/private/tmp/clean_baseline_family_score_gate_20260513/clean_liquidity_adjusted_reversal_baseline_v1/model_scores_D0.parquet`
- candidate_scheme_id / baseline_id: `clean_liquidity_adjusted_reversal_baseline_v1` / `clean_liquidity_adjusted_reversal_baseline_v1`
- row_count = `11,198,074`
- null_score_count = `418,025`
- nonfinite_score_count = `0`
- score_direction = `ascending 1d return first, descending liquidity tiebreak`
- liquidity_field_used = `amount`
- volume_field_source = `vol`
- amount_field_source = `amount`
- p98_used=false
- label_diagnostics_used=false
- frozen_test_accessed=false
- D0 visibility audit: `pass`
- leakage audit: `pass`
- score-layer gate: `pass`

### clean_equal_weight_random_eligible_baseline_v1

- output path: `/private/tmp/clean_baseline_family_score_gate_20260513/clean_equal_weight_random_eligible_baseline_v1/model_scores_D0.parquet`
- candidate_scheme_id / baseline_id: `clean_equal_weight_random_eligible_baseline_v1` / `clean_equal_weight_random_eligible_baseline_v1`
- row_count = `11,198,074`
- null_score_count = `417,118`
- nonfinite_score_count = `0`
- score_direction = `ascending deterministic hash / pseudo-random but reproducible order`
- p98_used=false
- label_diagnostics_used=false
- frozen_test_accessed=false
- D0 visibility audit: `pass`
- leakage audit: `pass`
- score-layer gate: `pass`

## Governance Statement

- no p98
- no label diagnostics
- frozen_test_accessed=false
- D0 visibility audit pass
- leakage audit pass
- portfolio_ran=false
- formal_metrics_generated=false

当前结论仅表示 clean baseline family 的 real trainval score-layer gate 已通过，可进入下一步 clean baseline family model-layer diagnosis。该结论不是 portfolio approval，不是策略有效性结论，不是 OOS 证明。
