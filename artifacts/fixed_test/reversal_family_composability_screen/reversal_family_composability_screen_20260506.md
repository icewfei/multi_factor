# Reversal Family Composability Screen

- generated_at: 2026-05-06T12:58:15+08:00

## Baseline p98

- median_daily_ic = 0.045971
- mean_daily_ic = 0.048058
- top10_avg_label = 0.007625
- top10_bot10_spread = 0.004935
- top10_avg_liquidity_rank = 0.621422

## Candidates

| partner | weight | median_IC | mean_IC | Top10 | Spread | Top10 avg liq_rank | avg corr with p98 |
|---|---|---|---|---|---|---|---|
| reversal_followthrough_rank | 0.10 | 0.045965 | 0.048060 | 0.007625 | 0.004935 | 0.621422 | 0.999983 |
| reversal_followthrough_rank | 0.20 | 0.045959 | 0.048061 | 0.007625 | 0.004935 | 0.621422 | 0.999983 |
| intraday_reversal_asymmetry_rank | 0.10 | 0.046364 | 0.048446 | 0.008491 | 0.012088 | 0.645511 | 0.054841 |
| intraday_reversal_asymmetry_rank | 0.20 | 0.046347 | 0.048060 | 0.008258 | 0.012349 | 0.640157 | 0.054841 |
| upside_range_share_rank | 0.10 | 0.045801 | 0.047786 | 0.007730 | 0.010604 | 0.568628 | 0.329727 |
| upside_range_share_rank | 0.20 | 0.045486 | 0.046864 | 0.007734 | 0.011119 | 0.559256 | 0.329727 |
| intraday_trend_bias_rank | 0.10 | 0.045716 | 0.047961 | 0.008130 | 0.012378 | 0.595272 | 0.346685 |
| intraday_trend_bias_rank | 0.20 | 0.046311 | 0.047337 | 0.008244 | 0.012608 | 0.596340 | 0.346685 |
| liquidity_trend_rank | 0.10 | 0.047801 | 0.049569 | 0.008267 | 0.012058 | 0.521465 | 0.060744 |
| liquidity_trend_rank | 0.20 | 0.048725 | 0.050627 | 0.008579 | 0.012786 | 0.504505 | 0.060744 |

## Preferred follow-up

- partner = intraday_reversal_asymmetry_rank, weight = 0.20, median_IC = 0.046347, spread = 0.012349, top10_avg_liquidity_rank = 0.640157
