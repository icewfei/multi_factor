# price_volume_single_signal_intraday_reversal_asymmetry_20d_v1 (20260428)

Candidate: `price_volume_single_signal_intraday_reversal_asymmetry_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_v18_round8_orthogonal_20260428`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 3687`
- `null_score_share = 0.00024`
- `scored_with_label_rows = 15019043`

## 2. IC Readout
- Full-sample correlation IC: `0.005550`
- Average daily IC: `0.007620`
- Median daily IC: `0.005424`
- Positive daily IC share: `0.53415`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.004106`
- Decile 2: `0.004232`
- Decile 3: `0.004037`
- Decile 4: `0.004117`
- Decile 5: `0.004077`
- Decile 6: `0.004011`
- Decile 7: `0.003837`
- Decile 8: `0.003740`
- Decile 9: `0.003368`
- Decile 10: `0.002599`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.004405`
- Average label, rank 11-20: `0.004197`
- Average label, bottom 10: `0.001418`
- `top10 - rank11_20 = 0.000208`
- `top10 - bottom10 = 0.002987`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6361`
- Days with `|gap| < 0.005`: `6361`
- Days with `|gap| < 0.001`: `6071`

