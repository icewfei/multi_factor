# price_volume_single_signal_alpha158_klow2_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_klow2_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.003553`
- Average daily IC: `0.005063`
- Median daily IC: `0.006217`
- Positive daily IC share: `0.54005`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003807`
- Decile 2: `0.003951`
- Decile 3: `0.004093`
- Decile 4: `0.004092`
- Decile 5: `0.004030`
- Decile 6: `0.003981`
- Decile 7: `0.004021`
- Decile 8: `0.003843`
- Decile 9: `0.003552`
- Decile 10: `0.002749`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003733`
- Average label, rank 11-20: `0.003914`
- Average label, bottom 10: `-0.000479`
- `top10 - rank11_20 = -0.000181`
- `top10 - bottom10 = 0.004212`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

