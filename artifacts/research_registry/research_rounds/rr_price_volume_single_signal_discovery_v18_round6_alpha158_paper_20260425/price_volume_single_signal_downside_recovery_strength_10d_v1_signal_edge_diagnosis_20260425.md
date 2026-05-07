# price_volume_single_signal_downside_recovery_strength_10d_v1 (20260425)

Candidate: `price_volume_single_signal_downside_recovery_strength_10d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round6_alpha158_paper_20260425`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 2952`
- `null_score_share = 0.00019`
- `scored_with_label_rows = 15019298`

## 2. IC Readout
- Full-sample correlation IC: `0.006165`
- Average daily IC: `0.007899`
- Median daily IC: `0.006370`
- Positive daily IC share: `0.54076`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003599`
- Decile 2: `0.004088`
- Decile 3: `0.004257`
- Decile 4: `0.004239`
- Decile 5: `0.004361`
- Decile 6: `0.004327`
- Decile 7: `0.004159`
- Decile 8: `0.003975`
- Decile 9: `0.003347`
- Decile 10: `0.001703`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001345`
- Average label, rank 11-20: `0.003708`
- Average label, bottom 10: `-0.001299`
- `top10 - rank11_20 = -0.002363`
- `top10 - bottom10 = 0.002645`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

