#!/usr/bin/env python3
"""
Build clean baseline family model_scores_D0 and score-layer audits only.

Supported behavior:
- Delegates `no_p98_reversal_baseline_v1` to the existing dedicated builder.
- Builds the remaining clean baseline family candidates locally.

Hard boundaries:
- no p98
- no label diagnostics
- no ML training
- no portfolio
- no metrics/readout
- no frozen test access
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
MANIFEST_PATH = ROOT / "configs" / "clean_baselines" / "clean_baseline_family_manifest.json"
NO_P98_SCRIPT_PATH = ROOT / "scripts" / "build_no_p98_clean_baseline_scores.py"
DEFAULT_ATTEMPT_ID = "attempt_build_clean_baseline_family_scores"
NO_P98_BASELINE_ID = "no_p98_reversal_baseline_v1"
FROZEN_TEST_TOKENS = (
    "frozen_test",
    "fixed_test",
    "test_window_access",
)
FORBIDDEN_SQL_TOKENS = (
    "label_",
    "median_daily_ic",
    "top10_avg_label",
    "top10_bot10_spread",
    "label_5d_next_open_close",
    "realized_return",
    "future_return",
    "actual_exit_date",
    "actual_sell_price",
    "next_open",
    "next_close",
    "tail_exclude_p98",
    "reversal_tail_exclude_p98",
    "nr_daily_p98",
    "percentile_cont(0.98)",
    "frozen_test",
    "fixed_test",
    "holdings",
    "backtest_daily",
)
FORBIDDEN_PANEL_COLUMN_TOKENS = (
    "label_",
    "future",
    "realized",
    "actual_exit",
    "actual_sell",
    "next_open",
    "next_close",
    "frozen",
    "fixed_test",
    "test_window",
)
BASELINE_SPECS: dict[str, dict[str, Any]] = {
    "clean_momentum_20d_baseline_v1": {
        "source_candidate_scheme_id": "clean_momentum_20d_source_v1",
        "score_direction": "descending 20d cumulative return / stronger momentum first",
        "used_data_fields": ["adj_close", "ranking_eligible_D0", "snapshot_id"],
        "required_bar_fields": ["adj_close"],
        "feature_sql_template": """
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

CREATE OR REPLACE VIEW momentum_features AS
SELECT
    snapshot_id,
    ts_code AS instrument,
    trade_date AS signal_date,
    CASE
        WHEN LAG(adj_close, 20) OVER (
            PARTITION BY snapshot_id, ts_code
            ORDER BY trade_date
        ) > 1e-12
        THEN adj_close / LAG(adj_close, 20) OVER (
            PARTITION BY snapshot_id, ts_code
            ORDER BY trade_date
        ) - 1.0
        ELSE NULL
    END AS momentum_20d_raw
FROM bars;
""",
        "build_sql_template": """
COPY (
    WITH eligible AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            f.momentum_20d_raw
        FROM sample_panel s
        LEFT JOIN momentum_features f
          ON s.snapshot_id = f.snapshot_id
         AND s.instrument = f.instrument
         AND s.signal_date = f.signal_date
        WHERE s.ranking_eligible_D0
          AND f.momentum_20d_raw IS NOT NULL
    ),
    ranked AS (
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            momentum_20d_raw,
            PERCENT_RANK() OVER (
                PARTITION BY snapshot_id, signal_date
                ORDER BY momentum_20d_raw DESC, instrument ASC
            ) AS momentum_rank
        FROM eligible
    )
    SELECT
        s.snapshot_id,
        s.instrument,
        s.signal_date,
        CAST({baseline_id} AS VARCHAR) AS candidate_scheme_id,
        CAST({baseline_id} AS VARCHAR) AS baseline_id,
        r.momentum_20d_raw,
        r.momentum_rank,
        r.momentum_rank AS model_score_D0,
        CASE WHEN r.momentum_rank IS NOT NULL THEN 1 ELSE 0 END AS score_component_count
    FROM sample_panel s
    LEFT JOIN ranked r
      ON s.snapshot_id = r.snapshot_id
     AND s.instrument = r.instrument
     AND s.signal_date = r.signal_date
) TO {score_output_path} (FORMAT PARQUET);
""",
        "direction_sql_token": "order by momentum_20d_raw desc, instrument asc",
        "d0_check_tokens": {
            "adj_close_present": "adj_close",
            "lag_20_present": "lag(adj_close, 20)",
            "ranking_guard_present": "where s.ranking_eligible_d0",
            "cross_section_partition_present": "partition by snapshot_id, signal_date",
            "no_lead_usage": "lead(",
            "no_following_usage": "following",
        },
    },
    "clean_liquidity_adjusted_reversal_baseline_v1": {
        "source_candidate_scheme_id": "clean_liquidity_adjusted_reversal_source_v1",
        "score_direction": "ascending 1d return first, descending liquidity tiebreak",
        "used_data_fields": ["adj_close", "vol", "amount", "ranking_eligible_D0", "snapshot_id"],
        "required_bar_fields": ["adj_close", "vol", "amount"],
        "liquidity_field_used": "amount",
        "volume_field_source": "vol",
        "amount_field_source": "amount",
        "feature_sql_template": """
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
    adj_close,
    vol,
    amount
