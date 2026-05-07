# price_volume_v15_trend_liquidity_improvement_core Family-Level Root-Cause Diagnosis

- Generated at: `2026-04-22T13:37:49.105023+08:00`
- Candidate: `price_volume_v15_trend_liquidity_improvement_core`
- Reference: `baseline_momentum_v7_liquidity_guard70`
- Research round: `rr_price_volume_trend_liquidity_improvement_family_20260422`

## Signal Layer

- full_sample_corr_ic（全样本IC）: `0.009758 -> 0.011769`
- avg_daily_ic（平均日IC）: `0.013398 -> 0.018551`
- positive_daily_ic_share（正IC日占比）: `0.5236 -> 0.5552`
- avg_label_top10（前10平均标签）: `0.004282 -> 0.004986`
- avg_label_rank11_20（11-20名平均标签）: `0.005483 -> 0.005826`

challenger signal edge is stronger than calibrated v7 at broad ordering level, but the top slice remains fragile because rank 11-20 still beats rank 1-10.

## Selection Layer

- avg_overlap_count（平均TopK重叠只数）: `0.604`
- avg_overlap_share_of_smaller_topk（平均TopK重叠比例）: `0.0610`
- zero_overlap_day_share（零重叠交易日占比）: `0.5754`
- challenger median rank10_11 gap（挑战者10/11位中位分差）: `0.001939`
- reference median rank10_11 gap（参考10/11位中位分差）: `nan`

The challenger materially changes the selected basket relative to v7 while still operating in a thin-cutoff regime; this helps explain why relative return can improve yet perturbation robustness still fails.

## Fixed-Test Layer

- annual_relative_return（年化超额收益）: `-0.069766 -> -0.054911`
- relative_ir（相对信息比率）: `-0.528702 -> -0.411938`
- max_drawdown（最大回撤）: `-0.396811 -> -0.487516`
- avg_turnover_daily（平均日换手）: `0.098113 -> 0.088467`
- low_liquidity_weight_share（低流动性权重占比）: `0.020451 -> 0.159324`
- cost_drag_delta_annual_relative_return（成本压力额外拖累的年化超额收益）: `-0.041337`
- topk_perturbation_pass（TopK扰动通过）: `False -> False`
- cost_stress_pass（成本压力通过）: `False -> False`

v15 improves annual_relative_return and relative_ir and lowers turnover versus v7, but drawdown becomes worse and cost stress still pushes annual_relative_return materially lower.

## Holdings Tail

- p10_execution_delayed_realized_return（持仓收益10分位）: `-0.087634 -> -0.072711`
- p05_execution_delayed_realized_return（持仓收益5分位）: `-0.119453 -> -0.105882`
- avg_execution_delayed_realized_return（平均持仓真实收益）: `0.002217 -> 0.005036`

The challenger improves average holding return and also improves single-position left-tail quantiles versus v7. This suggests the worse portfolio-level drawdown is more likely driven by path dependence, basket concentration, or synchronized losses rather than by worse single-name tails.

## Conclusion

- The first constructed family is directionally more promising than several earlier mixed-family attempts because its broad signal edge is stronger than calibrated v7 and that improvement does survive into annual_relative_return and relative_ir.
- The main blocker is no longer gross edge absence. The blocker is that the family still extracts a fragile top slice, fails TopK perturbation, and converts some of its new edge into worse downside outcomes and higher low-liquidity share.
- This means the next best research action is not to discard the family outright, but to diagnose which retained atomic signal is driving the worse drawdown and liquidity share inside the mixed family.
