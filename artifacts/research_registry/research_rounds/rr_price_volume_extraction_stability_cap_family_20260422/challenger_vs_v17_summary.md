# v19 vs v17 Summary

- reference_candidate_scheme_id: `price_volume_v17_head_extraction_smoothing`
- challenger_candidate_scheme_id: `price_volume_v19_extraction_stability_cap`
- summary_judgement: `weak_candidate`

## Comparison
- annual_relative_return(年化超额收益): -0.047056 -> -0.047198
- relative_ir(相对信息比率): -0.409567 -> -0.412854
- max_drawdown(最大回撤): -0.282662 -> -0.281151
- avg_turnover_daily(平均日换手): 0.109358 -> 0.109377
- low_liquidity_weight_share(低流动性权重占比): 0.030185 -> 0.030132
- topk_perturbation_pass(TopK扰动通过): False -> False
- cost_stress_pass(成本压力通过): False -> False

## Conclusion
Extraction stability cap preserved the v17 profile and slightly improved max_drawdown(最大回撤) plus low_liquidity_weight_share(低流动性权重占比), but it did not reduce avg_turnover_daily(平均日换手), slightly worsened annual_relative_return(年化超额收益) and relative_ir(相对信息比率), and still failed both TopK perturbation(TopK扰动) plus cost stress(成本压力) audit gates.
