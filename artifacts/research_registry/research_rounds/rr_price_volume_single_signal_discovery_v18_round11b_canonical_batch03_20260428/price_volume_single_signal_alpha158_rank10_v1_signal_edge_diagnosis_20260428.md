# price_volume_single_signal_alpha158_rank10_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_rank10_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch03_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.015121`
- Average daily IC: `0.029500`
- Median daily IC: `0.025349`
- Positive daily IC share: `0.60252`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003982`
- Decile 2: `0.004397`
- Decile 3: `0.004916`
- Decile 4: `0.005066`
- Decile 5: `0.004896`
- Decile 6: `0.004551`
- Decile 7: `0.004205`
- Decile 8: `0.003720`
- Decile 9: `0.002156`
- Decile 10: `0.000220`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003276`
- Average label, rank 11-20: `0.004111`
- Average label, bottom 10: `-0.001003`
- `top10 - rank11_20 = -0.000835`
- `top10 - bottom10 = 0.004279`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

