# price_volume_single_signal_downside_gap_recovery_10d_v1 (20260425)

Candidate: `price_volume_single_signal_downside_gap_recovery_10d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round5_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 96358`
- `null_score_share = 0.00633`
- `scored_with_label_rows = 14927122`

## 2. IC Readout
- Full-sample correlation IC: `0.004330`
- Average daily IC: `0.005501`
- Median daily IC: `0.004920`
- Positive daily IC share: `0.53809`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004071`
- Decile 2: `0.004069`
- Decile 3: `0.004004`
- Decile 4: `0.003983`
- Decile 5: `0.004013`
- Decile 6: `0.004029`
- Decile 7: `0.003927`
- Decile 8: `0.003726`
- Decile 9: `0.003519`
- Decile 10: `0.002845`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003726`
- Average label, rank 11-20: `0.003834`
- Average label, bottom 10: `0.001714`
- `top10 - rank11_20 = -0.000109`
- `top10 - bottom10 = 0.002011`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000543`
- Median score gap `rank10 - rank11`: `0.000447`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6011`

