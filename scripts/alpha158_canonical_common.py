#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Shared helpers for canonical qlib Alpha158 single-signal execution under this
project's own data semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from single_signal_batch_common import CandidateSpec, sql_path, sql_quote


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
MANIFEST_PATH = REGISTRY_DIR / "alpha158_qlib_full_definition_manifest_20260428.json"
WHITELIST_REF = REGISTRY_DIR / "alpha158_paper_source_whitelist_20260428.json"
SOURCE_LOCATOR = "Qlib Alpha158 exact feature family specification (local manifest boundary)"
SOURCE_TITLE = "Qlib Alpha158 exact canonical feature definition"
INDEPENDENT_NOTE = (
    "implemented independently on this project's adjusted-price and native daily-bar contracts; "
    "no dependency on neighboring qlib adapters or exported qlib features"
)


FEATURE_META: dict[str, dict[str, str]] = {
    "KMID": {
        "ranking_direction": "DESC",
        "interpretation": "stronger bullish candle body relative to open",
        "nearest_canonical_signal": "candle_body_efficiency_20d_raw",
        "independent_budget_reason": "Single-day standardized body return differs from rolling body-efficiency averaging.",
    },
    "KLEN": {
        "ranking_direction": "ASC",
        "interpretation": "shorter intraday range relative to open",
        "nearest_canonical_signal": "volatility_20d_raw",
        "independent_budget_reason": "Single-day standardized full-range length differs from multi-day realized volatility levels.",
    },
    "KMID2": {
        "ranking_direction": "DESC",
        "interpretation": "larger body share within the daily range",
        "nearest_canonical_signal": "candle_body_efficiency_20d_raw",
        "independent_budget_reason": "Range-normalized body share is a stricter canonical definition than the project's earlier rolling body-efficiency proxy.",
    },
    "KUP": {
        "ranking_direction": "ASC",
        "interpretation": "smaller upper shadow relative to open",
        "nearest_canonical_signal": "upper_shadow_ratio_20d_raw",
        "independent_budget_reason": "Exact one-day upper-shadow standardization differs from the earlier rolling ratio construction.",
    },
    "KUP2": {
        "ranking_direction": "ASC",
        "interpretation": "smaller upper shadow share within the daily range",
        "nearest_canonical_signal": "upper_shadow_ratio_20d_raw",
        "independent_budget_reason": "Range-normalized upper-shadow share is more canonical than the project's earlier rolling upper-shadow averages.",
    },
    "KLOW": {
        "ranking_direction": "DESC",
        "interpretation": "stronger lower-shadow support relative to open",
        "nearest_canonical_signal": "lower_shadow_support_20d_raw",
        "independent_budget_reason": "Exact one-day lower-shadow support is distinct from the project's earlier rolling support aggregation.",
    },
    "KLOW2": {
        "ranking_direction": "DESC",
        "interpretation": "larger lower-shadow share within the daily range",
        "nearest_canonical_signal": "lower_shadow_support_20d_raw",
        "independent_budget_reason": "Range-normalized lower-shadow share is the exact Alpha158 form rather than a rolling support proxy.",
    },
    "KSFT": {
        "ranking_direction": "DESC",
        "interpretation": "close shifted higher within the day's range relative to open",
        "nearest_canonical_signal": "close_location_value_20d_raw",
        "independent_budget_reason": "This exact close-shift formula differs from the project's earlier close-location and skew-style summaries.",
    },
    "KSFT2": {
        "ranking_direction": "DESC",
        "interpretation": "range-normalized close shift toward the upper part of the bar",
        "nearest_canonical_signal": "close_location_value_20d_raw",
        "independent_budget_reason": "Range-normalized close shift is a stricter Alpha158 atomic definition than prior rolling close-location signals.",
    },
    "OPEN0": {
        "ranking_direction": "ASC",
        "interpretation": "lower open-to-close ratio, implying stronger close versus open",
        "nearest_canonical_signal": "overnight_intraday_consistency_20d_raw",
        "independent_budget_reason": "Direct open-versus-close ratio is a canonical one-day price-location measure rather than a rolling overnight/intraday interaction summary.",
    },
    "HIGH0": {
        "ranking_direction": "ASC",
        "interpretation": "high closer to close, implying stronger close near the daily high",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "Same-day high-to-close proximity is more primitive and standardized than the project's rolling breakout distance signals.",
    },
    "LOW0": {
        "ranking_direction": "ASC",
        "interpretation": "low closer to close, implying a stronger close away from the lower tail",
        "nearest_canonical_signal": "lower_shadow_support_20d_raw",
        "independent_budget_reason": "Same-day low-to-close proximity differs from rolling lower-shadow or support-frequency constructions.",
    },
    "VWAP0": {
        "ranking_direction": "ASC",
        "interpretation": "vwap below close, implying stronger close above volume-weighted trading level",
        "nearest_canonical_signal": "close_to_vwap_bias_20d_raw",
        "independent_budget_reason": "Exact adjusted vwap-to-close ratio is more canonical than the project's earlier OHLC-average vwap proxy signal.",
    },
    "ROC5": {
        "ranking_direction": "ASC",
        "interpretation": "stronger 5-day price momentum",
        "nearest_canonical_signal": "momentum_20_5_raw",
        "independent_budget_reason": "Direct lagged close ratio is a cleaner canonical momentum atom than the project's gap-based or multi-window momentum variants.",
    },
    "ROC10": {
        "ranking_direction": "ASC",
        "interpretation": "stronger 10-day price momentum",
        "nearest_canonical_signal": "momentum_60_5_raw",
        "independent_budget_reason": "Direct 10-day lagged close ratio is a canonical momentum definition distinct from the project's prior custom windows.",
    },
    "ROC20": {
        "ranking_direction": "ASC",
        "interpretation": "stronger 20-day price momentum",
        "nearest_canonical_signal": "momentum_120_20_raw",
        "independent_budget_reason": "Exact 20-day lagged price ratio anchors momentum to a standard Alpha158 definition rather than project-specific horizons.",
    },
    "ROC30": {
        "ranking_direction": "ASC",
        "interpretation": "stronger 30-day price momentum",
        "nearest_canonical_signal": "momentum_120_20_raw",
        "independent_budget_reason": "This adds a standardized intermediate horizon that the project had not tested in exact lagged-ratio form.",
    },
    "ROC60": {
        "ranking_direction": "ASC",
        "interpretation": "stronger 60-day price momentum",
        "nearest_canonical_signal": "momentum_250_20_raw",
        "independent_budget_reason": "Exact 60-day lagged ratio differs from the project's longer-horizon custom momentum ratios.",
    },
    "MA5": {
        "ranking_direction": "ASC",
        "interpretation": "current close above 5-day moving average",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Direct moving-average displacement is a canonical trend atom rather than a persistence/followthrough summary.",
    },
    "MA10": {
        "ranking_direction": "ASC",
        "interpretation": "current close above 10-day moving average",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Standardized 10-day moving-average displacement adds a cleaner trend atom than the project's earlier pattern signals.",
    },
    "MA20": {
        "ranking_direction": "ASC",
        "interpretation": "current close above 20-day moving average",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "Exact 20-day moving-average ratio is a canonical trend form rather than a composite trend-consistency measure.",
    },
    "MA30": {
        "ranking_direction": "ASC",
        "interpretation": "current close above 30-day moving average",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "The 30-day moving-average displacement introduces a standardized intermediate trend horizon not previously isolated in this form.",
    },
    "MA60": {
        "ranking_direction": "ASC",
        "interpretation": "current close above 60-day moving average",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "Longer-horizon moving-average displacement is more canonical than breakout proximity and other custom trend summaries.",
    },
    "STD5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day close volatility",
        "nearest_canonical_signal": "volatility_20d_raw",
        "independent_budget_reason": "Rolling price standard deviation is a canonical close-volatility atom rather than return-volatility or range-volatility customizations.",
    },
    "STD10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day close volatility",
        "nearest_canonical_signal": "volatility_20d_raw",
        "independent_budget_reason": "Exact 10-day close standard deviation adds a standardized horizon distinct from the project's earlier volatility windows.",
    },
    "STD20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day close volatility",
        "nearest_canonical_signal": "volatility_20d_raw",
        "independent_budget_reason": "This is the canonical close-based volatility form rather than the project's return-based volatility proxy.",
    },
    "STD30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day close volatility",
        "nearest_canonical_signal": "volatility_60d_raw",
        "independent_budget_reason": "30-day close standard deviation adds a standardized medium horizon absent from prior custom volatility tests.",
    },
    "STD60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day close volatility",
        "nearest_canonical_signal": "volatility_60d_raw",
        "independent_budget_reason": "Exact 60-day close standard deviation is a canonical long-horizon volatility atom distinct from earlier return-based variants.",
    },
    "BETA5": {
        "ranking_direction": "DESC",
        "interpretation": "stronger positive 5-day price slope",
        "nearest_canonical_signal": "momentum_20_5_raw",
        "independent_budget_reason": "Regression slope extracts directional trend strength more canonically than discrete lagged-return ratios.",
    },
    "BETA10": {
        "ranking_direction": "DESC",
        "interpretation": "stronger positive 10-day price slope",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Standardized 10-day regression slope is a canonical trend-strength atom rather than a custom persistence summary.",
    },
    "BETA20": {
        "ranking_direction": "DESC",
        "interpretation": "stronger positive 20-day price slope",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "20-day regression slope isolates standardized trend strength more canonically than multi-signal trend summaries.",
    },
    "BETA30": {
        "ranking_direction": "DESC",
        "interpretation": "stronger positive 30-day price slope",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day regression slope adds a clean medium-horizon trend-strength atom absent from earlier custom definitions.",
    },
    "BETA60": {
        "ranking_direction": "DESC",
        "interpretation": "stronger positive 60-day price slope",
        "nearest_canonical_signal": "momentum_250_20_raw",
        "independent_budget_reason": "60-day regression slope captures long-horizon trend shape more canonically than discrete momentum ratios.",
    },
    "RSQR5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day linear-trend fit quality",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Trend-fit quality is orthogonal to raw slope magnitude and differs from persistence-count style trend measures.",
    },
    "RSQR10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day linear-trend fit quality",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "10-day regression fit quality is a canonical smooth-trend atom not isolated by prior project signals.",
    },
    "RSQR20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day linear-trend fit quality",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "20-day R-squared captures medium-horizon path smoothness rather than directional level alone.",
    },
    "RSQR30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day linear-trend fit quality",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "30-day regression fit is a standardized path-smoothness metric distinct from custom path-efficiency formulations.",
    },
    "RSQR60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day linear-trend fit quality",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "60-day regression fit quality captures long-horizon smooth trend structure rather than simple return accumulation.",
    },
    "RESI5": {
        "ranking_direction": "DESC",
        "interpretation": "more positive 5-day regression residual relative to close",
        "nearest_canonical_signal": "intraday_path_curvature_20d_raw",
        "independent_budget_reason": "Short-window signed regression residuals isolate above-trend displacement in a canonical price-only way unlike earlier roughness proxies.",
    },
    "RESI10": {
        "ranking_direction": "DESC",
        "interpretation": "more positive 10-day regression residual relative to close",
        "nearest_canonical_signal": "intraday_path_curvature_20d_raw",
        "independent_budget_reason": "10-day signed regression residuals capture above-trend displacement rather than custom intraday noise summaries.",
    },
    "RESI20": {
        "ranking_direction": "DESC",
        "interpretation": "more positive 20-day regression residual relative to close",
        "nearest_canonical_signal": "path_efficiency_20d_raw",
        "independent_budget_reason": "20-day signed residuals provide a canonical medium-horizon above-trend displacement atom distinct from ratio-style path efficiency.",
    },
    "RESI30": {
        "ranking_direction": "DESC",
        "interpretation": "more positive 30-day regression residual relative to close",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "30-day signed regression residuals give a standardized medium-horizon above-trend displacement measure missing from earlier signals.",
    },
    "RESI60": {
        "ranking_direction": "DESC",
        "interpretation": "more positive 60-day regression residual relative to close",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "60-day signed residuals capture long-horizon above-trend displacement rather than pure cumulative momentum.",
    },
    "MAX5": {
        "ranking_direction": "ASC",
        "interpretation": "close nearer the 5-day rolling high",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "Exact rolling-high distance ratio is more canonical and horizon-specific than earlier breakout proximity variants.",
    },
    "MAX10": {
        "ranking_direction": "ASC",
        "interpretation": "close nearer the 10-day rolling high",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "10-day rolling-high ratio adds a standardized short trend-strength anchor absent from prior custom definitions.",
    },
    "MAX20": {
        "ranking_direction": "ASC",
        "interpretation": "close nearer the 20-day rolling high",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "20-day rolling-high ratio is the exact Alpha158 proximity form rather than the project's prior bespoke breakout distance.",
    },
    "MAX30": {
        "ranking_direction": "ASC",
        "interpretation": "close nearer the 30-day rolling high",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "30-day rolling-high ratio introduces a standardized intermediate breakout horizon not previously isolated in this exact form.",
    },
    "MAX60": {
        "ranking_direction": "ASC",
        "interpretation": "close nearer the 60-day rolling high",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "60-day rolling-high ratio is a canonical long-horizon breakout anchor distinct from other trend proxies.",
    },
    "MIN5": {
        "ranking_direction": "ASC",
        "interpretation": "close farther above the 5-day rolling low",
        "nearest_canonical_signal": "lower_shadow_support_20d_raw",
        "independent_budget_reason": "Rolling-low distance ratio measures support escape in a more canonical way than candle-shadow support summaries.",
    },
    "MIN10": {
        "ranking_direction": "ASC",
        "interpretation": "close farther above the 10-day rolling low",
        "nearest_canonical_signal": "lower_shadow_support_20d_raw",
        "independent_budget_reason": "10-day rolling-low ratio standardizes downside escape strength beyond intraday shadow-based support measures.",
    },
    "MIN20": {
        "ranking_direction": "ASC",
        "interpretation": "close farther above the 20-day rolling low",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "20-day rolling-low ratio is an exact Alpha158 downside-distance measure rather than the project's earlier custom breakdown distance.",
    },
    "MIN30": {
        "ranking_direction": "ASC",
        "interpretation": "close farther above the 30-day rolling low",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "30-day rolling-low ratio adds a standardized medium horizon to downside-distance measurement.",
    },
    "MIN60": {
        "ranking_direction": "ASC",
        "interpretation": "close farther above the 60-day rolling low",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "60-day rolling-low ratio is a canonical long-horizon downside-distance anchor distinct from custom breakdown metrics.",
    },
    "QTLU5": {
        "ranking_direction": "ASC",
        "interpretation": "close above the 5-day upper rolling quantile",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "Upper-quantile displacement captures robust breakout position beyond max-high sensitivity.",
    },
    "QTLU10": {
        "ranking_direction": "ASC",
        "interpretation": "close above the 10-day upper rolling quantile",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "10-day upper-quantile displacement is a standardized robust-strength atom not previously isolated in this form.",
    },
    "QTLU20": {
        "ranking_direction": "ASC",
        "interpretation": "close above the 20-day upper rolling quantile",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "20-day upper-quantile displacement is more robust to outliers than rolling-high distance alone.",
    },
    "QTLU30": {
        "ranking_direction": "ASC",
        "interpretation": "close above the 30-day upper rolling quantile",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "30-day upper-quantile displacement adds a standardized medium-horizon robust breakout anchor.",
    },
    "QTLU60": {
        "ranking_direction": "ASC",
        "interpretation": "close above the 60-day upper rolling quantile",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "60-day upper-quantile displacement provides a canonical long-horizon robust trend-position measure.",
    },
    "QTLD5": {
        "ranking_direction": "ASC",
        "interpretation": "close well above the 5-day lower rolling quantile",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "Lower-quantile displacement measures downside clearance more robustly than raw rolling lows.",
    },
    "QTLD10": {
        "ranking_direction": "ASC",
        "interpretation": "close well above the 10-day lower rolling quantile",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "10-day lower-quantile displacement standardizes downside clearance beyond extreme-low sensitivity.",
    },
    "QTLD20": {
        "ranking_direction": "ASC",
        "interpretation": "close well above the 20-day lower rolling quantile",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "20-day lower-quantile displacement is a more robust downside-clearance anchor than raw rolling lows.",
    },
    "QTLD30": {
        "ranking_direction": "ASC",
        "interpretation": "close well above the 30-day lower rolling quantile",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "30-day lower-quantile displacement adds a standardized medium-horizon downside-clearance measure.",
    },
    "QTLD60": {
        "ranking_direction": "ASC",
        "interpretation": "close well above the 60-day lower rolling quantile",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "60-day lower-quantile displacement provides a canonical long-horizon downside-clearance anchor.",
    },
    "RANK5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day rolling close percentile",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Rolling percentile position is a standardized location measure distinct from moving-average or breakout-distance summaries.",
    },
    "RANK10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day rolling close percentile",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "10-day rolling percentile position captures short-horizon price location in a more canonical way than custom trend summaries.",
    },
    "RANK20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day rolling close percentile",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "20-day percentile location is a robust Alpha158 position measure rather than a max-distance heuristic.",
    },
    "RANK30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day rolling close percentile",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "30-day percentile location adds a standardized medium-horizon position metric absent from prior custom definitions.",
    },
    "RANK60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day rolling close percentile",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "60-day percentile location provides a canonical long-horizon path-position measure distinct from rolling highs alone.",
    },
    "RSV5": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 5-day stochastic close position within rolling high-low range",
        "nearest_canonical_signal": "close_location_value_20d_raw",
        "independent_budget_reason": "Rolling stochastic value captures position within a multi-day range rather than within only the current daily bar.",
    },
    "RSV10": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 10-day stochastic close position within rolling high-low range",
        "nearest_canonical_signal": "close_location_value_20d_raw",
        "independent_budget_reason": "10-day rolling stochastic location is a standardized short-horizon range-position atom not isolated previously.",
    },
    "RSV20": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 20-day stochastic close position within rolling high-low range",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "20-day stochastic value is a canonical trend-position measure rather than a simple distance-to-high ratio.",
    },
    "RSV30": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 30-day stochastic close position within rolling high-low range",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "30-day stochastic value adds a standardized medium-horizon range-position anchor.",
    },
    "RSV60": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 60-day stochastic close position within rolling high-low range",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "60-day stochastic value provides a canonical long-horizon range-position measure distinct from moving-average displacement.",
    },
    "IMAX5": {
        "ranking_direction": "DESC",
        "interpretation": "more recent 5-day rolling high occurrence",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "Rolling-high recency isolates timing of local highs rather than only current distance to the high.",
    },
    "IMAX10": {
        "ranking_direction": "DESC",
        "interpretation": "more recent 10-day rolling high occurrence",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "10-day high recency captures breakout freshness rather than level-only proximity.",
    },
    "IMAX20": {
        "ranking_direction": "DESC",
        "interpretation": "more recent 20-day rolling high occurrence",
        "nearest_canonical_signal": "breakout_proximity_20d_raw",
        "independent_budget_reason": "20-day high recency is a canonical timing measure absent from prior distance-based breakout signals.",
    },
    "IMAX30": {
        "ranking_direction": "DESC",
        "interpretation": "more recent 30-day rolling high occurrence",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "30-day high recency adds a standardized medium-horizon breakout-timing signal.",
    },
    "IMAX60": {
        "ranking_direction": "DESC",
        "interpretation": "more recent 60-day rolling high occurrence",
        "nearest_canonical_signal": "breakout_proximity_60d_raw",
        "independent_budget_reason": "60-day high recency provides a canonical long-horizon breakout freshness measure.",
    },
    "IMIN5": {
        "ranking_direction": "ASC",
        "interpretation": "older 5-day rolling low occurrence",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "Rolling-low recency captures weakness timing rather than only current distance above the low.",
    },
    "IMIN10": {
        "ranking_direction": "ASC",
        "interpretation": "older 10-day rolling low occurrence",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "10-day low recency standardizes downside-timing information beyond level-only support distance.",
    },
    "IMIN20": {
        "ranking_direction": "ASC",
        "interpretation": "older 20-day rolling low occurrence",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "20-day low recency is a canonical timing measure distinct from pure downside-distance ratios.",
    },
    "IMIN30": {
        "ranking_direction": "ASC",
        "interpretation": "older 30-day rolling low occurrence",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "30-day low recency adds a standardized medium-horizon support-timing measure.",
    },
    "IMIN60": {
        "ranking_direction": "ASC",
        "interpretation": "older 60-day rolling low occurrence",
        "nearest_canonical_signal": "breakdown_distance_20d_raw",
        "independent_budget_reason": "60-day low recency provides a canonical long-horizon downside-timing anchor.",
    },
    "IMXD5": {
        "ranking_direction": "DESC",
        "interpretation": "5-day rolling high occurs after rolling low",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "High-minus-low timing spread encodes directional path ordering rather than level-only trend strength.",
    },
    "IMXD10": {
        "ranking_direction": "DESC",
        "interpretation": "10-day rolling high occurs after rolling low",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "10-day high-minus-low timing spread captures short-horizon path ordering in canonical Alpha158 form.",
    },
    "IMXD20": {
        "ranking_direction": "DESC",
        "interpretation": "20-day rolling high occurs after rolling low",
        "nearest_canonical_signal": "path_efficiency_20d_raw",
        "independent_budget_reason": "20-day high-minus-low ordering isolates path directionality rather than merely close position within range.",
    },
    "IMXD30": {
        "ranking_direction": "DESC",
        "interpretation": "30-day rolling high occurs after rolling low",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "30-day high-minus-low timing spread adds a medium-horizon directional path-ordering atom.",
    },
    "IMXD60": {
        "ranking_direction": "DESC",
        "interpretation": "60-day rolling high occurs after rolling low",
        "nearest_canonical_signal": "path_efficiency_60d_raw",
        "independent_budget_reason": "60-day high-minus-low ordering provides a canonical long-horizon path-direction timing measure.",
    },
    "CORR5": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 5-day rolling correlation between close and log volume",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "Short-horizon close-volume correlation is a standardized Alpha158 price-volume co-movement atom rather than an amount-based project variant.",
    },
    "CORR10": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 10-day rolling correlation between close and log volume",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "10-day close-volume correlation adds a standardized short-medium horizon co-movement measure distinct from prior amount-based signals.",
    },
    "CORR20": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 20-day rolling correlation between close and log volume",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "20-day close-volume correlation is the canonical medium-horizon Alpha158 co-movement form rather than the project's earlier custom variants.",
    },
    "CORR30": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 30-day rolling correlation between close and log volume",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "30-day close-volume correlation adds a standardized medium-horizon price-volume linkage measure.",
    },
    "CORR60": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 60-day rolling correlation between close and log volume",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "60-day close-volume correlation provides a canonical long-horizon price-volume co-movement anchor.",
    },
    "CORD5": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 5-day rolling correlation between price change ratio and volume change ratio",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "Change-on-change correlation is a cleaner short-horizon flow-response atom than level correlation alone.",
    },
    "CORD10": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 10-day rolling correlation between price change ratio and volume change ratio",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "10-day price-volume change correlation adds a standardized dynamic co-movement measure distinct from level correlation.",
    },
    "CORD20": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 20-day rolling correlation between price change ratio and volume change ratio",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "20-day change-on-change correlation captures medium-horizon responsiveness rather than static co-location.",
    },
    "CORD30": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 30-day rolling correlation between price change ratio and volume change ratio",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "30-day price-volume change correlation adds a standardized medium-horizon dynamic linkage atom.",
    },
    "CORD60": {
        "ranking_direction": "DESC",
        "interpretation": "stronger 60-day rolling correlation between price change ratio and volume change ratio",
        "nearest_canonical_signal": "price_volume_corr_20d_raw",
        "independent_budget_reason": "60-day change-on-change correlation provides a canonical long-horizon dynamic price-volume coupling measure.",
    },
    "CNTP5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day share of up closes",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Up-day frequency isolates directional win-rate rather than trend level or slope magnitude.",
    },
    "CNTP10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day share of up closes",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "10-day up-day frequency is a standardized directional persistence atom absent from prior custom constructions.",
    },
    "CNTP20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day share of up closes",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "20-day up-day share is a canonical direction-frequency measure rather than a cumulative return proxy.",
    },
    "CNTP30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day share of up closes",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day up-day share adds a standardized medium-horizon trend-frequency definition.",
    },
    "CNTP60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day share of up closes",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day up-day share provides a canonical long-horizon directional persistence signal.",
    },
    "CNTN5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day share of down closes",
        "nearest_canonical_signal": "reversal_5d_raw",
        "independent_budget_reason": "Down-day frequency directly measures downside persistence rather than net return magnitude.",
    },
    "CNTN10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day share of down closes",
        "nearest_canonical_signal": "reversal_5d_raw",
        "independent_budget_reason": "10-day down-day share adds a standardized downside-frequency persistence measure.",
    },
    "CNTN20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day share of down closes",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "20-day down-day frequency captures downside persistence distinct from trend level metrics.",
    },
    "CNTN30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day share of down closes",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day down-day share adds a standardized medium-horizon downside-frequency signal.",
    },
    "CNTN60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day share of down closes",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day down-day share provides a canonical long-horizon downside persistence measure.",
    },
    "CNTD5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day net up-minus-down close share",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "Net up-minus-down share is a cleaner directional breadth atom than cumulative price change.",
    },
    "CNTD10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day net up-minus-down close share",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "10-day net directional share adds a standardized short-horizon breadth definition.",
    },
    "CNTD20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day net up-minus-down close share",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "20-day net directional share is a canonical frequency-breadth trend measure.",
    },
    "CNTD30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day net up-minus-down close share",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day net directional share adds a standardized medium-horizon breadth metric.",
    },
    "CNTD60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day net up-minus-down close share",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day net directional share provides a canonical long-horizon breadth persistence measure.",
    },
    "SUMP5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day share of positive price movement magnitude",
        "nearest_canonical_signal": "momentum_20_5_raw",
        "independent_budget_reason": "Positive-move contribution share captures asymmetric directional strength beyond net return alone.",
    },
    "SUMP10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day share of positive price movement magnitude",
        "nearest_canonical_signal": "momentum_60_5_raw",
        "independent_budget_reason": "10-day positive-move share adds a standardized directional strength decomposition.",
    },
    "SUMP20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day share of positive price movement magnitude",
        "nearest_canonical_signal": "momentum_120_20_raw",
        "independent_budget_reason": "20-day positive-move magnitude share is a canonical directional-strength atom rather than simple lagged return.",
    },
    "SUMP30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day share of positive price movement magnitude",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day positive-move share adds a standardized medium-horizon directional-strength decomposition.",
    },
    "SUMP60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day share of positive price movement magnitude",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day positive-move share provides a canonical long-horizon directional-strength measure.",
    },
    "SUMN5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day share of negative price movement magnitude",
        "nearest_canonical_signal": "reversal_5d_raw",
        "independent_budget_reason": "Negative-move contribution share isolates downside dominance more directly than net return alone.",
    },
    "SUMN10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day share of negative price movement magnitude",
        "nearest_canonical_signal": "reversal_5d_raw",
        "independent_budget_reason": "10-day downside-magnitude share adds a standardized short-horizon downside-strength decomposition.",
    },
    "SUMN20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day share of negative price movement magnitude",
        "nearest_canonical_signal": "trend_consistency_20d_raw",
        "independent_budget_reason": "20-day downside-magnitude share provides a canonical medium-horizon downside-strength decomposition rather than net return alone.",
    },
    "SUMN30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day share of negative price movement magnitude",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day downside-magnitude share adds a standardized medium-horizon downside-dominance measure.",
    },
    "SUMN60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day share of negative price movement magnitude",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day downside-magnitude share provides a canonical long-horizon downside-strength decomposition.",
    },
    "SUMD5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day positive-minus-negative price movement share",
        "nearest_canonical_signal": "momentum_20_5_raw",
        "independent_budget_reason": "Net signed movement share is a cleaner directional-strength decomposition than plain cumulative return.",
    },
    "SUMD10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day positive-minus-negative price movement share",
        "nearest_canonical_signal": "momentum_60_5_raw",
        "independent_budget_reason": "10-day net signed movement share adds a standardized short-horizon directional-strength atom.",
    },
    "SUMD20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day positive-minus-negative price movement share",
        "nearest_canonical_signal": "momentum_120_20_raw",
        "independent_budget_reason": "20-day net signed movement share is a canonical medium-horizon directional-strength decomposition.",
    },
    "SUMD30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day positive-minus-negative price movement share",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "30-day net signed movement share adds a standardized medium-horizon direction-balance measure.",
    },
    "SUMD60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day positive-minus-negative price movement share",
        "nearest_canonical_signal": "trend_consistency_60d_raw",
        "independent_budget_reason": "60-day net signed movement share provides a canonical long-horizon direction-balance measure.",
    },
    "VMA5": {
        "ranking_direction": "ASC",
        "interpretation": "current volume above its 5-day average",
        "nearest_canonical_signal": "liquidity_20d_raw",
        "independent_budget_reason": "Direct volume-to-average-volume ratio is a canonical turnover-pressure atom rather than a custom liquidity level proxy.",
    },
    "VMA10": {
        "ranking_direction": "ASC",
        "interpretation": "current volume above its 10-day average",
        "nearest_canonical_signal": "liquidity_20d_raw",
        "independent_budget_reason": "10-day volume-to-average ratio adds a standardized short-horizon activity pressure measure.",
    },
    "VMA20": {
        "ranking_direction": "ASC",
        "interpretation": "current volume above its 20-day average",
        "nearest_canonical_signal": "liquidity_60d_raw",
        "independent_budget_reason": "20-day relative volume is the canonical medium-horizon activity-pressure form rather than the project's earlier custom liquidity windows.",
    },
    "VMA30": {
        "ranking_direction": "ASC",
        "interpretation": "current volume above its 30-day average",
        "nearest_canonical_signal": "liquidity_60d_raw",
        "independent_budget_reason": "30-day relative volume adds a standardized medium-horizon trading-activity measure.",
    },
    "VMA60": {
        "ranking_direction": "ASC",
        "interpretation": "current volume above its 60-day average",
        "nearest_canonical_signal": "liquidity_60d_raw",
        "independent_budget_reason": "60-day relative volume provides a canonical long-horizon activity-pressure anchor.",
    },
    "VSTD5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day volume volatility relative to current volume",
        "nearest_canonical_signal": "turnover_stability_20d_raw",
        "independent_budget_reason": "Short-window standardized volume variability is a canonical stability atom rather than a custom turnover smoothness proxy.",
    },
    "VSTD10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day volume volatility relative to current volume",
        "nearest_canonical_signal": "turnover_stability_20d_raw",
        "independent_budget_reason": "10-day standardized volume variability adds a standardized short-horizon stability measure.",
    },
    "VSTD20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day volume volatility relative to current volume",
        "nearest_canonical_signal": "turnover_stability_20d_raw",
        "independent_budget_reason": "20-day standardized volume volatility is the canonical medium-horizon turnover-stability form.",
    },
    "VSTD30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day volume volatility relative to current volume",
        "nearest_canonical_signal": "turnover_stability_20d_raw",
        "independent_budget_reason": "30-day standardized volume variability adds a medium-horizon canonical turnover-stability measure.",
    },
    "VSTD60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day volume volatility relative to current volume",
        "nearest_canonical_signal": "turnover_stability_20d_raw",
        "independent_budget_reason": "60-day standardized volume variability provides a canonical long-horizon turnover-stability anchor.",
    },
    "WVMA5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day volatility of absolute return weighted by volume relative to its mean",
        "nearest_canonical_signal": "amount_volatility_20d_raw",
        "independent_budget_reason": "Weighted return-volume variability is a canonical flow-turbulence atom rather than raw amount volatility alone.",
    },
    "WVMA10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day volatility of absolute return weighted by volume relative to its mean",
        "nearest_canonical_signal": "amount_volatility_20d_raw",
        "independent_budget_reason": "10-day weighted flow-turbulence ratio adds a standardized short-horizon price-volume stress measure.",
    },
    "WVMA20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day volatility of absolute return weighted by volume relative to its mean",
        "nearest_canonical_signal": "amount_volatility_20d_raw",
        "independent_budget_reason": "20-day weighted flow-turbulence ratio is the canonical medium-horizon price-volume stress form.",
    },
    "WVMA30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day volatility of absolute return weighted by volume relative to its mean",
        "nearest_canonical_signal": "amount_volatility_20d_raw",
        "independent_budget_reason": "30-day weighted flow-turbulence ratio adds a standardized medium-horizon stress measure.",
    },
    "WVMA60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day volatility of absolute return weighted by volume relative to its mean",
        "nearest_canonical_signal": "amount_volatility_20d_raw",
        "independent_budget_reason": "60-day weighted flow-turbulence ratio provides a canonical long-horizon price-volume stress anchor.",
    },
    "VSUMP5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day share of positive volume change magnitude",
        "nearest_canonical_signal": "volume_momentum_5_20_raw",
        "independent_budget_reason": "Positive volume-change contribution share captures directional activity expansion beyond simple average volume growth.",
    },
    "VSUMP10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day share of positive volume change magnitude",
        "nearest_canonical_signal": "volume_momentum_5_20_raw",
        "independent_budget_reason": "10-day positive volume-change share adds a standardized short-horizon activity-expansion decomposition.",
    },
    "VSUMP20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day share of positive volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_20_60_raw",
        "independent_budget_reason": "20-day positive volume-change share is a canonical medium-horizon activity-expansion measure rather than a level-only liquidity trend.",
    },
    "VSUMP30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day share of positive volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "30-day positive volume-change share adds a standardized medium-horizon directional activity decomposition.",
    },
    "VSUMP60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day share of positive volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "60-day positive volume-change share provides a canonical long-horizon activity-expansion measure.",
    },
    "VSUMN5": {
        "ranking_direction": "ASC",
        "interpretation": "lower 5-day share of negative volume change magnitude",
        "nearest_canonical_signal": "turnover_mean_reversion_gap_5_20_raw",
        "independent_budget_reason": "Negative volume-change share isolates downside activity contraction more directly than average volume gaps.",
    },
    "VSUMN10": {
        "ranking_direction": "ASC",
        "interpretation": "lower 10-day share of negative volume change magnitude",
        "nearest_canonical_signal": "turnover_mean_reversion_gap_5_20_raw",
        "independent_budget_reason": "10-day negative volume-change share adds a standardized short-horizon contraction-strength decomposition.",
    },
    "VSUMN20": {
        "ranking_direction": "ASC",
        "interpretation": "lower 20-day share of negative volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_20_60_raw",
        "independent_budget_reason": "20-day negative volume-change share provides a canonical medium-horizon contraction-strength measure.",
    },
    "VSUMN30": {
        "ranking_direction": "ASC",
        "interpretation": "lower 30-day share of negative volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "30-day negative volume-change share adds a standardized medium-horizon activity-contraction measure.",
    },
    "VSUMN60": {
        "ranking_direction": "ASC",
        "interpretation": "lower 60-day share of negative volume change magnitude",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "60-day negative volume-change share provides a canonical long-horizon contraction-strength anchor.",
    },
    "VSUMD5": {
        "ranking_direction": "DESC",
        "interpretation": "higher 5-day positive-minus-negative volume change share",
        "nearest_canonical_signal": "volume_momentum_5_20_raw",
        "independent_budget_reason": "Net signed volume-change share is a cleaner directional activity-strength decomposition than raw volume growth.",
    },
    "VSUMD10": {
        "ranking_direction": "DESC",
        "interpretation": "higher 10-day positive-minus-negative volume change share",
        "nearest_canonical_signal": "volume_momentum_5_20_raw",
        "independent_budget_reason": "10-day net signed volume-change share adds a standardized short-horizon activity-balance atom.",
    },
    "VSUMD20": {
        "ranking_direction": "DESC",
        "interpretation": "higher 20-day positive-minus-negative volume change share",
        "nearest_canonical_signal": "liquidity_trend_20_60_raw",
        "independent_budget_reason": "20-day net signed volume-change share is a canonical medium-horizon activity-balance decomposition.",
    },
    "VSUMD30": {
        "ranking_direction": "DESC",
        "interpretation": "higher 30-day positive-minus-negative volume change share",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "30-day net signed volume-change share adds a standardized medium-horizon activity-balance measure.",
    },
    "VSUMD60": {
        "ranking_direction": "DESC",
        "interpretation": "higher 60-day positive-minus-negative volume change share",
        "nearest_canonical_signal": "liquidity_trend_60_120_raw",
        "independent_budget_reason": "60-day net signed volume-change share provides a canonical long-horizon activity-balance anchor.",
    },
}


