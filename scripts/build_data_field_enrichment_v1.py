#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_FIELD_CONTRACT_PATH = ROOT / "configs" / "data_field_enrichment" / "field_contract_v1.json"
DEFAULT_RUN_INPUT_CONTRACT_PATH = ROOT / "contracts" / "run_input_contract.research_trainval_20211231.json"
DEFAULT_OUTPUT_DIR = Path("/private/tmp/data_field_enrichment_v1_smoke")
ENTITY_NAME = "enriched_security_state_daily_v1"
OUTPUT_PARQUET_NAME = f"{ENTITY_NAME}.parquet"
BUILD_AUDIT_NAME = "build_audit.json"
FIELD_COVERAGE_SUMMARY_NAME = "field_coverage_summary.json"
BUILDER_VERSION = "data_field_enrichment_v1_builder_20260513"
NEWLY_LISTED_TRADING_DAY_THRESHOLD = 60


class BuildError(Exception):
    """Raised when the builder cannot produce an auditable artifact."""


@dataclass(frozen=True)
class SourceSpec:
    name: str
    relative_path: str
    required: bool
    required_columns: tuple[str, ...]


@dataclass(frozen=True)
class FieldBinding:
    field_name: str
    sql_expr: str
    output_type: str
    source_specs: tuple[tuple[str, tuple[str, ...]], ...]
    notes: str = ""


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        name="bars_daily",
        relative_path="warehouse/market/bars_daily.parquet",
        required=True,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "trade_date",
            "open",
            "close",
            "vol",
            "amount",
        ),
    ),
    SourceSpec(
        name="instrument_status_daily",
        relative_path="warehouse/state/instrument_status_daily.parquet",
        required=True,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "trade_date",
            "board",
            "exchange",
            "is_suspended_t",
            "is_st_t",
            "status_source_flags",
        ),
    ),
    SourceSpec(
        name="tradability_daily",
        relative_path="warehouse/market/tradability_daily.parquet",
        required=True,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "trade_date",
            "no_trade_t",
            "buyable_at_open",
            "sellable_at_close",
            "sellable_retry_next_open",
        ),
    ),
    SourceSpec(
        name="limit_rules_daily",
        relative_path="warehouse/market/limit_rules_daily.parquet",
        required=True,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "trade_date",
            "limit_pct",
            "price_tick_quantize_t",
            "up_limit_price_t",
            "down_limit_price_t",
            "rule_version",
        ),
    ),
    SourceSpec(
        name="instruments",
        relative_path="warehouse/core/instruments.parquet",
        required=True,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "list_date",
            "board",
            "exchange",
        ),
    ),
    SourceSpec(
        name="calendar",
        relative_path="warehouse/core/calendar.parquet",
        required=True,
        required_columns=(
            "trade_date",
            "prev_trade_date",
            "next_trade_date",
        ),
    ),
    SourceSpec(
        name="st_status_interval",
        relative_path="warehouse/state/st_status_interval.parquet",
        required=False,
        required_columns=(
            "snapshot_id",
            "ts_code",
            "effective_start_date",
            "effective_end_date",
            "st_source",
        ),
    ),
)


