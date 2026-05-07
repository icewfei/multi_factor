# intraday_trend_bias_20d composability screening diagnosis

- `candidate_scheme_id(候选方案ID) = price_volume_screen_intraday_trend_bias_20d_composability_v1`
- `research_round_id(研究轮次ID) = rr_price_volume_intraday_trend_bias_composability_screen_20260425`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`

## Core answer

intraday_trend_bias_20d_raw is a real standalone keeper, but its additive fit with the frozen v18 core family is mixed rather than clean. It improves some static ordering diagnostics, but at least one of additive monotonicity, head stability, or liquidity/head proxy behavior remains questionable.

## Single-signal baseline

- `full_sample_corr_ic(全样本IC) = 0.014740`
- `avg_daily_ic(平均日IC) = 0.019716`
- `positive_daily_ic_share(正IC日占比) = 0.555940`
- `avg_label_top10(前10平均标签) = 0.005909`
- `avg_label_rank11_20(11-20名平均标签) = 0.005601`

## Reference vs screen static family readout

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.016015`
- `reference_avg_label_top10(参考前10平均标签) = 0.006814`
- `screen_avg_label_top10(筛查前10平均标签) = 0.007802`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.000853`
- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = 0.002021`
- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = 0.002541`

## Component interaction

- `momentum_vs_intraday_trend_bias_corr_avg_daily(动量与日内趋势偏置日均相关) = 0.340537`
- `liquidity_trend_vs_intraday_trend_bias_corr_avg_daily(流动性趋势与日内趋势偏置日均相关) = 0.396480`
- `core_v18_vs_intraday_trend_bias_corr_avg_daily(v18核心分数与日内趋势偏置日均相关) = 0.449398`
- `core_high_bias_high_avg_label(核心高+日内偏置高平均标签) = 0.004799`
- `core_high_bias_mid_avg_label(核心高+日内偏置中平均标签) = 0.004797`
- `core_high_bias_low_avg_label(核心高+日内偏置低平均标签) = 0.003479`

## Head stability proxy

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.663585`
- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = 3.655379`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.442297`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.470823`

## Judgement

- `classification(分类) = composability_screen_mixed`
- `implication_for_next_step(下一步含义) = Do not promote intraday_trend_bias_20d_raw into a direct equal-weight family replacement yet. If used later, prefer a constrained third-signal test or gated modifier design.`
