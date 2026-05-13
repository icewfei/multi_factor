#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_FIELD_CONTRACT_PATH = ROOT / "configs" / "data_field_enrichment" / "field_contract_v1.json"
DEFAULT_ARTIFACT_DIR = Path("/private/tmp/data_field_enrichment_v1_smoke")
ENTITY_NAME = "enriched_security_state_daily_v1"
INPUT_PARQUET_NAME = f"{ENTITY_NAME}.parquet"
BUILD_AUDIT_NAME = "build_audit.json"
FIELD_COVERAGE_SUMMARY_NAME = "field_coverage_summary.json"
AUDIT_REPORT_JSON_NAME = "audit_report.json"
AUDIT_REPORT_MD_NAME = "audit_report.md"

FORBIDDEN_EXACT_FIELDS = {
    "entry_filled_D1",
    "entry_buyable_D1_open",
    "exit_sellable_D5_close",
    "execution_attempt_D1",
    "actually_exited",
    "label_defined",
    "backtest_executable",
    "topk_frozen_D0",
    "portfolio_return",
}
FORBIDDEN_REGEXES = (
    re.compile(r"(^|_)D[1-9][0-9]*($|_)"),
    re.compile(r"(^|_)D5($|_)"),
)
FORBIDDEN_SOURCE_PATH_SNIPPETS = (
    "/warehouse/research/",
    "/artifacts/fixed_test/",
    "fixed_test",
)


