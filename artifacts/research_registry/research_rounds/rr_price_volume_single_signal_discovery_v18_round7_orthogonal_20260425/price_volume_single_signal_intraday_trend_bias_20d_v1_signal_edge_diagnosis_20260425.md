# price_volume_single_signal_intraday_trend_bias_20d_v1 (20260425)

Candidate: `price_volume_single_signal_intraday_trend_bias_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.014740`
- Average daily IC: `0.019716`
- Median daily IC: `0.016798`
- Positive daily IC share: `0.55594`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004615`
- Decile 2: `0.004438`
- Decile 3: `0.004516`
- Decile 4: `0.004532`
- Decile 5: `0.004464`
- Decile 6: `0.004470`
- Decile 7: `0.004276`
- Decile 8: `0.003863`
- Decile 9: `0.003044`
- Decile 10: `-0.000109`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.005909`
- Average label, rank 11-20: `0.005601`
- Average label, bottom 10: `-0.003439`
- `top10 - rank11_20 = 0.000308`
- `top10 - bottom10 = 0.009348`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

