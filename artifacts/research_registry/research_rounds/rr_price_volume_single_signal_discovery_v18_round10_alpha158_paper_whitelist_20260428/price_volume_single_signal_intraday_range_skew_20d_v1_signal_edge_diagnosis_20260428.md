# price_volume_single_signal_intraday_range_skew_20d_v1 (20260428)

Candidate: `price_volume_single_signal_intraday_range_skew_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round10_alpha158_paper_whitelist_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `0.002082`
- Average daily IC: `0.002195`
- Median daily IC: `-0.001286`
- Positive daily IC share: `0.49504`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.003338`
- Decile 2: `0.003937`
- Decile 3: `0.003966`
- Decile 4: `0.004025`
- Decile 5: `0.004078`
- Decile 6: `0.004266`
- Decile 7: `0.004171`
- Decile 8: `0.004000`
- Decile 9: `0.003729`
- Decile 10: `0.002609`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.003087`
- Average label, rank 11-20: `0.003865`
- Average label, bottom 10: `0.001539`
- `top10 - rank11_20 = -0.000778`
- `top10 - bottom10 = 0.001547`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

