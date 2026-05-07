# price_volume_single_signal_alpha158_full_032_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_full_032_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.000664`
- Average daily IC: `0.002897`
- Median daily IC: `0.000344`
- Positive daily IC share: `0.50197`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003809`
- Decile 2: `0.003775`
- Decile 3: `0.003777`
- Decile 4: `0.003891`
- Decile 5: `0.003909`
- Decile 6: `0.003906`
- Decile 7: `0.003990`
- Decile 8: `0.003824`
- Decile 9: `0.003767`
- Decile 10: `0.003472`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004365`
- Average label, rank 11-20: `0.004435`
- Average label, bottom 10: `0.001862`
- `top10 - rank11_20 = -0.000070`
- `top10 - bottom10 = 0.002503`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

