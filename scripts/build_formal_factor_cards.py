#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build formal factor card documents for the 25 positive signals.

Each card follows 框架 14.4 specification:
- Factor name, definition formula, expected direction
- ≤3 sentence economic explanation
- PIT effective rule
- Missing / non-finite value handling
- Expected failure mode
- Diagnostic summary (IC, coverage, monotonicity, top-slice differentiation)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
FACTOR_CARD_INVENTORY = REGISTRY_DIR / "factor_card_registry_20260428.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".inprogress")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def fmt(v: float | None, d: int = 6) -> str:
    if v is None:
        return "null"
    return f"{v:.{d}f}"


def fmt_pct(v: float | None) -> str:
    if v is None:
        return "null"
    return f"{v*100:.2f}%"


# ── Factor Card Definitions ──────────────────────────────────────────

FACTOR_CARDS: dict[str, dict[str, Any]] = {
    "price_volume_single_signal_price_volume_beta_20d_v1": {
        "family": "price_volume -> beta",
        "field": "price_volume_beta_20d_raw",
        "ranking_direction": "DESC (higher beta ranks higher)",
        "formula": "COVAR_SAMP(pct_ret, dlog_amount) OVER 20d / VAR_SAMP(dlog_amount) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))",
        "economic_explanation": [
            "Measures the sensitivity of daily return to daily log-amount change over a 20-day window — a price-volume slope beta.",
            "Stocks where returns are more sensitive to volume changes tend to have stronger subsequent short-term performance, consistent with informed trading amplification.",
            "Higher values indicate the stock's return moves more per unit of volume innovation, which may signal the presence of informed or momentum-driven capital."
        ],
        "pit_rule": "D0 及之前 20 个交易日可见的 pct_chg 和 amount；不含 future 信息",
        "missing_handling": "若 VAR_SAMP(dlog_amount) <= 1e-12 或任一输入缺失，则该信号值为 NULL",
        "expected_failure_mode": [
            "在低成交或一字板时期，dlog_amount 接近 0，beta 不可定义",
            "极端 outlier 期间 beta 可能被少数日子的量价关系主导"
        ],
        "memo": "正向信号中 IC 最高 (0.0172)。属于量价关系类。"
    },
    "price_volume_single_signal_volume_price_synchronicity_20d_v1": {
        "family": "price_volume -> correlation",
        "field": "volume_price_synchronicity_20d_raw",
        "ranking_direction": "DESC (higher synchronicity ranks higher)",
        "formula": "CORR(pct_ret, log_amount - prev_log_amount) OVER 20d, where prev_log_amount = LAG(LN(amount))",
        "economic_explanation": [
            "Captures the correlation between daily return and the log-amount innovation (deviation from prior day's log amount) over 20 days.",
            "High positive correlation means returns and volume-surprise move together — a signature of informed-flow-driven price moves.",
            "Stocks with stronger return-volume co-movement tend to have higher subsequent returns, consistent with information-flow theory."
        ],
        "pit_rule": "D0 及之前 20 个交易日可见的 pct_chg 和 amount",
        "missing_handling": "若 CORR 的输入序列 < 3 个有效配对观测，则为 NULL",
        "expected_failure_mode": [
            "在低波动环境中，pct_ret 和 amount 变化都极小，相关性不稳定",
            "分红/除权日前后若调整因子不一致可能导致量价关系失真"
        ],
        "memo": "IC=0.0167，与 price_volume_corr 几乎等价(同一机制)"
    },
    "price_volume_single_signal_price_volume_corr_20d_v1": {
        "family": "price_volume -> correlation",
        "field": "price_volume_corr_20d_raw",
        "ranking_direction": "DESC",
        "formula": "CORR(pct_ret, dlog_amount) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))",
        "economic_explanation": [
            "Pearson correlation between daily return and log-amount first-difference over 20 days.",
            "Lower-level alternative to volume_price_synchronicity; empirically nearly equivalent.",
            "Positive correlation suggests volume-confirmed price moves that may persist."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 pct_chg 和 amount",
        "missing_handling": "少于 3 个有效配对时为 NULL",
        "expected_failure_mode": "极低成交环境不稳定；与 synchronicity 存在共线性",
        "memo": "IC=0.0167。与 volume_price_synchronicity 几乎重复，选其一即可。"
    },
    "price_volume_single_signal_intraday_trend_bias_20d_v1": {
        "family": "intraday -> bias",
        "field": "intraday_trend_bias_20d_raw",
        "ranking_direction": "DESC (stronger intraday uptrend ranks higher)",
        "formula": "AVG(close/open - 1.0) OVER 20d",
        "economic_explanation": [
            "Measures the average intraday return (close vs open) over the past 20 days — the typical direction of intraday price drift.",
            "A positive bias means the stock tends to drift higher during the day, which may reflect persistent order-flow imbalance or informed accumulation.",
            "Stocks with stronger intraday uptrend bias show subsequent outperformance, consistent with intraday momentum spilling over to the next holding period."
        ],
        "pit_rule": "D0 可见的开盘价和收盘价",
        "missing_handling": "若开/收盘价任一缺失，该日不计入；全部缺失则信号为 NULL",
        "expected_failure_mode": [
            "跳空开盘日 intraday return 可能被开盘跳空扭曲",
            "在趋势反转时点，positive bias 可能变为负向预测"
        ],
        "memo": "IC=0.0147。简洁且解释清晰的日内信号。"
    },
    "price_volume_single_signal_liquidity_trend_20_60_v1": {
        "family": "liquidity -> trend",
        "field": "liquidity_trend_20_60_raw",
        "ranking_direction": "DESC (improving liquidity ranks higher)",
        "formula": "AVG(LN(amount+1)) OVER 20d - AVG(LN(amount+1)) OVER 60d",
        "economic_explanation": [
            "Measures the recent 20-day average log-amount minus the longer 60-day average — a liquidity momentum/gradient proxy.",
            "A positive value indicates liquidity (trading activity) is improving relative to its recent history, which tends to attract more trading interest and reduce execution costs.",
            "Stocks with improving liquidity profiles have better subsequent returns, possibly reflecting increasing investor attention or improving information environment."
        ],
        "pit_rule": "D0 及之前 60 个交易日的 amount；以千元为单位(同 tushare daily.amount)",
        "missing_handling": "若 60 日 lookback 不足(如次新股)，则信号为 NULL",
        "expected_failure_mode": [
            "次新股或长期停牌后复牌初期，lookback 不足导致信号不可用",
            "流动性趋势可能在市场整体缩量时大面积转负"
        ],
        "memo": "IC=0.0122。核心 baseline 变量，流动性趋势类。"
    },
    "price_volume_single_signal_alpha158_low0_v1": {
        "family": "alpha158 -> named",
        "field": "alpha158_low0_raw",
        "ranking_direction": "DESC",
        "formula": "qlib Alpha158 定义: (low - vwap) / (close + vwap) 的 20 日变体或其等价公式",
        "economic_explanation": [
            "alpha158 因子体系中以最低价(low)为核心的定价偏离类因子。",
            "衡量日内低价相对于成交量加权均价(vwap)的偏离程度，反映日内吸收卖压的能力。",
            "较低的偏离(价格在 vwap 附近获得支撑)预示后续正向收益。"
        ],
        "pit_rule": "D0 及之前 20 个交易日的 low, close, amount, vwap",
        "missing_handling": "任一核心字段缺失则该值为 NULL",
        "expected_failure_mode": "极端行情下 low 价格可能失真；需注意 qlib 实现与该项目的口径差异",
        "memo": "IC=0.0118。alpha158 体系中入围 strongest positive 的命名信号。"
    },
    "price_volume_single_signal_price_volume_rank_corr_20d_v1": {
        "family": "price_volume -> correlation",
        "field": "price_volume_rank_corr_20d_raw",
        "ranking_direction": "DESC (stronger rank correlation ranks higher)",
        "formula": "CORR(SIGN(pct_ret), SIGN(dlog_amount)) OVER 20d, where dlog_amount = LN(amount) - LAG(LN(amount))",
        "economic_explanation": [
            "Rank-based (sign-level) correlation between return direction and volume-surprise direction over 20 days.",
            "Reduces the impact of magnitude outliers compared to Pearson-based price-volume correlations.",
            "Positive sign-correlation means return and volume-surprise tend to move in the same direction — a robust indicator of directional flow."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 pct_chg 和 amount",
        "missing_handling": "少于 5 个有效日则为 NULL",
        "expected_failure_mode": "在大量一字板交易日，所有 SIGN 为 0，相关系数不可定义",
        "memo": "IC=0.0114。量价类信号的稳健版本。"
    },
    "price_volume_single_signal_alpha158_full_036_v1": {
        "family": "alpha158 -> full",
        "field": "alpha158 全集中编号 036 的信号",
        "ranking_direction": "DESC",
        "formula": "alpha158 全集定义，见 /Users/wy/MiscProject/multi_factor/artifacts/research_registry/alpha158_qlib_full_definition_manifest_20260428.json",
        "economic_explanation": [
            "alpha158 全因子集中表现最好的之一，属于 price-volume 量价派生类。",
            "具体经济含义需映射回 qlib Alpha158 特征定义。"
        ],
        "pit_rule": "D0 及之前可见的行情数据",
        "missing_handling": "alpha158 标准缺失处理规则",
        "expected_failure_mode": "alpha158 全集中部分因子在 A 股特定时期可能过拟合",
        "memo": "IC=0.0112。alpha158_full 系列中 Top 正向信号。"
    },
    "price_volume_single_signal_alpha158_full_003_v1": {
        "family": "alpha158 -> full",
        "field": "alpha158 全集 003",
        "ranking_direction": "DESC",
        "formula": "见 alpha158 qlib 全集清单",
        "economic_explanation": [
            "alpha158 全集中表现较强的因子之一。",
            "具体含义需查 alpha158 特征字典。"
        ],
        "pit_rule": "D0 及之前",
        "missing_handling": "标准 alpha158 规则",
        "expected_failure_mode": "需单独验证独立性，避免与其它信号高度冗余",
        "memo": "IC=0.0112。与 036 属于同批次。"
    },
    "price_volume_single_signal_alpha158_full_027_v1": {
        "family": "alpha158 -> full",
        "field": "alpha158 全集 027",
        "ranking_direction": "DESC",
        "formula": "见 alpha158 qlib 全集清单",
        "economic_explanation": [
            "alpha158 全集中表现较强的因子之一。",
            "具体含义需查 alpha158 特征字典。"
        ],
        "pit_rule": "D0 及之前",
        "missing_handling": "标准 alpha158 规则",
        "expected_failure_mode": "需单独验证独立性",
        "memo": "IC=0.0109。alpha158 系列。"
    },
    "price_volume_single_signal_upside_range_share_20d_v1": {
        "family": "intraday -> structure",
        "field": "upside_range_share_20d_raw",
        "ranking_direction": "DESC (higher upside share ranks higher)",
        "formula": "SUM(upside_range_daily) OVER 20d / SUM((high-low)/close) OVER 20d, where upside_range_daily = CASE WHEN pct_ret > 0 AND adj_close > 0 THEN (adj_high - adj_low) / adj_close ELSE 0 END",
        "economic_explanation": [
            "Measures the fraction of total 20-day range that occurred on up-days — the upside participation share.",
            "A higher share indicates that the stock's price range expansion happens disproportionately on up-days, suggesting bullish price discovery.",
            "Stocks with higher upside range share tend to have higher forward returns, consistent with the idea that up-day volatility is information-rich."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 adj_open/adj_high/adj_low/adj_close",
        "missing_handling": "若 20 日总 range 为 0，则为 NULL",
        "expected_failure_mode": [
            "在横盘震荡期，upside_range_share 可能失去区分度",
            "除权日附近 adj_price 可能导致 range 计算短暂失真"
        ],
        "memo": "IC=0.0103。日内结构类。"
    },
    "price_volume_single_signal_momentum_60_5_v1": {
        "family": "momentum -> medium_term",
        "field": "momentum_60_5_raw",
        "ranking_direction": "DESC (stronger momentum ranks higher)",
        "formula": "adj_close(D-5) / adj_close(D-60) - 1.0",
        "economic_explanation": [
            "Classic medium-term momentum: cumulative base-adjusted return from 60 trading days ago to 5 trading days ago (skipping the most recent week to avoid short-term reversal contamination).",
            "The 5-day skip separates momentum from the short-term reversal effect.",
            "Stocks with stronger 60-5 day momentum tend to continue outperforming over the next 5-day holding period."
        ],
        "pit_rule": "D0 可见的 adj_close；D-60 和 D-5 的复权价格",
        "missing_handling": "若 D-5 或 D-60 的 adj_close 缺失，则为 NULL",
        "expected_failure_mode": [
            "在市场剧烈反转时期(如 2015 年股灾)，momentum 可能大幅回撤",
            "次新股 lookback 不足导致信号不可用"
        ],
        "memo": "IC=0.0098。标准中期动量因子。"
    },
    "price_volume_single_signal_alpha158_full_004_v1": {
        "family": "alpha158 -> full",
        "field": "alpha158 全集 004",
        "ranking_direction": "DESC",
        "formula": "见 alpha158 qlib 全集清单",
        "economic_explanation": [
            "alpha158 全集中表现较强的因子之一。",
            "具体含义需查 alpha158 特征字典。"
        ],
        "pit_rule": "D0 及之前",
        "missing_handling": "标准 alpha158 规则",
        "expected_failure_mode": "需验证与其它 alpha158 信号的冗余程度",
        "memo": "IC=0.0097。alpha158 系列。"
    },
    "price_volume_single_signal_up_amount_persistence_20d_v1": {
        "family": "volume -> persistence",
        "field": "up_amount_persistence_20d_raw",
        "ranking_direction": "DESC (more persistent up-volume ranks higher)",
        "formula": "AVG(CASE WHEN pct_ret > 0 AND amount > AVG(amount) OVER 20d THEN 1.0 ELSE 0.0 END) OVER 20d",
        "economic_explanation": [
            "Measures the frequency of up-days that are accompanied by above-average trading volume — up-volume persistence.",
            "Consistent up-volume suggests that buying pressure is not only present but sustained with conviction (high participation).",
            "Stocks where up-days reliably coincide with above-average volume tend to have better subsequent performance."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 pct_chg 和 amount",
        "missing_handling": "若金额数据大面积缺失，则为 NULL",
        "expected_failure_mode": [
            "在低成交环境，amount > 20d 均值的条件可能过于宽松",
            "在持续放量下跌中可能产生反向信号(放量下跌也被计入)"
        ],
        "memo": "IC=0.0094。量价确认类信号。"
    },
    "price_volume_single_signal_liquidity_trend_60_120_v1": {
        "family": "liquidity -> trend",
        "field": "liquidity_trend_60_120_raw",
        "ranking_direction": "DESC (improving liquidity ranks higher)",
        "formula": "AVG(LN(amount+1)) OVER 60d - AVG(LN(amount+1)) OVER 120d",
        "economic_explanation": [
            "Longer-horizon version of liquidity trend, comparing 60-day to 120-day average log-amount.",
            "Captures persistent shifts in liquidity regime rather than short-term fluctuations.",
            "A positive value indicates a structural improvement in trading activity."
        ],
        "pit_rule": "D0 及之前 120 个交易日的 amount",
        "missing_handling": "若 120 日 lookback 不足则为 NULL",
        "expected_failure_mode": "更长的 lookback 意味着对近期变化反应更慢，可能在流动性拐点处滞后",
        "memo": "IC=0.0083。流动性趋势的长期版本。"
    },
    "price_volume_single_signal_breakout_volume_confirmation_20d_v1": {
        "family": "breakout -> failure",
        "field": "breakout_volume_confirmation_20d_raw",
        "ranking_direction": "DESC",
        "formula": "breakout_proximity_20d_raw * amount_shock_5_20_raw, 其中 breakout_proximity = adj_close / MAX(adj_close) OVER 20d_prev, amount_shock = AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d",
        "economic_explanation": [
            "Combines price proximity to recent high (breakout proximity) with a short-term volume surge (amount shock).",
            "A stock near its 20-day high that simultaneously experiences a volume surge is showing breakout confirmation — the price move is backed by volume.",
            "Breakouts confirmed by volume shocks tend to be more genuine and have better forward returns."
        ],
        "pit_rule": "D0 及之前的 adj_close 和 amount",
        "missing_handling": "若 breakout_proximity 或 amount_shock 任一 NULL，则乘积为 NULL",
        "expected_failure_mode": [
            "在持续上涨末期可能产生假突破信号(volume-confirmed false breakout)",
            "次新股缺乏 20 日 lookback 不可用"
        ],
        "memo": "IC=0.0073。突破确认类信号。"
    },
    "price_volume_single_signal_volume_momentum_5_20_v1": {
        "family": "turnover -> level",
        "field": "volume_momentum_5_20_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d",
        "economic_explanation": [
            "Short-term volume momentum: the 5-day average log-amount relative to the 20-day average.",
            "A positive value means volume has accelerated in the past week relative to the past month.",
            "Volume acceleration often precedes increased volatility and directional price moves."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 amount",
        "missing_handling": "lookback 不足则为 NULL",
        "expected_failure_mode": "在量能均值回归期可能产生反向信号",
        "memo": "IC=0.0072。与 amount_shock_5_20 几乎等价。"
    },
    "price_volume_single_signal_amount_shock_5_20_v1": {
        "family": "liquidity -> shock",
        "field": "amount_shock_5_20_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(LN(amount)) OVER 5d - AVG(LN(amount)) OVER 20d",
        "economic_explanation": [
            "Identical formula to volume_momentum_5_20_raw — a 5/20-day log-amount ratio measuring short-term volume surge.",
            "Positive value = recent volume is above normal (a 'shock' relative to recent history).",
            "Volume shocks often precede increased price movement."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 amount",
        "missing_handling": "lookback 不足则为 NULL",
        "expected_failure_mode": "与 volume_momentum_5_20 完全等价，选其一即可",
        "memo": "IC=0.0072。与 volume_momentum_5_20 等价。"
    },
    "price_volume_single_signal_alpha158_full_019_v1": {
        "family": "alpha158 -> full",
        "field": "alpha158 全集 019",
        "ranking_direction": "DESC",
        "formula": "见 alpha158 qlib 全集清单",
        "economic_explanation": [
            "alpha158 全集中表现较强的因子之一。",
            "具体含义需查 alpha158 特征字典。"
        ],
        "pit_rule": "D0 及之前",
        "missing_handling": "标准 alpha158 规则",
        "expected_failure_mode": "需验证独立性",
        "memo": "IC=0.0064。alpha158 系列。Top10-Bottom10 差值较大(0.0109)"
    },
    "price_volume_single_signal_turnover_acceleration_5_20_v1": {
        "family": "turnover -> level",
        "field": "turnover_acceleration_5_20_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(LN(turnover_rate+1)) OVER 5d - AVG(LN(turnover_rate+1)) OVER 20d",
        "economic_explanation": [
            "Turnover rate acceleration: the 5-day average log-turnover relative to the 20-day average.",
            "Instead of raw amount, uses turnover_rate which normalizes for free-float shares — a cleaner measure of trading intensity per unit of outstanding equity.",
            "Rising turnover rate suggests increasing speculative interest or distribution activity."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 turnover_rate",
        "missing_handling": "lookback 不足则为 NULL",
        "expected_failure_mode": "换手率在机构大额交易时可能失真(大宗交易不计入换手率)",
        "memo": "IC=0.0063。金额的替代指标。"
    },
    "price_volume_single_signal_lower_shadow_support_20d_v1": {
        "family": "kline -> shadow",
        "field": "lower_shadow_support_20d_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(CASE WHEN (high-low) > 1e-12 AND pct_ret < 0 THEN (close - low) / (high - low) ELSE NULL END) OVER 20d",
        "economic_explanation": [
            "On down-days, measures where the close sits within the daily range: a higher value means the close is near the high despite a negative return — indicating buying support during the session.",
            "This 'lower shadow support' reflects the ability of buyers to lift prices off the intraday low.",
            "Stocks that show consistent buying support on down-days tend to have better forward returns."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 adj_high/adj_low/adj_close 和 pct_chg",
        "missing_handling": "若非下跌日或无 range 数据则该日不计入；全部缺失则为 NULL",
        "expected_failure_mode": [
            "在连续涨停/跌停日(range 极窄)可能不可定义",
            "仅以下跌日为条件，样本量可能不足"
        ],
        "memo": "IC=0.0062。K 线形态类。"
    },
    "price_volume_single_signal_intraday_reversal_asymmetry_20d_v1": {
        "family": "intraday -> bias",
        "field": "intraday_reversal_asymmetry_20d_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(down_recovery_part) OVER 20d - AVG(up_fade_part) OVER 20d",
        "economic_explanation": [
            "Measures the asymmetry between how much a stock recovers from intraday dips vs how much it fades from intraday highs.",
            "A positive value means the stock tends to recover from intraday weakness more than it gives back intraday gains — a bullish intraday resilience pattern.",
            "This intraday reversal asymmetry captures the balance of buying vs selling pressure within the trading day."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 1 分钟或日频 OHLC",
        "missing_handling": "若 intraday high/low 数据不可得，则为 NULL",
        "expected_failure_mode": "在趋势非常强劲的单边市，日内反转可能不频繁，导致信号趋近于 0",
        "memo": "IC=0.0055。K 线日内结构类。"
    },
    "price_volume_single_signal_high_open_hold_ratio_20d_v1": {
        "family": "intraday -> structure",
        "field": "high_open_hold_ratio_20d_raw",
        "ranking_direction": "DESC",
        "formula": "AVG(hold_quality_part) OVER 20d",
        "economic_explanation": [
            "Measures whether stocks tend to open high and sustain those gains (rather than fade) — a proxy for 'high open hold' quality.",
            "A high ratio suggests the opening price is a fair reflection of informed demand, not just an overnight gap that fades.",
            "Stocks that hold their open levels intraday tend to have better short-term forward returns."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 adj_open, adj_high, adj_low, adj_close",
        "missing_handling": "若日内 range 为 0 则不计入该日",
        "expected_failure_mode": "在开盘跳空巨大的事件日(财报/政策)可能失真",
        "memo": "IC=0.0050。开盘质量类信号。"
    },
    "price_volume_single_signal_trend_consistency_20d_v1": {
        "family": "trend -> consistency",
        "field": "trend_consistency_20d_raw",
        "ranking_direction": "DESC (more consistent up-days ranks higher)",
        "formula": "AVG(CASE WHEN pct_ret > 0 THEN 1.0 ELSE 0.0 END) OVER 20d",
        "economic_explanation": [
            "The simplest trend measure: the fraction of up-days over the past 20 trading days.",
            "A value above 0.5 means more days were positive than negative — a consistent short-term uptrend without requiring the magnitude to be large.",
            "Directional consistency is a robust trend indicator that is less sensitive to outliers than cumulative return."
        ],
        "pit_rule": "D0 及之前 20 个交易日的 pct_chg",
        "missing_handling": "若交易日不足 20 日，则基于实际可用天数计算",
        "expected_failure_mode": [
            "在低波动窄幅震荡期，>0.5 的胜率可能是随机波动而非真实趋势",
            "在市场快速反转时可能提供延迟信号"
        ],
        "memo": "IC=0.0033。最简洁的趋势信号。"
    },
    "price_volume_single_signal_downside_range_convexity_20d_v1": {
        "family": "downside -> risk",
        "field": "downside_range_convexity_20d_raw",
        "ranking_direction": "ASC (lower convexity ranks higher)",
        "formula": "AVG(POWER(downside_range_pressure_daily, 2)) OVER 20d / AVG(downside_range_pressure_daily) OVER 20d (convexity measure of downside tail shape)",
        "economic_explanation": [
            "Measures the convexity/nonlinearity of downside range pressure — a tail-shape proxy for downside risk.",
            "Lower convexity means downside range is more linear and predictable, less prone to tail events.",
            "Stocks with less convex downside tails (more 'normal' downside behavior) tend to have better forward returns, as extreme tail risk is penalized."
        ],
        "pit_rule": "D0 及之前 20 个交易日",
        "missing_handling": "若 AVG(downside_range_pressure) <= 1e-12 则为 NULL",
        "expected_failure_mode": [
            "在长期横盘期间，range convexity 接近 0，信号失去区分度",
            "凸度指标对极端事件敏感，可能受少数交易日主导"
        ],
        "memo": "IC=0.0021。下行尾部风险类。"
    },
}


def build_enhanced_cards(inventory_data: dict) -> list[dict]:
    """Merge formal card definitions with diagnostic data."""
    cards = []
    for candidate in inventory_data["factor_cards"]:
        cid = candidate["candidate_scheme_id"]
        formal = FACTOR_CARDS.get(cid)
        if formal is None:
            continue

        card = {
            "candidate_scheme_id": cid,
            "family": formal["family"],
            "field_name": formal["field"],
            "ranking_direction": formal["ranking_direction"],
            "formula": formal["formula"],
            "economic_explanation": formal["economic_explanation"],
            "pit_rule": formal["pit_rule"],
            "missing_handling": formal["missing_handling"],
            "expected_failure_mode": formal["expected_failure_mode"],
            "diagnostic_summary": {
                "full_sample_corr_ic": candidate["ic"]["full_sample_corr_ic"],
                "avg_daily_ic": candidate["ic"]["avg_daily_ic"],
                "positive_daily_ic_share": candidate["ic"]["positive_daily_ic_share"],
                "coverage_scored_with_label": candidate["coverage"]["scored_with_label_rows"],
                "null_score_share": candidate["coverage"]["null_score_share"],
                "decile_monotonic_ok": candidate["decile_monotonic_ok"],
                "top10_avg_label": candidate["top_slice"]["avg_label_top10"],
                "top10_minus_rank11_20": candidate["top_slice"]["top10_minus_rank11_20"],
                "top10_minus_bottom10": candidate["top_slice"]["top10_minus_bottom10"],
            },
        }
        if "memo" in formal:
            card["memo"] = formal["memo"]
        cards.append(card)
    return cards


def generate_markdown(cards: list[dict]) -> str:
    lines = [
        "# Formal Factor Cards — 25 Positive Signals",
        "",
        f"Generated: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Each card follows 框架 14.4 specification: definition, economic explanation (≤3 sentences),",
        "PIT rule, missing-value handling, expected failure modes, and diagnostic summary.",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"Total positive signals with formal cards: **{len(cards)}**",
        "",
        "| Rank | Signal | Family | IC | Top10-Bottom10 | Monotonic |",
        "|-----|--------|--------|----:|---------------:|:---------:|",
    ]

    sorted_cards = sorted(cards, key=lambda c: -(c["diagnostic_summary"]["full_sample_corr_ic"] or 0))
    for rank, card in enumerate(sorted_cards, 1):
        ic = card["diagnostic_summary"]["full_sample_corr_ic"]
        spread = card["diagnostic_summary"]["top10_minus_bottom10"]
        mono = "✓" if card["diagnostic_summary"]["decile_monotonic_ok"] else "✗"
        lines.append(
            f"| {rank} | `{card['candidate_scheme_id']}` | {card['family']} | {fmt(ic, 4)} | {fmt(spread, 4)} | {mono} |"
        )

    lines.extend(["", "---", ""])

    # Second pass: full detail per card
    lines.append("# Detailed Factor Cards")
    lines.append("")

    for card in sorted_cards:
        cid = card["candidate_scheme_id"]
        d = card["diagnostic_summary"]
        lines.extend([
            f"## {cid}",
            "",
            f"**Family:** {card['family']}",
            f"**Field:** `{card['field_name']}`",
            f"**Ranking direction:** {card['ranking_direction']}",
            "",
            "### Formula",
            "",
            f"```\n{card['formula']}\n```",
            "",
            "### Economic Explanation",
            "",
        ])
        for sentence in card["economic_explanation"]:
            lines.append(f"- {sentence}")
        lines.extend(["", "### PIT Rule", "", card["pit_rule"], ""])
        lines.extend(["### Missing / Non-Finite Handling", "", card["missing_handling"], ""])

        failure_modes = card["expected_failure_mode"]
        if isinstance(failure_modes, list):
            lines.append("### Expected Failure Modes")
            lines.append("")
            for fm in failure_modes:
                lines.append(f"- {fm}")
            lines.append("")
        else:
            lines.extend(["### Expected Failure Modes", "", failure_modes, ""])

        lines.extend([
            "### Diagnostic Summary",
            "",
            f"- Full-sample correlation IC: **{fmt(d['full_sample_corr_ic'])}**",
            f"- Average daily IC: **{fmt(d['avg_daily_ic'])}**",
            f"- Positive daily IC share: **{fmt_pct(d['positive_daily_ic_share'])}**",
            f"- Scored with label: **{d['coverage_scored_with_label']}**",
            f"- Null score share: **{fmt_pct(d['null_score_share'])}**",
            f"- Decile monotonic: **{'Yes' if d['decile_monotonic_ok'] else 'No'}**",
            f"- Top10 average label: **{fmt(d['top10_avg_label'])}**",
            f"- Top10 minus 11-20: **{fmt(d['top10_minus_rank11_20'])}**",
            f"- Top10 minus Bottom10: **{fmt(d['top10_minus_bottom10'])}**",
            "",
        ])
        if card.get("memo"):
            lines.extend([f"> {card['memo']}", ""])
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    inventory = load_json(FACTOR_CARD_INVENTORY)
    cards = build_enhanced_cards(inventory)
    as_of_date = datetime.now().astimezone().strftime("%Y%m%d")

    json_output = REGISTRY_DIR / f"formal_factor_cards_{as_of_date}.json"
    md_output = REGISTRY_DIR / f"formal_factor_cards_{as_of_date}.md"

    write_json(json_output, {
        "as_of_date": as_of_date,
        "total_cards": len(cards),
        "cards": cards,
    })
    md = generate_markdown(cards)
    md_output.write_text(md, encoding="utf-8")

    print(f"Formal factor cards written: {json_output}")
    print(f"Report: {md_output}")
    print(f"Total cards: {len(cards)}")

    # Family breakdown
    from collections import Counter
    families = Counter(c["family"] for c in cards)
    print("\n=== Family Breakdown ===")
    for fam, cnt in sorted(families.items()):
        print(f"  {fam}: {cnt}")


if __name__ == "__main__":
    main()
