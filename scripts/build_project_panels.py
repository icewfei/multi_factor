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
POST_DELIST_TERMINAL_EVENT_BRIDGE_PRICING_METHOD = "terminal_event_bridge_required"


@dataclass(frozen=True)
class BuildContext:
    run_id: str
    snapshot_id: str
    source_db_path: Path
    output_dir: Path
    run_input_contract_path: Path
    repaired_terminal_event_candidate_path: Path | None
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


def build_context(
    run_id: str,
    output_dir: Path | None,
    run_input_contract_path: Path | None,
    repaired_terminal_event_candidate_path: Path | None = None,
) -> BuildContext:
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
        repaired_terminal_event_candidate_path=repaired_terminal_event_candidate_path,
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


def load_repaired_terminal_event_candidate_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = load_json(path)
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError(f"repaired_terminal_event_candidate rows must be an array: {path}")
    return [dict(row) for row in rows]


def register_repaired_terminal_event_candidate(
    con: duckdb.DuckDBPyConnection,
    path: Path | None,
) -> None:
    rows = load_repaired_terminal_event_candidate_rows(path)
    if rows:
        table = pa.Table.from_pylist(rows)
    else:
        table = pa.table(
            {
                "snapshot_id": pa.array([], type=pa.string()),
                "instrument": pa.array([], type=pa.string()),
                "signal_date": pa.array([], type=pa.string()),
                "entry_date": pa.array([], type=pa.string()),
                "planned_exit_date": pa.array([], type=pa.string()),
                "terminal_event_date": pa.array([], type=pa.string()),
                "terminal_event_type": pa.array([], type=pa.string()),
                "approval_origin_case": pa.array([], type=pa.string()),
                "approval_evidence_case": pa.array([], type=pa.string()),
                "candidate_target_state": pa.array([], type=pa.string()),
                "approved_terminal_pricing_path": pa.array([], type=pa.string()),
                "candidate_pricing_date": pa.array([], type=pa.string()),
                "candidate_last_tradable_close": pa.array([], type=pa.float64()),
                "candidate_adj_factor": pa.array([], type=pa.float64()),
                "candidate_volume": pa.array([], type=pa.float64()),
                "pricing_policy_version": pa.array([], type=pa.string()),
                "terminal_event_source_degraded_flag": pa.array([], type=pa.bool_()),
                "terminal_exit_approximation_flag": pa.array([], type=pa.bool_()),
                "source_repair_flag": pa.array([], type=pa.bool_()),
                "terminal_event_bridge_required_flag": pa.array([], type=pa.bool_()),
            }
        )
    con.register("repaired_terminal_event_candidate_t", table)


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
    register_repaired_terminal_event_candidate(con, ctx.repaired_terminal_event_candidate_path)

    e_snapshot_id = mapped_source_field(ctx, "common_keys", "snapshot_id")
    e_signal_date = mapped_source_field(ctx, "common_keys", "signal_date")
    e_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    e_entry_date = mapped_source_field(ctx, "execution_path_daily", "entry_date")
    e_planned_exit_date = mapped_source_field(ctx, "execution_path_daily", "planned_exit_date")
    e_actual_exit_date = mapped_source_field(ctx, "execution_path_daily", "actual_exit_date")
    e_actual_exit_event_type = mapped_source_field(ctx, "execution_path_daily", "actual_exit_event_type")
    e_actual_exit_price_field = mapped_source_field(ctx, "execution_path_daily", "actual_exit_price_field")
    e_actual_sell_price = mapped_source_field(ctx, "execution_path_daily", "actual_sell_price")
    e_exit_delay_days = mapped_source_field(ctx, "execution_path_daily", "exit_delay_days")
    e_execution_path_status = mapped_source_field(ctx, "execution_path_daily", "execution_path_status")
    e_execution_delayed_realized_return = mapped_source_field(
        ctx, "execution_path_daily", "execution_delayed_realized_return"
    )
    e_terminal_event_flag = mapped_source_field(ctx, "execution_path_daily", "terminal_event_flag")
    e_terminal_event_type = mapped_source_field(ctx, "execution_path_daily", "terminal_event_type")
    e_terminal_event_date = mapped_source_field(ctx, "execution_path_daily", "terminal_event_date")
    e_terminal_exit_pricing_method = mapped_source_field(ctx, "execution_path_daily", "terminal_exit_pricing_method")
    e_terminal_exit_approximation_flag = mapped_source_field(
        ctx, "execution_path_daily", "terminal_exit_approximation_flag"
    )
    e_terminal_exit_conservative_flag = mapped_source_field(
        ctx, "execution_path_daily", "terminal_exit_conservative_flag"
    )
    t_snapshot_id = mapped_source_field(ctx, "common_keys", "snapshot_id")
    t_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    t_trade_date = mapped_source_field(ctx, "common_keys", "signal_date")
    t_terminal_event_type = mapped_source_field(ctx, "terminal_event_daily", "terminal_event_type")
    t_terminal_event_date = mapped_source_field(ctx, "terminal_event_daily", "terminal_event_date")
    t_last_tradable_date = mapped_source_field(ctx, "terminal_event_daily", "last_tradable_date")
    tr_snapshot_id = mapped_source_field(ctx, "common_keys", "snapshot_id")
    tr_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    tr_trade_date = mapped_source_field(ctx, "common_keys", "signal_date")
    b_snapshot_id = mapped_source_field(ctx, "common_keys", "snapshot_id")
    b_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    b_trade_date = mapped_source_field(ctx, "common_keys", "signal_date")
    l_snapshot_id = mapped_source_field(ctx, "common_keys", "snapshot_id")
    l_instrument = mapped_source_field(ctx, "common_keys", "instrument")
    l_signal_date = mapped_source_field(ctx, "common_keys", "signal_date")
    l_adj_open_base_D1 = mapped_source_field(ctx, "labels_daily", "adj_open_base_D1")

    planned_exit_expr = f"e.{e_planned_exit_date} AS planned_exit_date"
    candidate_apply_expr = (
        "CASE "
        "WHEN rc.candidate_target_state = 'repaired_terminal_event_candidate' "
        " AND rc.approved_terminal_pricing_path = 'terminal_priced_last_tradable_close' "
        f" AND l.{l_adj_open_base_D1} IS NOT NULL "
        f" AND l.{l_adj_open_base_D1} > 0 "
        " AND rc.candidate_pricing_date IS NOT NULL "
        " AND rc.candidate_last_tradable_close IS NOT NULL "
        " AND rc.candidate_adj_factor IS NOT NULL "
        "THEN TRUE ELSE FALSE END"
    )
    actual_exit_date_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN rc.candidate_pricing_date "
        f"ELSE e.{e_actual_exit_date} END AS actual_exit_date"
    )
    actual_exit_event_type_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN 'TERMINAL_LAST_CLOSE' "
        f"ELSE e.{e_actual_exit_event_type} END AS actual_exit_event_type"
    )
    actual_exit_price_field_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN 'close' "
        f"ELSE e.{e_actual_exit_price_field} END AS actual_exit_price_field"
    )
    actual_sell_price_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN rc.candidate_last_tradable_close "
        f"ELSE e.{e_actual_sell_price} END AS actual_sell_price"
    )
    exit_delay_days_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN candidate_exit_offset.exit_trading_day_offset "
        f"ELSE e.{e_exit_delay_days} END AS exit_delay_days"
    )
    bridge_terminal_event_flag_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN TRUE "
        "WHEN bridge.bridge_to_terminal_event_unpriced THEN TRUE "
        f"ELSE e.{e_terminal_event_flag} END AS terminal_event_flag"
    )
    bridge_terminal_event_type_expr = (
        "COALESCE("
        f"CASE WHEN {candidate_apply_expr} THEN rc.terminal_event_type ELSE NULL END, "
        f"e.{e_terminal_event_type}, "
        f"t.{t_terminal_event_type}, "
        "CASE "
        "WHEN bridge.bridge_to_terminal_event_unpriced THEN bridge.bridge_terminal_event_type "
        "ELSE NULL "
        "END"
        ") "
        "AS terminal_event_type"
    )
    bridge_terminal_event_date_expr = (
        "COALESCE("
        f"CASE WHEN {candidate_apply_expr} THEN rc.terminal_event_date ELSE NULL END, "
        f"e.{e_terminal_event_date}, "
        f"t.{t_terminal_event_date}, "
        "CASE "
        "WHEN bridge.bridge_to_terminal_event_unpriced THEN bridge.bridge_terminal_event_date "
        "ELSE NULL "
        "END"
        ") "
        "AS terminal_event_date"
    )
    bridge_execution_path_status_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN 'terminal_priced_last_tradable_close' "
        "WHEN bridge.bridge_to_terminal_event_unpriced THEN 'terminal_event_unpriced' "
        f"ELSE e.{e_execution_path_status} END AS execution_path_status"
    )
    bridge_terminal_exit_pricing_method_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN 'last_tradable_close' "
        "WHEN bridge.bridge_to_terminal_event_unpriced "
        f"AND e.{e_terminal_exit_pricing_method} IS NULL THEN '{POST_DELIST_TERMINAL_EVENT_BRIDGE_PRICING_METHOD}' "
        f"ELSE e.{e_terminal_exit_pricing_method} END AS terminal_exit_pricing_method"
    )
    pricing_policy_version_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN rc.pricing_policy_version "
        "ELSE NULL END AS pricing_policy_version"
    )
    source_repair_flag_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN rc.source_repair_flag "
        "ELSE NULL END AS source_repair_flag"
    )
    execution_delayed_realized_return_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN "
        f"((rc.candidate_last_tradable_close * rc.candidate_adj_factor) / l.{l_adj_open_base_D1}) - 1.0 "
        f"ELSE e.{e_execution_delayed_realized_return} END AS execution_delayed_realized_return"
    )
    terminal_exit_approximation_flag_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN rc.terminal_exit_approximation_flag "
        f"ELSE e.{e_terminal_exit_approximation_flag} END AS terminal_exit_approximation_flag"
    )
    terminal_exit_conservative_flag_expr = (
        "CASE "
        f"WHEN {candidate_apply_expr} THEN FALSE "
        f"ELSE e.{e_terminal_exit_conservative_flag} END AS terminal_exit_conservative_flag"
    )

    select_exprs = [
        mapped_select_expr(ctx, "common_keys", "snapshot_id", table_alias="e"),
        mapped_select_expr(ctx, "common_keys", "instrument", table_alias="e"),
        f"e.{e_signal_date} AS signal_date",
        f"e.{e_entry_date} AS entry_date",
        planned_exit_expr,
        actual_exit_date_expr,
        actual_exit_event_type_expr,
        actual_exit_price_field_expr,
        actual_sell_price_expr,
        exit_delay_days_expr,
        bridge_execution_path_status_expr,
        execution_delayed_realized_return_expr,
        bridge_terminal_event_flag_expr,
        bridge_terminal_event_type_expr,
        bridge_terminal_event_date_expr,
        bridge_terminal_exit_pricing_method_expr,
        pricing_policy_version_expr,
        source_repair_flag_expr,
        terminal_exit_approximation_flag_expr,
        terminal_exit_conservative_flag_expr,
    ]
    sql = """
        WITH bridge_candidates AS (
            SELECT
                e.{e_snapshot_id} AS snapshot_id,
                e.{e_instrument} AS instrument,
                e.{e_signal_date} AS signal_date,
                bridge_event.bridge_terminal_event_type,
                bridge_event.bridge_terminal_event_date,
                post_calendar.post_calendar_days,
                post_tradability.post_planned_exit_tradability_rows,
                post_bars.post_planned_exit_bars_rows,
                CASE
                    WHEN bridge_event.bridge_terminal_event_date IS NOT NULL
                     AND post_calendar.post_calendar_days > 0
                     AND post_tradability.post_planned_exit_tradability_rows = 0
                     AND post_bars.post_planned_exit_bars_rows = 0
                    THEN TRUE
                    ELSE FALSE
                END AS bridge_to_terminal_event_unpriced
            FROM serving.vw_execution_path_daily e
            LEFT JOIN LATERAL (
                SELECT
                    t.{t_terminal_event_type} AS bridge_terminal_event_type,
                    t.{t_terminal_event_date} AS bridge_terminal_event_date
                FROM serving.vw_terminal_event_daily t
                WHERE t.{t_snapshot_id} = e.{e_snapshot_id}
                  AND t.{t_instrument} = e.{e_instrument}
                  AND t.{t_terminal_event_type} = 'delist'
                  AND t.{t_terminal_event_date} >= e.{e_signal_date}
                  AND t.{t_terminal_event_date} <= e.{e_planned_exit_date}
                  AND t.{t_last_tradable_date} IS NOT NULL
                  AND t.{t_last_tradable_date} < e.{e_planned_exit_date}
                ORDER BY t.{t_terminal_event_date} DESC
                LIMIT 1
            ) bridge_event ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS post_calendar_days
                FROM serving.vw_calendar cal
                WHERE cal.trade_date > e.{e_planned_exit_date}
            ) post_calendar ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS post_planned_exit_tradability_rows
                FROM serving.vw_tradability_daily tr
                WHERE tr.{tr_snapshot_id} = e.{e_snapshot_id}
                  AND tr.{tr_instrument} = e.{e_instrument}
                  AND tr.{tr_trade_date} > e.{e_planned_exit_date}
            ) post_tradability ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS post_planned_exit_bars_rows
                FROM serving.vw_bars_daily b
                WHERE b.{b_snapshot_id} = e.{e_snapshot_id}
                  AND b.{b_instrument} = e.{e_instrument}
                  AND b.{b_trade_date} > e.{e_planned_exit_date}
            ) post_bars ON TRUE
            WHERE e.{e_snapshot_id} = ?
              AND e.{e_execution_path_status} = 'exit_unresolved'
              AND e.{e_actual_exit_date} IS NULL
              AND e.{e_actual_sell_price} IS NULL
        )
        SELECT
            {select_exprs}
        FROM serving.vw_execution_path_daily e
        LEFT JOIN serving.vw_terminal_event_daily t
            ON e.{e_snapshot_id} = t.{t_snapshot_id}
           AND e.{e_instrument} = t.{t_instrument}
           AND e.{e_terminal_event_date} = t.{t_terminal_event_date}
        LEFT JOIN repaired_terminal_event_candidate_t rc
            ON e.{e_snapshot_id} = rc.snapshot_id
           AND e.{e_instrument} = rc.instrument
           AND e.{e_signal_date} = rc.signal_date
        LEFT JOIN serving.vw_labels_daily l
            ON e.{e_snapshot_id} = l.{l_snapshot_id}
           AND e.{e_instrument} = l.{l_instrument}
           AND e.{e_signal_date} = l.{l_signal_date}
        LEFT JOIN bridge_candidates bridge
            ON e.{e_snapshot_id} = bridge.snapshot_id
           AND e.{e_instrument} = bridge.instrument
           AND e.{e_signal_date} = bridge.signal_date
        LEFT JOIN LATERAL (
            SELECT
                CASE
                    WHEN rc.candidate_pricing_date IS NULL OR e.{e_planned_exit_date} IS NULL THEN NULL
                    WHEN rc.candidate_pricing_date = e.{e_planned_exit_date} THEN 0
                    WHEN rc.candidate_pricing_date > e.{e_planned_exit_date} THEN (
                        SELECT COUNT(*) - 1
                        FROM serving.vw_calendar cal
                        WHERE cal.trade_date >= e.{e_planned_exit_date}
                          AND cal.trade_date <= rc.candidate_pricing_date
                    )
                    ELSE -(
                        SELECT COUNT(*) - 1
                        FROM serving.vw_calendar cal
                        WHERE cal.trade_date >= rc.candidate_pricing_date
                          AND cal.trade_date <= e.{e_planned_exit_date}
                    )
                END AS exit_trading_day_offset
        ) candidate_exit_offset ON TRUE
        WHERE e.snapshot_id = ?
    """
    return fetch_arrow_table(
        con,
        sql.format(
            select_exprs=",\n            ".join(select_exprs),
            e_snapshot_id=e_snapshot_id,
            e_instrument=e_instrument,
            e_signal_date=e_signal_date,
            e_planned_exit_date=e_planned_exit_date,
            e_actual_exit_date=e_actual_exit_date,
            e_actual_sell_price=e_actual_sell_price,
            e_execution_path_status=e_execution_path_status,
            e_terminal_event_flag=e_terminal_event_flag,
            e_terminal_exit_pricing_method=e_terminal_exit_pricing_method,
            t_snapshot_id=t_snapshot_id,
            t_instrument=t_instrument,
            t_trade_date=t_trade_date,
            e_terminal_event_date=e_terminal_event_date,
            t_terminal_event_type=t_terminal_event_type,
            t_terminal_event_date=t_terminal_event_date,
            t_last_tradable_date=t_last_tradable_date,
            tr_snapshot_id=tr_snapshot_id,
            tr_instrument=tr_instrument,
                tr_trade_date=tr_trade_date,
                b_snapshot_id=b_snapshot_id,
                b_instrument=b_instrument,
                b_trade_date=b_trade_date,
                l_snapshot_id=l_snapshot_id,
                l_instrument=l_instrument,
                l_signal_date=l_signal_date,
            ),
            [ctx.snapshot_id, ctx.snapshot_id],
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
    con.register("project_execution_panel_audit_t", execution_panel)

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
        "project_execution_unresolved_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM project_execution_panel_audit_t
            WHERE execution_path_status IN ('terminal_event_unpriced', 'exit_unresolved', 'calendar_insufficient')
               OR actual_exit_date IS NULL
               OR actual_sell_price IS NULL
               OR execution_delayed_realized_return IS NULL
            """,
        ),
        "project_execution_terminal_priced_last_tradable_close_rows": scalar_count(
            con,
            """
            SELECT COUNT(*)
            FROM project_execution_panel_audit_t
            WHERE execution_path_status = 'terminal_priced_last_tradable_close'
            """,
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
    if summary_counts["project_execution_unresolved_rows"] > 0:
        warnings.append("project_execution_panel still contains unresolved or incomplete actual exit rows.")

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
        "--repaired-terminal-event-candidate",
        default=None,
        help=(
            "Optional repaired_terminal_event_candidate JSON path. "
            "When provided, build_project_panels may emit upstream terminal_priced_last_tradable_close "
            "rows with complete actual exit fields."
        ),
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
        Path(args.repaired_terminal_event_candidate) if args.repaired_terminal_event_candidate else None,
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
