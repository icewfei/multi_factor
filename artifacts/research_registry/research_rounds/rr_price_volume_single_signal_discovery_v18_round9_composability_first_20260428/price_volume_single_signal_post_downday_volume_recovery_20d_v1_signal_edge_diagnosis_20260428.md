# price_volume_single_signal_post_downday_volume_recovery_20d_v1 (20260428)

Candidate: `price_volume_single_signal_post_downday_volume_recovery_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round9_composability_first_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 3696`
- `null_score_share = 0.00024`
- `scored_with_label_rows = 15018352`

## 2. IC Readout
- Full-sample correlation IC: `-0.010552`
- Average daily IC: `-0.016239`
- Median daily IC: `-0.017493`
- Positive daily IC share: `0.39613`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001722`
- Decile 2: `0.003247`
- Decile 3: `0.003628`
- Decile 4: `0.003823`
- Decile 5: `0.003922`
- Decile 6: `0.004009`
- Decile 7: `0.004168`
- Decile 8: `0.004360`
- Decile 9: `0.004596`
- Decile 10: `0.004656`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `-0.005362`
- Average label, rank 11-20: `-0.000872`
- Average label, bottom 10: `0.005090`
- `top10 - rank11_20 = -0.004490`
- `top10 - bottom10 = -0.010452`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000541`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6360`
- Days with `|gap| < 0.001`: `6075`

