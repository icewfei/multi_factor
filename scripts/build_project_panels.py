#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build project-side normalized panels from the shared parquet_duckdb warehouse.

Outputs:
- project_label_panel.parquet
- project_sample_panel.parquet
- project_execution_panel.parquet
- data_quality_audit.json

This script intentionally does not build run-state tables such as:
- ranking_state_daily
- execution_state_daily

Those remain project-owned downstream artifacts.

Expected runtime environment:
- /opt/anaconda3/envs/quant_trade
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
ARTIFACTS_DIR = ROOT / "artifacts" / "run_state"
HOLDING_PERIOD_OVERRIDE_BLOCKED_MESSAGE = (
    "当前 v1 审计阶段禁止使用 --holding-period-days，因为它会破坏 "
    "label/sample/execution panel 一致性。"
)


@dataclass(frozen=True)
class BuildContext:
    run_id: str
    snapshot_id: str
    source_db_path: Path
    output_dir: Path
    run_input_contract_path: Path
    run_input_contract: dict[str, Any]
    field_mapping: dict[str, Any]
    table_mapping: dict[str, Any]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to an object")
    return data


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def enforce_holding_period_days_guardrail(holding_period_days: int | None) -> None:
    if holding_period_days is not None:
        raise ValueError(HOLDING_PERIOD_OVERRIDE_BLOCKED_MESSAGE)


def build_context(run_id: str, output_dir: Path | None, run_input_contract_path: Path | None) -> BuildContext:
    resolved_contract_path = run_input_contract_path or (CONTRACTS_DIR / "run_input_contract.current.json")
    run_input = load_json(resolved_contract_path)
    field_mapping = load_yaml(CONTRACTS_DIR / "source_field_mapping.yaml")
    table_mapping = load_yaml(CONTRACTS_DIR / "source_table_mapping.yaml")

    snapshot_path = Path(run_input["source_root"]["snapshot_path"])
    source_db_path = snapshot_path / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    resolved_output_dir = output_dir or (ARTIFACTS_DIR / run_id)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    return BuildContext(
        run_id=run_id,
        snapshot_id=run_input["snapshot_id"],
        source_db_path=source_db_path,
        output_dir=resolved_output_dir,
        run_input_contract_path=resolved_contract_path,
        run_input_contract=run_input,
        field_mapping=field_mapping,
        table_mapping=table_mapping,
    )


def fetch_arrow_table(
    con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None
) -> pa.Table:
    return con.execute(sql, params or []).to_arrow_table()


def mapped_source_field(ctx: BuildContext, section: str, local_field: str) -> str:
    section_mapping = ctx.field_mapping.get(section)
    if not isinstance(section_mapping, dict) or local_field not in section_mapping:
        raise KeyError(f"Missing field mapping for {section}.{local_field}")
    source_field = section_mapping[local_field].get("source_field")
    if source_field in (None, "null"):
        raise KeyError(f"Field mapping for {section}.{local_field} does not provide a source_field")
    return str(source_field)


def mapped_select_expr(
    ctx: BuildContext,
    section: str,
    local_field: str,
    table_alias: str | None = None,
    output_alias: str | None = None,
) -> str:
    source_field = mapped_source_field(ctx, section, local_field)
    qualified = f"{table_alias}.{source_field}" if table_alias else source_field
    return f"{qualified} AS {output_alias or local_field}"


def build_project_label_panel(con: duckdb.DuckDBPyConnection, ctx: BuildContext) -> pa.Table:
    select_exprs = [
        mapped_select_expr(ctx, "common_keys", "snapshot_id"),
        mapped_select_expr(ctx, "common_keys", "instrument"),
        mapped_select_expr(ctx, "common_keys", "signal_date"),
        mapped_select_expr(ctx, "labels_daily", "entry_date"),
        mapped_select_expr(ctx, "labels_daily", "planned_exit_date"),
        mapped_select_expr(ctx, "labels_daily", "open_D1"),
        mapped_select_expr(ctx, "labels_daily", "close_D5"),
        mapped_select_expr(ctx, "labels_daily", "adj_factor_D1"),
        mapped_select_expr(ctx, "labels_daily", "adj_factor_D5"),
        mapped_select_expr(ctx, "labels_daily", "adj_open_base_D1"),
        mapped_select_expr(ctx, "labels_daily", "adj_close_base_D5"),
        mapped_select_expr(ctx, "labels_daily", "label_defined"),
        mapped_select_expr(ctx, "labels_daily", "label_raw", output_alias="label_5d_next_open_close_raw"),
        mapped_select_expr(ctx, "labels_daily", "label", output_alias="label_5d_next_open_close"),
        mapped_select_expr(ctx, "labels_daily", "label_masked_reason"),
    ]
    sql = """
        SELECT
            {select_exprs}
        FROM serving.vw_labels_daily
        WHERE snapshot_id = ?
    """
    return fetch_arrow_table(con, sql.format(select_exprs=",\n            ".join(select_exprs)), [ctx.snapshot_id])


