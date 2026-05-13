#!/usr/bin/env python3
"""
Build model_scores_D0.parquet and source-chain audit artifacts for the governed
no-p98 clean baseline candidate.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import duckdb


BASELINE_ID = "no_p98_reversal_baseline_v1"
SOURCE_CANDIDATE_SCHEME_ID = "exploratory_cross_horizon_c1_reversal_only"
DEFAULT_ATTEMPT_ID = "attempt_build_no_p98_clean_baseline"
SCORE_DIRECTION = "ASC / reversal_rank"
FROZEN_TEST_TOKENS = (
    "frozen_test",
    "fixed_test",
    "test_window_access",
)
FORBIDDEN_SQL_TOKENS = (
    "label_",
    "realized_return",
    "actual_exit_date",
    "actual_sell_price",
    "next_open",
    "next_close",
    "tail_exclude_p98",
    "reversal_tail_exclude_p98",
    "nr_daily_p98",
    "percentile_cont(0.98)",
)
FORBIDDEN_PANEL_COLUMNS = {
    "realized_return",
    "actual_exit_date",
    "actual_sell_price",
    "future_return",
    "execution_delayed_realized_return",
}

FEATURE_SQL_TEMPLATE = """
CREATE OR REPLACE VIEW sample_panel AS
SELECT
    snapshot_id,
    instrument,
    signal_date,
    ranking_eligible_D0
FROM read_parquet({sample_panel_path});

CREATE OR REPLACE VIEW bars AS
SELECT
    snapshot_id,
    ts_code,
    trade_date,
    adj_close
FROM warehouse_db.serving.vw_bars_daily;

CREATE OR REPLACE VIEW reversal_features AS
SELECT
    snapshot_id,
    ts_code AS instrument,
    trade_date AS signal_date,
    adj_close / LAG(adj_close, 5) OVER (
        PARTITION BY snapshot_id, ts_code
        ORDER BY trade_date
    ) - 1.0 AS reversal_5d_raw
FROM bars;
"""

BUILD_SQL_TEMPLATE = """
COPY (
    WITH eligible AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            f.reversal_5d_raw
        FROM sample_panel s
        LEFT JOIN reversal_features f
          ON s.snapshot_id = f.snapshot_id
         AND s.instrument = f.instrument
         AND s.signal_date = f.signal_date
        WHERE s.ranking_eligible_D0
          AND f.reversal_5d_raw IS NOT NULL
    ),
    ranked AS (
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            reversal_5d_raw,
            PERCENT_RANK() OVER (
                PARTITION BY snapshot_id, signal_date
                ORDER BY reversal_5d_raw ASC, instrument ASC
            ) AS reversal_rank
        FROM eligible
    )
    SELECT
        s.snapshot_id,
        s.instrument,
        s.signal_date,
        CAST({baseline_id} AS VARCHAR) AS candidate_scheme_id,
        CAST({baseline_id} AS VARCHAR) AS baseline_id,
        r.reversal_5d_raw,
        r.reversal_rank,
        r.reversal_rank AS model_score_D0,
        CASE WHEN r.reversal_rank IS NOT NULL THEN 1 ELSE 0 END AS score_component_count
    FROM sample_panel s
    LEFT JOIN ranked r
      ON s.snapshot_id = r.snapshot_id
     AND s.instrument = r.instrument
     AND s.signal_date = r.signal_date
) TO {score_output_path} (FORMAT PARQUET);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build no-p98 clean baseline model_scores_D0 and source-chain audits."
    )
    parser.add_argument("--run-id", required=True, help="Run identifier for this rebuild.")
    parser.add_argument(
        "--project-sample-panel",
        required=True,
        help="Path to project_sample_panel.parquet.",
    )
    parser.add_argument(
        "--run-input-contract",
        required=True,
        help="Path to run input contract JSON used to locate the source warehouse DB.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Defaults to a local temp directory.",
    )
    parser.add_argument(
        "--attempt-id",
        default=DEFAULT_ATTEMPT_ID,
        help="Attempt identifier for run_state_attempt_manifest.json.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required {label} not found: {path}")
    return path


