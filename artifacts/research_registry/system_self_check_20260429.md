# System Self-Check (20260429)

Run: `confirmatory_baseline_v1_trainval_20260429` | Snapshot: `warehouse_20260429_trainval_20211231` | Seed: `42`

## 1. Data Quality
- Scored eligible rows: `10780946`
- With label: `10604557` (98.4%)
- Main mask: `10537650` | Conservative: `10393059`
- Mask disagreement: `1.4%`
- ✅ PASS (threshold < 30%)

## 2. Signal Baseline
- Full-sample IC: `0.017758`
- Avg daily IC: `0.029527` | Median: `0.029716`
- Positive IC days: `58.9%` (5327 days)

## 3. Placebo Tests
### 3a. Shuffled Labels
- Trials: `3`, max rows: `2000000`
- Mean shuffled IC: `0.000054` | Max |IC|: `0.000432`
- ✅ PASS (|mean| < 0.005)

### 3b. Shuffled Scores
- Trials: `3`
- Mean shuffled-score IC: `0.000288` | Max |IC|: `0.001089`
- ✅ PASS (|mean| < 0.005)

### 3c. PIT Integrity (Feature Lagging)
- IC (score vs same-day label): `0.017760`
- IC (score vs NEXT-day label): `0.015177`
- ✅ PASS

## 4. Sub-period Direction Stability
- 2010-2012: IC = `0.014380`
- 2013-2015: IC = `0.016858`
- 2016-2018: IC = `0.024943`
- 2019-2021: IC = `0.008169`
- Direction consistency: `4/4` = `100%`
- ✅ PASS (threshold >= 75%)

## 5. Low Liquidity Exposure
- Normal liq IC: `0.017155` (n=9626919)
- Low liq IC: `0.045151` (n=977638)
- ✅ PASS

## 6. Benchmark
- Benchmark: `CSI_ALL_SHARE_TR` total-return=`True` days=`4133`
- ✅ PASS

## Overall
**7/7 checks passed** (0 failed)
- ✅ Mask consistency
- ✅ Placebo: shuffled labels
- ✅ Placebo: shuffled scores
- ✅ PIT integrity (no forward-looking breach)
- ✅ Sub-period direction consistency >= 75%
- ✅ Alpha not low-liquidity dependent
- ✅ Benchmark total-return available

✅ **All checks passed. System integrity confirmed on trainval snapshot.**
The 5-signal baseline is standing on a clean data foundation with no structural placebo or PIT breaches.