# price_volume_single_signal_alpha158_cntn60_v1 (20260428)

Candidate: `price_volume_single_signal_alpha158_cntn60_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round11b_canonical_batch04_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.002416`
- Average daily IC: `0.003111`
- Median daily IC: `0.000337`
- Positive daily IC share: `0.50087`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003879`
- Decile 2: `0.004012`
- Decile 3: `0.003922`
- Decile 4: `0.003935`
- Decile 5: `0.003926`
- Decile 6: `0.003878`
- Decile 7: `0.003886`
- Decile 8: `0.003791`
- Decile 9: `0.003740`
- Decile 10: `0.003151`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003722`
- Average label, rank 11-20: `0.003882`
- Average label, bottom 10: `0.003198`
- `top10 - rank11_20 = -0.000160`
- `top10 - bottom10 = 0.000524`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

