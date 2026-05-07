# price_volume_single_signal_price_volume_corr_20d_v1 (20260425)

Candidate: `price_volume_single_signal_price_volume_corr_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.016661`
- Average daily IC: `0.029966`
- Median daily IC: `0.027631`
- Positive daily IC share: `0.63676`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.005305`
- Decile 2: `0.004883`
- Decile 3: `0.004720`
- Decile 4: `0.004374`
- Decile 5: `0.004273`
- Decile 6: `0.003997`
- Decile 7: `0.003695`
- Decile 8: `0.003194`
- Decile 9: `0.002652`
- Decile 10: `0.000981`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.007764`
- Average label, rank 11-20: `0.006709`
- Average label, bottom 10: `-0.001614`
- `top10 - rank11_20 = 0.001056`
- `top10 - bottom10 = 0.009379`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

