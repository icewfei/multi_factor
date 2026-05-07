# price_volume_single_signal_alpha158_roc10_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_roc10_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch01_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 9091`
- `null_score_share = 0.00060`
- `scored_with_label_rows = 15013014`

## 2. IC Readout
- Full-sample correlation IC: `0.013505`
- Average daily IC: `0.022806`
- Median daily IC: `0.018973`
- Positive daily IC share: `0.56281`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003758`
- Decile 2: `0.004498`
- Decile 3: `0.004643`
- Decile 4: `0.004729`
- Decile 5: `0.004791`
- Decile 6: `0.004677`
- Decile 7: `0.004443`
- Decile 8: `0.003890`
- Decile 9: `0.002911`
- Decile 10: `-0.000215`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.000482`
- Average label, rank 11-20: `0.003479`
- Average label, bottom 10: `-0.002233`
- `top10 - rank11_20 = -0.003961`
- `top10 - bottom10 = 0.001751`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000536`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6352`
- Days with `|gap| < 0.005`: `6352`
- Days with `|gap| < 0.001`: `6075`

