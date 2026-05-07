# Preregistration: Exploratory Intraday Cohort5 Contract Design

- `research_round_id`: `rr_exploratory_intraday_cohort5_contract_design_20260501`
- `research_tier`: `exploratory`
- `round_type`: `contract_design_exploratory`
- `status`: `preregistered`

## Research Question

在保持 score family 和所有其他合同要素不变的前提下，仅将 `holding_cohort_count` 从 auto-detected (26) 改为 fixed 5，intraday microstructure independent baseline 是否从 not viable 变为 viable（Layer A），以及在同一新合同下 intraday family 相对 contract-matched v18 是否更优（Layer B）？

## Changed Dimension

`portfolio_contract_parameter` → `holding_cohort_count`: 26 → 5

## Serial Execution Order

1. `exploratory_cohort5_v18_ref` → 汇报后，才允许
2. `exploratory_cohort5_c1_trendbias_only` → 汇报后，才允许
3. `exploratory_cohort5_c2_trendbias_upsideshare` → 汇报后，才允许
4. `exploratory_cohort5_c3_trendbias_upsideshare_reversalasym`

不得并行，不得边改边跑。

## Planned Candidates

| ID | Feature Preset | Signal Count | holding_cohort_count |
|---|---|---|---|
| `cohort5_v18_ref` | `price_volume_v16_remove_trend_consistency` | 2 | 5 |
| `cohort5_c1` | `single_signal_intraday_trend_bias` | 1 | 5 |
| `cohort5_c2` | `intraday_trend_bias_upside_share_2sig` | 2 | 5 |
| `cohort5_c3` | `intraday_full_microstructure_3sig` | 3 | 5 |

## Success Rules

Same 8 gates as previous round (cross-contract comparability).

All delta rules reference contract-matched v18 baseline (5-cohort), not historical 26-cohort v18.

## Verdict Layers

- Layer A: any intraday candidate passes core_pass → "viable under new contract"
- Layer B: intraday passes while v18_ref_5cohort does not → "relative superiority"
