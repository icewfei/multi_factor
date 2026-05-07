#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a validation-window readout from fixed-test backtest_daily outputs.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import duckdb


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build confirmatory validation-window metrics.")
    parser.add_argument("--fixed-test-dir", required=True)
    parser.add_argument("--validation-start", required=True)
    parser.add_argument("--validation-end", required=True)
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixed_test_dir = Path(args.fixed_test_dir)
    backtest_daily = fixed_test_dir / "backtest_daily.csv"
    metrics_json = fixed_test_dir / "metrics.json"
    if not backtest_daily.exists():
        raise FileNotFoundError(f"Required input not found: {backtest_daily}")
    if not metrics_json.exists():
        raise FileNotFoundError(f"Required input not found: {metrics_json}")

    base_metrics = load_json(metrics_json)

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            CREATE OR REPLACE VIEW backtest_daily_t AS
            SELECT * FROM read_csv_auto({sql_path(backtest_daily)}, HEADER=TRUE)
            """
        )
        stats = con.execute(
            f"""
            WITH windowed AS (
                SELECT *
                FROM backtest_daily_t
                WHERE trade_date >= {sql_quote(args.validation_start)}
                  AND trade_date <= {sql_quote(args.validation_end)}
            ),
            dd AS (
                SELECT
                    *,
                    MAX(total_equity) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_peak
                FROM windowed
            )
            SELECT
                COUNT(*) AS n_days,
                ANY_VALUE(total_equity) FILTER (
                    WHERE trade_date = (SELECT MAX(trade_date) FROM windowed)
                ) AS final_equity,
                STDDEV_SAMP(portfolio_daily_return) AS daily_volatility,
                MIN((total_equity / NULLIF(running_peak, 0.0)) - 1.0) AS max_drawdown,
                AVG(cash_weight) AS avg_cash_weight,
                AVG(invested_weight) AS avg_invested_weight,
                AVG(turnover_daily) AS avg_turnover_daily,
                SUM(CASE WHEN rebalance_event_flag THEN 1 ELSE 0 END) AS rebalance_days
            FROM dd
            """
        ).fetchone()

        relative_stats = con.execute(
            f"""
            SELECT
                COUNT(*) AS n_effective_days,
                EXP(SUM(LN(GREATEST((1.0 + portfolio_daily_return) / NULLIF(1.0 + benchmark_return_daily, 0.0), 1e-12)))) AS relative_nav_end,
                EXP(SUM(LN(GREATEST(1.0 + benchmark_return_daily, 1e-12)))) AS benchmark_nav_end,
                AVG(relative_return_daily) AS avg_relative_return_daily,
                STDDEV_SAMP(relative_return_daily) AS std_relative_return_daily,
                SUM(CASE WHEN relative_return_daily > 0 THEN 1 ELSE 0 END) AS positive_relative_days
            FROM backtest_daily_t
            WHERE trade_date >= {sql_quote(args.validation_start)}
              AND trade_date <= {sql_quote(args.validation_end)}
              AND benchmark_return_daily IS NOT NULL
            """
        ).fetchone()
    finally:
        con.close()

    n_days = int(stats[0] or 0)
    final_equity = float(stats[1] or 1.0)
    total_return = final_equity - 1.0
    daily_vol = float(stats[2] or 0.0)
    annualized_return = math.pow(final_equity, 252.0 / n_days) - 1.0 if n_days > 0 and final_equity > 0 else None
    annualized_volatility = daily_vol * math.sqrt(252.0) if daily_vol is not None else None
    sharpe_ratio = (
        annualized_return / annualized_volatility
        if annualized_return is not None and annualized_volatility not in (None, 0.0)
        else None
    )

    n_effective_days = int(relative_stats[0] or 0)
    relative_nav_end = float(relative_stats[1] or 1.0)
    benchmark_nav_end = float(relative_stats[2] or 1.0)
    annual_relative_return = (
        math.pow(relative_nav_end, 252.0 / n_effective_days) - 1.0
        if n_effective_days > 0 and relative_nav_end > 0
        else None
    )
    avg_relative_return_daily = float(relative_stats[3] or 0.0)
    std_relative_return_daily = float(relative_stats[4] or 0.0)
    relative_ir = (
        avg_relative_return_daily / std_relative_return_daily * math.sqrt(252.0)
        if n_effective_days > 1 and std_relative_return_daily not in (0.0, None)
        else None
    )

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fixed_test_run_id": base_metrics.get("fixed_test_run_id"),
        "run_id": base_metrics.get("run_id"),
        "candidate_scheme_id": base_metrics.get("candidate_scheme_id"),
        "research_round_id": base_metrics.get("research_round_id"),
        "snapshot_id": base_metrics.get("snapshot_id"),
        "window_name": "validation",
        "validation_start": args.validation_start,
        "validation_end": args.validation_end,
        "n_days": n_days,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "benchmark_total_return": benchmark_nav_end - 1.0 if n_effective_days > 0 else None,
        "annual_relative_return": annual_relative_return,
        "effective_relative_days": n_effective_days,
        "positive_relative_days": int(relative_stats[5] or 0),
        "relative_ir": relative_ir,
        "daily_volatility": daily_vol,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": float(stats[3] or 0.0),
        "avg_cash_weight": float(stats[4] or 0.0),
        "avg_invested_weight": float(stats[5] or 0.0),
        "avg_turnover_daily": float(stats[6] or 0.0),
        "rebalance_days": int(stats[7] or 0),
    }
    write_json(Path(args.output_path), payload)


if __name__ == "__main__":
    main()
