# price_volume_single_signal_alpha158_sump5_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_sump5_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 907`
- `null_score_share = 0.00006`
- `scored_with_label_rows = 15021120`

## 2. IC Readout
- Full-sample correlation IC: `0.017155`
- Average daily IC: `0.033833`
- Median daily IC: `0.029665`
- Positive daily IC share: `0.61394`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004035`
- Decile 2: `0.004808`
- Decile 3: `0.004948`
- Decile 4: `0.005036`
- Decile 5: `0.004959`
- Decile 6: `0.004557`
- Decile 7: `0.004159`
- Decile 8: `0.003527`
- Decile 9: `0.002259`
- Decile 10: `-0.000212`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.001755`
- Average label, rank 11-20: `0.003563`
- Average label, bottom 10: `-0.002395`
- `top10 - rank11_20 = -0.001807`
- `top10 - bottom10 = 0.004150`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