SUPPORTED_SQL: dict[str, str] = {
    "KMID": "CASE WHEN adj_open > 1e-12 THEN (adj_close - adj_open) / adj_open ELSE NULL END",
    "KLEN": "CASE WHEN adj_open > 1e-12 THEN (adj_high - adj_low) / adj_open ELSE NULL END",
    "KMID2": "CASE WHEN adj_high - adj_low + 1e-12 > 0 THEN (adj_close - adj_open) / (adj_high - adj_low + 1e-12) ELSE NULL END",
    "KUP": "CASE WHEN adj_open > 1e-12 THEN (adj_high - GREATEST(adj_open, adj_close)) / adj_open ELSE NULL END",
    "KUP2": "CASE WHEN adj_high - adj_low + 1e-12 > 0 THEN (adj_high - GREATEST(adj_open, adj_close)) / (adj_high - adj_low + 1e-12) ELSE NULL END",
    "KLOW": "CASE WHEN adj_open > 1e-12 THEN (LEAST(adj_open, adj_close) - adj_low) / adj_open ELSE NULL END",
    "KLOW2": "CASE WHEN adj_high - adj_low + 1e-12 > 0 THEN (LEAST(adj_open, adj_close) - adj_low) / (adj_high - adj_low + 1e-12) ELSE NULL END",
    "KSFT": "CASE WHEN adj_open > 1e-12 THEN (2.0 * adj_close - adj_high - adj_low) / adj_open ELSE NULL END",
    "KSFT2": "CASE WHEN adj_high - adj_low + 1e-12 > 0 THEN (2.0 * adj_close - adj_high - adj_low) / (adj_high - adj_low + 1e-12) ELSE NULL END",
    "OPEN0": "CASE WHEN adj_close > 1e-12 THEN adj_open / adj_close ELSE NULL END",
    "HIGH0": "CASE WHEN adj_close > 1e-12 THEN adj_high / adj_close ELSE NULL END",
    "LOW0": "CASE WHEN adj_close > 1e-12 THEN adj_low / adj_close ELSE NULL END",
    "VWAP0": "CASE WHEN adj_close > 1e-12 THEN adj_vwap / adj_close ELSE NULL END",
    "ROC5": "CASE WHEN adj_close > 1e-12 THEN LAG(adj_close, 5) OVER w / adj_close ELSE NULL END",
    "ROC10": "CASE WHEN adj_close > 1e-12 THEN LAG(adj_close, 10) OVER w / adj_close ELSE NULL END",
    "ROC20": "CASE WHEN adj_close > 1e-12 THEN LAG(adj_close, 20) OVER w / adj_close ELSE NULL END",
    "ROC30": "CASE WHEN adj_close > 1e-12 THEN LAG(adj_close, 30) OVER w / adj_close ELSE NULL END",
    "ROC60": "CASE WHEN adj_close > 1e-12 THEN LAG(adj_close, 60) OVER w / adj_close ELSE NULL END",
    "MA5": "CASE WHEN adj_close > 1e-12 THEN AVG(adj_close) OVER w5 / adj_close ELSE NULL END",
    "MA10": "CASE WHEN adj_close > 1e-12 THEN AVG(adj_close) OVER w10 / adj_close ELSE NULL END",
    "MA20": "CASE WHEN adj_close > 1e-12 THEN AVG(adj_close) OVER w20 / adj_close ELSE NULL END",
    "MA30": "CASE WHEN adj_close > 1e-12 THEN AVG(adj_close) OVER w30 / adj_close ELSE NULL END",
    "MA60": "CASE WHEN adj_close > 1e-12 THEN AVG(adj_close) OVER w60 / adj_close ELSE NULL END",
    "STD5": "CASE WHEN adj_close > 1e-12 THEN STDDEV_SAMP(adj_close) OVER w5 / adj_close ELSE NULL END",
    "STD10": "CASE WHEN adj_close > 1e-12 THEN STDDEV_SAMP(adj_close) OVER w10 / adj_close ELSE NULL END",
    "STD20": "CASE WHEN adj_close > 1e-12 THEN STDDEV_SAMP(adj_close) OVER w20 / adj_close ELSE NULL END",
    "STD30": "CASE WHEN adj_close > 1e-12 THEN STDDEV_SAMP(adj_close) OVER w30 / adj_close ELSE NULL END",
    "STD60": "CASE WHEN adj_close > 1e-12 THEN STDDEV_SAMP(adj_close) OVER w60 / adj_close ELSE NULL END",
    "BETA5": "CASE WHEN adj_close > 1e-12 THEN REGR_SLOPE(adj_close, time_idx) OVER w5 / adj_close ELSE NULL END",
    "BETA10": "CASE WHEN adj_close > 1e-12 THEN REGR_SLOPE(adj_close, time_idx) OVER w10 / adj_close ELSE NULL END",
    "BETA20": "CASE WHEN adj_close > 1e-12 THEN REGR_SLOPE(adj_close, time_idx) OVER w20 / adj_close ELSE NULL END",
    "BETA30": "CASE WHEN adj_close > 1e-12 THEN REGR_SLOPE(adj_close, time_idx) OVER w30 / adj_close ELSE NULL END",
    "BETA60": "CASE WHEN adj_close > 1e-12 THEN REGR_SLOPE(adj_close, time_idx) OVER w60 / adj_close ELSE NULL END",
    "RSQR5": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w5, 0.0) > 2e-05 THEN REGR_R2(adj_close, time_idx) OVER w5 ELSE NULL END",
    "RSQR10": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w10, 0.0) > 2e-05 THEN REGR_R2(adj_close, time_idx) OVER w10 ELSE NULL END",
    "RSQR20": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w20, 0.0) > 2e-05 THEN REGR_R2(adj_close, time_idx) OVER w20 ELSE NULL END",
    "RSQR30": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w30, 0.0) > 2e-05 THEN REGR_R2(adj_close, time_idx) OVER w30 ELSE NULL END",
    "RSQR60": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w60, 0.0) > 2e-05 THEN REGR_R2(adj_close, time_idx) OVER w60 ELSE NULL END",
    "RESI5": "CASE WHEN adj_close > 1e-12 THEN (adj_close - (COALESCE(REGR_INTERCEPT(adj_close, time_idx) OVER w5, 0.0) + COALESCE(REGR_SLOPE(adj_close, time_idx) OVER w5, 0.0) * time_idx)) / adj_close ELSE NULL END",
    "RESI10": "CASE WHEN adj_close > 1e-12 THEN (adj_close - (COALESCE(REGR_INTERCEPT(adj_close, time_idx) OVER w10, 0.0) + COALESCE(REGR_SLOPE(adj_close, time_idx) OVER w10, 0.0) * time_idx)) / adj_close ELSE NULL END",
    "RESI20": "CASE WHEN adj_close > 1e-12 THEN (adj_close - (COALESCE(REGR_INTERCEPT(adj_close, time_idx) OVER w20, 0.0) + COALESCE(REGR_SLOPE(adj_close, time_idx) OVER w20, 0.0) * time_idx)) / adj_close ELSE NULL END",
    "RESI30": "CASE WHEN adj_close > 1e-12 THEN (adj_close - (COALESCE(REGR_INTERCEPT(adj_close, time_idx) OVER w30, 0.0) + COALESCE(REGR_SLOPE(adj_close, time_idx) OVER w30, 0.0) * time_idx)) / adj_close ELSE NULL END",
    "RESI60": "CASE WHEN adj_close > 1e-12 THEN (adj_close - (COALESCE(REGR_INTERCEPT(adj_close, time_idx) OVER w60, 0.0) + COALESCE(REGR_SLOPE(adj_close, time_idx) OVER w60, 0.0) * time_idx)) / adj_close ELSE NULL END",
    "MAX5": "CASE WHEN adj_close > 1e-12 THEN MAX(adj_high) OVER w5 / adj_close ELSE NULL END",
    "MAX10": "CASE WHEN adj_close > 1e-12 THEN MAX(adj_high) OVER w10 / adj_close ELSE NULL END",
    "MAX20": "CASE WHEN adj_close > 1e-12 THEN MAX(adj_high) OVER w20 / adj_close ELSE NULL END",
    "MAX30": "CASE WHEN adj_close > 1e-12 THEN MAX(adj_high) OVER w30 / adj_close ELSE NULL END",
    "MAX60": "CASE WHEN adj_close > 1e-12 THEN MAX(adj_high) OVER w60 / adj_close ELSE NULL END",
    "MIN5": "CASE WHEN adj_close > 1e-12 THEN MIN(adj_low) OVER w5 / adj_close ELSE NULL END",
    "MIN10": "CASE WHEN adj_close > 1e-12 THEN MIN(adj_low) OVER w10 / adj_close ELSE NULL END",
    "MIN20": "CASE WHEN adj_close > 1e-12 THEN MIN(adj_low) OVER w20 / adj_close ELSE NULL END",
    "MIN30": "CASE WHEN adj_close > 1e-12 THEN MIN(adj_low) OVER w30 / adj_close ELSE NULL END",
    "MIN60": "CASE WHEN adj_close > 1e-12 THEN MIN(adj_low) OVER w60 / adj_close ELSE NULL END",
    "QTLU5": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.8) OVER w5 / adj_close ELSE NULL END",
    "QTLU10": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.8) OVER w10 / adj_close ELSE NULL END",
    "QTLU20": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.8) OVER w20 / adj_close ELSE NULL END",
    "QTLU30": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.8) OVER w30 / adj_close ELSE NULL END",
    "QTLU60": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.8) OVER w60 / adj_close ELSE NULL END",
    "QTLD5": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.2) OVER w5 / adj_close ELSE NULL END",
    "QTLD10": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.2) OVER w10 / adj_close ELSE NULL END",
    "QTLD20": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.2) OVER w20 / adj_close ELSE NULL END",
    "QTLD30": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.2) OVER w30 / adj_close ELSE NULL END",
    "QTLD60": "CASE WHEN adj_close > 1e-12 THEN QUANTILE_CONT(adj_close, 0.2) OVER w60 / adj_close ELSE NULL END",
    "RANK5": "LIST_COUNT(LIST_FILTER(LIST(adj_close) OVER w5, x -> x <= adj_close)) * 1.0 / NULLIF(LIST_COUNT(LIST(adj_close) OVER w5), 0)",
    "RANK10": "LIST_COUNT(LIST_FILTER(LIST(adj_close) OVER w10, x -> x <= adj_close)) * 1.0 / NULLIF(LIST_COUNT(LIST(adj_close) OVER w10), 0)",
    "RANK20": "LIST_COUNT(LIST_FILTER(LIST(adj_close) OVER w20, x -> x <= adj_close)) * 1.0 / NULLIF(LIST_COUNT(LIST(adj_close) OVER w20), 0)",
    "RANK30": "LIST_COUNT(LIST_FILTER(LIST(adj_close) OVER w30, x -> x <= adj_close)) * 1.0 / NULLIF(LIST_COUNT(LIST(adj_close) OVER w30), 0)",
    "RANK60": "LIST_COUNT(LIST_FILTER(LIST(adj_close) OVER w60, x -> x <= adj_close)) * 1.0 / NULLIF(LIST_COUNT(LIST(adj_close) OVER w60), 0)",
    "RSV5": "CASE WHEN MAX(adj_high) OVER w5 - MIN(adj_low) OVER w5 + 1e-12 > 0 THEN (adj_close - MIN(adj_low) OVER w5) / (MAX(adj_high) OVER w5 - MIN(adj_low) OVER w5 + 1e-12) ELSE NULL END",
    "RSV10": "CASE WHEN MAX(adj_high) OVER w10 - MIN(adj_low) OVER w10 + 1e-12 > 0 THEN (adj_close - MIN(adj_low) OVER w10) / (MAX(adj_high) OVER w10 - MIN(adj_low) OVER w10 + 1e-12) ELSE NULL END",
    "RSV20": "CASE WHEN MAX(adj_high) OVER w20 - MIN(adj_low) OVER w20 + 1e-12 > 0 THEN (adj_close - MIN(adj_low) OVER w20) / (MAX(adj_high) OVER w20 - MIN(adj_low) OVER w20 + 1e-12) ELSE NULL END",
    "RSV30": "CASE WHEN MAX(adj_high) OVER w30 - MIN(adj_low) OVER w30 + 1e-12 > 0 THEN (adj_close - MIN(adj_low) OVER w30) / (MAX(adj_high) OVER w30 - MIN(adj_low) OVER w30 + 1e-12) ELSE NULL END",
    "RSV60": "CASE WHEN MAX(adj_high) OVER w60 - MIN(adj_low) OVER w60 + 1e-12 > 0 THEN (adj_close - MIN(adj_low) OVER w60) / (MAX(adj_high) OVER w60 - MIN(adj_low) OVER w60 + 1e-12) ELSE NULL END",
    "IMAX5": "(ARG_MAX(time_idx, adj_high) OVER w5 - GREATEST(time_idx - 5, 0)) * 1.0 / 5.0",
    "IMAX10": "(ARG_MAX(time_idx, adj_high) OVER w10 - GREATEST(time_idx - 10, 0)) * 1.0 / 10.0",
    "IMAX20": "(ARG_MAX(time_idx, adj_high) OVER w20 - GREATEST(time_idx - 20, 0)) * 1.0 / 20.0",
    "IMAX30": "(ARG_MAX(time_idx, adj_high) OVER w30 - GREATEST(time_idx - 30, 0)) * 1.0 / 30.0",
    "IMAX60": "(ARG_MAX(time_idx, adj_high) OVER w60 - GREATEST(time_idx - 60, 0)) * 1.0 / 60.0",
    "IMIN5": "(ARG_MIN(time_idx, adj_low) OVER w5 - GREATEST(time_idx - 5, 0)) * 1.0 / 5.0",
    "IMIN10": "(ARG_MIN(time_idx, adj_low) OVER w10 - GREATEST(time_idx - 10, 0)) * 1.0 / 10.0",
    "IMIN20": "(ARG_MIN(time_idx, adj_low) OVER w20 - GREATEST(time_idx - 20, 0)) * 1.0 / 20.0",
    "IMIN30": "(ARG_MIN(time_idx, adj_low) OVER w30 - GREATEST(time_idx - 30, 0)) * 1.0 / 30.0",
    "IMIN60": "(ARG_MIN(time_idx, adj_low) OVER w60 - GREATEST(time_idx - 60, 0)) * 1.0 / 60.0",
    "IMXD5": "((ARG_MAX(time_idx, adj_high) OVER w5 - GREATEST(time_idx - 5, 0)) - (ARG_MIN(time_idx, adj_low) OVER w5 - GREATEST(time_idx - 5, 0))) * 1.0 / 5.0",
    "IMXD10": "((ARG_MAX(time_idx, adj_high) OVER w10 - GREATEST(time_idx - 10, 0)) - (ARG_MIN(time_idx, adj_low) OVER w10 - GREATEST(time_idx - 10, 0))) * 1.0 / 10.0",
    "IMXD20": "((ARG_MAX(time_idx, adj_high) OVER w20 - GREATEST(time_idx - 20, 0)) - (ARG_MIN(time_idx, adj_low) OVER w20 - GREATEST(time_idx - 20, 0))) * 1.0 / 20.0",
    "IMXD30": "((ARG_MAX(time_idx, adj_high) OVER w30 - GREATEST(time_idx - 30, 0)) - (ARG_MIN(time_idx, adj_low) OVER w30 - GREATEST(time_idx - 30, 0))) * 1.0 / 30.0",
    "IMXD60": "((ARG_MAX(time_idx, adj_high) OVER w60 - GREATEST(time_idx - 60, 0)) - (ARG_MIN(time_idx, adj_low) OVER w60 - GREATEST(time_idx - 60, 0))) * 1.0 / 60.0",
    "CORR5": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w5, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume) OVER w5, 0.0) > 2e-05 THEN CORR(adj_close, log_volume) OVER w5 ELSE NULL END",
    "CORR10": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w10, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume) OVER w10, 0.0) > 2e-05 THEN CORR(adj_close, log_volume) OVER w10 ELSE NULL END",
    "CORR20": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w20, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume) OVER w20, 0.0) > 2e-05 THEN CORR(adj_close, log_volume) OVER w20 ELSE NULL END",
    "CORR30": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w30, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume) OVER w30, 0.0) > 2e-05 THEN CORR(adj_close, log_volume) OVER w30 ELSE NULL END",
    "CORR60": "CASE WHEN COALESCE(STDDEV_SAMP(adj_close) OVER w60, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume) OVER w60, 0.0) > 2e-05 THEN CORR(adj_close, log_volume) OVER w60 ELSE NULL END",
    "CORD5": "CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w5, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w5, 0.0) > 2e-05 THEN CORR(close_rel1, log_volume_rel1) OVER w5 ELSE NULL END",
    "CORD10": "CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w10, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w10, 0.0) > 2e-05 THEN CORR(close_rel1, log_volume_rel1) OVER w10 ELSE NULL END",
    "CORD20": "CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w20, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w20, 0.0) > 2e-05 THEN CORR(close_rel1, log_volume_rel1) OVER w20 ELSE NULL END",
    "CORD30": "CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w30, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w30, 0.0) > 2e-05 THEN CORR(close_rel1, log_volume_rel1) OVER w30 ELSE NULL END",
    "CORD60": "CASE WHEN COALESCE(STDDEV_SAMP(close_rel1) OVER w60, 0.0) > 2e-05 AND COALESCE(STDDEV_SAMP(log_volume_rel1) OVER w60, 0.0) > 2e-05 THEN CORR(close_rel1, log_volume_rel1) OVER w60 ELSE NULL END",
    "CNTP5": "AVG(up_day_flag) OVER w5",
    "CNTP10": "AVG(up_day_flag) OVER w10",
    "CNTP20": "AVG(up_day_flag) OVER w20",
    "CNTP30": "AVG(up_day_flag) OVER w30",
    "CNTP60": "AVG(up_day_flag) OVER w60",
    "CNTN5": "AVG(down_day_flag) OVER w5",
    "CNTN10": "AVG(down_day_flag) OVER w10",
    "CNTN20": "AVG(down_day_flag) OVER w20",
    "CNTN30": "AVG(down_day_flag) OVER w30",
    "CNTN60": "AVG(down_day_flag) OVER w60",
    "CNTD5": "AVG(up_day_flag) OVER w5 - AVG(down_day_flag) OVER w5",
    "CNTD10": "AVG(up_day_flag) OVER w10 - AVG(down_day_flag) OVER w10",
    "CNTD20": "AVG(up_day_flag) OVER w20 - AVG(down_day_flag) OVER w20",
    "CNTD30": "AVG(up_day_flag) OVER w30 - AVG(down_day_flag) OVER w30",
    "CNTD60": "AVG(up_day_flag) OVER w60 - AVG(down_day_flag) OVER w60",
    "SUMP5": "SUM(pos_close_delta) OVER w5 / (SUM(abs_close_delta) OVER w5 + 1e-12)",
    "SUMP10": "SUM(pos_close_delta) OVER w10 / (SUM(abs_close_delta) OVER w10 + 1e-12)",
    "SUMP20": "SUM(pos_close_delta) OVER w20 / (SUM(abs_close_delta) OVER w20 + 1e-12)",
    "SUMP30": "SUM(pos_close_delta) OVER w30 / (SUM(abs_close_delta) OVER w30 + 1e-12)",
    "SUMP60": "SUM(pos_close_delta) OVER w60 / (SUM(abs_close_delta) OVER w60 + 1e-12)",
    "SUMN5": "SUM(neg_close_delta) OVER w5 / (SUM(abs_close_delta) OVER w5 + 1e-12)",
    "SUMN10": "SUM(neg_close_delta) OVER w10 / (SUM(abs_close_delta) OVER w10 + 1e-12)",
    "SUMN20": "SUM(neg_close_delta) OVER w20 / (SUM(abs_close_delta) OVER w20 + 1e-12)",
    "SUMN30": "SUM(neg_close_delta) OVER w30 / (SUM(abs_close_delta) OVER w30 + 1e-12)",
    "SUMN60": "SUM(neg_close_delta) OVER w60 / (SUM(abs_close_delta) OVER w60 + 1e-12)",
    "SUMD5": "(SUM(pos_close_delta) OVER w5 - SUM(neg_close_delta) OVER w5) / (SUM(abs_close_delta) OVER w5 + 1e-12)",
    "SUMD10": "(SUM(pos_close_delta) OVER w10 - SUM(neg_close_delta) OVER w10) / (SUM(abs_close_delta) OVER w10 + 1e-12)",
    "SUMD20": "(SUM(pos_close_delta) OVER w20 - SUM(neg_close_delta) OVER w20) / (SUM(abs_close_delta) OVER w20 + 1e-12)",
    "SUMD30": "(SUM(pos_close_delta) OVER w30 - SUM(neg_close_delta) OVER w30) / (SUM(abs_close_delta) OVER w30 + 1e-12)",
    "SUMD60": "(SUM(pos_close_delta) OVER w60 - SUM(neg_close_delta) OVER w60) / (SUM(abs_close_delta) OVER w60 + 1e-12)",
    "VMA5": "AVG(vol) OVER w5 / (vol + 1e-12)",
    "VMA10": "AVG(vol) OVER w10 / (vol + 1e-12)",
    "VMA20": "AVG(vol) OVER w20 / (vol + 1e-12)",
    "VMA30": "AVG(vol) OVER w30 / (vol + 1e-12)",
    "VMA60": "AVG(vol) OVER w60 / (vol + 1e-12)",
    "VSTD5": "STDDEV_SAMP(vol) OVER w5 / (vol + 1e-12)",
    "VSTD10": "STDDEV_SAMP(vol) OVER w10 / (vol + 1e-12)",
    "VSTD20": "STDDEV_SAMP(vol) OVER w20 / (vol + 1e-12)",
    "VSTD30": "STDDEV_SAMP(vol) OVER w30 / (vol + 1e-12)",
    "VSTD60": "STDDEV_SAMP(vol) OVER w60 / (vol + 1e-12)",
    "WVMA5": "STDDEV_SAMP(abs_return_times_volume) OVER w5 / (AVG(abs_return_times_volume) OVER w5 + 1e-12)",
    "WVMA10": "STDDEV_SAMP(abs_return_times_volume) OVER w10 / (AVG(abs_return_times_volume) OVER w10 + 1e-12)",
    "WVMA20": "STDDEV_SAMP(abs_return_times_volume) OVER w20 / (AVG(abs_return_times_volume) OVER w20 + 1e-12)",
    "WVMA30": "STDDEV_SAMP(abs_return_times_volume) OVER w30 / (AVG(abs_return_times_volume) OVER w30 + 1e-12)",
    "WVMA60": "STDDEV_SAMP(abs_return_times_volume) OVER w60 / (AVG(abs_return_times_volume) OVER w60 + 1e-12)",
    "VSUMP5": "SUM(pos_vol_delta) OVER w5 / (SUM(abs_vol_delta) OVER w5 + 1e-12)",
    "VSUMP10": "SUM(pos_vol_delta) OVER w10 / (SUM(abs_vol_delta) OVER w10 + 1e-12)",
    "VSUMP20": "SUM(pos_vol_delta) OVER w20 / (SUM(abs_vol_delta) OVER w20 + 1e-12)",
    "VSUMP30": "SUM(pos_vol_delta) OVER w30 / (SUM(abs_vol_delta) OVER w30 + 1e-12)",
    "VSUMP60": "SUM(pos_vol_delta) OVER w60 / (SUM(abs_vol_delta) OVER w60 + 1e-12)",
    "VSUMN5": "SUM(neg_vol_delta) OVER w5 / (SUM(abs_vol_delta) OVER w5 + 1e-12)",
    "VSUMN10": "SUM(neg_vol_delta) OVER w10 / (SUM(abs_vol_delta) OVER w10 + 1e-12)",
    "VSUMN20": "SUM(neg_vol_delta) OVER w20 / (SUM(abs_vol_delta) OVER w20 + 1e-12)",
    "VSUMN30": "SUM(neg_vol_delta) OVER w30 / (SUM(abs_vol_delta) OVER w30 + 1e-12)",
    "VSUMN60": "SUM(neg_vol_delta) OVER w60 / (SUM(abs_vol_delta) OVER w60 + 1e-12)",
    "VSUMD5": "(SUM(pos_vol_delta) OVER w5 - SUM(neg_vol_delta) OVER w5) / (SUM(abs_vol_delta) OVER w5 + 1e-12)",
    "VSUMD10": "(SUM(pos_vol_delta) OVER w10 - SUM(neg_vol_delta) OVER w10) / (SUM(abs_vol_delta) OVER w10 + 1e-12)",
    "VSUMD20": "(SUM(pos_vol_delta) OVER w20 - SUM(neg_vol_delta) OVER w20) / (SUM(abs_vol_delta) OVER w20 + 1e-12)",
    "VSUMD30": "(SUM(pos_vol_delta) OVER w30 - SUM(neg_vol_delta) OVER w30) / (SUM(abs_vol_delta) OVER w30 + 1e-12)",
    "VSUMD60": "(SUM(pos_vol_delta) OVER w60 - SUM(neg_vol_delta) OVER w60) / (SUM(abs_vol_delta) OVER w60 + 1e-12)",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def build_feature_batch(*, start_slot: int, count: int) -> list[dict]:
    manifest = load_manifest()
    selected = [
        row for row in manifest["feature_catalog"]
        if start_slot <= int(row["canonical_slot"]) < start_slot + count
    ]
    if len(selected) != count:
        raise ValueError(f"Expected {count} features from slot {start_slot}, got {len(selected)}.")
    missing_meta = [row["qlib_feature_name"] for row in selected if row["qlib_feature_name"] not in FEATURE_META]
    missing_sql = [row["qlib_feature_name"] for row in selected if row["qlib_feature_name"] not in SUPPORTED_SQL]
    if missing_meta or missing_sql:
        raise ValueError(
            f"Unsupported canonical feature subset. missing_meta={missing_meta}, missing_sql={missing_sql}"
        )
    enriched: list[dict] = []
    for row in selected:
        meta = FEATURE_META[row["qlib_feature_name"]]
        enriched.append({**row, **meta})
    return enriched


