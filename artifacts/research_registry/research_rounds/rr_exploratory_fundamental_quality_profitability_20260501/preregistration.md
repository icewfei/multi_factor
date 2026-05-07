# Preregistration: Fundamental Quality/Profitability

- `research_round_id`: `rr_exploratory_fundamental_quality_profitability_20260501`
- `research_tier`: `exploratory`
- `round_type`: `family_construction`
- `status`: `preregistered`

## Baseline

`exploratory_cohort5_v18_ref` (contract-matched, 5-cohort)

## Candidates

| Order | ID | Preset | min_feature | Role |
|---|---|---|---|---|
| 1 | `c1_roe_dt` | single_roe_dt | >= 1 | Single signal control |
| 2 | `c2_roa_yearly` | single_roa_yearly | >= 1 | Single signal control |
| 3 | `c3_roe_roa` | roe_dt_plus_roa_yearly | >= 2 | Main test candidate |

## Serial Rule

Serial but non-cascading. All 3 frozen upfront. No mid-round definition changes.

## Success Rules

Same 9 gates as all previous rounds. Core pass condition: all 9 must pass.