FROM warehouse_db.serving.vw_bars_daily;

CREATE OR REPLACE VIEW reversal_liquidity_features AS
SELECT
    snapshot_id,
    ts_code AS instrument,
    trade_date AS signal_date,
    CASE
        WHEN LAG(adj_close, 1) OVER (
            PARTITION BY snapshot_id, ts_code
            ORDER BY trade_date
        ) > 1e-12
        THEN adj_close / LAG(adj_close, 1) OVER (
            PARTITION BY snapshot_id, ts_code
            ORDER BY trade_date
        ) - 1.0
        ELSE NULL
    END AS reversal_1d_raw,
    MEDIAN(vol) OVER (
        PARTITION BY snapshot_id, ts_code
        ORDER BY trade_date
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS median_vol_20d,
    MEDIAN(amount) OVER (
        PARTITION BY snapshot_id, ts_code
        ORDER BY trade_date
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS median_amount_20d
FROM bars;
""",
        "build_sql_template": """
COPY (
    WITH eligible AS (
        SELECT
            s.snapshot_id,
            s.instrument,
            s.signal_date,
            f.reversal_1d_raw,
            f.median_vol_20d,
            f.median_amount_20d
        FROM sample_panel s
        LEFT JOIN reversal_liquidity_features f
          ON s.snapshot_id = f.snapshot_id
         AND s.instrument = f.instrument
         AND s.signal_date = f.signal_date
        WHERE s.ranking_eligible_D0
          AND f.reversal_1d_raw IS NOT NULL
          AND f.median_vol_20d IS NOT NULL
          AND f.median_amount_20d IS NOT NULL
    ),
    ranked AS (
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            reversal_1d_raw,
            median_vol_20d,
            median_amount_20d,
            PERCENT_RANK() OVER (
                PARTITION BY snapshot_id, signal_date
                ORDER BY reversal_1d_raw ASC, median_amount_20d DESC, instrument ASC
            ) AS reversal_liquidity_rank
        FROM eligible
    )
    SELECT
        s.snapshot_id,
        s.instrument,
        s.signal_date,
        CAST({baseline_id} AS VARCHAR) AS candidate_scheme_id,
        CAST({baseline_id} AS VARCHAR) AS baseline_id,
        r.reversal_1d_raw,
        r.median_vol_20d,
        r.median_amount_20d,
        r.reversal_liquidity_rank,
        r.reversal_liquidity_rank AS model_score_D0,
        CASE WHEN r.reversal_liquidity_rank IS NOT NULL THEN 1 ELSE 0 END AS score_component_count
    FROM sample_panel s
    LEFT JOIN ranked r
      ON s.snapshot_id = r.snapshot_id
     AND s.instrument = r.instrument
     AND s.signal_date = r.signal_date
) TO {score_output_path} (FORMAT PARQUET);
""",
        "direction_sql_token": (
            "order by reversal_1d_raw asc, median_amount_20d desc, instrument asc"
        ),
        "d0_check_tokens": {
            "adj_close_present": "adj_close",
            "vol_present": "vol",
            "amount_present": "amount",
            "lag_1_present": "lag(adj_close, 1)",
            "median_vol_20d_present": "median(vol) over",
            "median_amount_20d_present": "median(amount) over",
            "window_20d_present": "rows between 19 preceding and current row",
            "ranking_guard_present": "where s.ranking_eligible_d0",
            "cross_section_partition_present": "partition by snapshot_id, signal_date",
            "no_lead_usage": "lead(",
            "no_following_usage": "following",
        },
    },
    "clean_equal_weight_random_eligible_baseline_v1": {
        "source_candidate_scheme_id": "clean_equal_weight_random_eligible_source_v1",
        "score_direction": "ascending deterministic hash / pseudo-random but reproducible order",
        "used_data_fields": ["instrument_id", "ranking_eligible_D0", "snapshot_id"],
        "required_bar_fields": [],
        "feature_sql_template": """
CREATE OR REPLACE VIEW sample_panel AS
SELECT
    snapshot_id,
    instrument,
    signal_date,
    ranking_eligible_D0
FROM read_parquet({sample_panel_path});
""",
        "build_sql_template": """
COPY (
    WITH eligible AS (
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            MD5(
                CAST(snapshot_id AS VARCHAR)
                || '|'
                || CAST(instrument AS VARCHAR)
                || '|'
                || CAST({baseline_id} AS VARCHAR)
            ) AS stable_hash
        FROM sample_panel
        WHERE ranking_eligible_D0
    ),
    ranked AS (
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            stable_hash,
            PERCENT_RANK() OVER (
                PARTITION BY snapshot_id, signal_date
                ORDER BY stable_hash ASC, instrument ASC
            ) AS hash_rank
        FROM eligible
    )
    SELECT
        s.snapshot_id,
        s.instrument,
        s.signal_date,
        CAST({baseline_id} AS VARCHAR) AS candidate_scheme_id,
        CAST({baseline_id} AS VARCHAR) AS baseline_id,
        r.stable_hash,
        r.hash_rank,
        r.hash_rank AS model_score_D0,
        CASE WHEN r.hash_rank IS NOT NULL THEN 1 ELSE 0 END AS score_component_count
    FROM sample_panel s
    LEFT JOIN ranked r
      ON s.snapshot_id = r.snapshot_id
     AND s.instrument = r.instrument
     AND s.signal_date = r.signal_date
) TO {score_output_path} (FORMAT PARQUET);
""",
        "direction_sql_token": "order by stable_hash asc, instrument asc",
        "d0_check_tokens": {
            "md5_present": "md5(",
            "baseline_id_salt_present": "cast(",
            "ranking_guard_present": "where ranking_eligible_d0",
            "cross_section_partition_present": "partition by snapshot_id, signal_date",
            "no_lead_usage": "lead(",
            "no_following_usage": "following",
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build clean baseline family model_scores_D0 and score-layer audits."
    )
    parser.add_argument("--run-id", required=True, help="Run identifier for this score-layer build.")
    parser.add_argument(
        "--baseline-id",
        required=True,
        help="Baseline identifier from clean_baseline_family_manifest.json.",
    )
    parser.add_argument(
        "--project-sample-panel",
        "--clean-sample-panel",
        dest="project_sample_panel",
        required=True,
        help="Path to clean/project sample panel parquet.",
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


def resolve_output_dir(run_id: str, baseline_id: str, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    return Path(tempfile.gettempdir()) / run_id / baseline_id


def load_family_manifest() -> dict[str, Any]:
    return load_json(MANIFEST_PATH)


def resolve_manifest_baseline(baseline_id: str) -> dict[str, Any]:
    manifest = load_family_manifest()
    for baseline in manifest["baselines"]:
        if baseline.get("baseline_id") == baseline_id:
            return baseline
    raise ValueError(f"baseline_id not found in clean baseline family manifest: {baseline_id}")


def list_parquet_columns(parquet_path: Path) -> list[str]:
    con = duckdb.connect()
    try:
        rows = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({sql_path(parquet_path)})"
        ).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def list_source_bar_columns(source_db_path: Path) -> list[str]:
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        rows = con.execute("DESCRIBE warehouse_db.serving.vw_bars_daily").fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def detect_forbidden_sample_panel_columns(columns: list[str]) -> list[str]:
    hits: list[str] = []
    for column in columns:
        lowered = column.lower()
        if any(token in lowered for token in FORBIDDEN_PANEL_COLUMN_TOKENS):
            hits.append(column)
    return sorted(set(hits))


def inspect_run_input_contract(run_input_contract: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(run_input_contract, ensure_ascii=False).lower()
    frozen_hits = [token for token in FROZEN_TEST_TOKENS if token in text]
    return {
        "frozen_test_reference_hits": frozen_hits,
        "frozen_test_accessed": bool(frozen_hits),
    }


def build_sql_contract(
    *,
    baseline_id: str,
    sample_panel_path: Path,
    score_output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    spec = BASELINE_SPECS[baseline_id]
    feature_sql = spec["feature_sql_template"].format(sample_panel_path=sql_path(sample_panel_path))
    build_sql = spec["build_sql_template"].format(
        baseline_id=sql_quote(baseline_id),
        score_output_path=sql_path(score_output_path),
    )
    return feature_sql, build_sql, spec


def inspect_sql_contract(feature_sql: str, build_sql: str, spec: dict[str, Any]) -> dict[str, Any]:
    sql_text = f"{feature_sql}\n{build_sql}".lower()
    forbidden_hits = [token for token in FORBIDDEN_SQL_TOKENS if token in sql_text]

    checks: dict[str, bool] = {}
    for check_name, token in spec["d0_check_tokens"].items():
        if check_name.startswith("no_"):
            checks[check_name] = token not in sql_text
        else:
            checks[check_name] = token in sql_text

    direction_present = spec["direction_sql_token"] in sql_text
    return {
        "forbidden_sql_hits": forbidden_hits,
        "score_direction": spec["score_direction"] if direction_present else "unknown",
        "score_direction_clear": direction_present,
        "d0_visibility_checks": checks,
        "d0_visibility_pass": all(checks.values()),
    }


def validate_required_bar_fields(source_db_path: Path, required_bar_fields: list[str]) -> list[str]:
    if not required_bar_fields:
        return []
    columns = list_source_bar_columns(source_db_path)
    column_set = {column.lower() for column in columns}
    missing = [field for field in required_bar_fields if field.lower() not in column_set]
    return missing


def run_build(
    *,
    baseline_id: str,
    sample_panel_path: Path,
    source_db_path: Path,
    score_output_path: Path,
) -> dict[str, Any]:
    feature_sql, build_sql, spec = build_sql_contract(
        baseline_id=baseline_id,
        sample_panel_path=sample_panel_path,
        score_output_path=score_output_path,
    )
    sql_audit = inspect_sql_contract(feature_sql, build_sql, spec)
    if sql_audit["forbidden_sql_hits"]:
        raise ValueError(f"Forbidden SQL tokens detected: {sql_audit['forbidden_sql_hits']}")
    if not sql_audit["score_direction_clear"]:
        raise ValueError(f"score direction unclear for baseline_id={baseline_id}")
    if not sql_audit["d0_visibility_pass"]:
        raise ValueError(f"D0 visibility audit failed for baseline_id={baseline_id}")

    con = duckdb.connect()
    try:
        if spec["required_bar_fields"]:
            con.execute(f"ATTACH {sql_path(source_db_path)} AS warehouse_db (READ_ONLY)")
        con.execute(feature_sql)
        con.execute(build_sql)
    finally:
        con.close()
    return {
        "feature_sql": feature_sql,
        "build_sql": build_sql,
        "spec": spec,
        "sql_audit": sql_audit,
    }


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
    baseline_id: str,
    score_output_path: Path,
    score_summary: dict[str, int],
    sample_panel_columns: list[str],
    sql_audit: dict[str, Any],
    contract_audit: dict[str, Any],
    manifest_baseline: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    forbidden_panel_hits = detect_forbidden_sample_panel_columns(sample_panel_columns)
    leakage_pass = (
        not forbidden_panel_hits
        and not sql_audit["forbidden_sql_hits"]
        and not contract_audit["frozen_test_accessed"]
        and sql_audit["score_direction_clear"]
        and sql_audit["d0_visibility_pass"]
    )
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_scheme_id": baseline_id,
        "baseline_id": baseline_id,
        "source_candidate_scheme_id": spec["source_candidate_scheme_id"],
        "score_output_path": score_output_path.as_posix(),
        "row_count": score_summary["row_count"],
        "null_score_count": score_summary["null_score_count"],
        "nonfinite_score_count": score_summary["nonfinite_score_count"],
        "summary_counts": score_summary,
        "score_direction": spec["score_direction"],
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "sample_panel_columns": sample_panel_columns,
        "used_data_fields": spec["used_data_fields"],
        "liquidity_field_used": spec.get("liquidity_field_used"),
        "volume_field_source": spec.get("volume_field_source"),
        "amount_field_source": spec.get("amount_field_source"),
        "manifest_allowed_inputs": manifest_baseline["allowed_inputs"],
        "manifest_forbidden_inputs": manifest_baseline["forbidden_inputs"],
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
            "No p98 component was used.",
            "No label diagnostics were used.",
            "No frozen test access was used.",
            "No portfolio or metrics/readout artifacts were produced.",
        ],
    }


def build_source_chain_audit(
    *,
    run_id: str,
    attempt_id: str,
    baseline_id: str,
    score_output_path: Path,
    score_summary: dict[str, int],
    sample_panel_columns: list[str],
    sql_audit: dict[str, Any],
    contract_audit: dict[str, Any],
    manifest_baseline: dict[str, Any],
    spec: dict[str, Any],
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

    leakage_pass = not blockers
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_scheme_id": baseline_id,
        "baseline_id": baseline_id,
        "source_candidate_scheme_id": spec["source_candidate_scheme_id"],
        "source_chain_status": "pass" if not blockers else "blocked",
        "score_output_path": score_output_path.as_posix(),
        "row_count": score_summary["row_count"],
        "null_score_count": score_summary["null_score_count"],
        "nonfinite_score_count": score_summary["nonfinite_score_count"],
        "summary_counts": score_summary,
        "score_direction": spec["score_direction"],
        "p98_used": False,
        "label_diagnostics_used": False,
        "frozen_test_accessed": False,
        "manifest_allowed_inputs": manifest_baseline["allowed_inputs"],
        "manifest_forbidden_inputs": manifest_baseline["forbidden_inputs"],
        "used_data_fields": spec["used_data_fields"],
        "liquidity_field_used": spec.get("liquidity_field_used"),
        "volume_field_source": spec.get("volume_field_source"),
        "amount_field_source": spec.get("amount_field_source"),
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
        "blockers": blockers,
        "notes": [
            f"Score direction fixed to {spec['score_direction']}.",
            "No p98, no label diagnostics, no frozen test access.",
        ],
    }


def build_attempt_manifest(
    *,
    run_id: str,
    attempt_id: str,
    baseline_id: str,
    output_dir: Path,
    sample_panel_path: Path,
    source_db_path: Path,
    score_output_path: Path,
    audit_output_path: Path,
    source_chain_audit_path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "run_type": "clean_baseline_family_score_build",
        "candidate_scheme_id": baseline_id,
        "baseline_id": baseline_id,
        "source_candidate_scheme_id": spec["source_candidate_scheme_id"],
        "parameters": {
            "score_direction": spec["score_direction"],
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
            "D0 visible only score-layer baseline build.",
            "No p98, no label diagnostics, no frozen test access.",
            "No portfolio, no holdings, no backtest_daily, no metrics/readout.",
        ],
    }


def validate_snapshot_alignment(sample_panel_path: Path, snapshot_id: str) -> None:
    con = duckdb.connect()
    try:
        mismatch_rows = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet({sql_path(sample_panel_path)})
            WHERE snapshot_id != {sql_quote(snapshot_id)}
            """
        ).fetchone()[0]
    finally:
        con.close()
    if mismatch_rows:
        raise ValueError("project sample panel contains snapshot_id values outside the run input contract.")


def delegate_no_p98_builder(args: argparse.Namespace) -> None:
    require_file(NO_P98_SCRIPT_PATH, "no_p98 builder script")
    cmd = [
        sys.executable,
        str(NO_P98_SCRIPT_PATH),
        "--run-id",
        args.run_id,
        "--project-sample-panel",
        args.project_sample_panel,
        "--run-input-contract",
        args.run_input_contract,
        "--attempt-id",
        args.attempt_id,
    ]
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    if result.stdout:
        sys.stdout.write(result.stdout)


def main() -> None:
    args = parse_args()

    manifest_baseline = resolve_manifest_baseline(args.baseline_id)
    if manifest_baseline["baseline_id"] != args.baseline_id:
        raise ValueError("Manifest baseline_id mismatch.")

    if args.baseline_id == NO_P98_BASELINE_ID:
        delegate_no_p98_builder(args)
        return

    if args.baseline_id not in BASELINE_SPECS:
        raise ValueError(f"Unsupported clean baseline family builder: {args.baseline_id}")

    sample_panel_path = require_file(Path(args.project_sample_panel), "project sample panel")
    run_input_contract_path = require_file(Path(args.run_input_contract), "run input contract")
    run_input_contract = load_json(run_input_contract_path)
    contract_audit = inspect_run_input_contract(run_input_contract)
    if contract_audit["frozen_test_accessed"]:
        raise ValueError(
            "Frozen/test input detected in run input contract: "
            f"{contract_audit['frozen_test_reference_hits']}"
        )

    sample_panel_columns = list_parquet_columns(sample_panel_path)
    forbidden_panel_hits = detect_forbidden_sample_panel_columns(sample_panel_columns)
    if forbidden_panel_hits:
        raise ValueError(f"Forbidden sample panel columns detected: {forbidden_panel_hits}")

    snapshot_id = str(run_input_contract["snapshot_id"])
    source_db_path = Path(run_input_contract["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    spec = BASELINE_SPECS[args.baseline_id]
    if spec["required_bar_fields"]:
        require_file(source_db_path, "source warehouse DB")
        missing_bar_fields = validate_required_bar_fields(source_db_path, spec["required_bar_fields"])
        if missing_bar_fields:
            raise ValueError(f"Missing required warehouse bar fields: {missing_bar_fields}")

    validate_snapshot_alignment(sample_panel_path, snapshot_id)

    output_dir = resolve_output_dir(args.run_id, args.baseline_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    attempt_dir = output_dir / "attempts" / args.attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    score_output_path = output_dir / "model_scores_D0.parquet"
    audit_output_path = output_dir / "model_scores_D0_audit.json"
    source_chain_audit_path = output_dir / "source_chain_audit.json"
    manifest_path = attempt_dir / "run_state_attempt_manifest.json"

    build_result = run_build(
        baseline_id=args.baseline_id,
        sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
        score_output_path=score_output_path,
    )
    score_summary = summarize_scores(score_output_path)
    model_scores_audit = build_model_scores_audit(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        baseline_id=args.baseline_id,
        score_output_path=score_output_path,
        score_summary=score_summary,
        sample_panel_columns=sample_panel_columns,
        sql_audit=build_result["sql_audit"],
        contract_audit=contract_audit,
        manifest_baseline=manifest_baseline,
        spec=spec,
    )
    source_chain_audit = build_source_chain_audit(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        baseline_id=args.baseline_id,
        score_output_path=score_output_path,
        score_summary=score_summary,
        sample_panel_columns=sample_panel_columns,
        sql_audit=build_result["sql_audit"],
        contract_audit=contract_audit,
        manifest_baseline=manifest_baseline,
        spec=spec,
    )
    if source_chain_audit["source_chain_status"] != "pass":
        raise ValueError(f"Source-chain audit blocked: {source_chain_audit['blockers']}")

    attempt_manifest = build_attempt_manifest(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        baseline_id=args.baseline_id,
        output_dir=output_dir,
        sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
        score_output_path=score_output_path,
        audit_output_path=audit_output_path,
        source_chain_audit_path=source_chain_audit_path,
        spec=spec,
    )

    write_json(audit_output_path, model_scores_audit)
    write_json(source_chain_audit_path, source_chain_audit)
    write_json(manifest_path, attempt_manifest)


if __name__ == "__main__":
    main()
