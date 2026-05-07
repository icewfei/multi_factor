# Orthogonal Family Composability Screen — v19 Candidate vs v18

- `research_round_id(研究轮次ID) = rr_composability_screen_orthogonal_family_v19_test_20260430`
- `candidate_scheme_id(候选方案ID) = composability_screen_orthogonal_family_v19_v1`
- `reference_candidate_scheme_id(参考候选方案ID) = price_volume_v18_refresh_hysteresis`

## Candidate Signal Composition

- `alpha158_corr20_raw` (alpha158)
- `alpha158_vsumd60_raw` (alpha158)
- `intraday_trend_bias_20d` (project)
- `momentum_60_5` (project)
- `lower_shadow_support_20d` (project)

## Reference Signal Composition (v18)

- `pv_beta_20d` (project)
- `intraday_trend_bias_20d` (project)
- `liq_trend_20_60` (project)
- `momentum_60_5` (project)
- `upside_range_share_20d` (project)

## Core Answer

**composability_screen_mixed**

The orthogonal 5-signal family shows mixed composability vs v18. It may improve some static ordering diagnostics, but at least one of additive monotonicity, head stability, or liquidity/head proxy behavior remains questionable.

## Reference vs Screen Static Readout

- `reference_full_sample_corr_ic(参考全样本IC) = 0.018332`
- `screen_full_sample_corr_ic(筛查全样本IC) = 0.022453`
- `reference_avg_daily_ic(参考平均日IC) = 0.030288`
- `screen_avg_daily_ic(筛查平均日IC) = 0.036800`
- `reference_top10_minus_rank11_20(参考前10减11-20) = 0.002459`
- `screen_top10_minus_rank11_20(筛查前10减11-20) = 0.002992`
- `reference_avg_rank10_11_score_gap(参考第10/11名平均间距) = 0.012535`
- `screen_avg_rank10_11_score_gap(筛查第10/11名平均间距) = 0.014229`

## Component Interaction (Candidate Family)

- `alpha158_corr20 ↔ alpha158_vsumd60`: full_corr=0.147896, avg_daily=0.137117
- `alpha158_corr20 ↔ intraday_trend_bias_20d`: full_corr=0.203266, avg_daily=0.181174
- `alpha158_corr20 ↔ momentum_60_5`: full_corr=0.062004, avg_daily=0.047659
- `alpha158_corr20 ↔ lower_shadow_support_20d`: full_corr=-0.041279, avg_daily=-0.040215
- `alpha158_vsumd60 ↔ intraday_trend_bias_20d`: full_corr=0.271379, avg_daily=0.253073
- `alpha158_vsumd60 ↔ momentum_60_5`: full_corr=0.263993, avg_daily=0.240200
- `alpha158_vsumd60 ↔ lower_shadow_support_20d`: full_corr=0.035800, avg_daily=0.034673
- `intraday_trend_bias_20d ↔ momentum_60_5`: full_corr=0.336776, avg_daily=0.326725
- `intraday_trend_bias_20d ↔ lower_shadow_support_20d`: full_corr=0.175748, avg_daily=0.177724
- `momentum_60_5 ↔ lower_shadow_support_20d`: full_corr=0.079003, avg_daily=0.074684

## Bucket Analysis

- `ref_high_scr_high`: avg_label=0.005516
- `ref_high_scr_low`: avg_label=0.004918
- `ref_high_scr_mid`: avg_label=0.004863
- `ref_low_scr_high`: avg_label=0.006868
- `ref_low_scr_low`: avg_label=0.001967
- `ref_low_scr_mid`: avg_label=0.004342
- `ref_mid_scr_high`: avg_label=0.005849
- `ref_mid_scr_low`: avg_label=0.003360
- `ref_mid_scr_mid`: avg_label=0.004289

## Head Stability

- `reference_avg_top10_overlap_next_day(参考次日前10平均重叠) = 6.647408`
- `screen_avg_top10_overlap_next_day(筛查次日前10平均重叠) = 4.876190`
- `overlap_drop_tolerance(重叠下降容忍阈值) = 0.2`
- `avg_top10_overlap_same_day_vs_reference(与参考同日前10平均重叠) = 2.706418`
- `reference_avg_top10_liquidity_rank_mean(参考前10平均流动性分位) = 0.450284`
- `screen_avg_top10_liquidity_rank_mean(筛查前10平均流动性分位) = 0.481272`

## Judgement

- `classification(分类) = composability_screen_mixed`
- `top_slice_improved(头部区分改善) = True`
- `head_stability_not_worse(头部稳定性未恶化) = False`
- `liquidity_not_worse(流动性未恶化) = True`
- `additive_high_bucket(单调加成) = True`
- `implication_for_next_step(下一步含义) = Keep the orthogonal family as a research candidate; do not promote into confirmatory yet. Consider subset reduction or alternative signal selection.`