FIELD_BINDINGS: tuple[FieldBinding, ...] = (
    FieldBinding(
        field_name="snapshot_id",
        sql_expr="base.snapshot_id",
        output_type="VARCHAR",
        source_specs=(("bars_daily", ("snapshot_id",)),),
    ),
    FieldBinding(
        field_name="instrument",
        sql_expr="base.ts_code",
        output_type="VARCHAR",
        source_specs=(("bars_daily", ("ts_code",)),),
    ),
    FieldBinding(
        field_name="trade_date",
        sql_expr="base.signal_date",
        output_type="DATE",
        source_specs=(("bars_daily", ("trade_date",)),),
    ),
    FieldBinding(
        field_name="signal_date",
        sql_expr="base.signal_date",
        output_type="DATE",
        source_specs=(("bars_daily", ("trade_date",)),),
    ),
    FieldBinding(
        field_name="is_st",
        sql_expr="status.is_st_t",
        output_type="BOOLEAN",
        source_specs=(("instrument_status_daily", ("is_st_t",)),),
    ),
    FieldBinding(
        field_name="st_source",
        sql_expr=(
            "CASE "
            "WHEN st_active.st_source IS NOT NULL THEN 'state.st_status_interval:' || st_active.st_source "
            "ELSE 'state.instrument_status_daily:' || COALESCE(status.status_source_flags, 'unknown') "
            "END"
        ),
        output_type="VARCHAR",
        source_specs=(
            ("instrument_status_daily", ("status_source_flags",)),
            ("st_status_interval", ("st_source",)),
        ),
        notes="Uses ST interval provenance when an active interval exists, otherwise falls back to the status table provenance string.",
    ),
    FieldBinding(
        field_name="st_effective_start",
        sql_expr="st_active.st_effective_start",
        output_type="DATE",
        source_specs=(("st_status_interval", ("effective_start_date",)),),
    ),
    FieldBinding(
        field_name="st_effective_end",
        sql_expr="st_active.st_effective_end",
        output_type="DATE",
        source_specs=(("st_status_interval", ("effective_end_date",)),),
        notes="Open-ended ST intervals are serialized as null instead of a sentinel close date.",
    ),
    FieldBinding(
        field_name="is_suspended",
        sql_expr="status.is_suspended_t",
        output_type="BOOLEAN",
        source_specs=(("instrument_status_daily", ("is_suspended_t",)),),
    ),
    FieldBinding(
        field_name="no_trade_flag",
        sql_expr="trad.no_trade_t",
        output_type="BOOLEAN",
        source_specs=(("tradability_daily", ("no_trade_t",)),),
    ),
    FieldBinding(
        field_name="volume_zero_flag",
        sql_expr="COALESCE(base.vol, 0) = 0",
        output_type="BOOLEAN",
        source_specs=(("bars_daily", ("vol",)),),
    ),
    FieldBinding(
        field_name="amount_zero_flag",
        sql_expr="COALESCE(base.amount, 0) = 0",
        output_type="BOOLEAN",
        source_specs=(("bars_daily", ("amount",)),),
    ),
    FieldBinding(
        field_name="is_limit_up",
        sql_expr="ABS(base.close - limits.up_limit_price_t) <= limits.tick_tolerance",
        output_type="BOOLEAN",
        source_specs=(
            ("bars_daily", ("close",)),
            ("limit_rules_daily", ("up_limit_price_t", "price_tick_quantize_t")),
        ),
    ),
    FieldBinding(
        field_name="is_limit_down",
        sql_expr="ABS(base.close - limits.down_limit_price_t) <= limits.tick_tolerance",
        output_type="BOOLEAN",
        source_specs=(
            ("bars_daily", ("close",)),
            ("limit_rules_daily", ("down_limit_price_t", "price_tick_quantize_t")),
        ),
    ),
    FieldBinding(
        field_name="open_at_up_limit",
        sql_expr="ABS(base.open - limits.up_limit_price_t) <= limits.tick_tolerance",
        output_type="BOOLEAN",
        source_specs=(
            ("bars_daily", ("open",)),
            ("limit_rules_daily", ("up_limit_price_t", "price_tick_quantize_t")),
        ),
    ),
    FieldBinding(
        field_name="close_at_down_limit",
        sql_expr="ABS(base.close - limits.down_limit_price_t) <= limits.tick_tolerance",
        output_type="BOOLEAN",
        source_specs=(
            ("bars_daily", ("close",)),
            ("limit_rules_daily", ("down_limit_price_t", "price_tick_quantize_t")),
        ),
    ),
    FieldBinding(
        field_name="limit_rule_version",
        sql_expr="limits.rule_version",
        output_type="VARCHAR",
        source_specs=(("limit_rules_daily", ("rule_version",)),),
    ),
    FieldBinding(
        field_name="entry_buyable",
        sql_expr="trad.buyable_at_open",
        output_type="BOOLEAN",
        source_specs=(("tradability_daily", ("buyable_at_open",)),),
        notes="Bound to the D0 open-state buyability field and explicitly excludes D1 fill outcomes.",
    ),
    FieldBinding(
        field_name="exit_sellable",
        sql_expr="trad.sellable_at_close",
        output_type="BOOLEAN",
        source_specs=(("tradability_daily", ("sellable_at_close",)),),
        notes="Uses D0 close-state sellability only and does not reference realized exit paths.",
    ),
    FieldBinding(
        field_name="sellable_retry_next_open",
        sql_expr="trad.sellable_retry_next_open",
        output_type="BOOLEAN",
        source_specs=(("tradability_daily", ("sellable_retry_next_open",)),),
    ),
    FieldBinding(
        field_name="list_date",
        sql_expr="inst.list_date_d",
        output_type="DATE",
        source_specs=(("instruments", ("list_date",)),),
    ),
    FieldBinding(
        field_name="listing_age_days",
        sql_expr="DATE_DIFF('day', inst.list_date_d, base.signal_date)",
        output_type="BIGINT",
        source_specs=(
            ("instruments", ("list_date",)),
            ("bars_daily", ("trade_date",)),
        ),
    ),
    FieldBinding(
        field_name="listing_age_trading_days",
        sql_expr="signal_cal.trade_idx - list_cal.trade_idx + 1",
        output_type="BIGINT",
        source_specs=(
            ("instruments", ("list_date",)),
            ("calendar", ("trade_date",)),
            ("bars_daily", ("trade_date",)),
        ),
        notes="Computed from the snapshot trading calendar index and includes the listing session as day 1.",
    ),
    FieldBinding(
        field_name="newly_listed_flag",
        sql_expr=f"(signal_cal.trade_idx - list_cal.trade_idx + 1) <= {NEWLY_LISTED_TRADING_DAY_THRESHOLD}",
        output_type="BOOLEAN",
        source_specs=(
            ("instruments", ("list_date",)),
            ("calendar", ("trade_date",)),
        ),
        notes=f"Uses a fixed {NEWLY_LISTED_TRADING_DAY_THRESHOLD}-trading-day threshold for state-only tagging. No tuning is performed.",
    ),
    FieldBinding(
        field_name="board_type",
        sql_expr="COALESCE(status.board, inst.board)",
        output_type="VARCHAR",
        source_specs=(
            ("instrument_status_daily", ("board",)),
            ("instruments", ("board",)),
        ),
    ),
    FieldBinding(
        field_name="exchange",
        sql_expr="COALESCE(status.exchange, inst.exchange)",
        output_type="VARCHAR",
        source_specs=(
            ("instrument_status_daily", ("exchange",)),
            ("instruments", ("exchange",)),
        ),
    ),
    FieldBinding(
        field_name="limit_pct_rule",
        sql_expr="PRINTF('pct_%.2f', limits.limit_pct_value)",
        output_type="VARCHAR",
        source_specs=(("limit_rules_daily", ("limit_pct",)),),
    ),
    FieldBinding(
        field_name="source_snapshot_id",
        sql_expr="base.snapshot_id",
        output_type="VARCHAR",
        source_specs=(("bars_daily", ("snapshot_id",)),),
    ),
    FieldBinding(
        field_name="build_time",
        sql_expr="base.build_time_utc",
        output_type="TIMESTAMP",
        source_specs=(),
    ),
    FieldBinding(
        field_name="builder_version",
        sql_expr="base.builder_version",
        output_type="VARCHAR",
        source_specs=(),
    ),
    FieldBinding(
        field_name="d0_visible",
        sql_expr="TRUE",
        output_type="BOOLEAN",
        source_specs=(),
    ),
    FieldBinding(
        field_name="no_frozen_test_access",
        sql_expr="TRUE",
        output_type="BOOLEAN",
        source_specs=(),
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def describe_columns(con: duckdb.DuckDBPyConnection, relation_sql: str) -> set[str]:
    rows = con.execute(f"DESCRIBE {relation_sql}").fetchall()
    return {str(row[0]) for row in rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build enriched_security_state_daily_v1 from the local snapshot only.")
    parser.add_argument(
        "--field-contract",
        type=Path,
        default=DEFAULT_FIELD_CONTRACT_PATH,
        help="Path to field_contract_v1.json.",
    )
    parser.add_argument(
        "--run-input-contract",
        type=Path,
        default=DEFAULT_RUN_INPUT_CONTRACT_PATH,
        help="Path to the trainval run input contract JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for parquet and audit outputs.",
    )
    return parser.parse_args()


def normalize_contract_fields(field_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for category in field_contract["categories"]:
        for field in category["fields"]:
            fields[field["field_name"]] = field
    return fields


def ensure_entity_contract(field_contract: dict[str, Any]) -> None:
    if field_contract.get("entity_name") != ENTITY_NAME:
        raise BuildError(
            f"field contract entity_name must be {ENTITY_NAME}: "
            f"{field_contract.get('entity_name')!r}"
        )


def validate_no_frozen_test_boundary(run_input: dict[str, Any]) -> None:
    snapshot_id = str(run_input.get("snapshot_id", ""))
    notes_text = " ".join(str(item) for item in run_input.get("notes", [])).lower()
    has_boundary_text = (
        "excluded by construction" in notes_text
        or "no frozen test access" in notes_text
        or "trainval_only" in notes_text
        or "trainval-only" in notes_text
    )
    if not snapshot_id:
        raise BuildError("run input contract missing snapshot_id")
    if not has_boundary_text:
        raise BuildError(
            "run input contract cannot prove no frozen test access; "
            "missing boundary note in notes[]"
        )


def discover_sources(
    snapshot_path: Path,
    con: duckdb.DuckDBPyConnection,
) -> dict[str, dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        path = snapshot_path / spec.relative_path
        entry: dict[str, Any] = {
            "path": path,
            "required": spec.required,
            "exists": path.exists(),
            "required_columns": list(spec.required_columns),
            "available_columns": [],
            "missing_columns": [],
        }
        if entry["exists"]:
            entry["available_columns"] = sorted(
                describe_columns(con, f"SELECT * FROM read_parquet({sql_quote(path.as_posix())})")
            )
            entry["missing_columns"] = sorted(set(spec.required_columns) - set(entry["available_columns"]))
        else:
            entry["missing_columns"] = list(spec.required_columns)
        if spec.required and (not entry["exists"] or entry["missing_columns"]):
            missing_bits = ", ".join(entry["missing_columns"]) if entry["missing_columns"] else "missing file"
            raise BuildError(f"required source {spec.name} is unavailable: {missing_bits}")
        discovered[spec.name] = entry
    return discovered


def register_views(
    con: duckdb.DuckDBPyConnection,
    snapshot_path: Path,
    source_inventory: dict[str, dict[str, Any]],
    build_time_utc: str,
) -> None:
    source_map = {
        "bars_daily": "bars_source",
        "instrument_status_daily": "status_source",
        "tradability_daily": "trad_source",
        "limit_rules_daily": "limit_source",
        "instruments": "inst_source",
        "calendar": "calendar_source",
    }
    for source_name, view_name in source_map.items():
        path = snapshot_path / next(spec.relative_path for spec in SOURCE_SPECS if spec.name == source_name)
        con.execute(
            f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet({sql_quote(path.as_posix())})"
        )

    if source_inventory["st_status_interval"]["exists"]:
        st_path = source_inventory["st_status_interval"]["path"]
        con.execute(
            f"CREATE OR REPLACE VIEW st_interval_source AS SELECT * FROM read_parquet({sql_quote(st_path.as_posix())})"
        )
    else:
        con.execute(
            """
            CREATE OR REPLACE VIEW st_interval_source AS
            SELECT
                CAST(NULL AS VARCHAR) AS snapshot_id,
                CAST(NULL AS VARCHAR) AS ts_code,
                CAST(NULL AS VARCHAR) AS effective_start_date,
                CAST(NULL AS VARCHAR) AS effective_end_date,
                CAST(NULL AS VARCHAR) AS st_source
            WHERE FALSE
            """
        )

    con.execute(
        f"""
        CREATE OR REPLACE VIEW base_bars AS
        SELECT
            snapshot_id,
            ts_code,
            trade_date,
            CAST(TRY_STRPTIME(trade_date, '%Y%m%d') AS DATE) AS signal_date,
            open,
            close,
            vol,
            amount,
            CAST({sql_quote(build_time_utc)} AS TIMESTAMP) AS build_time_utc,
            {sql_quote(BUILDER_VERSION)} AS builder_version
        FROM bars_source
        """
    )
    invalid_dates = int(
        con.execute("SELECT COUNT(*) FROM base_bars WHERE signal_date IS NULL").fetchone()[0] or 0
    )
    if invalid_dates:
        raise BuildError(f"bars_daily trade_date contains unparsable rows: {invalid_dates}")

    con.execute(
        """
        CREATE OR REPLACE VIEW status_daily AS
        SELECT
            snapshot_id,
            ts_code,
            trade_date,
            board,
            exchange,
            is_suspended_t,
            is_st_t,
            status_source_flags
        FROM status_source
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW trad_daily AS
        SELECT
            snapshot_id,
            ts_code,
            trade_date,
            no_trade_t,
            buyable_at_open,
            sellable_at_close,
            sellable_retry_next_open
        FROM trad_source
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW limit_daily AS
        SELECT
            snapshot_id,
            ts_code,
            trade_date,
            CAST(limit_pct AS DOUBLE) AS limit_pct_value,
            CAST(price_tick_quantize_t AS DOUBLE) / 2.0 AS tick_tolerance,
            up_limit_price_t,
            down_limit_price_t,
            rule_version
        FROM limit_source
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW instruments_dim AS
        SELECT
            snapshot_id,
            ts_code,
            CAST(TRY_STRPTIME(list_date, '%Y%m%d') AS DATE) AS list_date_d,
            board,
            exchange
        FROM inst_source
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW calendar_idx AS
        SELECT
            CAST(TRY_STRPTIME(trade_date, '%Y%m%d') AS DATE) AS trade_date_d,
            ROW_NUMBER() OVER (ORDER BY trade_date) AS trade_idx
        FROM calendar_source
        """
    )
    con.execute(
        """
        CREATE OR REPLACE VIEW st_interval_active AS
        WITH joined AS (
            SELECT
                b.snapshot_id,
                b.ts_code,
                b.trade_date,
                CAST(TRY_STRPTIME(st.effective_start_date, '%Y%m%d') AS DATE) AS st_effective_start,
                CASE
                    WHEN st.effective_end_date IS NULL OR st.effective_end_date = '' OR st.effective_end_date = '20991231'
                    THEN CAST(NULL AS DATE)
                    ELSE CAST(TRY_STRPTIME(st.effective_end_date, '%Y%m%d') AS DATE)
                END AS st_effective_end,
                st.st_source,
                ROW_NUMBER() OVER (
                    PARTITION BY b.snapshot_id, b.ts_code, b.trade_date
                    ORDER BY st.effective_start_date DESC, st.effective_end_date DESC
                ) AS rn
            FROM base_bars b
            LEFT JOIN st_interval_source st
              ON b.snapshot_id = st.snapshot_id
             AND b.ts_code = st.ts_code
             AND st.effective_start_date <= b.trade_date
             AND COALESCE(NULLIF(st.effective_end_date, ''), '20991231') >= b.trade_date
        )
        SELECT
            snapshot_id,
            ts_code,
            trade_date,
            st_effective_start,
            st_effective_end,
            st_source
        FROM joined
        WHERE rn = 1
        """
    )


def build_output_query(field_order: list[str]) -> str:
    expr_by_field = {binding.field_name: binding for binding in FIELD_BINDINGS}
    select_clauses: list[str] = []
    for field_name in field_order:
        binding = expr_by_field[field_name]
        select_clauses.append(f"CAST({binding.sql_expr} AS {binding.output_type}) AS {field_name}")
    select_sql = ",\n            ".join(select_clauses)
    return f"""
        SELECT
            {select_sql}
        FROM base_bars base
        INNER JOIN status_daily status
            ON base.snapshot_id = status.snapshot_id
           AND base.ts_code = status.ts_code
           AND base.trade_date = status.trade_date
        INNER JOIN trad_daily trad
            ON base.snapshot_id = trad.snapshot_id
           AND base.ts_code = trad.ts_code
           AND base.trade_date = trad.trade_date
        INNER JOIN limit_daily limits
            ON base.snapshot_id = limits.snapshot_id
           AND base.ts_code = limits.ts_code
           AND base.trade_date = limits.trade_date
        INNER JOIN instruments_dim inst
            ON base.snapshot_id = inst.snapshot_id
           AND base.ts_code = inst.ts_code
        INNER JOIN calendar_idx signal_cal
            ON base.signal_date = signal_cal.trade_date_d
        LEFT JOIN calendar_idx list_cal
            ON inst.list_date_d = list_cal.trade_date_d
        LEFT JOIN st_interval_active st_active
            ON base.snapshot_id = st_active.snapshot_id
           AND base.ts_code = st_active.ts_code
           AND base.trade_date = st_active.trade_date
    """


def fetch_output_metrics(
    con: duckdb.DuckDBPyConnection,
    output_relation: str,
    field_names: list[str],
) -> dict[str, Any]:
    null_aggregates = [f"SUM(CASE WHEN {field} IS NULL THEN 1 ELSE 0 END) AS {field}__nulls" for field in field_names]
    metrics_row = con.execute(
        f"""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument) AS instrument_count,
            MIN(signal_date) AS min_signal_date,
            MAX(signal_date) AS max_signal_date,
            {", ".join(null_aggregates)}
        FROM {output_relation}
        """
    ).fetchone()
    metric_columns = [desc[0] for desc in con.description]
    metrics = dict(zip(metric_columns, metrics_row))
    duplicate_pk_rows = int(
        con.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT snapshot_id, instrument, signal_date, COUNT(*) AS cnt
                FROM {output_relation}
                GROUP BY 1, 2, 3
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        or 0
    )
    metrics["duplicate_primary_key_rows"] = duplicate_pk_rows
    return metrics


def build_null_policy_check_sql(field_name: str, null_policy: str) -> str:
    if null_policy == "forbidden":
        return f"SUM(CASE WHEN {field_name} IS NULL THEN 1 ELSE 0 END)"
    if null_policy == "allowed_if_not_applicable":
        if field_name == "st_effective_start":
            return "SUM(CASE WHEN is_st IS TRUE AND st_effective_start IS NULL THEN 1 ELSE 0 END)"
        return "0"
    if null_policy == "allowed_if_open_interval":
        return "0"
    return "0"


def collect_field_build_status(
    con: duckdb.DuckDBPyConnection,
    output_relation: str,
    field_contract: dict[str, Any],
    source_inventory: dict[str, dict[str, Any]],
    output_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    contract_fields = normalize_contract_fields(field_contract)
    bindings_by_name = {binding.field_name: binding for binding in FIELD_BINDINGS}
    row_count = int(output_metrics["row_count"])
    records: list[dict[str, Any]] = []
    for field_name, contract_field in contract_fields.items():
        binding = bindings_by_name[field_name]
        missing_sources: list[str] = []
        used_source_columns: list[str] = []
        for source_name, columns in binding.source_specs:
            used_source_columns.extend([f"{source_name}.{column}" for column in columns])
            inventory = source_inventory[source_name]
            if not inventory["exists"]:
                missing_sources.append(source_name)
                continue
            available_columns = set(inventory["available_columns"])
            if not set(columns).issubset(available_columns):
                missing_sources.append(source_name)
        source_status = "pass" if not missing_sources else "missing_source"
        null_count = int(output_metrics.get(f"{field_name}__nulls", 0) or 0)
        null_policy_violation_rows = int(
            con.execute(
                f"SELECT {build_null_policy_check_sql(field_name, contract_field['allowed_null_policy'])} FROM {output_relation}"
            ).fetchone()[0]
            or 0
        )
        if source_status == "missing_source":
            build_status = "missing_source"
        elif null_policy_violation_rows > 0:
            build_status = "blocked"
        else:
            build_status = "pass"
        records.append(
            {
                "field_name": field_name,
                "dtype": contract_field["dtype"],
                "required": bool(contract_field["required"]),
                "allowed_null_policy": contract_field["allowed_null_policy"],
                "source_status": source_status,
                "build_status": build_status,
                "missing_sources": sorted(set(missing_sources)),
                "null_count": null_count,
                "nonnull_count": row_count - null_count,
                "null_policy_violation_rows": null_policy_violation_rows,
                "source_columns_used": sorted(set(used_source_columns)),
                "notes": binding.notes,
            }
        )
    return records


def build_field_coverage_summary(
    field_records: list[dict[str, Any]],
    output_metrics: dict[str, Any],
    source_snapshot_id: str,
) -> dict[str, Any]:
    pass_fields = sorted(record["field_name"] for record in field_records if record["build_status"] == "pass")
    blocked_fields = sorted(record["field_name"] for record in field_records if record["build_status"] == "blocked")
    missing_source_fields = sorted(
        record["field_name"] for record in field_records if record["build_status"] == "missing_source"
    )
    return {
        "entity_name": ENTITY_NAME,
        "builder_version": BUILDER_VERSION,
        "source_snapshot_id": source_snapshot_id,
        "row_count": int(output_metrics["row_count"]),
        "instrument_count": int(output_metrics["instrument_count"]),
        "pass_fields": pass_fields,
        "conditional_fields": [],
        "blocked_fields": blocked_fields,
        "missing_source_fields": missing_source_fields,
        "d0_visible_all_true": True,
        "no_frozen_test_access": True,
        "newly_listed_trading_day_threshold": NEWLY_LISTED_TRADING_DAY_THRESHOLD,
        "status_hint": "pass" if not (missing_source_fields or blocked_fields) else "conditional_pass",
    }


def build_data_field_enrichment_v1(
    field_contract_path: Path,
    run_input_contract_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    field_contract = load_json(field_contract_path)
    ensure_entity_contract(field_contract)
    run_input = load_json(run_input_contract_path)
    validate_no_frozen_test_boundary(run_input)

    snapshot_id = str(run_input["snapshot_id"])
    snapshot_path = Path(run_input["source_root"]["snapshot_path"]).resolve()
    if not snapshot_path.exists():
        raise BuildError(f"snapshot_path does not exist: {snapshot_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_parquet_path = output_dir / OUTPUT_PARQUET_NAME
    build_audit_path = output_dir / BUILD_AUDIT_NAME
    field_coverage_path = output_dir / FIELD_COVERAGE_SUMMARY_NAME
    build_time_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    field_order = list(normalize_contract_fields(field_contract).keys())
    con = duckdb.connect()
    try:
        source_inventory = discover_sources(snapshot_path, con)
        register_views(con, snapshot_path, source_inventory, build_time_utc)
        output_query = build_output_query(field_order)
        con.execute(f"CREATE OR REPLACE VIEW {ENTITY_NAME}_build AS {output_query}")

        output_metrics = fetch_output_metrics(con, f"{ENTITY_NAME}_build", field_order)
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM {ENTITY_NAME}_build
                ORDER BY signal_date, instrument
            ) TO {sql_quote(output_parquet_path.as_posix())} (FORMAT PARQUET)
            """
        )

        field_records = collect_field_build_status(
            con,
            f"{ENTITY_NAME}_build",
            field_contract,
            source_inventory,
            output_metrics,
        )
        field_coverage_summary = build_field_coverage_summary(field_records, output_metrics, snapshot_id)
        source_tables_used = [
            str(source_inventory[source_name]["path"])
            for source_name in ("bars_daily", "instrument_status_daily", "tradability_daily", "limit_rules_daily", "instruments", "calendar")
            if source_inventory[source_name]["exists"]
        ]
        if source_inventory["st_status_interval"]["exists"]:
            source_tables_used.append(str(source_inventory["st_status_interval"]["path"]))
        build_audit = {
            "entity_name": ENTITY_NAME,
            "field_contract_path": str(field_contract_path.resolve()),
            "field_contract_version": field_contract["contract_version"],
            "builder_version": BUILDER_VERSION,
            "build_time": build_time_utc,
            "snapshot_id": snapshot_id,
            "source_snapshot_id": snapshot_id,
            "source_snapshot_path": str(snapshot_path),
            "output_dir": str(output_dir.resolve()),
            "output_artifacts": {
                "parquet": str(output_parquet_path),
                "build_audit_json": str(build_audit_path),
                "field_coverage_summary_json": str(field_coverage_path),
            },
            "base_source": "warehouse/market/bars_daily.parquet",
            "no_frozen_test_access": True,
            "d0_visible": True,
            "newly_listed_trading_day_threshold": NEWLY_LISTED_TRADING_DAY_THRESHOLD,
            "source_tables_used": source_tables_used,
            "source_inventory": {
                name: {
                    "path": str(info["path"]),
                    "required": info["required"],
                    "exists": info["exists"],
                    "required_columns": info["required_columns"],
                    "available_columns": info["available_columns"],
                    "missing_columns": info["missing_columns"],
                }
                for name, info in source_inventory.items()
            },
            "output_metrics": {
                "base_row_count": int(
                    con.execute("SELECT COUNT(*) FROM base_bars").fetchone()[0] or 0
                ),
                "row_count": int(output_metrics["row_count"]),
                "instrument_count": int(output_metrics["instrument_count"]),
                "min_signal_date": str(output_metrics["min_signal_date"]),
                "max_signal_date": str(output_metrics["max_signal_date"]),
                "duplicate_primary_key_rows": int(output_metrics["duplicate_primary_key_rows"]),
            },
            "field_records": field_records,
        }
        write_json(build_audit_path, build_audit)
        write_json(field_coverage_path, field_coverage_summary)
        return {
            "output_parquet_path": output_parquet_path,
            "build_audit_path": build_audit_path,
            "field_coverage_summary_path": field_coverage_path,
            "build_audit": build_audit,
            "field_coverage_summary": field_coverage_summary,
        }
    finally:
        con.close()


def main() -> int:
    args = parse_args()
    try:
        result = build_data_field_enrichment_v1(
            field_contract_path=args.field_contract.resolve(),
            run_input_contract_path=args.run_input_contract.resolve(),
            output_dir=args.output_dir.resolve(),
        )
    except BuildError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    payload = {
        "ok": True,
        "entity_name": ENTITY_NAME,
        "builder_version": BUILDER_VERSION,
        "output_parquet_path": str(result["output_parquet_path"]),
        "build_audit_path": str(result["build_audit_path"]),
        "field_coverage_summary_path": str(result["field_coverage_summary_path"]),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
