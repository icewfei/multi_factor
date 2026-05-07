# price_volume_single_signal_alpha158_resi60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_resi60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch02_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.011714`
- Average daily IC: `0.020750`
- Median daily IC: `0.016549`
- Positive daily IC share: `0.55673`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004214`
- Decile 2: `0.003959`
- Decile 3: `0.004212`
- Decile 4: `0.004483`
- Decile 5: `0.004658`
- Decile 6: `0.004658`
- Decile 7: `0.004542`
- Decile 8: `0.004254`
- Decile 9: `0.003302`
- Decile 10: `-0.000169`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003292`
- Average label, rank 11-20: `0.006066`
- Average label, bottom 10: `-0.001517`
- `top10 - rank11_20 = -0.002774`
- `top10 - bottom10 = 0.004809`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

