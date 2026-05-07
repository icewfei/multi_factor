# round11 / round11b governance reconciliation (20260428)

## Decision

Round11 and round11b now use **exact qlib Alpha158 full-definition scope** as the only active governance boundary.

## What changed

- The active canonical source is the local qlib package entry `Alpha158DL.get_feature_config()`, which returns exactly `158` features.
- The old `alpha158_atomic_pool_v1` boundary is retained only as a historical record and is no longer the meaning of "full Alpha158".
- The earlier slot-numbered `alpha158_full_001~036` runs are preserved as historical alpha158-style pilots, but they do **not** count toward exact qlib Alpha158 completion.

## Active scope

- Canonical full-definition count: `158`
- Canonical executed count: `0`
- Canonical remaining count: `158`
- Canonical candidate naming rule: `price_volume_single_signal_alpha158_<qlib_feature_name_lower>_v1`
- Canonical field naming rule: `alpha158_<qlib_feature_name_lower>_raw`

## Source anchors

- Canonical manifest: `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_qlib_full_definition_manifest_20260428.json`
- Reconciled universe manifest: `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_full158_universe_manifest_20260428.json`
- Historical superseded boundary: `/Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_atomic_pool_v1_round11_manifest_20260428.json`

## Consequence

Future round11b execution should no longer extend slot-numbered `alpha158_full_0xx` candidates. It should reopen from canonical batch01 using exact qlib feature names and exact qlib expressions, implemented independently on this project's own data pipeline.
