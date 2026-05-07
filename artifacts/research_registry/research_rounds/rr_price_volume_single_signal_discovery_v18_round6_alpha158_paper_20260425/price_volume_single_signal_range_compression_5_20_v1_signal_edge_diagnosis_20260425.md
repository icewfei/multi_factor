# price_volume_single_signal_range_compression_5_20_v1 (20260425)

Candidate: `price_volume_single_signal_range_compression_5_20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 769`
- `null_score_share = 0.00005`
- `scored_with_label_rows = 15021902`

## 2. IC Readout
- Full-sample correlation IC: `-0.001915`
- Average daily IC: `-0.002900`
- Median daily IC: `-0.004684`
- Positive daily IC share: `0.47459`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001591`
- Decile 2: `0.003818`
- Decile 3: `0.004316`
- Decile 4: `0.004530`
- Decile 5: `0.004558`
- Decile 6: `0.004548`
- Decile 7: `0.004410`
- Decile 8: `0.004148`
- Decile 9: `0.003691`
- Decile 10: `0.002513`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.003696`
- Average label, rank 11-20: `-0.000888`
- Average label, bottom 10: `0.002755`
- `top10 - rank11_20 = -0.002808`
- `top10 - bottom10 = -0.006451`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6071`

