# price_volume_single_signal_momentum_250_20_v1 Signal Edge Diagnosis (20260423)

Candidate: `price_volume_single_signal_momentum_250_20_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round3_20260423`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1055789`
- `null_score_share = 0.06931`
- `scored_with_label_rows = 13981278`

## 2. IC Readout
- Full-sample correlation IC: `0.000253`
- Average daily IC: `-0.000670`
- Median daily IC: `-0.003613`
- Positive daily IC share: `0.48902`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003256`
- Decile 2: `0.003905`
- Decile 3: `0.004090`
- Decile 4: `0.004205`
- Decile 5: `0.004335`
- Decile 6: `0.004295`
- Decile 7: `0.004014`
- Decile 8: `0.003922`
- Decile 9: `0.003765`
- Decile 10: `0.003321`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002782`
- Average label, rank 11-20: `0.003568`
- Average label, bottom 10: `0.003961`
- `top10 - rank11_20 = -0.000786`
- `top10 - bottom10 = -0.001179`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000566`
- Median score gap `rank10 - rank11`: `0.000462`
- Days with both ranks present: `6112`
- Days with `|gap| < 0.005`: `6111`
- Days with `|gap| < 0.001`: `5848`

