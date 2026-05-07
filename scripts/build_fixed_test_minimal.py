#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build minimal fixed-test artifacts from portfolio-layer outputs.

Inputs:
- artifacts/run_state/<run_id>/attempts/<attempt_id>/holdings.csv
- artifacts/run_state/<run_id>/attempts/<attempt_id>/portfolio_daily_summary.csv
- artifacts/run_state/<run_id>/attempts/<attempt_id>/turnover_daily.csv
- shared warehouse bars daily

Outputs:
- artifacts/fixed_test/<run_id>/backtest_daily.csv
- artifacts/fixed_test/<run_id>/metrics.json
- artifacts/fixed_test/<run_id>/trade_statistics_summary.json
- artifacts/fixed_test/<run_id>/annual_return_table.csv
- artifacts/fixed_test/<run_id>/holding_period_return_distribution.csv
- artifacts/fixed_test/<run_id>/topk_perturbation_summary.json
- artifacts/fixed_test/<run_id>/data_contract_summary.json
- artifacts/fixed_test/<run_id>/audit_summary.json
- artifacts/fixed_test/<run_id>/cash_source_explanation.csv
- artifacts/fixed_test/<run_id>/low_liquidity_exposure_summary.json
- artifacts/fixed_test/<run_id>/cost_stress_summary.json
- artifacts/fixed_test/<run_id>/return_attribution_summary.json
- artifacts/fixed_test/<run_id>/fixed_test_manifest.json

This is a near-formal fixed-test artifact builder. It still does not produce the full
appendix set from the framework, but it now includes:
- benchmark-relative metrics on the primary total-return benchmark
- annual return table
- holding-period return distribution
- TopK perturbation summary

Unit discipline:
- All `*_return` fields use decimal-return convention unless explicitly labeled as `%`
  or `bp`. Example: `0.05 = 5%`.
