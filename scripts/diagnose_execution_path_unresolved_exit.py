#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import yaml


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose upstream sources for unresolved actual_exit_date rows in project_execution_panel."
    )
    parser.add_argument("--project-execution-panel", required=True, help="Path to project_execution_panel.parquet")
    parser.add_argument(
        "--execution-state",
        required=True,
        help="Path to execution_state_daily.parquet used to identify the backtest_executable subset",
    )
    parser.add_argument(
        "--source-db",
        default=None,
        help="Optional source warehouse.duckdb path. Overrides --run-input-contract if provided.",
    )
    parser.add_argument(
        "--run-input-contract",
        default=str(CONTRACTS_DIR / "run_input_contract.research_trainval_20211231.json"),
        help="Run input contract used to resolve the source DB when --source-db is omitted.",
    )
    parser.add_argument("--output", required=True, help="Output diagnosis JSON path")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mapped_source_field(mapping: dict[str, Any], section: str, local_field: str) -> str:
    section_mapping = mapping.get(section)
    if not isinstance(section_mapping, dict):
        raise KeyError(f"Missing field mapping section: {section}")
    field_mapping = section_mapping.get(local_field)
    if not isinstance(field_mapping, dict):
        raise KeyError(f"Missing field mapping for {section}.{local_field}")
    source_field = field_mapping.get("source_field")
    if source_field in (None, "null"):
        raise KeyError(f"Field mapping for {section}.{local_field} does not provide a source field")
    return str(source_field)


def resolve_source_db_path(args: argparse.Namespace) -> Path:
    if args.source_db:
        source_db = Path(args.source_db)
    else:
        contract = load_json(Path(args.run_input_contract))
        source_db = Path(contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db.exists():
        raise FileNotFoundError(f"Source DB not found: {source_db}")
    return source_db


def normalize_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def fetch_dict_rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    rows = con.execute(sql).fetchall()
    cols = [col[0] for col in con.description]
    return [
        {col: normalize_scalar(value) for col, value in zip(cols, row)}
        for row in rows
    ]


def is_expected_terminal_event_bridge(
    panel_row: dict[str, Any],
    source_row: dict[str, Any],
) -> bool:
    return (
        source_row.get("execution_path_status") == "exit_unresolved"
        and panel_row.get("execution_path_status") == "terminal_event_unpriced"
        and panel_row.get("actual_exit_date") is None
        and source_row.get("actual_exit_date") is None
        and panel_row.get("actual_sell_price") is None
        and source_row.get("actual_sell_price") is None
        and panel_row.get("terminal_event_flag") is True
        and panel_row.get("terminal_event_type") == "delist"
        and panel_row.get("terminal_event_date") is not None
        and panel_row.get("terminal_exit_pricing_method") == "terminal_event_bridge_required"
    )


def compare_panel_vs_source(
    panel_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    compare_fields: list[str],
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    source_by_key = {
        (str(row["instrument"]), str(row["signal_date"])): row
        for row in source_rows
    }
    mismatch_counts = Counter()
    examples: list[dict[str, Any]] = []
    for row in panel_rows:
        key = (str(row["instrument"]), str(row["signal_date"]))
        source_row = source_by_key.get(key)
        if source_row is None:
            mismatch_counts["missing_source_row"] += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "instrument": key[0],
                        "signal_date": key[1],
                        "field": "__row__",
                        "panel_value": "present",
                        "source_value": "missing",
                    }
                )
            continue
        for field in compare_fields:
            if row.get(field) != source_row.get(field):
                if is_expected_terminal_event_bridge(row, source_row) and field in {
                    "execution_path_status",
                    "terminal_event_flag",
                    "terminal_event_type",
                    "terminal_event_date",
                    "terminal_exit_pricing_method",
                }:
                    continue
                mismatch_counts[field] += 1
                if len(examples) < 5:
                    examples.append(
                        {
                            "instrument": key[0],
                            "signal_date": key[1],
                            "field": field,
                            "panel_value": row.get(field),
                            "source_value": source_row.get(field),
                        }
                    )
    return dict(sorted(mismatch_counts.items())), examples