def build_project_sample_panel(con: duckdb.DuckDBPyConnection, ctx: BuildContext) -> pa.Table:
    select_exprs = [
        mapped_select_expr(ctx, "common_keys", "snapshot_id"),
        mapped_select_expr(ctx, "common_keys", "instrument"),
        mapped_select_expr(ctx, "common_keys", "signal_date"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "entry_date"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "planned_exit_date"),
        mapped_select_expr(ctx, "labels_daily", "label_defined"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "entry_tradeable"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "planned_exit_tradeable"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "actually_exited"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "feature_ready_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "price_window_ready_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "core_features_complete_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "pit_state_complete_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "base_universe_member_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "rules_filter_pass_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "state_filter_pass_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "universe_eligible_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "signal_emittable"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "ranking_eligible_D0"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "train_mask_v1"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "eval_mask_v1"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "train_mask_conservative"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "eval_mask_conservative"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "mask_reason_json"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "entry_filled_D1", output_alias="entry_filled_D1_shared_proxy"),
        mapped_select_expr(ctx, "sample_eligibility_daily", "backtest_executable", output_alias="backtest_executable_shared_proxy"),
    ]
    sql = """
        SELECT
            {select_exprs}
        FROM serving.vw_sample_eligibility_daily
        WHERE snapshot_id = ?
    """
    return fetch_arrow_table(con, sql.format(select_exprs=",\n            ".join(select_exprs)), [ctx.snapshot_id])


def build_project_execution_panel(con: duckdb.DuckDBPyConnection, ctx: BuildContext) -> pa.Table:
    e_signal_date = mapped_source_field(ctx, "common_keys", "signal_date")
    e_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    e_entry_date = mapped_source_field(ctx, "execution_path_daily", "entry_date")
    e_planned_exit_date = mapped_source_field(ctx, "execution_path_daily", "planned_exit_date")
    e_terminal_event_type = mapped_source_field(ctx, "execution_path_daily", "terminal_event_type")
    e_terminal_event_date = mapped_source_field(ctx, "execution_path_daily", "terminal_event_date")
    t_terminal_event_type = mapped_source_field(ctx, "terminal_event_daily", "terminal_event_type")
    t_terminal_event_date = mapped_source_field(ctx, "terminal_event_daily", "terminal_event_date")

    planned_exit_expr = f"e.{e_planned_exit_date} AS planned_exit_date"

    select_exprs = [
        mapped_select_expr(ctx, "common_keys", "snapshot_id", table_alias="e"),
        mapped_select_expr(ctx, "common_keys", "instrument", table_alias="e"),
        f"e.{e_signal_date} AS signal_date",
        f"e.{e_entry_date} AS entry_date",
        planned_exit_expr,
        mapped_select_expr(ctx, "execution_path_daily", "actual_exit_date", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "actual_exit_event_type", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "actual_exit_price_field", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "actual_sell_price", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "exit_delay_days", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "execution_path_status", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "execution_delayed_realized_return", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "terminal_event_flag", table_alias="e"),
        f"COALESCE(e.{e_terminal_event_type}, t.{t_terminal_event_type}) AS terminal_event_type",
        f"COALESCE(e.{e_terminal_event_date}, t.{t_terminal_event_date}) AS terminal_event_date",
        mapped_select_expr(ctx, "execution_path_daily", "terminal_exit_pricing_method", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "terminal_exit_approximation_flag", table_alias="e"),
        mapped_select_expr(ctx, "execution_path_daily", "terminal_exit_conservative_flag", table_alias="e"),
    ]
    sql = """
        SELECT
            {select_exprs}
        FROM serving.vw_execution_path_daily e
        LEFT JOIN serving.vw_terminal_event_daily t
            ON e.{e_instrument} = t.{t_instrument}
           AND e.{e_terminal_event_date} = t.{t_terminal_event_date}
        WHERE e.snapshot_id = ?
    """
    return fetch_arrow_table(
        con,
        sql.format(
            select_exprs=",\n            ".join(select_exprs),
            e_instrument=e_instrument,
            t_instrument=mapped_source_field(ctx, "common_keys", "instrument"),
            e_terminal_event_date=e_terminal_event_date,
            t_terminal_event_date=t_terminal_event_date,
        ),
        [ctx.snapshot_id],
    )