def resolve_output_dir(run_id: str, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    return Path(tempfile.gettempdir()) / run_id


def list_sample_panel_columns(sample_panel_path: Path) -> list[str]:
    con = duckdb.connect()
    try:
        rows = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({sql_path(sample_panel_path)})"
        ).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def detect_forbidden_sample_panel_columns(columns: list[str]) -> list[str]:
    hits: list[str] = []
    for column in columns:
        lowered = column.lower()
        if lowered.startswith("label_"):
            hits.append(column)
            continue
        if lowered in FORBIDDEN_PANEL_COLUMNS:
            hits.append(column)
    return sorted(set(hits))


def inspect_sql_contract(feature_sql: str, build_sql: str) -> dict[str, Any]:
    sql_text = f"{feature_sql}\n{build_sql}".lower()
    forbidden_hits = [token for token in FORBIDDEN_SQL_TOKENS if token in sql_text]
    direction_present = "order by reversal_5d_raw asc, instrument asc" in sql_text
    d0_checks = {
        "adj_close_present": "adj_close" in sql_text,
        "lag_5_present": "lag(adj_close, 5)" in sql_text,
        "ranking_guard_present": "where s.ranking_eligible_d0" in sql_text,
        "no_lead_usage": "lead(" not in sql_text,
        "no_following_usage": "following" not in sql_text,
        "signal_date_partitioned_cross_section": "partition by snapshot_id, signal_date" in sql_text,
    }
    return {
        "forbidden_sql_hits": forbidden_hits,
        "score_direction": SCORE_DIRECTION if direction_present else "unknown",
        "score_direction_clear": direction_present,
        "d0_visibility_checks": d0_checks,
        "d0_visibility_pass": all(d0_checks.values()),
    }


