# cord10 composability screening diagnosis

- `candidate_scheme_id(候选方案ID) = price_volume_screen_alpha158_cord10_composability_v1`
- `research_round_id(研究轮次ID) = rr_alpha158_exact_keeper_composability_screen_round3_20260429`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`

## Core answer

alpha158_cord10_raw is a real standalone keeper, but its additive fit with the frozen v18 core family is mixed rather than clean. It improves some static ordering diagnostics, but at least one of additive monotonicity, head stability, or liquidity/head proxy behavior remains questionable.

## Single-signal baseline

- `full_sample_corr_ic(全样本IC) = 0.013113`
- `avg_daily_ic(平均日IC) = 0.024033`
- `positive_daily_ic_share(正IC日占比) = 0.623957`
- `avg_label_top10(前10平均标签) = 0.005906`
- `avg_label_rank11_20(11-20名平均标签) = 0.005780`

## Reference vs screen static family readout

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.017224`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.002018`
- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = 0.002021`
- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = 0.002963`

## Component interaction

- `momentum_vs_screen_signal_corr_avg_daily(动量与新信号日均相关) = 0.067338`
- `liquidity_trend_vs_screen_signal_corr_avg_daily(流动性趋势与新信号日均相关) = 0.134299`
- `core_v18_vs_screen_signal_corr_avg_daily(v18核心与新信号日均相关) = 0.122488`
- `core_high_signal_high_avg_label(核心高+信号高平均标签) = 0.005074`
- `core_high_signal_mid_avg_label(核心高+信号中平均标签) = 0.004950`
- `core_high_signal_low_avg_label(核心高+信号低平均标签) = 0.003529`

## Head stability proxy

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 6.232207`
- `overlap_drop_tolerance(重叠下降容忍阈值) = 0.2`
- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = 2.684310`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.442297`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.415536`

## Judgement

- `classification(分类) = composability_screen_mixed`
- `implication_for_next_step(下一步含义) = Do not promote alpha158_cord10_raw into a direct family overlay yet. Keep it as a standalone keeper or later reserve-candidate only.`
