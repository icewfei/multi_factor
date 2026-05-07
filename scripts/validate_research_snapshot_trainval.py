#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_SPEC_PATH = (
    ROOT
    / "artifacts"
    / "research_registry"
    / "research_snapshot_trainval_only_spec_20260429.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_value(actual: str | None, expected_max: str) -> tuple[bool, str]:
    if actual is None:
        return False, "actual value is null"
    if str(actual) <= expected_max:
        return True, f"{actual} <= {expected_max}"
    return False, f"{actual} > {expected_max}"


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        print(
            "usage: validate_research_snapshot_trainval.py <snapshot_path> [spec_json_path]",
            file=sys.stderr,
        )
        return 2

    snapshot_path = Path(argv[1]).resolve()
    spec_path = Path(argv[2]).resolve() if len(argv) == 3 else DEFAULT_SPEC_PATH
    spec = load_json(spec_path)
    duckdb_path = snapshot_path / "duckdb" / "warehouse.duckdb"
    if not duckdb_path.exists():
        print(json.dumps({"ok": False, "error": f"warehouse DB not found: {duckdb_path}"}, ensure_ascii=False))
        return 1

    con = duckdb.connect(str(duckdb_path), read_only=True)
    results: list[dict] = []
    ok = True
    try:
        for check in spec["acceptance_checks"]:
            actual = con.execute(check["sql"]).fetchone()[0]
            passed, detail = compare_value(actual, check["expected_max"])
            results.append(
                {
                    "name": check["name"],
                    "passed": passed,
                    "actual": actual,
                    "expected_max": check["expected_max"],
                    "detail": detail,
                }
            )
            ok = ok and passed
    finally:
        con.close()

    payload = {
        "ok": ok,
        "snapshot_path": str(snapshot_path),
        "spec_path": str(spec_path),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
