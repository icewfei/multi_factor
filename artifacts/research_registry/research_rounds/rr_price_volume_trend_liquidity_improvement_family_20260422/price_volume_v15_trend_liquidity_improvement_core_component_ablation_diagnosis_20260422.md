# price_volume_v15_trend_liquidity_improvement_core Component Ablation Diagnosis

- Generated at: `2026-04-22T13:50:09.457863+08:00`
- Candidate: `price_volume_v15_trend_liquidity_improvement_core`
- Research round: `rr_price_volume_trend_liquidity_improvement_family_20260422`

## Actual v15 Selected Profile

- avg_momentum_rank（平均动量分位）: `0.951530`
- avg_trend_consistency_rank（平均趋势一致性分位）: `0.941749`
- avg_liquidity_trend_rank（平均流动性改善分位）: `0.947553`
- low_liquidity_share_proxy（低流动性占比代理）: `0.165373`

## Ablation Blocks

### full_v15

- full_sample_corr_ic（全样本IC）: `0.011848`
- avg_daily_ic（平均日IC）: `0.019011`
- positive_daily_ic_share（正IC日占比）: `0.5558`
- avg_label_top10（前10平均标签）: `0.005266`
- avg_label_rank11_20（11-20名平均标签）: `0.005781`
- top10_low_liquidity_share_proxy（前10低流动性占比代理）: `0.168149`

### remove_momentum_60_5

- full_sample_corr_ic（全样本IC）: `0.009928`
- avg_daily_ic（平均日IC）: `0.015946`
- positive_daily_ic_share（正IC日占比）: `0.5580`
- avg_label_top10（前10平均标签）: `0.003260`
- avg_label_rank11_20（11-20名平均标签）: `0.004745`
- top10_low_liquidity_share_proxy（前10低流动性占比代理）: `0.188198`

### remove_trend_consistency_20d

- full_sample_corr_ic（全样本IC）: `0.013345`
- avg_daily_ic（平均日IC）: `0.020658`
- positive_daily_ic_share（正IC日占比）: `0.5582`
- avg_label_top10（前10平均标签）: `0.006814`
- avg_label_rank11_20（11-20名平均标签）: `0.006295`
- top10_low_liquidity_share_proxy（前10低流动性占比代理）: `0.157887`

### remove_liquidity_trend_20_60

- full_sample_corr_ic（全样本IC）: `0.008353`
- avg_daily_ic（平均日IC）: `0.012601`
- positive_daily_ic_share（正IC日占比）: `0.5293`
- avg_label_top10（前10平均标签）: `0.003676`
- avg_label_rank11_20（11-20名平均标签）: `0.005432`
- top10_low_liquidity_share_proxy（前10低流动性占比代理）: `0.130278`

## Interpretations

- liquidity_trend_20_60_raw likely contributes positively to broad edge because removing it lowers full_sample_corr_ic(全样本IC).
- liquidity_trend_20_60_raw likely contributes to higher low-liquidity exposure because removing it lowers top10_low_liquidity_share_proxy(前10低流动性占比代理).
- trend_consistency_20d_raw may be the weakest contributor to head extraction because removing it does not worsen avg_label_top10(前10平均标签).
- momentum_60_5_raw remains a core positive component because removing it weakens broad cross-sectional edge.

