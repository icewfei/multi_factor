#!/opt/anaconda3/envs/quant_trade/bin/python
"""Validate a terminal_event_repair_audit JSON against its schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path("/Users/wy/MiscProject/multi_factor")
SCHEMA_PATH = ROOT / "schemas" / "terminal_event_repair_audit.schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate terminal_event_repair_audit.json against schema."
    )
    parser.add_argument(
        "--audit-json",
        default="/private/tmp/terminal_event_repair_audit.json",
        help="Path to the repair audit JSON",
    )
    parser.add_argument(
        "--schema",
        default=str(SCHEMA_PATH),
        help="Path to the JSON Schema",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_row(row: dict[str, Any], row_schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        jsonschema.validate(row, row_schema)
    except jsonschema.ValidationError as e:
        errors.append(e.message)
    return errors


def validate_audit(audit: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    top_errors: list[str] = []
    try:
        jsonschema.validate(audit, schema)
    except jsonschema.ValidationError as e:
        top_errors.append(e.message)

    row_schema = schema["properties"]["rows"]["items"]
    row_errors: list[dict[str, Any]] = []
    for i, row in enumerate(audit.get("rows", [])):
        errs = validate_row(row, row_schema)
        if errs:
            row_errors.append({
                "index": i,
                "instrument": row.get("instrument"),
                "signal_date": row.get("signal_date"),
                "errors": errs,
            })

    total_rows = len(audit.get("rows", []))
    valid_rows = total_rows - len(row_errors)

    return {
        "schema_path": str(SCHEMA_PATH),
        "top_level_valid": len(top_errors) == 0,
        "top_level_errors": top_errors,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": len(row_errors),
        "row_errors": row_errors,
        "passed": len(top_errors) == 0 and len(row_errors) == 0,
    }


def main() -> None:
    args = parse_args()
    audit_path = Path(args.audit_json)
    schema_path = Path(args.schema)

    if not audit_path.exists():
        print(f"ERROR: audit JSON not found: {audit_path}", file=sys.stderr)
        sys.exit(1)
    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    audit = load_json(audit_path)
    schema = load_json(schema_path)
    result = validate_audit(audit, schema)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["passed"]:
        print(f"VALIDATION PASSED: {result['total_rows']} rows, {result['valid_rows']} valid", file=sys.stderr)
    else:
        print(f"VALIDATION FAILED: {result['invalid_rows']}/{result['total_rows']} rows have errors", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
