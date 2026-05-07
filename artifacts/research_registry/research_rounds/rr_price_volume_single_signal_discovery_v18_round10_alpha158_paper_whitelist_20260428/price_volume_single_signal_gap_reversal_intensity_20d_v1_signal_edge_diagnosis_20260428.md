# price_volume_single_signal_gap_reversal_intensity_20d_v1 (20260428)

Candidate: `price_volume_single_signal_gap_reversal_intensity_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 1276`
- `null_score_share = 0.00008`
- `scored_with_label_rows = 15020751`

## 2. IC Readout
- Full-sample correlation IC: `0.001094`
- Average daily IC: `0.000924`
- Median daily IC: `-0.001355`
- Positive daily IC share: `0.49339`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003540`
- Decile 2: `0.003858`
- Decile 3: `0.003962`
- Decile 4: `0.004020`
- Decile 5: `0.003987`
- Decile 6: `0.003948`
- Decile 7: `0.003899`
- Decile 8: `0.003827`
- Decile 9: `0.003790`
- Decile 10: `0.003253`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.002917`
- Average label, rank 11-20: `0.003675`
- Average label, bottom 10: `0.003213`
- `top10 - rank11_20 = -0.000757`
- `top10 - bottom10 = -0.000296`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6075`

