# Rank-Band Full Profile Descriptive Diagnosis Summary

This record summarizes the implemented rank-band full profile descriptive diagnosis.

The diagnosis is descriptive-only exploratory mechanism research. It does not make an alpha claim, does not create a candidate, does not train, does not backtest, does not run portfolio, does not read frozen test, and does not treat trainval diagnosis as OOS.

## Outputs

The implemented script writes:

- `/private/tmp/rank_band_full_profile_descriptive_diagnosis.json`
- `/private/tmp/rank_band_full_profile_descriptive_diagnosis.md`

## Scope

The diagnosis reports fixed rank bands for existing clean scores:

- 1-30
- 31-60
- 31-100
- 31-200
- 101-300
- 301-600
- bottom 30

For each band, it reports mean, median, volatility, daily win rate vs 0, yearly mean, best 5% contribution, worst 5% damage, band profile shape, and exposure structure.

Exposure structure includes amount bucket, board / exchange, limit / tradability, and listing_age_days bucket.

## Conditional References

`p98` and `multi_equal_weight_v1` are reported only as conditional references. They are not clean gold standards, not clean components, and not promotion anchors.

## Final Statement

This diagnosis is descriptive only. It gives no deployment conclusion and no portfolio recommendation.