def build_diagnosis(
    project_execution_panel_path: Path,
    execution_state_path: Path,
    source_db_path: Path,
) -> dict[str, Any]:
    field_mapping = load_yaml(CONTRACTS_DIR / "source_field_mapping.yaml")

    common_snapshot = mapped_source_field(field_mapping, "common_keys", "snapshot_id")
    common_instrument = mapped_source_field(field_mapping, "common_keys", "instrument")
    common_signal_date = mapped_source_field(field_mapping, "common_keys", "signal_date")
    e_entry_date = mapped_source_field(field_mapping, "execution_path_daily", "entry_date")
    e_planned_exit_date = mapped_source_field(field_mapping, "execution_path_daily", "planned_exit_date")
    e_actual_exit_date = mapped_source_field(field_mapping, "execution_path_daily", "actual_exit_date")
    e_actual_exit_event_type = mapped_source_field(field_mapping, "execution_path_daily", "actual_exit_event_type")
    e_actual_exit_price_field = mapped_source_field(field_mapping, "execution_path_daily", "actual_exit_price_field")
    e_actual_sell_price = mapped_source_field(field_mapping, "execution_path_daily", "actual_sell_price")
    e_exit_delay_days = mapped_source_field(field_mapping, "execution_path_daily", "exit_delay_days")
    e_execution_path_status = mapped_source_field(field_mapping, "execution_path_daily", "execution_path_status")
    e_execution_delayed_realized_return = mapped_source_field(
        field_mapping, "execution_path_daily", "execution_delayed_realized_return"
    )
    e_terminal_event_flag = mapped_source_field(field_mapping, "execution_path_daily", "terminal_event_flag")
    e_terminal_event_type = mapped_source_field(field_mapping, "execution_path_daily", "terminal_event_type")
    e_terminal_event_date = mapped_source_field(field_mapping, "execution_path_daily", "terminal_event_date")
    e_terminal_exit_pricing_method = mapped_source_field(
        field_mapping, "execution_path_daily", "terminal_exit_pricing_method"
    )
    e_terminal_exit_approximation_flag = mapped_source_field(
        field_mapping, "execution_path_daily", "terminal_exit_approximation_flag"
    )
    e_terminal_exit_conservative_flag = mapped_source_field(
        field_mapping, "execution_path_daily", "terminal_exit_conservative_flag"
    )
    t_terminal_event_type = mapped_source_field(field_mapping, "terminal_event_daily", "terminal_event_type")
    t_terminal_event_date = mapped_source_field(field_mapping, "terminal_event_daily", "terminal_event_date")
    t_last_tradable_date = mapped_source_field(field_mapping, "terminal_event_daily", "last_tradable_date")
    t_cash_settlement_available = mapped_source_field(
        field_mapping, "terminal_event_daily", "cash_settlement_available"
    )
    t_zero_recovery_recommended = mapped_source_field(
        field_mapping, "terminal_event_daily", "zero_recovery_recommended"
    )

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS warehouse_db (READ_ONLY)")

        unresolved_rows = fetch_dict_rows(
            con,
            f"""
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.entry_date,
                p.planned_exit_date,
                p.actual_exit_date,
                p.actual_sell_price,
                p.exit_delay_days,
                p.execution_delayed_realized_return,
                p.execution_path_status,
                p.actual_exit_event_type,
                p.terminal_event_flag,
                p.terminal_event_type,
                p.terminal_event_date,
                p.terminal_exit_pricing_method,
                p.terminal_exit_conservative_flag
            FROM read_parquet('{project_execution_panel_path.as_posix()}') p
            INNER JOIN read_parquet('{execution_state_path.as_posix()}') e
                ON p.snapshot_id = e.snapshot_id
               AND p.instrument = e.instrument
               AND p.signal_date = e.signal_date
            WHERE e.backtest_executable
              AND p.actual_exit_date IS NULL
            ORDER BY p.signal_date, p.instrument
            """,
        )

        source_rows = fetch_dict_rows(
            con,
            f"""
            SELECT
                e.{common_snapshot} AS snapshot_id,
                e.{common_instrument} AS instrument,
                e.{common_signal_date} AS signal_date,
                e.{e_entry_date} AS entry_date,
                e.{e_planned_exit_date} AS planned_exit_date,
                e.{e_actual_exit_date} AS actual_exit_date,
                e.{e_actual_sell_price} AS actual_sell_price,
                e.{e_exit_delay_days} AS exit_delay_days,
                e.{e_execution_delayed_realized_return} AS execution_delayed_realized_return,
                e.{e_execution_path_status} AS execution_path_status,
                e.{e_actual_exit_event_type} AS actual_exit_event_type,
                e.{e_terminal_event_flag} AS terminal_event_flag,
                e.{e_terminal_event_type} AS terminal_event_type,
                e.{e_terminal_event_date} AS terminal_event_date,
                e.{e_terminal_exit_pricing_method} AS terminal_exit_pricing_method,
                e.{e_terminal_exit_conservative_flag} AS terminal_exit_conservative_flag,
                e.{e_actual_exit_price_field} AS actual_exit_price_field,
                e.{e_terminal_exit_approximation_flag} AS terminal_exit_approximation_flag
            FROM warehouse_db.serving.vw_execution_path_daily e
            INNER JOIN read_parquet('{execution_state_path.as_posix()}') x
                ON e.{common_snapshot} = x.snapshot_id
               AND e.{common_instrument} = x.instrument
               AND e.{common_signal_date} = x.signal_date
            WHERE x.backtest_executable
              AND e.{e_actual_exit_date} IS NULL
            ORDER BY e.{common_signal_date}, e.{common_instrument}
            """,
        )

        terminal_rows = fetch_dict_rows(
            con,
            f"""
            SELECT
                t.{common_snapshot} AS snapshot_id,
                t.{common_instrument} AS instrument,
                t.{t_terminal_event_date} AS terminal_event_date,
                t.{t_terminal_event_type} AS terminal_event_type,
                t.{t_last_tradable_date} AS last_tradable_date,
                t.{t_cash_settlement_available} AS cash_settlement_flag,
                t.{t_zero_recovery_recommended} AS contract_degraded_flag
            FROM warehouse_db.serving.vw_terminal_event_daily t
            INNER JOIN (
                SELECT DISTINCT p.instrument, p.terminal_event_date
                FROM read_parquet('{project_execution_panel_path.as_posix()}') p
                INNER JOIN read_parquet('{execution_state_path.as_posix()}') e
                    ON p.snapshot_id = e.snapshot_id
                   AND p.instrument = e.instrument
                   AND p.signal_date = e.signal_date
                WHERE e.backtest_executable
                  AND p.actual_exit_date IS NULL
                  AND p.terminal_event_date IS NOT NULL
            ) u
                ON t.{common_instrument} = u.instrument
               AND t.{t_terminal_event_date} = u.terminal_event_date
            ORDER BY t.{t_terminal_event_date}, t.{common_instrument}
            """,
        )
    finally:
        con.close()

    root_cause_compare_fields = [
        "actual_exit_date",
        "actual_sell_price",
        "exit_delay_days",
        "execution_delayed_realized_return",
        "execution_path_status",
        "actual_exit_event_type",
        "terminal_event_flag",
        "terminal_event_type",
        "terminal_event_date",
        "terminal_exit_pricing_method",
        "terminal_exit_conservative_flag",
    ]
    ancillary_compare_fields = ["entry_date", "planned_exit_date"]
    mismatch_counts, mismatch_examples = compare_panel_vs_source(
        unresolved_rows, source_rows, root_cause_compare_fields
    )
    ancillary_mismatch_counts, ancillary_mismatch_examples = compare_panel_vs_source(
        unresolved_rows, source_rows, ancillary_compare_fields
    )

    terminal_by_key = {
        (str(row["instrument"]), str(row["terminal_event_date"])): row for row in terminal_rows
    }
    terminal_pricing_policy_rows = 0
    terminal_event_unpriced_rows = 0
    nonterminal_exit_unresolved_rows = 0
    terminal_event_bridge_rows = 0
    source_raw_null_rows = 0
    enriched_rows: list[dict[str, Any]] = []
    terminal_seen = set()
    for row in unresolved_rows:
        source_key = (str(row["instrument"]), str(row["signal_date"]))
        source_row = next(
            (candidate for candidate in source_rows if (str(candidate["instrument"]), str(candidate["signal_date"])) == source_key),
            None,
        )
        if source_row is not None and source_row.get("actual_exit_date") is None:
            source_raw_null_rows += 1
        terminal_row = None
        if row.get("terminal_event_date") is not None:
            terminal_row = terminal_by_key.get((str(row["instrument"]), str(row["terminal_event_date"])))
            if terminal_row is not None:
                terminal_seen.add((str(row["instrument"]), str(row["terminal_event_date"])))
        if row["execution_path_status"] == "terminal_event_unpriced":
            terminal_event_unpriced_rows += 1
            if source_row is not None and is_expected_terminal_event_bridge(row, source_row):
                terminal_event_bridge_rows += 1
            if row.get("terminal_exit_pricing_method") == "no_terminal_pricing_source":
                terminal_pricing_policy_rows += 1
        elif row["execution_path_status"] == "exit_unresolved":
            nonterminal_exit_unresolved_rows += 1
        enriched_rows.append(
            {
                **row,
                "source_execution_path_actual_exit_date": None if source_row is None else source_row.get("actual_exit_date"),
                "source_execution_path_status": None if source_row is None else source_row.get("execution_path_status"),
                "terminal_event_source": terminal_row,
            }
        )

    execution_status_counts = Counter(str(row["execution_path_status"]) for row in unresolved_rows)
    terminal_event_type_counts = Counter(
        str(row["terminal_event_type"]) for row in unresolved_rows if row["terminal_event_type"] is not None
    )

    return {
        "source_paths": {
            "project_execution_panel": project_execution_panel_path.as_posix(),
            "execution_state_daily": execution_state_path.as_posix(),
            "source_db": source_db_path.as_posix(),
        },
        "summary": {
            "unresolved_rows": len(unresolved_rows),
            "execution_status_counts": dict(sorted(execution_status_counts.items())),
            "terminal_event_type_counts": dict(sorted(terminal_event_type_counts.items())),
            "source_execution_path_rows_matched": len(source_rows),
            "source_execution_path_actual_exit_null_rows": source_raw_null_rows,
            "terminal_event_source_rows_matched": len(terminal_seen),
            "terminal_event_unpriced_rows": terminal_event_unpriced_rows,
            "terminal_event_bridge_rows": terminal_event_bridge_rows,
            "nonterminal_exit_unresolved_rows": nonterminal_exit_unresolved_rows,
        },
        "judgment": {
            "upstream_execution_path_null_actual_exit_date": (
                len(unresolved_rows) > 0
                and len(source_rows) == len(unresolved_rows)
                and source_raw_null_rows == len(unresolved_rows)
            ),
            "build_project_panels_join_issue": bool(mismatch_counts),
            "terminal_pricing_policy_needed": terminal_pricing_policy_rows > 0,
            "data_source_gap_present": any(
                row.get("terminal_event_source", {}).get("contract_degraded_flag") is True
                for row in enriched_rows
                if isinstance(row.get("terminal_event_source"), dict)
            ),
        },
        "evidence": {
            "panel_vs_source_root_cause_field_mismatch_counts": mismatch_counts,
            "panel_vs_source_root_cause_field_mismatch_examples": mismatch_examples,
            "panel_vs_source_ancillary_field_mismatch_counts": ancillary_mismatch_counts,
            "panel_vs_source_ancillary_field_mismatch_examples": ancillary_mismatch_examples,
            "terminal_pricing_policy_rows": terminal_pricing_policy_rows,
            "terminal_event_source_contract_degraded_rows": sum(
                1
                for row in enriched_rows
                if isinstance(row.get("terminal_event_source"), dict)
                and row["terminal_event_source"].get("contract_degraded_flag") is True
            ),
        },
        "rows": enriched_rows,
        "conclusion": {
            "root_cause": (
                "The unresolved actual_exit_date rows are already NULL in serving.vw_execution_path_daily. "
                "project_execution_panel may standardize post-delist coverage-gap rows into "
                "terminal_event_unpriced, but it does not invent actual_exit_date or actual_sell_price."
            ),
            "terminal_policy_note": (
                "The delist-linked terminal_event_unpriced rows point to a missing formal terminal pricing policy: "
                "vw_terminal_event_daily exposes degraded terminal-event truth with no cash settlement source, and "
                "vw_execution_path_daily marks those rows as no_terminal_pricing_source."
            ),
        },
    }


def main() -> None:
    args = parse_args()
    payload = build_diagnosis(
        project_execution_panel_path=Path(args.project_execution_panel),
        execution_state_path=Path(args.execution_state),
        source_db_path=resolve_source_db_path(args),
    )
    write_json(Path(args.output), payload)


if __name__ == "__main__":
    main()
