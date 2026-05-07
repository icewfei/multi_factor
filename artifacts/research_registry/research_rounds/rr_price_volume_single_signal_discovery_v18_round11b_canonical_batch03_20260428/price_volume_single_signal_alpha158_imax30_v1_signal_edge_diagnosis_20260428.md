# price_volume_single_signal_alpha158_imax30_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_imax30_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.012305`
- Average daily IC: `0.019401`
- Median daily IC: `0.019083`
- Positive daily IC share: `0.57797`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004284`
- Decile 2: `0.004782`
- Decile 3: `0.004666`
- Decile 4: `0.004284`
- Decile 5: `0.004118`
- Decile 6: `0.004120`
- Decile 7: `0.004164`
- Decile 8: `0.003777`
- Decile 9: `0.002913`
- Decile 10: `0.001004`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004465`
- Average label, rank 11-20: `0.004775`
- Average label, bottom 10: `-0.001460`
- `top10 - rank11_20 = -0.000310`
- `top10 - bottom10 = 0.005925`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