def build_candidate_specs(feature_batch: list[dict]) -> list[CandidateSpec]:
    return [
        CandidateSpec(
            row["canonical_candidate_scheme_id"],
            row["canonical_project_field"],
            row["ranking_direction"],
            row["interpretation"],
        )
        for row in feature_batch
    ]


def build_signal_pool(feature_batch: list[dict]) -> list[dict]:
    signal_pool: list[dict] = []
    for row in feature_batch:
        feature_name = row["qlib_feature_name"]
        signal_pool.append(
            {
                "candidate_scheme_id": row["canonical_candidate_scheme_id"],
                "field": row["canonical_project_field"],
                "ranking_direction": row["ranking_direction"],
                "interpretation": row["interpretation"],
                "source_provenance": {
                    "source_category": "alpha158_style",
                    "source_id": f"QlibAlpha158Exact:{feature_name}",
                    "source_title": SOURCE_TITLE,
                    "source_locator": SOURCE_LOCATOR,
                    "mechanism_mapping": f"Exact Alpha158 canonical expression: {row['qlib_expression']}",
                    "independent_implementation_note": INDEPENDENT_NOTE,
                },
                "dedup_note": {
                    "nearest_canonical_signal": row["nearest_canonical_signal"],
                    "relationship_type": "new_mechanism",
                    "independent_budget_reason": row["independent_budget_reason"],
                    "override_reason": "",
                },
            }
        )
    return signal_pool


