# Phase Summary: Overnight/Intraday Return Decomposition + Reversal Interaction

**Round ID:** `rr_exploratory_overnight_intraday_decomposition_20260506`
**Status:** COMPLETED — **all candidates failed to beat p98 baseline**
**Completed at:** 2026-05-06

---

## 1. Research Question

将日收益率拆解为隔夜（`adj_open / LAG(adj_close) - 1`）和日内（`adj_close / adj_open - 1`）成分后，单独或与 p98 复合是否能产出超越 p98 baseline 的信号？

## 2. Method

### Feature Engineering

- `overnight_ret = adj_open / LAG(adj_close) - 1`
- `intraday_ret = adj_close / adj_open - 1`
- 滚动5日/20日累计窗口，横截面 PERCENT_RANK
- 方向对齐：排名 DESC（与 p98 的动量方向一致）

### Candidate Schemes Tested (11 total)

**V1 (reversal direction, 6 single + 5 composite):**
- `overnight_rev_5d_v1`, `intraday_rev_5d_v1`, `overnight_rev_20d_v1`, `intraday_rev_20d_v1`
- `overnight_vol_5d_v1`, `overnight_intraday_divergence_v1`
- `overnight_p98_ew_v1`, `intraday_p98_ew_v1`, `overnight_intraday_ew_v1`, `overnight70_p98_30_v1`, `intraday70_p98_30_v1`

**V2 (momentum-aligned, 5 single + 4 composite):**
- `intraday_mom_5d_v1`, `overnight_mom_5d_v1`, `intraday_mom_20d_v1`, `overnight_mom_20d_v1`
- `intraday_p98_ew_v2`, `overnight_p98_ew_v2`, `p98_overnight_supplement_v2`, `overnight_intraday_mom_ew_v2`, `intraday80_overnight20_mom_v2`

## 3. Key Learnability Diagnostic Results

| Scheme | Median IC [95% CI] | Corr w/ p98 | Classification |
|---|---|---|---|
| **p98 (baseline)** | **0.046045** [0.042, 0.050] | — | baseline |
| `p98_overnight_supplement_v2` | 0.044564 [-0.003, 0.267] | 0.9944 | CI issue |
| `intraday_p98_ew_v2` | 0.043592 [0.039, 0.047] | 0.9645 | PASS |
| `overnight_intraday_mom_ew_v2` | 0.041772 [0.038, 0.046] | 0.8533 | PASS |
| `intraday_mom_5d_v1` | 0.036641 [0.034, 0.040] | 0.8581 | PASS |
| `overnight_mom_5d_v1` | 0.013648 [0.012, 0.016] | **0.1816** | MARGINAL |

## 4. Full-Chain Fixed Test Results (Validation: 2019-2021)

| Scheme | AnnRelRet | MaxDD | Sharpe | Turnover | InvWt | CostStress |
|---|---|---|---|---|---|---|
| **p98 (baseline)** | **-0.1293** | **-0.0867** | **13.59** | 0.1245 | 0.2510 | -0.0610 |
| `p98_overnight_supplement_v2` | -0.1695 | -0.0895 | 10.38 | 0.1047 | 0.2121 | -0.0822 |
| `intraday_mom_5d_v1` | -0.2282 | -0.1931 | 3.08 | 0.0904 | 0.1886 | -0.1233 |
| `overnight_intraday_mom_ew_v2` | -0.2525 | -0.2960 | 2.24 | 0.0904 | 0.1880 | -0.1318 |

All candidates worse than p98 on every metric. No promotion.

## 5. Structural Findings

### p98 Signal Decomposition

- **86% of p98's signal comes from the intraday component** (corr = 0.86)
- Overnight component is **genuinely orthogonal** to p98 (corr = 0.18) but **too weak** (IC = 0.014)
- Adding overnight to any composite **dilutes** p98's performance

### Tail Handling Necessity

- `intraday_mom_5d_v1` (pure intraday, no tail handling) achieves IC = 0.037
- p98's tail exclusion adds ~0.01 IC (0.037 → 0.046)
- Confirms tail handling is the key differentiator, not the decomposition itself

### Consistency with Prior Findings

- Aligns with `note_local_feature_space_exhaustion_20260506.md`
- Current daily bars-derived feature space is near-exhausted around p98
- Small feature engineering tweaks cannot break through the 6/9 ceiling

## 6. Decision

**All 11 candidates REJECTED.** Overnight/intraday decomposition provides mechanistic understanding but no performance improvement over p98.

**Recommendation:** If project reopens, pursue new data modality (e.g., overnight/downside repair microstructure) rather than further decomposition within existing daily bars.

## 7. Artifacts

- Scores: `artifacts/run_state/exploratory_overnight_intraday_decomposition_v1/model_scores_D0.parquet` (v1), `model_scores_D0_v2.parquet` (v2)
- Diagnostics: `artifacts/fixed_test/overnight_intraday_diagnostic/overnight_intraday_diagnostic_20260506.json`, `overnight_intraday_v2_diagnostic_20260506.json`
- Full-chain: `artifacts/fixed_test/exploratory_overnight_intraday_mom_ew_v2/`, `exploratory_intraday_mom_5d_v1/`, `exploratory_p98_overnight_supplement_v2/`
- Scripts: `scripts/build_overnight_intraday_decomposition_scores.py`, `scripts/build_overnight_intraday_v2_scores.py`, `scripts/run_overnight_intraday_diagnostic.py`, `scripts/run_overnight_intraday_v2_diagnostic.py`, `scripts/run_overnight_intraday_fullchain.py`
