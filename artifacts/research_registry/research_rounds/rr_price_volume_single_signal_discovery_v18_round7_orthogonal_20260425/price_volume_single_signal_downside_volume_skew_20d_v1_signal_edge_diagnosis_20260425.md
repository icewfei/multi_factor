# price_volume_single_signal_downside_volume_skew_20d_v1 (20260425)

Candidate: `price_volume_single_signal_downside_volume_skew_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.006697`
- Average daily IC: `0.012988`
- Median daily IC: `0.010099`
- Positive daily IC share: `0.54398`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003871`
- Decile 2: `0.004160`
- Decile 3: `0.004198`
- Decile 4: `0.004248`
- Decile 5: `0.004190`
- Decile 6: `0.004155`
- Decile 7: `0.004094`
- Decile 8: `0.003872`
- Decile 9: `0.003516`
- Decile 10: `0.001812`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003118`
- Average label, rank 11-20: `0.004200`
- Average label, bottom 10: `-0.002862`
- `top10 - rank11_20 = -0.001081`
- `top10 - bottom10 = 0.005980`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

