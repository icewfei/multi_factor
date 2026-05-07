# price_volume_single_signal_return_skew_20d_v1 (20260425)

Candidate: `price_volume_single_signal_return_skew_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round7_orthogonal_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 903`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021124`

## 2. IC Readout
- Full-sample correlation IC: `0.009823`
- Average daily IC: `0.014188`
- Median daily IC: `0.013648`
- Positive daily IC share: `0.58782`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004129`
- Decile 2: `0.004465`
- Decile 3: `0.004521`
- Decile 4: `0.004451`
- Decile 5: `0.004298`
- Decile 6: `0.004155`
- Decile 7: `0.003788`
- Decile 8: `0.003453`
- Decile 9: `0.002941`
- Decile 10: `0.001879`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002094`
- Average label, rank 11-20: `0.003052`
- Average label, bottom 10: `0.000440`
- `top10 - rank11_20 = -0.000958`
- `top10 - bottom10 = 0.001655`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