- All `*_weight` fields use normalized `0-1` portfolio-weight convention.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
ARTIFACTS_FIXED_TEST_DIR = ROOT / "artifacts" / "fixed_test"
CONTRACTS_DIR = ROOT / "contracts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build minimal fixed-test artifacts.")
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--run-state-dir",
        default=None,
        help="Optional run-state directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="Optional run-state attempt identifier. Defaults to run_state_latest_attempt.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional fixed-test output directory. Defaults to artifacts/fixed_test/<run_id>/",
    )
    parser.add_argument(
        "--fixed-test-run-id",
        default=None,
        help="Optional fixed test run id. Defaults to run_id.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def atomic_json_write(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".inprogress")
    write_json(temp_path, payload)
    os.replace(temp_path, path)


def sql_quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def require_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def resolve_run_state_dir(run_id: str, run_state_dir: str | None) -> Path:
    resolved = Path(run_state_dir) if run_state_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    return require_path(resolved)


def resolve_attempt_dir(run_dir: Path, attempt_id: str | None) -> tuple[str, Path]:
    if attempt_id:
        resolved_attempt_id = attempt_id
    else:
        latest_pointer = require_path(run_dir / "run_state_latest_attempt.json")
        latest_payload = load_json(latest_pointer)
        resolved_attempt_id = latest_payload["attempt_id"]
    attempt_dir = require_path(run_dir / "attempts" / resolved_attempt_id)
    return resolved_attempt_id, attempt_dir


def atomic_csv_copy(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> None:
    temp_path = output_path.with_suffix(output_path.suffix + ".inprogress")
    if temp_path.exists():
        temp_path.unlink()
    con.execute(
        f"""
        COPY (
            {query}
        ) TO {sql_path(temp_path)}
        (HEADER, DELIMITER ',', FORCE_QUOTE *)
        """
    )
    os.replace(temp_path, output_path)


def main() -> None:
    args = parse_args()

    run_dir = resolve_run_state_dir(args.run_id, args.run_state_dir)
    attempt_id, attempt_dir = resolve_attempt_dir(run_dir, args.attempt_id)
    output_dir = Path(args.output_dir) if args.output_dir else (ARTIFACTS_FIXED_TEST_DIR / args.run_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    fixed_test_run_id = args.fixed_test_run_id or args.run_id

    holdings_path = require_path(attempt_dir / "holdings.csv")
    summary_path = require_path(attempt_dir / "portfolio_daily_summary.csv")
    turnover_path = require_path(attempt_dir / "turnover_daily.csv")
    ranking_state_path = require_path(attempt_dir / "ranking_state_daily.parquet")
    execution_state_path = require_path(attempt_dir / "execution_state_daily.parquet")
    project_execution_panel_path = require_path(run_dir / "project_execution_panel.parquet")
    run_state_audit_path = require_path(attempt_dir / "data_quality_audit.json")
    run_state_manifest_path = require_path(attempt_dir / "run_state_attempt_manifest.json")
    portfolio_manifest_path = require_path(attempt_dir / "portfolio_artifacts_manifest.json")

    run_input_contract_path = Path(args.run_input_contract) if args.run_input_contract else (
        CONTRACTS_DIR / "run_input_contract.current.json"
    )
    run_input = load_json(run_input_contract_path)
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_path(source_db_path)

    backtest_daily_path = output_dir / "backtest_daily.csv"
    metrics_path = output_dir / "metrics.json"
    trade_stats_path = output_dir / "trade_statistics_summary.json"
    annual_return_table_path = output_dir / "annual_return_table.csv"
    holding_period_distribution_path = output_dir / "holding_period_return_distribution.csv"
    topk_perturbation_summary_path = output_dir / "topk_perturbation_summary.json"
    data_contract_summary_path = output_dir / "data_contract_summary.json"
    audit_summary_path = output_dir / "audit_summary.json"
    cash_source_explanation_path = output_dir / "cash_source_explanation.csv"
    low_liquidity_exposure_summary_path = output_dir / "low_liquidity_exposure_summary.json"
    cost_stress_summary_path = output_dir / "cost_stress_summary.json"
    return_attribution_summary_path = output_dir / "return_attribution_summary.json"
    manifest_path = output_dir / "fixed_test_manifest.json"
    portfolio_manifest = load_json(portfolio_manifest_path)
    cohort_fraction = float(portfolio_manifest["assumptions"]["cohort_capital_fraction"])

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW holdings_t AS
            SELECT
                CAST(run_id AS VARCHAR) AS run_id,
                CAST(attempt_id AS VARCHAR) AS attempt_id,
                CAST(run_type AS VARCHAR) AS run_type,
                CAST(snapshot_id AS VARCHAR) AS snapshot_id,
                CAST(position_id AS VARCHAR) AS position_id,
                CAST(instrument AS VARCHAR) AS instrument,
                CAST(signal_date AS VARCHAR) AS signal_date,
                CAST(entry_date AS VARCHAR) AS entry_date,
                CAST(planned_exit_date AS VARCHAR) AS planned_exit_date,
                CAST(actual_exit_date AS VARCHAR) AS actual_exit_date,
                CAST(actual_exit_event_type AS VARCHAR) AS actual_exit_event_type,
                CAST(actual_exit_price_field AS VARCHAR) AS actual_exit_price_field,
                CAST(actual_sell_price AS DOUBLE) AS actual_sell_price,
                CAST(exit_delay_days AS BIGINT) AS exit_delay_days,
                CAST(execution_delayed_realized_return AS DOUBLE) AS execution_delayed_realized_return,
                CAST(execution_path_status AS VARCHAR) AS execution_path_status,
                CAST(target_weight_D0 AS DOUBLE) AS target_weight_D0,
                CAST(entry_fill_weight AS DOUBLE) AS entry_fill_weight,
                CAST(cohort_capital_fraction AS DOUBLE) AS cohort_capital_fraction,
                CAST(entry_filled_D1 AS BOOLEAN) AS entry_filled_D1,
                CAST(entry_filled_reason AS VARCHAR) AS entry_filled_reason,
                CAST(backtest_executable AS BOOLEAN) AS backtest_executable,
                CAST(terminal_event_flag AS BOOLEAN) AS terminal_event_flag,
                CAST(terminal_event_type AS VARCHAR) AS terminal_event_type,
                CAST(terminal_event_date AS VARCHAR) AS terminal_event_date,
                CAST(terminal_exit_pricing_method AS VARCHAR) AS terminal_exit_pricing_method,
                CAST(terminal_exit_approximation_flag AS BOOLEAN) AS terminal_exit_approximation_flag,
                CAST(terminal_exit_conservative_flag AS BOOLEAN) AS terminal_exit_conservative_flag
            FROM read_csv_auto({sql_path(holdings_path)}, HEADER=TRUE)
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW portfolio_daily_summary_t AS
            SELECT
                CAST(run_id AS VARCHAR) AS run_id,
                CAST(attempt_id AS VARCHAR) AS attempt_id,
                CAST(run_type AS VARCHAR) AS run_type,
                CAST(trade_date AS VARCHAR) AS trade_date,
                CAST(cash_weight AS DOUBLE) AS cash_weight,
                CAST(invested_weight AS DOUBLE) AS invested_weight,
                CAST(max_single_name_weight AS DOUBLE) AS max_single_name_weight,
                CAST(top3_weight AS DOUBLE) AS top3_weight,
                CAST(portfolio_herfindahl_index AS DOUBLE) AS portfolio_herfindahl_index,
                CAST(industry_active_weight_max AS DOUBLE) AS industry_active_weight_max
            FROM read_csv_auto({sql_path(summary_path)}, HEADER=TRUE)
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW turnover_daily_t AS
            SELECT
                CAST(run_id AS VARCHAR) AS run_id,
                CAST(attempt_id AS VARCHAR) AS attempt_id,
                CAST(run_type AS VARCHAR) AS run_type,
                CAST(trade_date AS VARCHAR) AS trade_date,
                CAST(buy_notional_daily AS DOUBLE) AS buy_notional_daily,
                CAST(sell_notional_daily AS DOUBLE) AS sell_notional_daily,
                CAST(turnover_daily AS DOUBLE) AS turnover_daily,
                CAST(rebalance_event_flag AS BOOLEAN) AS rebalance_event_flag
            FROM read_csv_auto({sql_path(turnover_path)}, HEADER=TRUE)
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW ranking_state_t AS
            SELECT * FROM read_parquet({sql_path(ranking_state_path)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_state_t AS
            SELECT * FROM read_parquet({sql_path(execution_state_path)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_execution_panel_t AS
            SELECT * FROM read_parquet({sql_path(project_execution_panel_path)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW tradability_t AS
            SELECT
                snapshot_id,
                ts_code AS instrument,
                trade_date,
                low_liquidity_flag_t,
                is_suspended_t,
                open_at_up_limit_t,
                one_word_up_limit_t,
                buyable_at_open,
                entry_buyable_D1_open
            FROM warehouse_db.serving.vw_tradability_daily
            WHERE snapshot_id = {sql_quote(run_input["snapshot_id"])}
            """
        )
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
            SELECT
                trade_date
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
            WHERE snapshot_id = {sql_quote(run_input["snapshot_id"])}
              AND benchmark_code = 'CSI_ALL_SHARE_TR'
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW auxiliary_benchmark_t AS
            SELECT
                trade_date,
                benchmark_code,
                benchmark_name,
                daily_return,
                is_total_return
            FROM warehouse_db.serving.vw_benchmark_aux_daily
            WHERE snapshot_id = {sql_quote(run_input["snapshot_id"])}
              AND benchmark_code = 'CSI_300_TR'
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW position_daily_returns_t AS
            SELECT
                h.run_id,
                h.attempt_id,
                h.run_type,
                h.position_id,
                h.instrument,
                c.trade_date,
                h.entry_fill_weight,
                h.entry_date,
                h.actual_exit_date,
                h.planned_exit_date,
                h.actual_exit_event_type,
                h.actual_exit_price_field,
                h.actual_sell_price,
                h.exit_delay_days,
                h.execution_delayed_realized_return,
                CASE
                    WHEN c.trade_date = h.entry_date THEN
                        CASE
                            WHEN b.open IS NULL OR b.open = 0 OR b.close IS NULL THEN 0.0
                            ELSE (b.close / b.open) - 1.0
                        END
                    WHEN c.trade_date < h.actual_exit_date THEN
                        CASE
                            WHEN b.pre_close IS NULL OR b.pre_close = 0 OR b.close IS NULL THEN 0.0
                            ELSE (b.close / b.pre_close) - 1.0
                        END
                    WHEN c.trade_date = h.actual_exit_date THEN
                        CASE
                            WHEN b.pre_close IS NULL OR b.pre_close = 0 OR h.actual_sell_price IS NULL THEN 0.0
                            ELSE (h.actual_sell_price / b.pre_close) - 1.0
                        END
                    ELSE 0.0
                END AS position_daily_return,
                h.entry_fill_weight * (
                    CASE
                        WHEN c.trade_date = h.entry_date THEN
                            CASE
                                WHEN b.open IS NULL OR b.open = 0 OR b.close IS NULL THEN 0.0
                                ELSE (b.close / b.open) - 1.0
                            END
                        WHEN c.trade_date < h.actual_exit_date THEN
                            CASE
                                WHEN b.pre_close IS NULL OR b.pre_close = 0 OR b.close IS NULL THEN 0.0
                                ELSE (b.close / b.pre_close) - 1.0
                            END
                        WHEN c.trade_date = h.actual_exit_date THEN
                            CASE
                                WHEN b.pre_close IS NULL OR b.pre_close = 0 OR h.actual_sell_price IS NULL THEN 0.0
                                ELSE (h.actual_sell_price / b.pre_close) - 1.0
                            END
                        ELSE 0.0
                    END
                ) AS pnl_weight_contribution
            FROM holdings_t h
            INNER JOIN calendar_t c
                ON c.trade_date >= h.entry_date
               AND c.trade_date <= h.actual_exit_date
            LEFT JOIN bars_t b
                ON h.instrument = b.instrument
               AND c.trade_date = b.trade_date
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW portfolio_daily_returns_t AS
            SELECT
                run_id,
                attempt_id,
                run_type,
                trade_date,
                SUM(pnl_weight_contribution) AS portfolio_daily_return
            FROM position_daily_returns_t
            GROUP BY 1, 2, 3, 4
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW backtest_daily_t AS
            WITH merged AS (
                SELECT
                    CAST({sql_quote(fixed_test_run_id)} AS VARCHAR) AS fixed_test_run_id,
                    s.run_id,
                    s.attempt_id,
                    s.run_type,
                    s.trade_date,
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
                    t.rebalance_event_flag
                FROM portfolio_daily_summary_t s
                LEFT JOIN portfolio_daily_returns_t r
                    ON s.run_id = r.run_id
                   AND s.attempt_id = r.attempt_id
                   AND s.run_type IS NOT DISTINCT FROM r.run_type
                   AND s.trade_date = r.trade_date
                LEFT JOIN turnover_daily_t t
                    ON s.run_id = t.run_id
                   AND s.attempt_id = t.attempt_id
                   AND s.run_type IS NOT DISTINCT FROM t.run_type
                   AND s.trade_date = t.trade_date
                LEFT JOIN primary_benchmark_t b
                    ON s.trade_date = b.trade_date
            ),
            equity_path AS (
                SELECT
                    *,
                    EXP(
                        SUM(LN(GREATEST(1.0 + portfolio_daily_return, 1e-12))) OVER (
                            ORDER BY trade_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        )
                    ) AS total_equity
                    ,
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
                fixed_test_run_id,
                run_id,
                attempt_id,
                run_type,
                trade_date,
                portfolio_daily_return,
                benchmark_return_daily,
                CASE
                    WHEN benchmark_return_daily IS NULL THEN NULL
                    ELSE portfolio_daily_return - benchmark_return_daily
                END AS relative_return_daily,
                total_equity,
                benchmark_equity,
                total_equity - 1.0 AS cumulative_return,
                benchmark_equity - 1.0 AS benchmark_cumulative_return,
                cash_weight,
                invested_weight,
                max_single_name_weight,
                top3_weight,
                portfolio_herfindahl_index,
                buy_notional_daily,
                sell_notional_daily,
                turnover_daily,
                rebalance_event_flag
            FROM equity_path
            """
        )

        atomic_csv_copy(
            con,
            """
            SELECT
                fixed_test_run_id,
                run_id,
                attempt_id,
                run_type,
                trade_date,
                portfolio_daily_return,
                benchmark_return_daily,
                relative_return_daily,
                total_equity,
                benchmark_equity,
                cumulative_return,
                benchmark_cumulative_return,
                cash_weight,
                invested_weight,
                max_single_name_weight,
                top3_weight,
                portfolio_herfindahl_index,
                buy_notional_daily,
                sell_notional_daily,
                turnover_daily,
                rebalance_event_flag
            FROM backtest_daily_t
            ORDER BY trade_date
            """,
            backtest_daily_path,
        )
        return_sanity = con.execute(
            """
            SELECT
                MAX(ABS(portfolio_daily_return)) AS max_abs_portfolio_daily_return,
                MAX(ABS(benchmark_return_daily)) AS max_abs_benchmark_return_daily,
                MAX(ABS(relative_return_daily)) AS max_abs_relative_return_daily,
                MAX(ABS(cash_weight)) AS max_abs_cash_weight,
                MAX(ABS(invested_weight)) AS max_abs_invested_weight
            FROM backtest_daily_t
            """
        ).fetchone()
        if float(return_sanity[0] or 0.0) > 5.0 or float(return_sanity[1] or 0.0) > 5.0:
            raise ValueError(
                "Detected daily returns with absolute value > 5.0. This usually points to "
                "a decimal-vs-percent unit mismatch."
            )
        if float(return_sanity[3] or 0.0) > 1.5 or float(return_sanity[4] or 0.0) > 1.5:
            raise ValueError(
                "Detected weights far above 1.0. Fixed-test expects normalized 0-1 weights."
            )

        atomic_csv_copy(
            con,
            """
            WITH yearly AS (
                SELECT
                    SUBSTR(trade_date, 1, 4) AS calendar_year,
                    COUNT(*) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS effective_days,
                    EXP(SUM(LN(GREATEST(1.0 + portfolio_daily_return, 1e-12)))) - 1.0 AS strategy_return_year,
                    EXP(SUM(LN(GREATEST(1.0 + benchmark_return_daily, 1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL)) - 1.0 AS benchmark_return_year,
                    EXP(SUM(LN(GREATEST((1.0 + portfolio_daily_return) / NULLIF(1.0 + benchmark_return_daily, 0.0), 1e-12))) FILTER (WHERE benchmark_return_daily IS NOT NULL)) - 1.0 AS year_relative_return
                FROM backtest_daily_t
                GROUP BY 1
            )
            SELECT
                calendar_year,
                effective_days,
                strategy_return_year,
                benchmark_return_year,
                year_relative_return,
                year_relative_return > 0 AS positive_relative_year_flag
            FROM yearly
            ORDER BY calendar_year
            """,
            annual_return_table_path,
        )

        atomic_csv_copy(
            con,
            """
            WITH bucketed AS (
                SELECT
                    CASE
                        WHEN execution_delayed_realized_return < -0.20 THEN 'lt_-20%'
                        WHEN execution_delayed_realized_return < -0.10 THEN '-20%_-10%'
                        WHEN execution_delayed_realized_return < -0.05 THEN '-10%_-5%'
                        WHEN execution_delayed_realized_return < 0.00 THEN '-5%_0%'
                        WHEN execution_delayed_realized_return < 0.05 THEN '0%_5%'
                        WHEN execution_delayed_realized_return < 0.10 THEN '5%_10%'
                        WHEN execution_delayed_realized_return < 0.20 THEN '10%_20%'
                        ELSE 'ge_20%'
                    END AS return_bucket,
                    execution_delayed_realized_return
                FROM holdings_t
            )
            SELECT
                return_bucket,
                COUNT(*) AS holding_count,
                COUNT(*) * 1.0 / NULLIF((SELECT COUNT(*) FROM holdings_t), 0) AS holding_share,
                MIN(execution_delayed_realized_return) AS bucket_min_return,
                MAX(execution_delayed_realized_return) AS bucket_max_return,
                AVG(execution_delayed_realized_return) AS bucket_avg_return
            FROM bucketed
            GROUP BY 1
            ORDER BY
                CASE return_bucket
                    WHEN 'lt_-20%' THEN 1
                    WHEN '-20%_-10%' THEN 2
                    WHEN '-10%_-5%' THEN 3
                    WHEN '-5%_0%' THEN 4
                    WHEN '0%_5%' THEN 5
                    WHEN '5%_10%' THEN 6
                    WHEN '10%_20%' THEN 7
                    WHEN 'ge_20%' THEN 8
                    ELSE 99
                END
            """,
            holding_period_distribution_path,
        )

        backtest_rows = con.execute("SELECT COUNT(*) FROM backtest_daily_t").fetchone()[0]
        stats = con.execute(
            """
            WITH dd AS (
                SELECT
                    trade_date,
                    total_equity,
                    MAX(total_equity) OVER (
                        ORDER BY trade_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_peak,
                    portfolio_daily_return,
                    cash_weight,
                    invested_weight,
                    turnover_daily,
                    rebalance_event_flag
                FROM backtest_daily_t
            )
            SELECT
                COUNT(*) AS n_days,
                ANY_VALUE(total_equity) FILTER (
                    WHERE trade_date = (SELECT MAX(trade_date) FROM backtest_daily_t)
                ) AS final_equity,
                AVG(portfolio_daily_return) AS avg_daily_return,
                STDDEV_SAMP(portfolio_daily_return) AS daily_volatility,
                MIN((total_equity / NULLIF(running_peak, 0.0)) - 1.0) AS max_drawdown,
                AVG(cash_weight) AS avg_cash_weight,
                AVG(invested_weight) AS avg_invested_weight,
                AVG(turnover_daily) AS avg_turnover_daily,
                SUM(CASE WHEN rebalance_event_flag THEN 1 ELSE 0 END) AS rebalance_days
            FROM dd
            """
        ).fetchone()

        n_days = int(stats[0] or 0)
        final_equity = float(stats[1] or 1.0)
        total_return = final_equity - 1.0
        daily_vol = float(stats[3] or 0.0)
        annualized_return = math.pow(final_equity, 252.0 / n_days) - 1.0 if n_days > 0 and final_equity > 0 else None
        annualized_volatility = daily_vol * math.sqrt(252.0) if daily_vol is not None else None
        sharpe = (
            annualized_return / annualized_volatility
            if annualized_return is not None and annualized_volatility not in (None, 0.0)
            else None
        )
        relative_stats = con.execute(
            """
            SELECT
                COUNT(*) AS n_effective_days,
                EXP(SUM(LN(GREATEST((1.0 + portfolio_daily_return) / NULLIF(1.0 + benchmark_return_daily, 0.0), 1e-12)))) AS relative_nav_end,
                EXP(SUM(LN(GREATEST(1.0 + benchmark_return_daily, 1e-12)))) AS benchmark_nav_end,
                AVG(relative_return_daily) AS avg_relative_return_daily,
                STDDEV_SAMP(relative_return_daily) AS std_relative_return_daily,
                SUM(CASE WHEN relative_return_daily > 0 THEN 1 ELSE 0 END) AS positive_relative_days
            FROM backtest_daily_t
            WHERE benchmark_return_daily IS NOT NULL
            """
        ).fetchone()
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
        annual_table_rows = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_csv_auto({sql_path(annual_return_table_path)}, HEADER=TRUE)
            WHERE effective_days > 0
            """
        ).fetchone()[0]
        positive_relative_years = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_csv_auto({sql_path(annual_return_table_path)}, HEADER=TRUE)
            WHERE positive_relative_year_flag
            """
        ).fetchone()[0]

        run_state_audit = load_json(run_state_audit_path)
        primary_benchmark_meta = con.execute(
            """
            SELECT ANY_VALUE(benchmark_code), ANY_VALUE(benchmark_name), BOOL_OR(is_total_return)
            FROM primary_benchmark_t
            """
        ).fetchone()
        auxiliary_benchmark_meta = con.execute(
            """
            SELECT ANY_VALUE(benchmark_code), ANY_VALUE(benchmark_name), BOOL_OR(is_total_return)
            FROM auxiliary_benchmark_t
            """
        ).fetchone()
        metrics_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "run_type": load_json(run_state_manifest_path).get("run_type"),
            "generated_at": datetime.now().astimezone().isoformat(),
            "snapshot_id": run_input["snapshot_id"],
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "n_days": n_days,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "benchmark_total_return": benchmark_nav_end - 1.0 if n_effective_days > 0 else None,
            "annual_relative_return": annual_relative_return,
            "effective_relative_days": n_effective_days,
            "positive_relative_days": int(relative_stats[5] or 0),
            "relative_ir": relative_ir,
            "positive_test_years_count": int(positive_relative_years or 0),
            "effective_test_years_count": int(annual_table_rows or 0),
            "daily_volatility": daily_vol,
            "annualized_volatility": annualized_volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": float(stats[4] or 0.0),
            "avg_cash_weight": float(stats[5] or 0.0),
            "avg_invested_weight": float(stats[6] or 0.0),
            "avg_turnover_daily": float(stats[7] or 0.0),
            "rebalance_days": int(stats[8] or 0),
            "benchmark_status": {
                "primary_benchmark_code": primary_benchmark_meta[0],
                "primary_benchmark_name": primary_benchmark_meta[1],
                "primary_is_total_return": bool(primary_benchmark_meta[2]),
                "auxiliary_benchmark_code": auxiliary_benchmark_meta[0],
                "auxiliary_benchmark_name": auxiliary_benchmark_meta[1],
                "auxiliary_is_total_return": bool(auxiliary_benchmark_meta[2]),
                "relative_metrics_available": n_effective_days > 0,
                "fallback_triggered": False,
                "promotion_eligible_relative_metrics": bool(n_effective_days > 0 and primary_benchmark_meta[2]),
                "notes": "Primary and auxiliary benchmark series are both total-return series from the shared source."
            }
        }
        atomic_json_write(metrics_path, metrics_payload)

        trade_stats = con.execute(
            """
            SELECT
                COUNT(*) AS holding_rows,
                COUNT(DISTINCT instrument) AS unique_instruments,
                COUNT(DISTINCT signal_date) AS signal_dates_with_positions,
                AVG(exit_delay_days) AS avg_exit_delay_days,
                SUM(CASE WHEN exit_delay_days > 0 THEN 1 ELSE 0 END) AS delayed_exit_positions,
                SUM(CASE WHEN terminal_event_flag THEN 1 ELSE 0 END) AS terminal_event_positions,
                SUM(entry_fill_weight) AS total_entry_fill_weight
            FROM holdings_t
            """
        ).fetchone()
        turnover_stats = con.execute(
            """
            SELECT
                AVG(turnover_daily) AS avg_turnover_daily,
                MEDIAN(turnover_daily) AS median_turnover_daily,
                MAX(turnover_daily) AS max_turnover_daily,
                SUM(CASE WHEN rebalance_event_flag THEN 1 ELSE 0 END) AS rebalance_days
            FROM turnover_daily_t
            """
        ).fetchone()

        trade_stats_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "holdings_count": int(trade_stats[0] or 0),
            "unique_instruments": int(trade_stats[1] or 0),
            "signal_dates_with_positions": int(trade_stats[2] or 0),
            "avg_exit_delay_days": float(trade_stats[3] or 0.0),
            "delayed_exit_positions": int(trade_stats[4] or 0),
            "terminal_event_positions": int(trade_stats[5] or 0),
            "total_entry_fill_weight": float(trade_stats[6] or 0.0),
            "avg_turnover_daily": float(turnover_stats[0] or 0.0),
            "median_turnover_daily": float(turnover_stats[1] or 0.0),
            "max_turnover_daily": float(turnover_stats[2] or 0.0),
            "rebalance_days": int(turnover_stats[3] or 0),
            "run_state_summary_counts": run_state_audit.get("summary_counts", {}),
            "warnings": run_state_audit.get("warnings", []),
            "fatal_blockers": run_state_audit.get("fatal_blockers", []),
        }
        atomic_json_write(trade_stats_path, trade_stats_payload)

        topk_perturbations = []
        for perturbed_topk in (8, 12):
            con.execute(
                f"""
                CREATE OR REPLACE VIEW perturbation_positions_t AS
                SELECT
                    r.run_id,
                    r.attempt_id,
                    r.run_type,
                    r.snapshot_id,
                    r.instrument,
                    r.signal_date,
                    e.entry_date,
                    e.planned_exit_date,
                    p.actual_exit_date,
                    p.actual_sell_price,
                    p.exit_delay_days,
                    p.execution_delayed_realized_return,
                    CASE
                        WHEN e.entry_tradeable_shared_flag THEN (1.0 / {perturbed_topk}) * {cohort_fraction}
                        ELSE 0.0
                    END AS entry_fill_weight
                FROM ranking_state_t r
                INNER JOIN execution_state_t e
                    ON r.run_id = e.run_id
                   AND r.attempt_id = e.attempt_id
                   AND r.instrument = e.instrument
                   AND r.signal_date = e.signal_date
                INNER JOIN project_execution_panel_t p
                    ON r.snapshot_id = p.snapshot_id
                   AND r.instrument = p.instrument
                   AND r.signal_date = p.signal_date
                WHERE r.rank_position IS NOT NULL
                  AND r.rank_position <= {perturbed_topk}
                  AND e.entry_tradeable_shared_flag
                """
            )
            con.execute(
                """
                CREATE OR REPLACE VIEW perturbation_daily_returns_t AS
                SELECT
                    c.trade_date,
                    SUM(
                        pp.entry_fill_weight * CASE
                            WHEN c.trade_date = pp.entry_date THEN
                                CASE
                                    WHEN b.open IS NULL OR b.open = 0 OR b.close IS NULL THEN 0.0
                                    ELSE (b.close / b.open) - 1.0
                                END
                            WHEN c.trade_date < pp.actual_exit_date THEN
                                CASE
                                    WHEN b.pre_close IS NULL OR b.pre_close = 0 OR b.close IS NULL THEN 0.0
                                    ELSE (b.close / b.pre_close) - 1.0
                                END
                            WHEN c.trade_date = pp.actual_exit_date THEN
                                CASE
                                    WHEN b.pre_close IS NULL OR b.pre_close = 0 OR pp.actual_sell_price IS NULL THEN 0.0
                                    ELSE (pp.actual_sell_price / b.pre_close) - 1.0
                                END
                            ELSE 0.0
                        END
                    ) AS strategy_return_daily
                FROM perturbation_positions_t pp
                INNER JOIN calendar_t c
                    ON c.trade_date >= pp.entry_date
                   AND c.trade_date <= pp.actual_exit_date
                LEFT JOIN bars_t b
                    ON pp.instrument = b.instrument
                   AND c.trade_date = b.trade_date
                GROUP BY 1
                """
            )
            perturbation_stats = con.execute(
                f"""
                SELECT
                    COUNT(*) AS n_effective_days,
                    EXP(SUM(LN(GREATEST((1.0 + p.strategy_return_daily) / NULLIF(1.0 + b.daily_return, 0.0), 1e-12)))) AS relative_nav_end,
                    AVG(p.strategy_return_daily - b.daily_return) AS avg_relative_return_daily,
                    STDDEV_SAMP(p.strategy_return_daily - b.daily_return) AS std_relative_return_daily
                FROM perturbation_daily_returns_t p
                INNER JOIN primary_benchmark_t b
                    ON p.trade_date = b.trade_date
                WHERE b.daily_return IS NOT NULL
                """
            ).fetchone()
            pert_n = int(perturbation_stats[0] or 0)
            pert_relative_nav_end = float(perturbation_stats[1] or 1.0)
            pert_annual_relative_return = (
                math.pow(pert_relative_nav_end, 252.0 / pert_n) - 1.0
                if pert_n > 0 and pert_relative_nav_end > 0
                else None
            )
            pert_std = float(perturbation_stats[3] or 0.0)
            pert_ir = (
                float(perturbation_stats[2] or 0.0) / pert_std * math.sqrt(252.0)
                if pert_n > 1 and pert_std not in (0.0, None)
                else None
            )
            topk_perturbations.append(
                {
                    "topk": perturbed_topk,
                    "effective_relative_days": pert_n,
                    "annual_relative_return": pert_annual_relative_return,
                    "relative_ir": pert_ir,
                }
            )

        atomic_json_write(
            topk_perturbation_summary_path,
            {
                "fixed_test_run_id": fixed_test_run_id,
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "generated_at": datetime.now().astimezone().isoformat(),
                "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
                "research_round_id": run_state_audit.get("research_round_id"),
                "benchmark_code": primary_benchmark_meta[0],
                "benchmark_name": primary_benchmark_meta[1],
                "statistics_definition": "annual_relative_return follows framework appendix B.2/B.2B using effective benchmark-overlap days.",
                "perturbations": topk_perturbations,
            },
        )

        atomic_csv_copy(
            con,
            f"""
            WITH topk_unfilled AS (
                SELECT
                    r.signal_date,
                    CASE
                        WHEN t.is_suspended_t THEN 'SUSPENSION'
                        WHEN t.open_at_up_limit_t OR t.one_word_up_limit_t OR NOT COALESCE(t.buyable_at_open, FALSE) THEN 'LIMIT_UP_UNBUYABLE'
                        ELSE 'FILTERED_OUT'
                    END AS cash_reason,
                    COUNT(*) AS event_count
                FROM ranking_state_t r
                INNER JOIN execution_state_t e
                    ON r.run_id = e.run_id
                   AND r.attempt_id = e.attempt_id
                   AND r.instrument = e.instrument
                   AND r.signal_date = e.signal_date
                LEFT JOIN tradability_t t
                    ON r.snapshot_id = t.snapshot_id
                   AND r.instrument = t.instrument
                   AND e.entry_date = t.trade_date
                WHERE r.topk_frozen_D0
                  AND NOT e.entry_filled_D1
                GROUP BY 1, 2
            ),
            no_signal_cash AS (
                SELECT
                    signal_date,
                    'NO_SIGNAL' AS cash_reason,
                    GREATEST(10 - SUM(CASE WHEN topk_frozen_D0 THEN 1 ELSE 0 END), 0) AS event_count
                FROM ranking_state_t
                GROUP BY 1
                HAVING GREATEST(10 - SUM(CASE WHEN topk_frozen_D0 THEN 1 ELSE 0 END), 0) > 0
            ),
            unioned AS (
                SELECT signal_date, cash_reason, event_count FROM topk_unfilled
                UNION ALL
                SELECT signal_date, cash_reason, event_count FROM no_signal_cash
            ),
            summarized AS (
                SELECT
                    cash_reason,
                    SUM(event_count) AS event_count,
                    SUM(event_count) * ({cohort_fraction} / 10.0) AS cash_weight_total
                FROM unioned
                GROUP BY 1
            )
            SELECT
                cash_reason,
                event_count,
                cash_weight_total,
                cash_weight_total / NULLIF(SUM(cash_weight_total) OVER (), 0.0) AS cash_weight_share_of_total
            FROM summarized
            ORDER BY cash_weight_total DESC, cash_reason
            """,
            cash_source_explanation_path,
        )

        con.execute(
            """
            CREATE OR REPLACE VIEW low_liquidity_positions_t AS
            SELECT
                h.position_id,
                h.instrument,
                h.signal_date,
                h.entry_fill_weight,
                COALESCE(t.low_liquidity_flag_t, FALSE) AS low_liquidity_flag
            FROM holdings_t h
            LEFT JOIN tradability_t t
                ON h.snapshot_id = t.snapshot_id
               AND h.instrument = t.instrument
               AND h.signal_date = t.trade_date
            """
        )
        low_liq_stats = con.execute(
            """
            WITH contrib AS (
                SELECT
                    SUM(CASE WHEN l.low_liquidity_flag THEN p.pnl_weight_contribution ELSE 0.0 END) AS low_liquidity_contribution_total,
                    SUM(p.pnl_weight_contribution) AS strategy_contribution_total
                FROM position_daily_returns_t p
                INNER JOIN low_liquidity_positions_t l
                    ON p.position_id = l.position_id
            ),
            weights AS (
                SELECT
                    SUM(CASE WHEN low_liquidity_flag THEN entry_fill_weight ELSE 0.0 END) AS low_liquidity_weight_total,
                    SUM(entry_fill_weight) AS total_weight
                FROM low_liquidity_positions_t
            )
            SELECT
                (SELECT COUNT(*) FROM low_liquidity_positions_t WHERE low_liquidity_flag) AS low_liquidity_holding_count,
                (SELECT low_liquidity_weight_total FROM weights) AS low_liquidity_weight_total,
                (SELECT total_weight FROM weights) AS total_weight,
                (SELECT low_liquidity_contribution_total FROM contrib) AS low_liquidity_contribution_total,
                (SELECT strategy_contribution_total FROM contrib) AS strategy_contribution_total
            """
        ).fetchone()
        low_liquidity_weight_share = (
            float(low_liq_stats[1] or 0.0) / float(low_liq_stats[2] or 1.0)
            if float(low_liq_stats[2] or 0.0) != 0.0
            else 0.0
        )
        low_liquidity_contribution_share = (
            float(low_liq_stats[3] or 0.0) / float(low_liq_stats[4] or 1.0)
            if float(low_liq_stats[4] or 0.0) != 0.0
            else 0.0
        )
        low_liquidity_alpha_contribution_share = (
            float(low_liq_stats[3] or 0.0) / float(total_return or 1.0)
            if float(total_return or 0.0) != 0.0
            else 0.0
        )
        low_liquidity_exposure_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "low_liquidity_holding_count": int(low_liq_stats[0] or 0),
            "low_liquidity_weight_total": float(low_liq_stats[1] or 0.0),
            "low_liquidity_weight_share": low_liquidity_weight_share,
            "low_liquidity_contribution_total": float(low_liq_stats[3] or 0.0),
            "low_liquidity_contribution_share_of_strategy": low_liquidity_contribution_share,
            "low_liquidity_alpha_contribution_share": low_liquidity_alpha_contribution_share,
            "flag_high_low_liquidity_exposure": bool(
                low_liquidity_weight_share > 0.2 or abs(low_liquidity_alpha_contribution_share) > 0.5
            ),
        }
        low_liquidity_unit_warning = None
        if low_liquidity_weight_share > 0.95:
            low_liquidity_unit_warning = (
                "low_liquidity_weight_share > 0.95; verify low_liquidity_flag_t threshold "
                "and amount-unit assumptions before interpreting this as pure strategy behavior."
            )
            low_liquidity_exposure_payload["unit_sanity_warning"] = low_liquidity_unit_warning
        atomic_json_write(low_liquidity_exposure_summary_path, low_liquidity_exposure_payload)

        stress_open_bp = 20.0
        stress_close_bp = 20.0
        cost_stress_stats = con.execute(
            f"""
            WITH stressed AS (
                SELECT
                    trade_date,
                    portfolio_daily_return - (
                        buy_notional_daily * ({stress_open_bp} / 10000.0) +
                        sell_notional_daily * ({stress_close_bp} / 10000.0)
                    ) AS stressed_strategy_return_daily,
                    benchmark_return_daily
                FROM backtest_daily_t
            )
            SELECT
                COUNT(*) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS n_effective_days,
                EXP(
                    SUM(
                        LN(
                            GREATEST(
                                (1.0 + stressed_strategy_return_daily) / NULLIF(1.0 + benchmark_return_daily, 0.0),
                                1e-12
                            )
                        )
                    ) FILTER (WHERE benchmark_return_daily IS NOT NULL)
                ) AS relative_nav_end
            FROM stressed
            """
        ).fetchone()
        stress_days = int(cost_stress_stats[0] or 0)
        stress_relative_nav_end = float(cost_stress_stats[1] or 1.0)
        cost_stress_annual_relative_return = (
            math.pow(stress_relative_nav_end, 252.0 / stress_days) - 1.0
            if stress_days > 0 and stress_relative_nav_end > 0
            else None
        )
        atomic_json_write(
            cost_stress_summary_path,
            {
                "fixed_test_run_id": fixed_test_run_id,
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "generated_at": datetime.now().astimezone().isoformat(),
                "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
                "research_round_id": run_state_audit.get("research_round_id"),
                "stress_open_bp": stress_open_bp,
                "stress_close_bp": stress_close_bp,
                "effective_relative_days": stress_days,
                "annual_relative_return": cost_stress_annual_relative_return,
                "pass_cost_stress_relative_return_floor": bool(
                    cost_stress_annual_relative_return is not None and cost_stress_annual_relative_return >= 0.0
                ),
            },
        )

        attribution_stats = con.execute(
            """
            WITH attribution AS (
                SELECT
                    portfolio_daily_return,
                    benchmark_return_daily,
                    cash_weight,
                    CASE
                        WHEN benchmark_return_daily IS NULL THEN NULL
                        ELSE - cash_weight * benchmark_return_daily
                    END AS cash_drag_daily,
                    CASE
                        WHEN benchmark_return_daily IS NULL THEN NULL
                        ELSE portfolio_daily_return - ((1.0 - cash_weight) * benchmark_return_daily)
                    END AS selection_alpha_daily
                FROM backtest_daily_t
            )
            SELECT
                SUM(benchmark_return_daily) FILTER (WHERE benchmark_return_daily IS NOT NULL) AS benchmark_contribution_total,
                SUM(cash_drag_daily) FILTER (WHERE cash_drag_daily IS NOT NULL) AS cash_drag_total,
                SUM(selection_alpha_daily) FILTER (WHERE selection_alpha_daily IS NOT NULL) AS selection_alpha_total
            FROM attribution
            """
        ).fetchone()
        return_attribution_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "benchmark_contribution_total": float(attribution_stats[0] or 0.0),
            "cash_drag_total": float(attribution_stats[1] or 0.0),
            "selection_alpha_total": float(attribution_stats[2] or 0.0),
            "low_liquidity_contribution_total": float(low_liq_stats[3] or 0.0),
        }
        atomic_json_write(return_attribution_summary_path, return_attribution_payload)

        data_contract_summary_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "snapshot_id": run_input["snapshot_id"],
            "etl_code_hash": run_input["etl_code_hash"],
            "execution_logic_version": run_input["execution_logic_version"],
            "data_contract_version": run_input["data_contract_version"],
            "runtime_environment": run_input["runtime_environment"],
            "source_views": run_input["source_views"],
            "shared_source_degraded_flags": run_input.get("shared_source_degraded_flags", {}),
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "benchmark_status": metrics_payload["benchmark_status"],
        }
        atomic_json_write(data_contract_summary_path, data_contract_summary_payload)

        audit_summary_payload = {
            "fixed_test_run_id": fixed_test_run_id,
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "candidate_scheme_id": run_state_audit.get("candidate_scheme_id"),
            "research_round_id": run_state_audit.get("research_round_id"),
            "warnings": run_state_audit.get("warnings", []),
            "fatal_blockers": run_state_audit.get("fatal_blockers", []),
            "ranking_anomaly_rows": run_state_audit.get("summary_counts", {}).get("ranking_anomaly_rows"),
            "unfilled_topk_count": run_state_audit.get("summary_counts", {}).get("unfilled_topk_count"),
            "terminal_event_degraded_rows": run_state_audit.get("summary_counts", {}).get("terminal_event_degraded_rows"),
            "benchmark_fallback_triggered": metrics_payload["benchmark_status"]["fallback_triggered"],
            "low_liquidity_flag_high": low_liquidity_exposure_payload["flag_high_low_liquidity_exposure"],
            "topk_perturbation_pass": all(
                p["annual_relative_return"] is not None and p["annual_relative_return"] >= 0.0
                for p in topk_perturbations
            ),
            "cost_stress_pass": bool(
                cost_stress_annual_relative_return is not None and cost_stress_annual_relative_return >= 0.0
            ),
            "cost_stress_annual_relative_return": cost_stress_annual_relative_return,
            "exposure_driven_or_liquidity_driven": low_liquidity_exposure_payload["flag_high_low_liquidity_exposure"],
            "notes": [
                "Low-liquidity exposure flag uses a heuristic threshold on weight share and alpha contribution share.",
                "Audit summary is a near-formal scaffold and still excludes full exposure attribution.",
                "All fixed-test return fields use decimal-return convention unless explicitly labeled otherwise."
            ],
        }
        if low_liquidity_unit_warning is not None:
            audit_summary_payload["warnings"].append(low_liquidity_unit_warning)
        atomic_json_write(audit_summary_path, audit_summary_payload)
    finally:
        con.close()

    manifest_payload = {
        "fixed_test_run_id": fixed_test_run_id,
        "run_id": args.run_id,
        "attempt_id": attempt_id,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": {
            "holdings_csv": str(holdings_path),
            "portfolio_daily_summary_csv": str(summary_path),
            "turnover_daily_csv": str(turnover_path),
            "run_state_audit_json": str(run_state_audit_path),
            "run_state_attempt_manifest_json": str(run_state_manifest_path),
            "portfolio_artifacts_manifest_json": str(portfolio_manifest_path),
        },
        "outputs": {
            "backtest_daily_csv": str(backtest_daily_path),
            "metrics_json": str(metrics_path),
            "trade_statistics_summary_json": str(trade_stats_path),
            "annual_return_table_csv": str(annual_return_table_path),
            "holding_period_return_distribution_csv": str(holding_period_distribution_path),
            "topk_perturbation_summary_json": str(topk_perturbation_summary_path),
            "data_contract_summary_json": str(data_contract_summary_path),
            "audit_summary_json": str(audit_summary_path),
            "cash_source_explanation_csv": str(cash_source_explanation_path),
            "low_liquidity_exposure_summary_json": str(low_liquidity_exposure_summary_path),
            "cost_stress_summary_json": str(cost_stress_summary_path),
            "return_attribution_summary_json": str(return_attribution_summary_path),
        },
        "notes": [
            "Near-formal fixed-test skeleton.",
            "Benchmark-relative metrics, annual return table, holding-period distribution, TopK perturbation summary, and audit-side summaries are included.",
            "Daily PnL uses open-to-close on entry day, close-to-close on hold days, and actual sell price on exit day."
        ]
    }
    atomic_json_write(manifest_path, manifest_payload)


if __name__ == "__main__":
    main()