def build_feature_views(
    con: duckdb.DuckDBPyConnection,
    sample_panel: Path,
    source_db_path: Path,
    snapshot_id: str,
    feature_batch: list[dict],
) -> None:
    feature_names = [row["qlib_feature_name"] for row in feature_batch]
    field_names = [row["canonical_project_field"] for row in feature_batch]
    unsupported = [name for name in feature_names if name not in SUPPORTED_SQL]
    if unsupported:
        raise ValueError(f"Unsupported canonical features: {unsupported}")

    con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW project_sample_panel AS
        SELECT * FROM read_parquet({sql_path(sample_panel)})
        """
    )

    feature_select_lines = [
        f"            {SUPPORTED_SQL[name]} AS {field}"
        for name, field in zip(feature_names, field_names)
    ]
    feature_select_sql = ",\n".join(feature_select_lines)
    frame_fields = [f"            b.{field}" for field in field_names]
    if "liquidity_20d_raw" not in field_names:
        frame_fields.append("            b.liquidity_20d_raw")
    frame_select_sql = ",\n".join(frame_fields)

    con.execute(
        f"""
        CREATE OR REPLACE VIEW bar_features AS
        WITH bars AS (
            SELECT
                ts_code AS instrument,
                trade_date AS signal_date,
                adj_open,
                adj_high,
                adj_low,
                adj_close,
                close,
                amount,
                vol,
                COALESCE(
                    adj_factor,
                    CASE
                        WHEN close > 1e-12 THEN adj_close / close
                        ELSE NULL
                    END
                ) AS adj_factor_used,
                ROW_NUMBER() OVER (
                    PARTITION BY ts_code
                    ORDER BY trade_date
                ) AS time_idx
            FROM warehouse_db.serving.vw_bars_daily
            WHERE snapshot_id = {sql_quote(snapshot_id)}
        ),
        enriched AS (
            SELECT
                instrument,
                signal_date,
                adj_open,
                adj_high,
                adj_low,
                adj_close,
                amount,
                vol,
                time_idx,
                LN(GREATEST(vol, 0.0) + 1.0) AS log_volume,
                LAG(adj_close, 1) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                ) AS prev_adj_close,
                LAG(vol, 1) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                ) AS prev_vol,
                CASE
                    WHEN vol > 1e-12 AND amount > 0 AND adj_factor_used > 0
                    THEN (amount * 10.0 / vol) * adj_factor_used
                    ELSE NULL
                END AS adj_vwap,
                CASE
                    WHEN LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ) > 1e-12
                    THEN adj_close / LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    )
                    ELSE NULL
                END AS close_rel1,
                CASE
                    WHEN LAG(vol, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ) > 1e-12
                    THEN LN(vol / LAG(vol, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ) + 1.0)
                    ELSE NULL
                END AS log_volume_rel1,
                CASE
                    WHEN adj_close > LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    )
                    THEN 1.0
                    ELSE 0.0
                END AS up_day_flag,
                CASE
                    WHEN adj_close < LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    )
                    THEN 1.0
                    ELSE 0.0
                END AS down_day_flag,
                GREATEST(
                    adj_close - LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ),
                    0.0
                ) AS pos_close_delta,
                GREATEST(
                    LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ) - adj_close,
                    0.0
                ) AS neg_close_delta,
                ABS(
                    adj_close - LAG(adj_close, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    )
                ) AS abs_close_delta,
                ABS(
                    COALESCE(
                        CASE
                            WHEN LAG(adj_close, 1) OVER (
                                PARTITION BY instrument
                                ORDER BY signal_date
                            ) > 1e-12
                            THEN adj_close / LAG(adj_close, 1) OVER (
                                PARTITION BY instrument
                                ORDER BY signal_date
                            ) - 1.0
                            ELSE NULL
                        END,
                        0.0
                    )
                ) * vol AS abs_return_times_volume,
                GREATEST(
                    vol - LAG(vol, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ),
                    0.0
                ) AS pos_vol_delta,
                GREATEST(
                    LAG(vol, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    ) - vol,
                    0.0
                ) AS neg_vol_delta,
                ABS(
                    vol - LAG(vol, 1) OVER (
                        PARTITION BY instrument
                        ORDER BY signal_date
                    )
                ) AS abs_vol_delta
            FROM bars
        )
        SELECT
            instrument,
            signal_date,
            AVG(LN(GREATEST(amount, 0.0) + 1.0)) OVER w20 AS liquidity_20d_raw,
{feature_select_sql}
        FROM enriched
        WINDOW
            w AS (
                PARTITION BY instrument
                ORDER BY signal_date
            ),
            w5 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
            w10 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
            ),
            w20 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ),
            w30 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ),
            w60 AS (
                PARTITION BY instrument
                ORDER BY signal_date
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            )
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW feature_frame AS
        SELECT
            p.snapshot_id,
            p.instrument,
            p.signal_date,
            p.ranking_eligible_D0,
{frame_select_sql}
        FROM project_sample_panel p
        LEFT JOIN bar_features b
          ON p.instrument = b.instrument
         AND p.signal_date = b.signal_date
        """
    )