def inspect_run_input_contract(run_input_contract: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(run_input_contract, ensure_ascii=False).lower()
    frozen_hits = [token for token in FROZEN_TEST_TOKENS if token in text]
    return {
        "frozen_test_reference_hits": frozen_hits,
        "frozen_test_accessed": bool(frozen_hits),
    }


def run_build(
    *,
    sample_panel_path: Path,
    source_db_path: Path,
    score_output_path: Path,
) -> None:
    feature_sql = FEATURE_SQL_TEMPLATE.format(sample_panel_path=sql_path(sample_panel_path))
    build_sql = BUILD_SQL_TEMPLATE.format(
        baseline_id=sql_quote(BASELINE_ID),
        score_output_path=sql_path(score_output_path),
    )

    sql_audit = inspect_sql_contract(feature_sql, build_sql)
    if sql_audit["forbidden_sql_hits"]:
        raise ValueError(f"Forbidden SQL tokens detected: {sql_audit['forbidden_sql_hits']}")
    if not sql_audit["score_direction_clear"]:
        raise ValueError("score direction unclear; expected ASC / reversal_rank")
    if not sql_audit["d0_visibility_pass"]:
        raise ValueError("D0 visibility audit failed.")

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(feature_sql)
        con.execute(build_sql)
    finally:
        con.close()


def summarize_scores(score_output_path: Path) -> dict[str, int]:
    con = duckdb.connect()
    try:
        row = con.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_count,
                SUM(
                    CASE
                        WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1
                        ELSE 0
                    END
                ) AS nonfinite_score_count
            FROM read_parquet({sql_path(score_output_path)})
            """
        ).fetchone()
    finally:
        con.close()
    return {
        "row_count": int(row[0] or 0),
        "null_score_count": int(row[1] or 0),
        "nonfinite_score_count": int(row[2] or 0),
    }


def build_model_scores_audit(
    *,
    run_id: str,
    attempt_id: str,
    score_output_path: Path,
    score_summary: dict[str, int],
    sample_panel_columns: list[str],
    sql_audit: dict[str, Any],
    contract_audit: dict[str, Any],
) -> dict[str, Any]:
    forbidden_panel_hits = detect_forbidden_sample_panel_columns(sample_panel_columns)
    leakage_pass = (
        not forbidden_panel_hits
        and not sql_audit["forbidden_sql_hits"]
        and not contract_audit["frozen_test_accessed"]
    )
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_scheme_id": BASELINE_ID,
        "baseline_id": BASELINE_ID,
        "source_candidate_scheme_id": SOURCE_CANDIDATE_SCHEME_ID,
        "score_output_path": score_output_path.as_posix(),
        "summary_counts": score_summary,
        "score_direction": SCORE_DIRECTION,
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "sample_panel_columns": sample_panel_columns,
        "d0_visibility_audit": {
            "pass": sql_audit["d0_visibility_pass"],
            "checks": sql_audit["d0_visibility_checks"],
        },
        "leakage_audit": {
            "pass": leakage_pass,
            "forbidden_sample_panel_columns": forbidden_panel_hits,
            "forbidden_sql_hits": sql_audit["forbidden_sql_hits"],
            "frozen_test_reference_hits": contract_audit["frozen_test_reference_hits"],
        },
        "notes": [
            "No p98 tail exclusion was used.",
            "No label-based source selection was used.",
            "No portfolio or formal metrics/readout artifacts were produced.",
        ],
    }


def build_source_chain_audit(
    *,
    run_id: str,
    attempt_id: str,
    score_output_path: Path,
    score_summary: dict[str, int],
    sql_audit: dict[str, Any],
    contract_audit: dict[str, Any],
    sample_panel_columns: list[str],
) -> dict[str, Any]:
    forbidden_panel_hits = detect_forbidden_sample_panel_columns(sample_panel_columns)
    blockers: list[str] = []
    if forbidden_panel_hits:
        blockers.append(f"forbidden sample panel columns: {forbidden_panel_hits}")
    if sql_audit["forbidden_sql_hits"]:
        blockers.append(f"forbidden sql hits: {sql_audit['forbidden_sql_hits']}")
    if contract_audit["frozen_test_reference_hits"]:
        blockers.append(
            f"frozen/test references detected: {contract_audit['frozen_test_reference_hits']}"
        )
    if not sql_audit["score_direction_clear"]:
        blockers.append("score direction unclear")
    if not sql_audit["d0_visibility_pass"]:
        blockers.append("D0 visibility audit failed")

    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_scheme_id": BASELINE_ID,
        "baseline_id": BASELINE_ID,
        "source_candidate_scheme_id": SOURCE_CANDIDATE_SCHEME_ID,
        "source_chain_status": "pass" if not blockers else "blocked",
        "output_path": score_output_path.as_posix(),
        "summary_counts": score_summary,
        "score_direction": SCORE_DIRECTION,
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "d0_visibility_audit": {
            "pass": sql_audit["d0_visibility_pass"],
            "checks": sql_audit["d0_visibility_checks"],
        },
        "leakage_audit": {
            "pass": not blockers,
            "forbidden_sample_panel_columns": forbidden_panel_hits,
            "forbidden_sql_hits": sql_audit["forbidden_sql_hits"],
            "frozen_test_reference_hits": contract_audit["frozen_test_reference_hits"],
        },
        "blockers": blockers,
        "notes": [
            "Score source fixed to c1 ASC / reversal_rank.",
            "No p98 component, no label diagnostics, no frozen test access.",
        ],
    }


def build_attempt_manifest(
    *,
    run_id: str,
    attempt_id: str,
    output_dir: Path,
    sample_panel_path: Path,
    source_db_path: Path,
    score_output_path: Path,
    audit_output_path: Path,
    source_chain_audit_path: Path,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "run_type": "clean_baseline_rebuild",
        "candidate_scheme_id": BASELINE_ID,
        "baseline_id": BASELINE_ID,
        "source_candidate_scheme_id": SOURCE_CANDIDATE_SCHEME_ID,
        "parameters": {
            "score_direction": SCORE_DIRECTION,
            "p98_used": False,
            "label_diagnostics_used": False,
            "portfolio_ran": False,
            "formal_metrics_generated": False,
            "frozen_test_accessed": False,
        },
        "input_paths": {
            "project_sample_panel": sample_panel_path.as_posix(),
            "source_warehouse_db": source_db_path.as_posix(),
        },
        "output_paths": {
            "run_dir": output_dir.as_posix(),
            "model_scores_D0": score_output_path.as_posix(),
            "model_scores_D0_audit": audit_output_path.as_posix(),
            "source_chain_audit": source_chain_audit_path.as_posix(),
        },
        "notes": [
            "D0 visible only baseline score rebuild.",
            "No p98, no label diagnostics, no frozen test access.",
        ],
    }


def main() -> None:
    args = parse_args()

    if BASELINE_ID != "no_p98_reversal_baseline_v1":
        raise ValueError("Unexpected baseline_id binding.")

    sample_panel_path = require_file(Path(args.project_sample_panel), "project sample panel")
    run_input_contract_path = require_file(Path(args.run_input_contract), "run input contract")
    run_input_contract = load_json(run_input_contract_path)
    contract_audit = inspect_run_input_contract(run_input_contract)
    if contract_audit["frozen_test_accessed"]:
        raise ValueError(
            "Frozen/test input detected in run input contract: "
            f"{contract_audit['frozen_test_reference_hits']}"
        )

    sample_panel_columns = list_sample_panel_columns(sample_panel_path)
    forbidden_panel_hits = detect_forbidden_sample_panel_columns(sample_panel_columns)
    if forbidden_panel_hits:
        raise ValueError(f"Forbidden sample panel columns detected: {forbidden_panel_hits}")

    snapshot_id = run_input_contract["snapshot_id"]
    source_db_path = Path(run_input_contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    require_file(source_db_path, "source warehouse DB")

    output_dir = resolve_output_dir(args.run_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    attempt_dir = output_dir / "attempts" / args.attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    score_output_path = output_dir / "model_scores_D0.parquet"
    audit_output_path = output_dir / "model_scores_D0_audit.json"
    source_chain_audit_path = output_dir / "source_chain_audit.json"
    manifest_path = attempt_dir / "run_state_attempt_manifest.json"

    feature_sql = FEATURE_SQL_TEMPLATE.format(sample_panel_path=sql_path(sample_panel_path))
    build_sql = BUILD_SQL_TEMPLATE.format(
        baseline_id=sql_quote(BASELINE_ID),
        score_output_path=sql_path(score_output_path),
    )
    sql_audit = inspect_sql_contract(feature_sql, build_sql)
    if sql_audit["forbidden_sql_hits"]:
        raise ValueError(f"Forbidden SQL tokens detected: {sql_audit['forbidden_sql_hits']}")
    if not sql_audit["score_direction_clear"]:
        raise ValueError("score direction unclear; expected ASC / reversal_rank")
    if not sql_audit["d0_visibility_pass"]:
        raise ValueError("D0 visibility audit failed.")

    con = duckdb.connect()
    try:
        snapshot_rows = con.execute(
            f"""
            SELECT COUNT(*) FROM read_parquet({sql_path(sample_panel_path)})
            WHERE snapshot_id != {sql_quote(snapshot_id)}
            """
        ).fetchone()[0]
    finally:
        con.close()
    if snapshot_rows:
        raise ValueError("project sample panel contains snapshot_id values outside the run input contract.")

    run_build(
        sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
        score_output_path=score_output_path,
    )

    score_summary = summarize_scores(score_output_path)
    model_scores_audit = build_model_scores_audit(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        score_output_path=score_output_path,
        score_summary=score_summary,
        sample_panel_columns=sample_panel_columns,
        sql_audit=sql_audit,
        contract_audit=contract_audit,
    )
    source_chain_audit = build_source_chain_audit(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        score_output_path=score_output_path,
        score_summary=score_summary,
        sql_audit=sql_audit,
        contract_audit=contract_audit,
        sample_panel_columns=sample_panel_columns,
    )
    if source_chain_audit["source_chain_status"] != "pass":
        raise ValueError(f"Source-chain audit blocked: {source_chain_audit['blockers']}")

    attempt_manifest = build_attempt_manifest(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        output_dir=output_dir,
        sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
        score_output_path=score_output_path,
        audit_output_path=audit_output_path,
        source_chain_audit_path=source_chain_audit_path,
    )

    write_json(audit_output_path, model_scores_audit)
    write_json(source_chain_audit_path, source_chain_audit)
    write_json(manifest_path, attempt_manifest)


if __name__ == "__main__":
    main()