class AuditError(Exception):
    """Raised when the audit inputs are incomplete."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit enriched_security_state_daily_v1 outputs.")
    parser.add_argument(
        "--field-contract",
        type=Path,
        default=DEFAULT_FIELD_CONTRACT_PATH,
        help="Path to field_contract_v1.json.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory containing the builder outputs.",
    )
    return parser.parse_args()


def normalize_contract_fields(field_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for category in field_contract["categories"]:
        for field in category["fields"]:
            fields[field["field_name"]] = field
    return fields


def describe_relation(con: duckdb.DuckDBPyConnection, parquet_path: Path) -> dict[str, str]:
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
    ).fetchall()
    return {str(row[0]): str(row[1]) for row in rows}


def logical_type_matches(contract_dtype: str, duckdb_type: str) -> bool:
    normalized = duckdb_type.upper()
    mapping = {
        "string": {"VARCHAR"},
        "boolean": {"BOOLEAN"},
        "date": {"DATE"},
        "timestamp": {"TIMESTAMP", "TIMESTAMP WITH TIME ZONE"},
        "integer": {"BIGINT", "INTEGER", "INT64", "INT32", "SMALLINT"},
    }
    return normalized in mapping.get(contract_dtype, set())


def is_forbidden_field_name(name: str) -> bool:
    if name in FORBIDDEN_EXACT_FIELDS:
        return True
    if name == "no_frozen_test_access":
        return False
    return any(pattern.search(name) for pattern in FORBIDDEN_REGEXES)


def load_field_source_status(build_audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        record["field_name"]: {
            "source_status": record["source_status"],
            "missing_sources": record.get("missing_sources", []),
        }
        for record in build_audit.get("field_records", [])
    }


def collect_global_metrics(con: duckdb.DuckDBPyConnection, parquet_path: Path) -> dict[str, Any]:
    relation = f"read_parquet('{parquet_path.as_posix()}')"
    row = con.execute(
        f"""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument) AS instrument_count,
            MIN(signal_date) AS min_signal_date,
            MAX(signal_date) AS max_signal_date,
            SUM(CASE WHEN d0_visible IS TRUE THEN 0 ELSE 1 END) AS d0_visible_fail_rows,
            SUM(CASE WHEN no_frozen_test_access IS TRUE THEN 0 ELSE 1 END) AS no_frozen_test_access_fail_rows,
            SUM(CASE WHEN trade_date IS NOT NULL AND trade_date <> signal_date THEN 1 ELSE 0 END) AS trade_signal_mismatch_rows,
            SUM(CASE WHEN source_snapshot_id <> snapshot_id THEN 1 ELSE 0 END) AS source_snapshot_mismatch_rows
        FROM {relation}
        """
    ).fetchone()
    columns = [desc[0] for desc in con.description]
    metrics = dict(zip(columns, row))
    duplicate_primary_key_rows = int(
        con.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT snapshot_id, instrument, signal_date, COUNT(*) AS cnt
                FROM {relation}
                GROUP BY 1, 2, 3
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        or 0
    )
    metrics["duplicate_primary_key_rows"] = duplicate_primary_key_rows
    return metrics


def null_policy_check_sql(field_name: str, null_policy: str) -> str:
    if null_policy == "forbidden":
        return f"SUM(CASE WHEN {field_name} IS NULL THEN 1 ELSE 0 END)"
    if null_policy == "allowed_if_not_applicable":
        if field_name == "st_effective_start":
            return "SUM(CASE WHEN is_st IS TRUE AND st_effective_start IS NULL THEN 1 ELSE 0 END)"
        return "0"
    if null_policy == "allowed_if_open_interval":
        return "0"
    if null_policy == "allowed_if_not_applicable":
        return "0"
    return "0"


def field_audit_records(
    con: duckdb.DuckDBPyConnection,
    parquet_path: Path,
    field_contract: dict[str, Any],
    build_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    relation = f"read_parquet('{parquet_path.as_posix()}')"
    described_types = describe_relation(con, parquet_path)
    contract_fields = normalize_contract_fields(field_contract)
    build_source_status = load_field_source_status(build_audit)
    records: list[dict[str, Any]] = []
    for field_name, contract_field in contract_fields.items():
        expected_dtype = contract_field["dtype"]
        actual_type = described_types.get(field_name)
        type_ok = actual_type is not None and logical_type_matches(expected_dtype, actual_type)
        null_violation_count = int(
            con.execute(
                f"SELECT {null_policy_check_sql(field_name, contract_field['allowed_null_policy'])} FROM {relation}"
            ).fetchone()[0]
            or 0
        )
        source_info = build_source_status.get(field_name, {"source_status": "blocked", "missing_sources": []})
        if actual_type is None or not type_ok or null_violation_count > 0:
            status = "blocked"
        elif source_info["source_status"] == "missing_source":
            status = "conditional"
        else:
            status = "pass"
        records.append(
            {
                "field_name": field_name,
                "required": bool(contract_field["required"]),
                "expected_dtype": expected_dtype,
                "actual_duckdb_type": actual_type,
                "allowed_null_policy": contract_field["allowed_null_policy"],
                "type_ok": type_ok,
                "null_policy_violation_rows": null_violation_count,
                "source_status": source_info["source_status"],
                "missing_sources": source_info.get("missing_sources", []),
                "audit_status": status,
            }
        )
    return records


def build_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Data Field Enrichment V1 Audit Report",
        "",
        f"- final_status: `{report['final_status']}`",
        f"- row_count: `{report['row_count']}`",
        f"- instrument_count: `{report['instrument_count']}`",
        f"- signal_date_range: `{report['min_signal_date']}` to `{report['max_signal_date']}`",
        f"- d0_visible_all_true: `{report['d0_visible_all_true']}`",
        f"- no_frozen_test_access: `{report['no_frozen_test_access']}`",
        "",
        "## Field Coverage",
        "",
        f"- pass_fields ({len(report['pass_fields'])}): {', '.join(report['pass_fields']) or 'none'}",
        f"- conditional_fields ({len(report['conditional_fields'])}): {', '.join(report['conditional_fields']) or 'none'}",
        f"- blocked_fields ({len(report['blocked_fields'])}): {', '.join(report['blocked_fields']) or 'none'}",
        f"- missing_source_fields ({len(report['missing_source_fields'])}): {', '.join(report['missing_source_fields']) or 'none'}",
        "",
        "## Guardrail Checks",
        "",
        f"- forbidden_output_columns: {', '.join(report['forbidden_output_columns']) or 'none'}",
        f"- unexpected_columns: {', '.join(report['unexpected_columns']) or 'none'}",
        f"- forbidden_source_tables: {', '.join(report['forbidden_source_tables']) or 'none'}",
        f"- forbidden_source_columns: {', '.join(report['forbidden_source_columns']) or 'none'}",
        f"- duplicate_primary_key_rows: `{report['duplicate_primary_key_rows']}`",
        f"- trade_date_signal_date_mismatch_rows: `{report['trade_date_signal_date_mismatch_rows']}`",
        f"- source_snapshot_mismatch_rows: `{report['source_snapshot_mismatch_rows']}`",
        "",
        "## Boundary Notes",
        "",
        "- This audit covers a D0-visible data-field enrichment artifact only.",
        "- This is not alpha.",
        "- This is not strategy approval.",
        "- No frozen test data is read by this pipeline.",
        "- No training, backtest, or portfolio flow is part of this audit.",
        "",
    ]
    return "\n".join(lines)


def audit_data_field_enrichment_v1(
    field_contract_path: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    field_contract = load_json(field_contract_path)
    contract_fields = normalize_contract_fields(field_contract)

    parquet_path = artifact_dir / INPUT_PARQUET_NAME
    build_audit_path = artifact_dir / BUILD_AUDIT_NAME
    field_coverage_summary_path = artifact_dir / FIELD_COVERAGE_SUMMARY_NAME
    audit_report_json_path = artifact_dir / AUDIT_REPORT_JSON_NAME
    audit_report_md_path = artifact_dir / AUDIT_REPORT_MD_NAME

    for path in (parquet_path, build_audit_path, field_coverage_summary_path):
        if not path.exists():
            raise AuditError(f"required artifact missing: {path}")

    build_audit = load_json(build_audit_path)
    field_coverage_summary = load_json(field_coverage_summary_path)

    con = duckdb.connect()
    try:
        described_types = describe_relation(con, parquet_path)
        output_columns = list(described_types.keys())
        expected_columns = list(contract_fields.keys())
        missing_columns = sorted(set(expected_columns) - set(output_columns))
        unexpected_columns = sorted(set(output_columns) - set(expected_columns))
        forbidden_output_columns = sorted(column for column in output_columns if is_forbidden_field_name(column))

        metrics = collect_global_metrics(con, parquet_path)
        records = field_audit_records(con, parquet_path, field_contract, build_audit)
    finally:
        con.close()

    pass_fields = sorted(record["field_name"] for record in records if record["audit_status"] == "pass")
    conditional_fields = sorted(record["field_name"] for record in records if record["audit_status"] == "conditional")
    blocked_fields = sorted(record["field_name"] for record in records if record["audit_status"] == "blocked")
    missing_source_fields = sorted(
        record["field_name"] for record in records if record["source_status"] == "missing_source"
    )

    source_tables_used = [str(path) for path in build_audit.get("source_tables_used", [])]
    forbidden_source_tables = sorted(
        path for path in source_tables_used if any(snippet in path for snippet in FORBIDDEN_SOURCE_PATH_SNIPPETS)
    )
    source_columns_used = sorted(
        {
            column
            for record in build_audit.get("field_records", [])
            for column in record.get("source_columns_used", [])
        }
    )
    forbidden_source_columns = sorted(
        column.split(".", 1)[1] if "." in column else column
        for column in source_columns_used
        if is_forbidden_field_name(column.split(".", 1)[1] if "." in column else column)
    )

    hard_failures = []
    if missing_columns:
        hard_failures.append("missing_columns")
    if unexpected_columns:
        hard_failures.append("unexpected_columns")
    if forbidden_output_columns:
        hard_failures.append("forbidden_output_columns")
    if forbidden_source_tables:
        hard_failures.append("forbidden_source_tables")
    if forbidden_source_columns:
        hard_failures.append("forbidden_source_columns")
    if int(metrics["duplicate_primary_key_rows"]) > 0:
        hard_failures.append("duplicate_primary_key_rows")
    if int(metrics["d0_visible_fail_rows"]) > 0:
        hard_failures.append("d0_visible_fail_rows")
    if int(metrics["no_frozen_test_access_fail_rows"]) > 0:
        hard_failures.append("no_frozen_test_access_fail_rows")
    if int(metrics["trade_signal_mismatch_rows"]) > 0:
        hard_failures.append("trade_signal_mismatch_rows")
    if int(metrics["source_snapshot_mismatch_rows"]) > 0:
        hard_failures.append("source_snapshot_mismatch_rows")
    if hard_failures:
        final_status = "blocked"
    elif conditional_fields or blocked_fields:
        final_status = "conditional_pass"
    else:
        final_status = "pass"

    report = {
        "entity_name": ENTITY_NAME,
        "audit_time": build_audit.get("build_time"),
        "field_contract_path": str(field_contract_path.resolve()),
        "artifact_dir": str(artifact_dir.resolve()),
        "parquet_path": str(parquet_path.resolve()),
        "build_audit_path": str(build_audit_path.resolve()),
        "field_coverage_summary_path": str(field_coverage_summary_path.resolve()),
        "row_count": int(metrics["row_count"]),
        "instrument_count": int(metrics["instrument_count"]),
        "min_signal_date": str(metrics["min_signal_date"]),
        "max_signal_date": str(metrics["max_signal_date"]),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "forbidden_output_columns": forbidden_output_columns,
        "forbidden_source_tables": forbidden_source_tables,
        "forbidden_source_columns": forbidden_source_columns,
        "duplicate_primary_key_rows": int(metrics["duplicate_primary_key_rows"]),
        "trade_date_signal_date_mismatch_rows": int(metrics["trade_signal_mismatch_rows"]),
        "source_snapshot_mismatch_rows": int(metrics["source_snapshot_mismatch_rows"]),
        "d0_visible_all_true": int(metrics["d0_visible_fail_rows"]) == 0,
        "no_frozen_test_access": int(metrics["no_frozen_test_access_fail_rows"]) == 0,
        "pass_fields": pass_fields,
        "conditional_fields": conditional_fields,
        "blocked_fields": blocked_fields,
        "missing_source_fields": missing_source_fields,
        "field_records": records,
        "final_status": final_status,
        "hard_failures": hard_failures,
        "build_summary_snapshot": field_coverage_summary,
    }
    write_json(audit_report_json_path, report)
    audit_report_md_path.write_text(build_markdown_report(report) + "\n", encoding="utf-8")
    return {
        "audit_report_json_path": audit_report_json_path,
        "audit_report_md_path": audit_report_md_path,
        "report": report,
    }


def main() -> int:
    args = parse_args()
    try:
        result = audit_data_field_enrichment_v1(
            field_contract_path=args.field_contract.resolve(),
            artifact_dir=args.artifact_dir.resolve(),
        )
    except AuditError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    payload = {
        "ok": True,
        "audit_report_json_path": str(result["audit_report_json_path"]),
        "audit_report_md_path": str(result["audit_report_md_path"]),
        "final_status": result["report"]["final_status"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
