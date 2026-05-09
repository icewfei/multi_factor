#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build a train/validation readout from portfolio dry-run artifacts only.

This script is intentionally NOT a fixed-test builder and NOT a formal strategy
readout. It estimates portfolio-level trainval behavior from run-state and
portfolio dry-run artifacts under the same daily-return construction used by the
fixed-test pipeline, but it never reads frozen-test outputs.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_RUN_INPUT_CONTRACT = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
DEFAULT_SPLIT_CONFIG = ROOT / "configs" / "dataset_split" / "dataset_split_research_trainval_20211231.json"
READOUT_LABEL = (
    "TRAINVAL PORTFOLIO DRY-RUN ESTIMATE ONLY — NOT FROZEN TEST — "
    "NOT A FORMAL STRATEGY CONCLUSION"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def normalize_date(value: str) -> str:
    return value.replace("-", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trainval dry-run validation readout.")
    parser.add_argument("--run-dir", required=True, help="Primary run directory.")
    parser.add_argument("--attempt-id", default=None, help="Optional primary attempt id.")
    parser.add_argument("--baseline-run-dir", default=None, help="Optional baseline run directory.")
    parser.add_argument("--baseline-attempt-id", default=None, help="Optional baseline attempt id.")
    parser.add_argument(
        "--run-input-contract",
        default=str(DEFAULT_RUN_INPUT_CONTRACT),
        help="Trainval run input contract JSON.",
    )
    parser.add_argument(
        "--split-config",
        default=str(DEFAULT_SPLIT_CONFIG),
        help="Train/validation split config JSON.",
    )
    parser.add_argument("--output-json", required=True, help="Output JSON path.")
    parser.add_argument("--output-md", required=True, help="Output Markdown path.")
    return parser.parse_args()


def resolve_attempt_id(run_dir: Path, attempt_id: str | None) -> str:
    if attempt_id:
        return attempt_id
    latest = load_json(run_dir / "run_state_latest_attempt.json")
    resolved = latest.get("attempt_id")
    if not isinstance(resolved, str) or not resolved:
        raise ValueError(f"Could not resolve attempt_id from {run_dir / 'run_state_latest_attempt.json'}")
    return resolved


def create_artifact_views(con: duckdb.DuckDBPyConnection, prefix: str, run_dir: Path, attempt_id: str) -> dict[str, Path]:
    attempt_dir = run_dir / "attempts" / attempt_id
    paths = {
        "holdings": attempt_dir / "holdings.csv",
        "summary": attempt_dir / "portfolio_daily_summary.csv",
        "turnover": attempt_dir / "turnover_daily.csv",
        "manifest": attempt_dir / "portfolio_artifacts_manifest.json",
        "run_state_acceptance": attempt_dir / "run_state_acceptance_report.json",
    }
    for key, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Required {prefix} artifact not found: {path}")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_holdings_t AS
        SELECT * FROM read_csv_auto({sql_path(paths['holdings'])}, HEADER=TRUE)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_summary_t AS
        SELECT * FROM read_csv_auto({sql_path(paths['summary'])}, HEADER=TRUE)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_turnover_t AS
        SELECT * FROM read_csv_auto({sql_path(paths['turnover'])}, HEADER=TRUE)
        """
    )
    return paths


def create_market_views(con: duckdb.DuckDBPyConnection, run_input: dict[str, Any]) -> None:
    snapshot_id = str(run_input["snapshot_id"])
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")
    con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
    con.execute(
        """
        CREATE OR REPLACE VIEW bars_t AS
        SELECT
            snapshot_id,
            ts_code AS instrument,
            trade_date,
            open,
            close,
            pre_close,
            pct_chg / 100.0 AS close_to_close_return
        FROM warehouse_db.serving.vw_bars_daily
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW calendar_t AS
        SELECT trade_date
        FROM warehouse_db.serving.vw_calendar
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW primary_benchmark_t AS
        SELECT
            trade_date,
            benchmark_code,
            benchmark_name,
            daily_return,
            is_total_return
        FROM warehouse_db.serving.vw_benchmark_daily
        WHERE snapshot_id = {sql_quote(snapshot_id)}
          AND benchmark_code = 'CSI_ALL_SHARE_TR'
        """
    )


def create_estimate_views(con: duckdb.DuckDBPyConnection, prefix: str) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_position_daily_returns_t AS
        SELECT
            h.run_id,
            h.attempt_id,
            h.run_type,
            h.position_id,
            h.instrument,
            CAST(c.trade_date AS VARCHAR) AS trade_date,
            h.entry_fill_weight,
            CAST(h.entry_date AS VARCHAR) AS entry_date,
            CAST(h.actual_exit_date AS VARCHAR) AS actual_exit_date,
            CAST(h.planned_exit_date AS VARCHAR) AS planned_exit_date,
            h.actual_exit_event_type,
            h.actual_exit_price_field,
            h.actual_sell_price,
            h.exit_delay_days,
            h.execution_delayed_realized_return,
            h.execution_path_status,
            h.pricing_policy_version,
            h.source_repair_flag,
            h.terminal_exit_approximation_flag,
            h.terminal_exit_conservative_flag,
            CASE
                WHEN CAST(c.trade_date AS VARCHAR) = CAST(h.entry_date AS VARCHAR) THEN
                    CASE
                        WHEN b.open IS NULL OR b.open = 0 OR b.close IS NULL THEN 0.0
                        ELSE (b.close / b.open) - 1.0
                    END
                WHEN CAST(c.trade_date AS VARCHAR) < CAST(h.actual_exit_date AS VARCHAR) THEN
                    CASE
                        WHEN b.pre_close IS NULL OR b.pre_close = 0 OR b.close IS NULL THEN 0.0
                        ELSE (b.close / b.pre_close) - 1.0
                    END
                WHEN CAST(c.trade_date AS VARCHAR) = CAST(h.actual_exit_date AS VARCHAR) THEN
                    CASE
                        WHEN b.pre_close IS NULL OR b.pre_close = 0 OR h.actual_sell_price IS NULL THEN 0.0
                        ELSE (h.actual_sell_price / b.pre_close) - 1.0
                    END
                ELSE 0.0
            END AS position_daily_return,
            h.entry_fill_weight * (
                CASE
                    WHEN CAST(c.trade_date AS VARCHAR) = CAST(h.entry_date AS VARCHAR) THEN
                        CASE
                            WHEN b.open IS NULL OR b.open = 0 OR b.close IS NULL THEN 0.0
                            ELSE (b.close / b.open) - 1.0
                        END
                    WHEN CAST(c.trade_date AS VARCHAR) < CAST(h.actual_exit_date AS VARCHAR) THEN
                        CASE
                            WHEN b.pre_close IS NULL OR b.pre_close = 0 OR b.close IS NULL THEN 0.0
                            ELSE (b.close / b.pre_close) - 1.0
                        END
                    WHEN CAST(c.trade_date AS VARCHAR) = CAST(h.actual_exit_date AS VARCHAR) THEN
                        CASE
                            WHEN b.pre_close IS NULL OR b.pre_close = 0 OR h.actual_sell_price IS NULL THEN 0.0
                            ELSE (h.actual_sell_price / b.pre_close) - 1.0
                        END
                    ELSE 0.0
                END
            ) AS pnl_weight_contribution
        FROM {prefix}_holdings_t h
        INNER JOIN calendar_t c
            ON CAST(c.trade_date AS VARCHAR) >= CAST(h.entry_date AS VARCHAR)
           AND CAST(c.trade_date AS VARCHAR) <= CAST(h.actual_exit_date AS VARCHAR)
        LEFT JOIN bars_t b
            ON h.instrument = b.instrument
           AND CAST(c.trade_date AS VARCHAR) = CAST(b.trade_date AS VARCHAR)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_portfolio_daily_returns_t AS
        SELECT
            run_id,
            attempt_id,
            run_type,
            trade_date,
            SUM(pnl_weight_contribution) AS portfolio_daily_return
        FROM {prefix}_position_daily_returns_t
        GROUP BY 1, 2, 3, 4
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {prefix}_backtest_daily_estimate_t AS
        WITH merged AS (
            SELECT
                s.run_id,
                s.attempt_id,
                s.run_type,
                CAST(s.trade_date AS VARCHAR) AS trade_date,
                COALESCE(r.portfolio_daily_return, 0.0) AS portfolio_daily_return,
                b.daily_return AS benchmark_return_daily,
                s.cash_weight,
                s.invested_weight,
                s.max_single_name_weight,
                s.top3_weight,
                s.portfolio_herfindahl_index,
                t.buy_notional_daily,
                t.sell_notional_daily,
                t.turnover_daily,
                t.rebalance_event_flag,
                CASE
                    WHEN COALESCE(s.invested_weight, 0.0) > 0.0
                    THEN COALESCE(r.portfolio_daily_return, 0.0) / s.invested_weight
                    ELSE 0.0
                END AS invested_sleeve_daily_return
            FROM {prefix}_summary_t s
            LEFT JOIN {prefix}_portfolio_daily_returns_t r
                ON s.run_id = r.run_id
               AND s.attempt_id = r.attempt_id
               AND s.run_type IS NOT DISTINCT FROM r.run_type
               AND CAST(s.trade_date AS VARCHAR) = CAST(r.trade_date AS VARCHAR)
            LEFT JOIN {prefix}_turnover_t t
                ON s.run_id = t.run_id
               AND s.attempt_id = t.attempt_id
               AND s.run_type IS NOT DISTINCT FROM t.run_type
               AND CAST(s.trade_date AS VARCHAR) = CAST(t.trade_date AS VARCHAR)
            LEFT JOIN primary_benchmark_t b
                ON CAST(s.trade_date AS VARCHAR) = b.trade_date
        ),
        equity_path AS (
            SELECT
                *,
                EXP(
                    SUM(LN(GREATEST(1.0 + portfolio_daily_return, 1e-12))) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS total_equity,
                EXP(
                    SUM(LN(GREATEST(1.0 + invested_sleeve_daily_return, 1e-12))) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS invested_capital_equity,
                EXP(
                    SUM(
                        LN(
                            CASE
                                WHEN benchmark_return_daily IS NULL THEN 1.0
                                ELSE GREATEST(1.0 + benchmark_return_daily, 1e-12)
                            END
                        )
                    ) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                ) AS benchmark_equity
            FROM merged
        )
        SELECT
            *,
            CASE
                WHEN benchmark_return_daily IS NULL THEN NULL
                ELSE portfolio_daily_return - benchmark_return_daily
            END AS relative_return_daily
        FROM equity_path
        """
    )


def annualize_equity(final_equity: float | None, n_days: int) -> float | None:
    if final_equity is None or n_days <= 0 or final_equity <= 0:
        return None
    return math.pow(final_equity, 252.0 / n_days) - 1.0


def compute_window_metrics(
    con: duckdb.DuckDBPyConnection,
    prefix: str,
    label: str,
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    stats = con.execute(
        f"""
        WITH windowed AS (
            SELECT *
            FROM {prefix}_backtest_daily_estimate_t
            WHERE trade_date >= {sql_quote(window_start)}
              AND trade_date <= {sql_quote(window_end)}
        ),
        dd AS (
            SELECT
                *,
                MAX(total_equity) OVER (
                    ORDER BY trade_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS total_running_peak,
                MAX(invested_capital_equity) OVER (
                    ORDER BY trade_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS invested_running_peak
            FROM windowed
        )
        SELECT
            COUNT(*) AS n_days,
            ANY_VALUE(total_equity) FILTER (
                WHERE trade_date = (SELECT MAX(trade_date) FROM windowed)
            ) AS final_total_equity,
            ANY_VALUE(invested_capital_equity) FILTER (
                WHERE trade_date = (SELECT MAX(trade_date) FROM windowed)
            ) AS final_invested_capital_equity,
            STDDEV_SAMP(portfolio_daily_return) AS total_daily_volatility,
            STDDEV_SAMP(invested_sleeve_daily_return) AS invested_daily_volatility,
            MIN((total_equity / NULLIF(total_running_peak, 0.0)) - 1.0) AS total_max_drawdown,
            MIN((invested_capital_equity / NULLIF(invested_running_peak, 0.0)) - 1.0) AS invested_max_drawdown,
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
        FROM {prefix}_backtest_daily_estimate_t
        WHERE trade_date >= {sql_quote(window_start)}
          AND trade_date <= {sql_quote(window_end)}
          AND benchmark_return_daily IS NOT NULL
        """
    ).fetchone()
    cash_dist = con.execute(
        f"""
        SELECT
            MIN(cash_weight),
            quantile_cont(cash_weight, 0.10),
            quantile_cont(cash_weight, 0.25),
            quantile_cont(cash_weight, 0.50),
            quantile_cont(cash_weight, 0.75),
            quantile_cont(cash_weight, 0.90),
            MAX(cash_weight)
        FROM {prefix}_summary_t
        WHERE CAST(trade_date AS VARCHAR) >= {sql_quote(window_start)}
          AND CAST(trade_date AS VARCHAR) <= {sql_quote(window_end)}
        """
    ).fetchone()
    turnover_dist = con.execute(
        f"""
        SELECT
            MIN(turnover_daily),
            AVG(turnover_daily),
            MEDIAN(turnover_daily),
            quantile_cont(turnover_daily, 0.95),
            quantile_cont(turnover_daily, 0.99),
            MAX(turnover_daily),
            COUNT(*) FILTER (WHERE turnover_daily > 1.0),
            COUNT(*) FILTER (WHERE turnover_daily > 1.5),
            COUNT(*) FILTER (WHERE turnover_daily > 2.0)
        FROM {prefix}_turnover_t
        WHERE CAST(trade_date AS VARCHAR) >= {sql_quote(window_start)}
          AND CAST(trade_date AS VARCHAR) <= {sql_quote(window_end)}
        """
    ).fetchone()
    terminal_impact = con.execute(
        f"""
        WITH positions AS (
            SELECT *
            FROM {prefix}_holdings_t
            WHERE signal_date >= {sql_quote(window_start)}
              AND signal_date <= {sql_quote(window_end)}
              AND actual_exit_event_type = 'TERMINAL_LAST_CLOSE'
        ),
        contrib AS (
            SELECT
                SUM(p.pnl_weight_contribution) AS pnl_weight_contribution_total,
                AVG(h.execution_delayed_realized_return) AS avg_realized_return,
                MIN(h.execution_delayed_realized_return) AS min_realized_return,
                MAX(h.execution_delayed_realized_return) AS max_realized_return,
                SUM(h.entry_fill_weight) AS entry_fill_weight_total
            FROM positions h
            LEFT JOIN {prefix}_position_daily_returns_t p
              ON h.position_id = p.position_id
        )
        SELECT
            (SELECT COUNT(*) FROM positions) AS terminal_last_close_positions,
            (SELECT COUNT(*) FROM positions WHERE source_repair_flag = TRUE) AS source_repair_flag_true_positions,
            (SELECT COUNT(*) FROM positions WHERE terminal_exit_conservative_flag = FALSE) AS conservative_flag_false_positions,
            (SELECT COUNT(*) FROM positions WHERE terminal_exit_approximation_flag = TRUE) AS approximation_true_positions,
            (SELECT COUNT(*) FROM positions WHERE terminal_exit_approximation_flag = FALSE) AS approximation_false_positions,
            (SELECT pnl_weight_contribution_total FROM contrib) AS pnl_weight_contribution_total,
            (SELECT entry_fill_weight_total FROM contrib) AS entry_fill_weight_total,
            (SELECT avg_realized_return FROM contrib) AS avg_realized_return,
            (SELECT min_realized_return FROM contrib) AS min_realized_return,
            (SELECT max_realized_return FROM contrib) AS max_realized_return
        """
    ).fetchone()
    attribution = con.execute(
        f"""
        SELECT
            SUM(benchmark_return_daily) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS benchmark_contribution_total,
            SUM(
                CASE
                    WHEN benchmark_return_daily IS NULL THEN NULL
                    ELSE - cash_weight * benchmark_return_daily
                END
            ) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS cash_drag_total,
            SUM(
                CASE
                    WHEN benchmark_return_daily IS NULL THEN NULL
                    ELSE portfolio_daily_return - ((1.0 - cash_weight) * benchmark_return_daily)
                END
            ) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS selection_alpha_total
        FROM {prefix}_backtest_daily_estimate_t
        WHERE trade_date >= {sql_quote(window_start)}
          AND trade_date <= {sql_quote(window_end)}
        """
    ).fetchone()
    turnover_peaks = con.execute(
        f"""
        SELECT
            CAST(trade_date AS VARCHAR) AS trade_date,
            turnover_daily,
            buy_notional_daily,
            sell_notional_daily,
            rebalance_event_flag
        FROM {prefix}_turnover_t
        WHERE CAST(trade_date AS VARCHAR) >= {sql_quote(window_start)}
          AND CAST(trade_date AS VARCHAR) <= {sql_quote(window_end)}
        ORDER BY turnover_daily DESC, trade_date ASC
        LIMIT 5
        """
    ).fetchall()

    n_days = int(stats[0] or 0)
    final_total_equity = float(stats[1] or 1.0)
    final_invested_capital_equity = float(stats[2] or 1.0)
    total_daily_vol = float(stats[3] or 0.0)
    invested_daily_vol = float(stats[4] or 0.0)
    n_effective_days = int(relative_stats[0] or 0)
    relative_nav_end = float(relative_stats[1] or 1.0)
    benchmark_nav_end = float(relative_stats[2] or 1.0)
    avg_relative_return_daily = float(relative_stats[3] or 0.0)
    std_relative_return_daily = float(relative_stats[4] or 0.0)

    annual_relative_return = annualize_equity(relative_nav_end, n_effective_days)
    total_annualized_return = annualize_equity(final_total_equity, n_days)
    invested_annualized_return = annualize_equity(final_invested_capital_equity, n_days)
    total_annualized_volatility = total_daily_vol * math.sqrt(252.0) if n_days > 1 else None
    invested_annualized_volatility = invested_daily_vol * math.sqrt(252.0) if n_days > 1 else None
    total_sharpe = (
        total_annualized_return / total_annualized_volatility
        if total_annualized_return is not None and total_annualized_volatility not in (None, 0.0)
        else None
    )
    invested_sharpe = (
        invested_annualized_return / invested_annualized_volatility
        if invested_annualized_return is not None and invested_annualized_volatility not in (None, 0.0)
        else None
    )
    relative_ir = (
        avg_relative_return_daily / std_relative_return_daily * math.sqrt(252.0)
        if n_effective_days > 1 and std_relative_return_daily not in (0.0, None)
        else None
    )

    return {
        "window_name": label,
        "window_start": window_start,
        "window_end": window_end,
        "n_days": n_days,
        "final_total_equity_estimate": final_total_equity,
        "total_return_estimate": final_total_equity - 1.0,
        "annualized_return_trainval_dry_run_estimate": total_annualized_return,
        "final_invested_capital_equity_estimate": final_invested_capital_equity,
        "invested_capital_total_return_estimate": final_invested_capital_equity - 1.0,
        "annualized_invested_capital_return_estimate": invested_annualized_return,
        "benchmark_total_return_estimate": benchmark_nav_end - 1.0 if n_effective_days > 0 else None,
        "annual_relative_return_trainval_dry_run_estimate": annual_relative_return,
        "relative_ir_estimate": relative_ir,
        "total_daily_volatility": total_daily_vol,
        "invested_daily_volatility": invested_daily_vol,
        "total_annualized_volatility": total_annualized_volatility,
        "invested_annualized_volatility": invested_annualized_volatility,
        "total_sharpe_estimate": total_sharpe,
        "invested_capital_sharpe_estimate": invested_sharpe,
        "max_drawdown_trainval_dry_run_estimate": float(stats[5] or 0.0),
        "invested_capital_max_drawdown_estimate": float(stats[6] or 0.0),
        "avg_cash_weight": float(stats[7] or 0.0),
        "avg_invested_weight": float(stats[8] or 0.0),
        "avg_turnover_daily": float(stats[9] or 0.0),
        "rebalance_days": int(stats[10] or 0),
        "positive_relative_days": int(relative_stats[5] or 0),
        "cash_weight_distribution": {
            "min": float(cash_dist[0] or 0.0),
            "p10": float(cash_dist[1] or 0.0),
            "p25": float(cash_dist[2] or 0.0),
            "p50": float(cash_dist[3] or 0.0),
            "p75": float(cash_dist[4] or 0.0),
            "p90": float(cash_dist[5] or 0.0),
            "max": float(cash_dist[6] or 0.0),
        },
        "turnover_summary": {
            "min": float(turnover_dist[0] or 0.0),
            "avg": float(turnover_dist[1] or 0.0),
            "median": float(turnover_dist[2] or 0.0),
            "p95": float(turnover_dist[3] or 0.0),
            "p99": float(turnover_dist[4] or 0.0),
            "max": float(turnover_dist[5] or 0.0),
            "gt_100pct_days": int(turnover_dist[6] or 0),
            "gt_150pct_days": int(turnover_dist[7] or 0),
            "gt_200pct_days": int(turnover_dist[8] or 0),
            "top5_days": [
                {
                    "trade_date": str(row[0]),
                    "turnover_daily": float(row[1] or 0.0),
                    "buy_notional_daily": float(row[2] or 0.0),
                    "sell_notional_daily": float(row[3] or 0.0),
                    "rebalance_event_flag": bool(row[4]),
                }
                for row in turnover_peaks
            ],
        },
        "terminal_last_close_impact_summary": {
            "positions": int(terminal_impact[0] or 0),
            "source_repair_flag_true_positions": int(terminal_impact[1] or 0),
            "terminal_exit_conservative_flag_false_positions": int(terminal_impact[2] or 0),
            "approximation_true_positions": int(terminal_impact[3] or 0),
            "approximation_false_positions": int(terminal_impact[4] or 0),
            "pnl_weight_contribution_total": float(terminal_impact[5] or 0.0),
            "entry_fill_weight_total": float(terminal_impact[6] or 0.0),
            "avg_realized_return": float(terminal_impact[7] or 0.0),
            "min_realized_return": float(terminal_impact[8] or 0.0),
            "max_realized_return": float(terminal_impact[9] or 0.0),
        },
        "return_attribution_summary": {
            "benchmark_contribution_total": float(attribution[0] or 0.0),
            "cash_drag_total": float(attribution[1] or 0.0),
            "selection_alpha_total": float(attribution[2] or 0.0),
        },
    }


def load_run_metadata(run_dir: Path, attempt_id: str) -> dict[str, Any]:
    manifest = load_json(run_dir / "attempts" / attempt_id / "portfolio_artifacts_manifest.json")
    run_state_acceptance = load_json(run_dir / "attempts" / attempt_id / "run_state_acceptance_report.json")
    run_state_manifest = load_json(run_dir / "attempts" / attempt_id / "run_state_attempt_manifest.json")
    return {
        "portfolio_manifest": manifest,
        "run_state_acceptance": run_state_acceptance,
        "run_state_manifest": run_state_manifest,
    }


def compare_windows(primary: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "annualized_return_trainval_dry_run_estimate",
        "annualized_invested_capital_return_estimate",
        "annual_relative_return_trainval_dry_run_estimate",
        "relative_ir_estimate",
        "max_drawdown_trainval_dry_run_estimate",
        "invested_capital_max_drawdown_estimate",
        "avg_cash_weight",
        "avg_invested_weight",
        "avg_turnover_daily",
        "final_total_equity_estimate",
        "final_invested_capital_equity_estimate",
    ]
    deltas: dict[str, Any] = {}
    for key in keys:
        p_val = primary.get(key)
        b_val = baseline.get(key)
        if isinstance(p_val, (int, float)) and isinstance(b_val, (int, float)):
            deltas[f"{key}_delta_vs_baseline"] = float(p_val - b_val)
    return deltas


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Nonlinear Confirmed5 Trainval Dry-Run Validation Readout",
        "",
        f"- Label: `{payload['readout_label']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Distinct from model edge diagnosis: `{payload['distinct_from_model_edge_diagnosis']}`",
        f"- Frozen test accessed: `{payload['frozen_test_accessed']}`",
        "",
    ]
    primary = payload["primary_run"]
    lines.extend([
        "## Primary Run",
        "",
        f"- run_id: `{primary['run_id']}`",
        f"- attempt_id: `{primary['attempt_id']}`",
        f"- candidate_scheme_id: `{primary['candidate_scheme_id']}`",
        "",
    ])
    for window_name, window_payload in payload["windows"]["primary"].items():
        lines.extend([
            f"## {window_name.title()}",
            "",
            f"- total_equity_estimate_end: `{window_payload['final_total_equity_estimate']:.6f}`",
            f"- invested_capital_equity_estimate_end: `{window_payload['final_invested_capital_equity_estimate']:.6f}`",
            f"- annualized_return_trainval_dry_run_estimate: `{window_payload['annualized_return_trainval_dry_run_estimate']}`",
            f"- annualized_invested_capital_return_estimate: `{window_payload['annualized_invested_capital_return_estimate']}`",
            f"- max_drawdown_trainval_dry_run_estimate: `{window_payload['max_drawdown_trainval_dry_run_estimate']}`",
            f"- avg_cash_weight: `{window_payload['avg_cash_weight']:.6f}`",
            f"- avg_invested_weight: `{window_payload['avg_invested_weight']:.6f}`",
            f"- avg_turnover_daily: `{window_payload['avg_turnover_daily']:.6f}`",
            f"- terminal_last_close_positions: `{window_payload['terminal_last_close_impact_summary']['positions']}`",
            "",
        ])
    if payload.get("baseline_run") is not None:
        base = payload["baseline_run"]
        lines.extend([
            "## Baseline Run",
            "",
            f"- run_id: `{base['run_id']}`",
            f"- attempt_id: `{base['attempt_id']}`",
            f"- candidate_scheme_id: `{base['candidate_scheme_id']}`",
            "",
            "## Comparison",
            "",
        ])
        for window_name, deltas in payload["windows"]["comparison"].items():
            lines.append(f"### {window_name.title()}")
            lines.append("")
            for key, value in deltas.items():
                lines.append(f"- {key}: `{value:+.6f}`")
            lines.append("")
    lines.extend([
        "## Caveat",
        "",
        "This document is a trainval portfolio dry-run estimate only. It is not a frozen-test readout and not a formal strategy-validity conclusion.",
        "",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    run_input = load_json(Path(args.run_input_contract))
    split_config = load_json(Path(args.split_config))

    train_start = normalize_date(split_config["train_start"])
    train_end = normalize_date(split_config["train_end"])
    validation_start = normalize_date(split_config["validation_start"])
    validation_end = normalize_date(split_config["validation_end"])

    primary_run_dir = Path(args.run_dir)
    primary_attempt_id = resolve_attempt_id(primary_run_dir, args.attempt_id)

    baseline_run_dir = Path(args.baseline_run_dir) if args.baseline_run_dir else None
    baseline_attempt_id = (
        resolve_attempt_id(baseline_run_dir, args.baseline_attempt_id)
        if baseline_run_dir is not None
        else None
    )

    con = duckdb.connect()
    try:
        create_market_views(con, run_input)
        primary_paths = create_artifact_views(con, "primary", primary_run_dir, primary_attempt_id)
        create_estimate_views(con, "primary")
        primary_meta = load_run_metadata(primary_run_dir, primary_attempt_id)

        baseline_paths = None
        baseline_meta = None
        if baseline_run_dir is not None and baseline_attempt_id is not None:
            baseline_paths = create_artifact_views(con, "baseline", baseline_run_dir, baseline_attempt_id)
            create_estimate_views(con, "baseline")
            baseline_meta = load_run_metadata(baseline_run_dir, baseline_attempt_id)

        windows_primary = {
            "train": compute_window_metrics(con, "primary", "train", train_start, train_end),
            "validation": compute_window_metrics(con, "primary", "validation", validation_start, validation_end),
        }
        windows_comparison: dict[str, Any] = {}
        windows_baseline: dict[str, Any] | None = None
        if baseline_run_dir is not None and baseline_attempt_id is not None:
            windows_baseline = {
                "train": compute_window_metrics(con, "baseline", "train", train_start, train_end),
                "validation": compute_window_metrics(con, "baseline", "validation", validation_start, validation_end),
            }
            windows_comparison = {
                "train": compare_windows(windows_primary["train"], windows_baseline["train"]),
                "validation": compare_windows(windows_primary["validation"], windows_baseline["validation"]),
            }
    finally:
        con.close()

    primary_manifest = primary_meta["run_state_manifest"]
    primary_scheme = primary_manifest.get("parameters", {}).get("candidate_scheme_id")
    baseline_scheme = None
    if baseline_meta is not None:
        baseline_scheme = baseline_meta["run_state_manifest"].get("parameters", {}).get("candidate_scheme_id")

    payload: dict[str, Any] = {
        "readout_label": READOUT_LABEL,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "distinct_from_model_edge_diagnosis": (
            "This readout is portfolio-layer trainval dry-run estimation. "
            "It is distinct from model-score-level edge diagnosis."
        ),
        "split_config": {
            "train_start": train_start,
            "train_end": train_end,
            "validation_start": validation_start,
            "validation_end": validation_end,
            "test_excluded_start": normalize_date(split_config["test_excluded_start"]),
            "test_excluded_end": normalize_date(split_config["test_excluded_end"]),
        },
        "primary_run": {
            "run_id": primary_run_dir.name,
            "attempt_id": primary_attempt_id,
            "candidate_scheme_id": primary_scheme,
            "paths": {k: str(v) for k, v in primary_paths.items()},
            "run_state_acceptance_overall_passed": bool(primary_meta["run_state_acceptance"]["overall_passed"]),
            "portfolio_manifest_summary_counts": primary_meta["portfolio_manifest"].get("summary_counts", {}),
        },
        "baseline_run": (
            {
                "run_id": baseline_run_dir.name,
                "attempt_id": baseline_attempt_id,
                "candidate_scheme_id": baseline_scheme,
                "paths": {k: str(v) for k, v in baseline_paths.items()} if baseline_paths else {},
                "run_state_acceptance_overall_passed": bool(baseline_meta["run_state_acceptance"]["overall_passed"]) if baseline_meta else None,
                "portfolio_manifest_summary_counts": baseline_meta["portfolio_manifest"].get("summary_counts", {}) if baseline_meta else {},
            }
            if baseline_run_dir is not None and baseline_attempt_id is not None and baseline_meta is not None
            else None
        ),
        "windows": {
            "primary": windows_primary,
            "baseline": windows_baseline,
            "comparison": windows_comparison,
        },
    }

    write_json(Path(args.output_json), payload)
    Path(args.output_md).write_text(build_markdown(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