def scalar_count(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> int:
    value = con.execute(sql, params or []).fetchone()[0]
    return int(value or 0)


def build_data_quality_audit(
    con: duckdb.DuckDBPyConnection,
    ctx: BuildContext,
    label_panel: pa.Table,
    sample_panel: pa.Table,
    execution_panel: pa.Table,
) -> dict[str, Any]:
    shared_degraded_flags = dict(ctx.run_input_contract.get("shared_source_degraded_flags", {}))

    summary_counts = {
        "project_label_panel_rows": label_panel.num_rows,
        "project_sample_panel_rows": sample_panel.num_rows,
        "project_execution_panel_rows": execution_panel.num_rows,
        "labels_masked_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_labels_daily
            WHERE snapshot_id = ?
              AND label_masked_reason IS NOT NULL
            """,
            [ctx.snapshot_id],
        ),
        "tradability_degraded_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_tradability_daily
            WHERE snapshot_id = ?
              AND tradability_degraded_flag
            """,
            [ctx.snapshot_id],
        ),
        "terminal_event_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_terminal_event_daily
            WHERE snapshot_id = ?
            """,
            [ctx.snapshot_id],
        ),
        "terminal_event_degraded_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_terminal_event_daily
            WHERE snapshot_id = ?
              AND contract_degraded_flag
            """,
            [ctx.snapshot_id],
        ),
        "terminal_event_flagged_rows_in_execution": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_execution_path_daily
            WHERE snapshot_id = ?
              AND terminal_event_flag
            """,
            [ctx.snapshot_id],
        ),
        "execution_unresolved_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_execution_path_daily
            WHERE snapshot_id = ?
              AND execution_path_status IN ('terminal_event_unpriced', 'exit_unresolved', 'calendar_insufficient')
            """,
            [ctx.snapshot_id],
        ),
        "sample_masked_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM serving.vw_sample_eligibility_daily
            WHERE snapshot_id = ?
              AND (NOT train_mask_v1 OR NOT eval_mask_v1)
            """,
            [ctx.snapshot_id],
        ),
    }

    warnings: list[str] = []
    fatal_blockers: list[str] = []

    if summary_counts["project_label_panel_rows"] == 0:
        fatal_blockers.append("project_label_panel_rows = 0")
    if summary_counts["project_sample_panel_rows"] == 0:
        fatal_blockers.append("project_sample_panel_rows = 0")
    if summary_counts["project_execution_panel_rows"] == 0:
        fatal_blockers.append("project_execution_panel_rows = 0")
    if summary_counts["terminal_event_degraded_rows"] > 0:
        warnings.append("terminal_event_daily is present but partially degraded in the shared source.")
    if summary_counts["tradability_degraded_rows"] > 0:
        warnings.append("tradability_daily contains degraded rows; downstream research must audit these rows.")
    if summary_counts["execution_unresolved_rows"] > 0:
        warnings.append("execution_path_daily contains unresolved or unpriced rows.")

    return {
        "run_id": ctx.run_id,
        "snapshot_id": ctx.snapshot_id,
        "run_input_contract_path": str(ctx.run_input_contract_path),
        "generated_at": utc_now_iso(),
        "field_mapping_version": ctx.field_mapping["version"],
        "shared_source_degraded_flags": shared_degraded_flags,
        "summary_counts": summary_counts,
        "fatal_blockers": fatal_blockers,
        "warnings": warnings,
        "source_views": ctx.run_input_contract["source_views"],
        "notes": [
            "This audit summarizes project-side panel assembly quality only.",
            "Run-state fields such as topk_frozen_D0 and execution_attempt_D1 remain downstream-owned.",
        ],
    }


def write_parquet(table: pa.Table, path: Path) -> None:
    pq.write_table(table, path)


def write_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build project-side normalized panels from the shared data source."
    )
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit output directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--run-input-contract",
        default=None,
        help="Optional explicit run input contract JSON path. Defaults to contracts/run_input_contract.current.json",
    )
    parser.add_argument(
        "--holding-period-days",
        type=int,
        default=None,
        help=(
            "Audit-stage guardrail parameter. Any explicit value is rejected because "
            "holding-period overrides would break panel consistency."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    enforce_holding_period_days_guardrail(args.holding_period_days)
    ctx = build_context(
        args.run_id,
        Path(args.output_dir) if args.output_dir else None,
        Path(args.run_input_contract) if args.run_input_contract else None,
    )

    with duckdb.connect(str(ctx.source_db_path), read_only=True) as con:
        label_panel = build_project_label_panel(con, ctx)
        sample_panel = build_project_sample_panel(con, ctx)
        execution_panel = build_project_execution_panel(con, ctx)
        audit = build_data_quality_audit(con, ctx, label_panel, sample_panel, execution_panel)

    write_parquet(label_panel, ctx.output_dir / "project_label_panel.parquet")
    write_parquet(sample_panel, ctx.output_dir / "project_sample_panel.parquet")
    write_parquet(execution_panel, ctx.output_dir / "project_execution_panel.parquet")
    write_json(audit, ctx.output_dir / "data_quality_audit.json")


if __name__ == "__main__":
    main()
