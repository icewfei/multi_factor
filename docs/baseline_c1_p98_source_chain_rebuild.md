# baseline c1 p98 source-chain rebuild

## Scope

本次工作只做 `exploratory_cross_horizon_c1_reversal_only` 与 `reversal_tail_exclude_p98_v1` 的 source-chain rebuild / audit，不训练模型，不跑 portfolio，不生成 formal metrics/readout，不读取 `frozen test`。

## Rebuild Goal

目标不是改 baseline 行为，而是补齐 upstream provenance evidence：

- 重建 `c1` 的 `model_scores_D0.parquet`
- 补一个受控 `run_state_attempt_manifest.json`
- 补一个受控 `data_quality_audit.json`
- 输出 `source_chain_audit.json`
- 明确 `score_rule` 方向问题是否被消解
- 明确 `p98` 是否仍依赖 label-based learnability diagnostics

## Controlled Outputs

脚本：
[rebuild_baseline_c1_p98_source_chain.py](/Users/wy/MiscProject/multi_factor/scripts/rebuild_baseline_c1_p98_source_chain.py)

受控输出位置：

- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/model_scores_D0.parquet`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/model_scores_D0_audit.json`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/attempts/attempt_rebuild_source_chain_provenance/run_state_attempt_manifest.json`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/attempts/attempt_rebuild_source_chain_provenance/data_quality_audit.json`
- `artifacts/run_state/exploratory_cross_horizon_c1_reversal_only/source_chain_audit.json`

这些产物是 `controlled rebuild artifacts`，不是历史原始 run 的 untouched recovery。

## Expected Audit Outcomes

如果本地可重建：

- 输出 `row_count`
- 输出 `candidate_scheme_id`
- 输出 `null/nonfinite score count`
- 输出 `D0 visibility audit`
- 输出 `leakage audit`
- 输出 `score direction audit`
- 输出 `p98 provenance audit`

如果本地不可重建：

- 只输出 blocker report
- 明确缺少的 source
- baseline 继续 `conditional`

## Current Governance Interpretation

- 这次 rebuild 只能补 provenance evidence，不自动把 baseline 升级成 unconditional gold standard。
- 如果 `score_rule direction mismatch` 仍然存在，或 `p98` 仍然有 `source-selection feedback risk`，baseline 仍应保持 `conditional baseline`。
