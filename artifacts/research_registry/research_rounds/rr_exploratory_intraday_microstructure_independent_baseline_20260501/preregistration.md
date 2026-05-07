# Preregistration: Exploratory Intraday Microstructure Independent Baseline

- `research_round_id`: `rr_exploratory_intraday_microstructure_independent_baseline_20260501`
- `registered_at`: `2026-05-01T10:00:00+08:00`
- `research_tier`: `exploratory`
- `round_type`: `family_construction`
- `status`: `preregistered`

---

## Research Question

在 D1-D5 短持有系统 + TopK + 现金保留 + 不补位合同下，以完全不包含 momentum 或 liquidity-trend 信号的日内微观结构信号构建的独立基线，能否在验证集（2019-2021）上通过 success rules？

## Baseline Reference

- `candidate_scheme_id`: `price_volume_v18_refresh_hysteresis`
- `snapshot_id`: `warehouse_20260429_trainval_20211231`
- `contract`: `run_input_contract.research_trainval_20211231.json`

### V18 验证集参考指标

来源：`fixed_test/confirmatory_reference_v18_trainval_20260429/validation_readout.json`

| 指标 | 值 |
|---|---|
| `annual_relative_return` | -0.2748 |
| `relative_ir` | -1.9034 |
| `max_drawdown` | -0.3988 |
| `avg_turnover_daily` | 0.0757 |
| `avg_invested_weight` | 0.1554 |

注意：此处使用 `validation_readout.json`（验证集窗口 2019-2021，730 天），而非 `metrics.json`（全量窗口 5271 天）。相对收益指标在两个文件中差异显著，本轮以验证集窗口为准。

## Planned Candidates

### c1: `exploratory_intraday_c1_trendbias_only`

| 字段 | 值 |
|---|---|
| Signal | `intraday_trend_bias_20d_raw` |
| 信号数 | 1 |
| Mechanism | intraday_bias |
| Score rule | `percentile_rank(DESC); min_feature_count >= 1` |
| 经济解释 | 日内趋势偏向——收盘相对于开盘的方向性漂移，反映订单流不平衡 |

### c2: `exploratory_intraday_c2_trendbias_upsideshare`

| 字段 | 值 |
|---|---|
| Signals | `intraday_trend_bias_20d_raw` + `upside_range_share_20d_raw` |
| 信号数 | 2 |
| Mechanisms | intraday_bias + intraday_structure |
| Score rule | `mean(percentile_rank(DESC)...); min_feature_count >= 2` |
| 经济解释 | 日内趋势方向 + 价格在日线区间上部的停留占比 |

### c3: `exploratory_intraday_c3_trendbias_upsideshare_reversalasym`

| 字段 | 值 |
|---|---|
| Signals | `intraday_trend_bias_20d_raw` + `upside_range_share_20d_raw` + `intraday_reversal_asymmetry_20d_raw` |
| 信号数 | 3 |
| Mechanisms | intraday_bias + intraday_structure + intraday_resilience |
| Score rule | `mean(percentile_rank(DESC)...); min_feature_count >= 3` |
| 经济解释 | 日内趋势方向 + 价格位置偏好 + 日内弹性（覆盖日内价格发现三维度） |

## Preprocess Contract

| 步骤 | 值 |
|---|---|
| missing_imputation | none |
| winsor_method | mad_clip, param=5.0 |
| standardization | cross_sectional_robust_zscore |
| neutralization | none |

## Success Rules

```
pass_validation_annual_relative_return: annual_relative_return >= 0.01
pass_validation_relative_ir: relative_ir >= 0.30
pass_not_worse_than_baseline_return: annual_relative_return_delta_vs_v18 >= -0.005
pass_avg_invested_weight: avg_invested_weight >= 0.15
pass_max_drawdown_not_worse: max_drawdown_delta_vs_v18 >= -0.05
pass_topk_perturbation: topk_8_relative_return >= 0.00 AND topk_12_relative_return >= 0.00
pass_cost_stress: cost_stress_annual_relative_return >= 0.00
pass_turnover_not_materially_worse: avg_turnover_daily_delta_vs_v18 <= 0.04

core_pass_condition: all of the above
```

## Verdict Rules

- Any candidate passes → `reasonable_candidate`（可进入下轮 confirmatory 候选）
- All 3 fail → `completed_intraday_family_not_viable`
- Candidates are parallel（互不阻塞）

## Registration Convention

> Spec-first, implementation-second. feature_preset 与 score_rule 已在注册时冻结，builder 的 SQL 实现尚待补齐后验证一致性。补齐前不跑实验。

## Supersedes

- `rr_confirmatory_pv_microstructure_baseline_20260501` — `preregistration_abandoned`, reason: `invalidated_due_to_reference_mismatch`
