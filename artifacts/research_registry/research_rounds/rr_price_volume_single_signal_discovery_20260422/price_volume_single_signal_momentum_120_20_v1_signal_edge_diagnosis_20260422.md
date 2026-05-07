# Momentum 120-20 Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_momentum_120_20_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 427865`
- `null_score_share = 0.02809`
- `scored_with_label_rows = 14601368`

## 2. IC Readout
- Full-sample correlation IC: `0.003439`
- Average daily IC: `0.003619`
- Median daily IC: `-0.001148`
- Positive daily IC share: `0.49495`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004001`
- Decile 2: `0.003872`
- Decile 3: `0.003840`
- Decile 4: `0.004058`
- Decile 5: `0.004067`
- Decile 6: `0.003861`
- Decile 7: `0.003797`
- Decile 8: `0.003612`
- Decile 9: `0.003455`
- Decile 10: `0.002997`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003843`
- Average label, rank 11-20: `0.004431`
- Average label, bottom 10: `0.002133`
- `top10 - rank11_20 = -0.000588`
- `top10 - bottom10 = 0.001710`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000548`
- Median score gap `rank10 - rank11`: `0.000452`
- Days with both ranks present: `6242`
- Days with `|gap| < 0.005`: `6241`
- Days with `|gap| < 0.001`: `5986`

