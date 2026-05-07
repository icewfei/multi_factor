# vsump60 composability screening diagnosis

- `candidate_scheme_id(候选方案ID) = price_volume_screen_alpha158_vsump60_composability_v1`
- `research_round_id(研究轮次ID) = rr_alpha158_exact_keeper_composability_screen_round3_20260429`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`

## Core answer

alpha158_vsump60_raw is a real standalone keeper, but its additive fit with the frozen v18 core family is mixed rather than clean. It improves some static ordering diagnostics, but at least one of additive monotonicity, head stability, or liquidity/head proxy behavior remains questionable.

## Single-signal baseline

- `full_sample_corr_ic(全样本IC) = 0.014042`
- `avg_daily_ic(平均日IC) = 0.023205`
- `positive_daily_ic_share(正IC日占比) = 0.618508`
- `avg_label_top10(前10平均标签) = 0.005502`
- `avg_label_rank11_20(11-20名平均标签) = 0.004937`

## Reference vs screen static family readout

- `reference_full_sample_corr_ic(参考全样本IC) = 0.013345`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.015818`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.000519`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.001277`
- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = 0.002021`
- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = 0.002260`

## Component interaction

- `momentum_vs_screen_signal_corr_avg_daily(动量与新信号日均相关) = 0.258557`
- `liquidity_trend_vs_screen_signal_corr_avg_daily(流动性趋势与新信号日均相关) = 0.467421`
- `core_v18_vs_screen_signal_corr_avg_daily(v18核心与新信号日均相关) = 0.438610`
- `core_high_signal_high_avg_label(核心高+信号高平均标签) = 0.004641`
- `core_high_signal_mid_avg_label(核心高+信号中平均标签) = 0.004990`
- `core_high_signal_low_avg_label(核心高+信号低平均标签) = 0.003783`

## Head stability proxy

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 7.223071`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 5.399155`
- `overlap_drop_tolerance(重叠下降容忍阈值) = 0.2`
- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = 5.180010`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.442297`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.432742`

## Judgement

- `classification(分类) = composability_screen_mixed`
- `implication_for_next_step(下一步含义) = Do not promote alpha158_vsump60_raw into a direct family overlay yet. Keep it as a standalone keeper or later reserve-candidate only.`
