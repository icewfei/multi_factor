# Design: Signal Learnability Diagnostic

**Status:** Design only, not registered. No new signal round.

**Context:** Corrected oracle proves massive returns are achievable (+2,888 annual_relative_return). Best real signal is -0.18. The gap is in signal/learnability — but where exactly?

---

## 1. Purpose

Answer: **given that the oracle label contains actionable information, how much of it is already present in the existing feature set?**

This is NOT a new signal discovery round. It's a backward-looking diagnostic on features we already have.

## 2. Method

For each existing raw feature (trend_bias, momentum, reversal, ROE, etc.), compute against the oracle label:

### 2.1 Daily IC (cross-sectional rank correlation)
`IC_t = CORR(feature_raw_t, label_5d_next_open_close_t) across stocks on signal_date t`
Average daily IC. Positive = feature directionally aligns with oracle.

### 2.2 Top-decile label lift
For each feature, rank stocks into deciles. Compute the average `label_5d_next_open_close` in the top decile vs. the bottom decile. Measures "how much does this feature tell you about the oracle label."

### 2.3 Rank overlap with oracle
For each feature's TopK=10 vs. oracle's TopK=10, compute Jaccard similarity. Measures "if we used this feature instead of the oracle, how many of the oracle's picks would we get?"

### 2.4 Composite score learnability
Take the existing 5-signal baseline score (IC-weighted) and compute its IC against the oracle label. Measures "how much oracle information is lost in score construction."

## 3. Features to Test

All existing raw features from `build_baseline_model_scores.py`:
- intraday_trend_bias_20d
- reversal_5d
- momentum_60_5
- liquidity_trend_20_60
- upside_range_share_20d
- (ROE/fundamental features from fina_indicator)

Plus the existing composite scores:
- baseline_v1 (5-signal equal weight)
- Various model_score_D0 from existing runs

## 4. Diagnostic Output

| Feature | Avg Daily IC | Top-Decile Label | Bottom-Decile Label | Spread | Oracle Overlap |
|---|---|---|---|---|---|
| intraday_trend_bias | X | Y | Z | Δ | JJ% |
| momentum_60_5 | ... | ... | ... | ... | ... |
| baseline composite | ... | ... | ... | ... | ... |

## 5. Interpretation

| Pattern | Implication |
|---|---|
| Many features have IC > 0.01 with oracle label | Information IS present in features; gap is in score construction or portfolio layer |
| All features have IC < 0.01 with oracle label | Features don't capture the oracle's information — need fundamentally different features |
| Composite score IC is similar to best single feature | Score construction adds no value (mapping loss confirmed) |
| Composite score IC is lower than best single feature | Score construction actively destroys information |

## 6. Resources

- No new builder needed — use existing `build_baseline_model_scores.py` feature output
- Oracle label is already available in `project_label_panel.parquet`
- Runs as a DuckDB query against existing score and label parquets
- No full-chain run needed — purely cross-sectional computation
