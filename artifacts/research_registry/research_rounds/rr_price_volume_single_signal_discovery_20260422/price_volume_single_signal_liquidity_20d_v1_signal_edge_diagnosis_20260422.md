# Liquidity 20D Single-Signal Edge Diagnosis (20260422)

Candidate: `price_volume_single_signal_liquidity_20d_v1`
Research round: `rr_price_volume_single_signal_discovery_20260422`

## 1. Coverage
- `ranking_eligible_rows = 15233701`
- `null_score_rows = 0`
- `null_score_share = 0.00000`
- `scored_with_label_rows = 15022019`

## 2. IC Readout
- Full-sample correlation IC: `-0.025580`
- Average daily IC: `-0.037555`
- Median daily IC: `-0.044321`
- Positive daily IC share: `0.36428`

## 3. Decile Monotonicity
Average forward label by score decile (descending):
- Decile 1: `0.001111`
- Decile 2: `0.001751`
- Decile 3: `0.002362`
- Decile 4: `0.002914`
- Decile 5: `0.003468`
- Decile 6: `0.003982`
- Decile 7: `0.004615`
- Decile 8: `0.005126`
- Decile 9: `0.005922`
- Decile 10: `0.006891`

## 4. Why `TopK=10` Still Matters
- Average label, top 10 names: `0.000797`
- Average label, rank 11-20: `0.000277`
- Average label, bottom 10: `0.008958`
- `top10 - rank11_20 = 0.000520`
- `top10 - bottom10 = -0.008161`

## 5. Cutoff Gap Around Rank 10/11
- Average score gap `rank10 - rank11`: `0.000537`
- Median score gap `rank10 - rank11`: `0.000445`
- Days with both ranks present: `6362`
- Days with `|gap| < 0.005`: `6362`
- Days with `|gap| < 0.001`: `6075`

