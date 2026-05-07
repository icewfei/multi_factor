#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Drawdown-triggered cash buffer: post-process backtest_daily.csv.

Rule: when trailing 60-day max drawdown exceeds threshold, scale new-position
weights by --cash-scaling. Since ~1/5 of positions refresh daily, the effective
invested weight decays toward scaling * baseline over ~5 days of sustained drawdown.

Simulates by deriving a daily effective-weight multiplier and adjusting returns.
"""

from __future__ import annotations

import argparse, json, math, os
from datetime import datetime
from pathlib import Path
import duckdb

ROOT = Path("/Users/wy/MiscProject/multi_factor")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fixed-test-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--threshold", type=float, default=-0.15)
    p.add_argument("--scaling", type=float, default=0.50)
    p.add_argument("--lookback", type=int, default=60)
    p.add_argument("--cohorts-per-day", type=float, default=0.20,
                   help="Fraction of portfolio refreshed daily (1/holding_days).")
    return p.parse_args()


def sql_quote(v): return "'" + str(v).replace("'", "''") + "'"


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    bt_csv = Path(args.fixed_test_dir) / "backtest_daily.csv"

    con = duckdb.connect()
    con.execute(f"CREATE VIEW bt AS SELECT * FROM read_csv_auto('{bt_csv}', HEADER=TRUE)")

    # 1. Trailing 60d peak equity and drawdown
    con.execute(f"""
    CREATE VIEW dd AS
    SELECT *,
        MAX(total_equity) OVER (ORDER BY trade_date ROWS BETWEEN {args.lookback - 1} PRECEDING AND CURRENT ROW) AS trailing_peak
    FROM bt
    """)
    con.execute(f"""
    CREATE VIEW dd2 AS
    SELECT *,
        total_equity / NULLIF(trailing_peak, 0.0) - 1.0 AS trailing_dd
    FROM dd
    """)

    # 2. Buffer state: 0 or 1. Decays with cohort refresh rate.
    #    buffer_active_t = (1 - cohort_refresh_rate) * buffer_active_{t-1} + cohort_refresh_rate * (trailing_dd <= threshold)
    #    effective_weight = 1.0 - buffer_active * (1 - scaling)
    #    We compute this in a rolling manner using a recursive-like window.
    #    Since DuckDB doesn't do recursive CTEs easily for this, we approximate:
    #    effective_weight decays exponentially toward target over ~5 days.

    # Simplified: compute a smoothed buffer_active using a 5-day EMA
    con.execute(f"""
    CREATE VIEW buffer_signal AS
    SELECT *,
        CASE WHEN trailing_dd <= {args.threshold} THEN 1.0 ELSE 0.0 END AS buffer_raw
    FROM dd2
    """)

    # Exponential smoothing: 5-day half-life → decay = 0.5^(1/5) ≈ 0.87 per day
    # EMA[t] = decay * EMA[t-1] + (1-decay) * raw[t]
    # Approximate with a 10-day rolling average (simple, directionally correct)
    decay = 0.5 ** (1.0 / 5.0)
    con.execute(f"""
    CREATE VIEW buffer_smooth AS
    SELECT *,
        AVG(buffer_raw) OVER (
            ORDER BY trade_date
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS buffer_active
    FROM buffer_signal
    """)

    con.execute(f"""
    CREATE VIEW adjusted AS
    SELECT *,
        1.0 - buffer_active * (1.0 - {args.scaling}) AS weight_multiplier,
        portfolio_daily_return * (1.0 - buffer_active * (1.0 - {args.scaling})) AS adj_portfolio_return,
        cash_weight + (1.0 - cash_weight) * buffer_active * (1.0 - {args.scaling}) AS adj_cash_weight,
        (1.0 - cash_weight) * (1.0 - buffer_active * (1.0 - {args.scaling})) AS adj_invested_weight
    FROM buffer_smooth
    """)

    # 3. Rebuild equity path
    con.execute("""
    CREATE VIEW adj_equity AS
    SELECT *,
        EXP(SUM(LN(GREATEST(1.0 + adj_portfolio_return, 1e-12))) OVER (
            ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )) AS adj_total_equity,
        EXP(SUM(LN(GREATEST(1.0 + COALESCE(benchmark_return_daily, 0.0), 1e-12))) OVER (
            ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )) AS benchmark_equity
    FROM adjusted
    """)

    # 4. Metrics
    m = con.execute("""
    WITH peaks AS (
        SELECT *,
            MAX(adj_total_equity) OVER (ORDER BY trade_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS peak
        FROM adj_equity
    ),
    last_eq AS (
        SELECT adj_total_equity AS final_eq FROM adj_equity ORDER BY trade_date DESC LIMIT 1
    )
    SELECT
        (SELECT COUNT(*) FROM peaks) AS n,
        (SELECT final_eq FROM last_eq) AS final_eq,
        AVG(adj_portfolio_return) AS avg_ret,
        STDDEV_SAMP(adj_portfolio_return) AS vol,
        MIN(adj_total_equity / NULLIF(peak, 0.0) - 1.0) AS max_dd,
        AVG(adj_invested_weight) AS avg_inv,
        AVG(buffer_active) AS avg_buffer
    FROM peaks
    """).fetchone()

    n = int(m[0] or 0); final_eq = float(m[1] or 1.0)
    total_ret = final_eq - 1.0
    ann_ret = math.pow(final_eq, 252.0 / n) - 1.0 if n > 0 and final_eq > 0 else 0
    ann_vol = float(m[3] or 0) * math.sqrt(252.0)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    max_dd_adj = float(m[4] or 0)
    avg_inv = float(m[5] or 0)
    avg_buffer = float(m[6] or 0)

    rel = con.execute("""
    SELECT
        COUNT(*) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS ne,
        EXP(SUM(LN(GREATEST((1.0+adj_portfolio_return)/NULLIF(1.0+COALESCE(benchmark_return_daily,0.0),0.0),1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL)) AS rel_nav
    FROM adj_equity
    """).fetchone()
    ne = int(rel[0] or 0); rel_nav = float(rel[1] or 1.0)
    ann_rel = math.pow(rel_nav, 252.0 / ne) - 1.0 if ne > 0 and rel_nav > 0 else 0

    # 2020 monthly
    mo2020 = con.execute("""
    SELECT SUBSTR(CAST(trade_date AS VARCHAR),1,7) AS mo,
        EXP(SUM(LN(GREATEST(1.0+adj_portfolio_return,1e-12))))-1.0 AS s,
        EXP(SUM(LN(GREATEST(1.0+COALESCE(benchmark_return_daily,0.0),1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL))-1.0 AS b,
        AVG(buffer_active) AS buf
    FROM adj_equity WHERE CAST(trade_date AS VARCHAR) >= '20200101' AND CAST(trade_date AS VARCHAR) <= '20201231'
    GROUP BY 1 ORDER BY 1
    """).fetchall()

    yr2020 = con.execute("""
    SELECT EXP(SUM(LN(GREATEST(1.0+adj_portfolio_return,1e-12))))-1.0,
           EXP(SUM(LN(GREATEST(1.0+COALESCE(benchmark_return_daily,0.0),1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL))-1.0
    FROM adj_equity WHERE CAST(trade_date AS VARCHAR) >= '20200101' AND CAST(trade_date AS VARCHAR) <= '20201231'
    """).fetchone()

    # Validation period
    val = con.execute("""
    SELECT EXP(SUM(LN(GREATEST(1.0+adj_portfolio_return,1e-12))))-1.0,
           EXP(SUM(LN(GREATEST(1.0+COALESCE(benchmark_return_daily,0.0),1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL))-1.0
    FROM adj_equity WHERE CAST(trade_date AS VARCHAR) >= '20190101' AND CAST(trade_date AS VARCHAR) <= '20211231'
    """).fetchone()

    con.close()

    # Baseline
    orig = json.loads((Path(args.fixed_test_dir) / "metrics.json").read_text())

    # Report
    lines = [
        f"# Drawdown Buffer: Threshold={args.threshold*100:.0f}% Scaling={args.scaling}",
        f"",
        f"Avg buffer active: `{avg_buffer*100:.1f}%` of days",
        f"Avg invested weight: `{avg_inv*100:.1f}%` (baseline: `{orig['avg_invested_weight']*100:.1f}%`)",
        f"",
        f"## Full Period",
        f"| Metric | Baseline | DD-Buffered | Delta |",
        f"|--------|---------:|------------:|------:|",
        f"| Total Return | {orig['total_return']:.1f}x | {total_ret:.1f}x | {total_ret - orig['total_return']:+.1f}x |",
        f"| Ann Return | {orig['annualized_return']*100:.1f}% | {ann_ret*100:.1f}% | {(ann_ret - orig['annualized_return'])*100:+.1f}pp |",
        f"| Ann Rel Return | {orig['annual_relative_return']*100:.1f}% | {ann_rel*100:.1f}% | {(ann_rel - orig['annual_relative_return'])*100:+.1f}pp |",
        f"| Sharpe | {orig['sharpe_ratio']:.2f} | {sharpe:.2f} | {sharpe - orig['sharpe_ratio']:+.2f} |",
        f"| Max Drawdown | {orig['max_drawdown']*100:.1f}% | {max_dd_adj*100:.1f}% | {(max_dd_adj - orig['max_drawdown'])*100:+.1f}pp |",
        f"",
        f"## Validation Period (2019-2021)",
    ]
    if val:
        vs, vb = float(val[0] or 0), float(val[1] or 0)
        vr = (1+vs)/(1+vb)-1
        nval = ne  # approx
        avr = math.pow(1+vr, 252.0/nval)-1 if nval > 0 and vr > -1 else 0
        lines.append(f"Strategy: `{vs*100:.1f}%` | Benchmark: `{vb*100:.1f}%` | Relative: `{vr*100:.1f}%` | Ann Rel: `{avr*100:.1f}%`")

    lines.extend([
        f"",
        f"## 2020",
    ])
    if yr2020:
        ys, yb = float(yr2020[0] or 0), float(yr2020[1] or 0)
        yr = (1+ys)/(1+yb)-1
        lines.append(f"Strategy: `{ys*100:.1f}%` | Benchmark: `{yb*100:.1f}%` | Relative: `{yr*100:.1f}%`")

    lines.extend([
        f"",
        f"## 2020 Monthly",
        f"| Month | Strategy | Benchmark | Relative | Buffer% |",
        f"|-------|--------:|----------:|---------:|--------:|",
    ])
    for mo, s, b, buf in mo2020:
        ss, bb = float(s or 0), float(b or 0)
        rr = (1+ss)/(1+bb)-1 if bb != -1 else 0
        lines.append(f"| {mo} | {ss*100:.1f}% | {bb*100:.1f}% | {rr*100:.1f}% | {float(buf or 0)*100:.0f}% |")

    lines.extend(["", f"Generated: {datetime.now().astimezone().isoformat()}"])

    (Path(args.output_dir) / "dd_buffer_report.md").write_text("\n".join(lines))
    json.dump({
        "threshold": args.threshold, "scaling": args.scaling,
        "avg_buffer_active": avg_buffer,
        "adj_total_return": total_ret, "adj_ann_return": ann_ret,
        "adj_ann_rel_return": ann_rel, "adj_sharpe": sharpe, "adj_max_dd": max_dd_adj,
        "baseline_total_return": orig['total_return'],
        "baseline_ann_return": orig['annualized_return'],
        "baseline_ann_rel_return": orig['annual_relative_return'],
        "baseline_sharpe": orig['sharpe_ratio'],
        "baseline_max_dd": orig['max_drawdown'],
    }, open(Path(args.output_dir) / "dd_buffer_metrics.json", "w"), indent=2)

    print(f"Done. Report: {args.output_dir}/dd_buffer_report.md")
    print(f"Ann Rel: {orig['annual_relative_return']*100:.1f}% → {ann_rel*100:.1f}% ({(ann_rel - orig['annual_relative_return'])*100:+.1f}pp)")
    print(f"Max DD: {orig['max_drawdown']*100:.1f}% → {max_dd_adj*100:.1f}% ({(max_dd_adj - orig['max_drawdown'])*100:+.1f}pp)")
    print(f"2020 Rel: check report")


if __name__ == "__main__":
    main()
