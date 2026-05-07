#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build minimal project-owned run-state tables with real TopK/execution logic.

Inputs:
- project_label_panel.parquet (not directly used yet, but expected in run directory)
- project_sample_panel.parquet
- project_execution_panel.parquet
- model_scores_D0.parquet or model_scores_D0.csv (optional default name in run directory,
  or pass explicitly via --scores-path)

Outputs:
- attempts/<attempt_id>/ranking_state_daily.parquet
- attempts/<attempt_id>/execution_state_daily.parquet
- attempts/<attempt_id>/data_quality_audit.json
- attempts/<attempt_id>/run_state_attempt_manifest.json
- run_state_latest_attempt.json

This script implements the minimum project-owned run-state logic required by the
framework:
- model_score_D0 comes from a project-owned score input file
- topk_frozen_D0 is ranked only within ranking_eligible_D0 entries
- ties break by instrument ascending
- execution_attempt_D1 = topk_frozen_D0
- entry_filled_D1 = execution_attempt_D1 & entry_tradeable
- backtest_executable = entry_filled_D1
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path("/Users/wy/MiscProject/multi_factor")
ARTIFACTS_RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
CANDIDATE_SCHEME_REGISTRY = RESEARCH_REGISTRY_DIR / "candidate_scheme_registry.jsonl"
RESEARCH_ROUND_REGISTRY = RESEARCH_REGISTRY_DIR / "research_round_registry.jsonl"
SCHEME_ATTEMPT_LOG = RESEARCH_REGISTRY_DIR / "scheme_attempt_log.jsonl"
FAILURE_EVIDENCE_LOG = RESEARCH_REGISTRY_DIR / "failure_evidence_log.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build minimal run-state tables with TopK logic.")
    parser.add_argument("--run-id", required=True, help="Project-side run identifier.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Optional run-state input directory. Defaults to artifacts/run_state/<run_id>/",
    )
    parser.add_argument(
        "--run-type",
        default=None,
        help="Optional run type label, e.g. exploratory, fixed_test, walk_forward.",
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="Optional rerun attempt identifier. Defaults to a timestamped attempt id.",
    )
    parser.add_argument(
        "--candidate-scheme-id",
        default=None,
        help="Optional candidate scheme identifier to carry into ranking_state_daily.",
    )
    parser.add_argument(
        "--research-round-id",
        default=None,
        help="Optional research round identifier for registry logging.",
    )
    parser.add_argument(
        "--scores-path",
        default=None,
        help=(
            "Optional model score input file. Supported suffixes: .parquet, .csv. "
            "If omitted, the script looks for model_scores_D0.parquet or model_scores_D0.csv "
            "under the run directory."
        ),
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=10,
        help="TopK freeze size. Defaults to 10 per framework v1.",
    )
    parser.add_argument(
        "--signal-date-chunk-size",
        type=int,
        default=5,
        help="Number of signal_date values to materialize per parquet write chunk.",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=8,
        help="DuckDB thread cap for full runs. Defaults to 8.",
    )
    parser.add_argument(
        "--memory-limit-gb",
        type=float,
        default=20.0,
        help="DuckDB memory limit in GB. Defaults to 20.0.",
    )
    return parser.parse_args()


def resolve_run_dir(run_id: str, input_dir: str | None) -> Path:
    run_dir = Path(input_dir) if input_dir else (ARTIFACTS_RUN_STATE_DIR / run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def require_input(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return path


def sql_quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def resolve_scores_path(run_dir: Path, scores_path: str | None) -> Path:
    if scores_path:
        return require_input(Path(scores_path))

    for candidate in ("model_scores_D0.parquet", "model_scores_D0.csv"):
        path = run_dir / candidate
        if path.exists():
            return path

    raise FileNotFoundError(
        "Model score input not found. Provide --scores-path or place "
        "model_scores_D0.parquet/model_scores_D0.csv in the run directory."
    )


def score_reader_sql(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return f"read_parquet({sql_path(path)})"
    if suffix == ".csv":
        return f"read_csv_auto({sql_path(path)}, HEADER=TRUE)"
    raise ValueError(f"Unsupported score input suffix: {suffix}")


def existing_columns(con: duckdb.DuckDBPyConnection, reader_sql: str) -> set[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM {reader_sql}").fetchall()
    return {row[0] for row in rows}


def load_existing_audit(path: Path) -> dict:
    if not path.exists():
        return {
            "run_id": "",
            "snapshot_id": "",
            "field_mapping_version": "unknown",
            "shared_source_degraded_flags": {},
            "summary_counts": {},
            "fatal_blockers": [],
            "warnings": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def unique_strings(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def latest_registry_entry(rows: list[dict], key: str, value: str) -> dict | None:
    matched = [row for row in rows if row.get(key) == value]
    return matched[-1] if matched else None


def preregistration_path(research_round_id: str) -> Path:
    return RESEARCH_REGISTRY_DIR / "research_rounds" / research_round_id / "preregistration.json"


def load_preregistration(research_round_id: str) -> dict:
    path = preregistration_path(research_round_id)
    if not path.exists():
        raise FileNotFoundError(
            f"Preregistration file not found for research_round_id={research_round_id}: {path}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry_guardrails(candidate_scheme_id: str | None, research_round_id: str | None) -> dict:
    if not candidate_scheme_id:
        raise ValueError("Formal full-chain runs require a non-null candidate_scheme_id.")
    if not research_round_id:
        raise ValueError("Formal full-chain runs require a non-null research_round_id.")

    candidate_entry = latest_registry_entry(
        load_jsonl(CANDIDATE_SCHEME_REGISTRY), "candidate_scheme_id", candidate_scheme_id
    )
    if candidate_entry is None:
        raise ValueError(
            f"candidate_scheme_id is not registered before full-chain execution: {candidate_scheme_id}"
        )

    research_round_entry = latest_registry_entry(
        load_jsonl(RESEARCH_ROUND_REGISTRY), "research_round_id", research_round_id
    )
    if research_round_entry is None:
        raise ValueError(
            f"research_round_id is not registered before full-chain execution: {research_round_id}"
        )

    prereg = load_preregistration(research_round_id)
    prereg_candidates = prereg.get("candidate_scheme_ids", [])
    baseline_reference_candidate_scheme_id = prereg.get("baseline_reference_candidate_scheme_id")
    if candidate_scheme_id not in prereg_candidates and candidate_scheme_id != baseline_reference_candidate_scheme_id:
        raise ValueError(
            "candidate_scheme_id is not included in preregistration candidate list or declared baseline reference: "
            f"{candidate_scheme_id}"
        )

    changed_dimension = prereg.get("changed_dimension")
    if not isinstance(changed_dimension, str) or not changed_dimension.strip():
        raise ValueError(
            "Preregistration must declare exactly one non-empty changed_dimension "
            "before full-chain execution."
        )

    change_control_rule = prereg.get("change_control_rule")
    if change_control_rule != "single_dimension_only":
        raise ValueError(
            "Preregistration must set change_control_rule = 'single_dimension_only' "
            "before full-chain execution."
        )

    return {
        "candidate_entry": candidate_entry,
        "research_round_entry": research_round_entry,
        "preregistration": prereg,
        "changed_dimension": changed_dimension.strip(),
    }


def parse_liquidity_guard(preregistration: dict) -> dict | None:
    changed_dimension = preregistration.get("changed_dimension")
    guard_contract = preregistration.get("guard_contract")
    if not isinstance(guard_contract, dict):
        guard_contract = preregistration.get("guard_contract_frozen")
    if not isinstance(guard_contract, dict):
        return None

    if changed_dimension in {"ranking_eligibility_guard", "universe_eligibility_guard"}:
        guard_application_stage = changed_dimension
    elif changed_dimension in {"score_family", "weight_mapping", "portfolio_extraction", "portfolio_refresh_rule"}:
        guard_application_stage = guard_contract.get("guard_application_stage")
        if guard_application_stage not in {"ranking_eligibility_guard", "universe_eligibility_guard"}:
            raise ValueError(
                f"{changed_dimension} preregistration with a frozen selection guard must declare "
                "guard_contract.guard_application_stage as ranking_eligibility_guard or "
                "universe_eligibility_guard."
            )
    else:
        return None

    guard_name = guard_contract.get("guard_name")
    liquidity_field = guard_contract.get("liquidity_field", "liquidity_20d_raw")
    liquidity_min_percentile = guard_contract.get("liquidity_min_percentile")
    if not isinstance(guard_name, str) or not guard_name.strip():
        raise ValueError("guard_contract.guard_name must be a non-empty string.")
    if liquidity_field != "liquidity_20d_raw":
        raise ValueError(
            "v1 minimal ranking_eligibility_guard only supports liquidity_field = 'liquidity_20d_raw'."
        )
    if not isinstance(liquidity_min_percentile, (int, float)):
        raise ValueError("guard_contract.liquidity_min_percentile must be numeric.")

    threshold = float(liquidity_min_percentile)
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("guard_contract.liquidity_min_percentile must be within [0, 1].")

    return {
        "changed_dimension": changed_dimension,
        "guard_application_stage": guard_application_stage,
        "guard_name": guard_name.strip(),
        "liquidity_field": liquidity_field,
        "liquidity_min_percentile": threshold,
    }


def default_attempt_id() -> str:
    return "attempt_" + datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def prepare_attempt_dir(run_dir: Path, attempt_id: str) -> Path:
    attempt_dir = run_dir / "attempts" / attempt_id
    if attempt_dir.exists() and any(attempt_dir.iterdir()):
        raise FileExistsError(
            f"Attempt directory already exists and is not empty: {attempt_dir}. "
            "Use a new --attempt-id for each rerun."
        )
    attempt_dir.mkdir(parents=True, exist_ok=True)
    return attempt_dir


def atomic_json_write(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".inprogress")
    write_json(temp_path, payload)
    os.replace(temp_path, path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def link_or_copy(src: Path, dst: Path) -> Path:
    if dst.exists():
        return dst
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


def chunked(items: list[str], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def load_signal_dates(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        """
        SELECT signal_date
        FROM project_sample_panel_t
        GROUP BY signal_date
        ORDER BY signal_date
        """
    ).fetchall()
    return [row[0] for row in rows]


def append_query_to_writer(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    writer: pq.ParquetWriter | None,
    batch_size: int = 1_000_000,
) -> pq.ParquetWriter | None:
    reader = con.execute(sql).fetch_record_batch(rows_per_batch=batch_size)
    for batch in reader:
        table = pa.Table.from_batches([batch])
        if writer is None:
            raise RuntimeError("Parquet writer must be initialized before appending query batches.")
        writer.write_table(table)
    return writer


def ensure_writer(
    con: duckdb.DuckDBPyConnection,
    writer: pq.ParquetWriter | None,
    sql: str,
    output_path: Path,
    batch_size: int = 1_000_000,
) -> pq.ParquetWriter:
    if writer is not None:
        return writer

    reader = con.execute(sql).fetch_record_batch(rows_per_batch=batch_size)
    try:
        first_batch = next(iter(reader))
    except StopIteration as exc:
        raise RuntimeError(f"Query returned no rows when initializing parquet writer: {output_path}") from exc

    table = pa.Table.from_batches([first_batch])
    writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
    writer.write_table(table)
    for batch in reader:
        writer.write_table(pa.Table.from_batches([batch]))
    return writer


def main() -> None:
    args = parse_args()
    if args.topk <= 0:
        raise ValueError("--topk must be positive.")
    if args.signal_date_chunk_size <= 0:
        raise ValueError("--signal-date-chunk-size must be positive.")
    if args.max_threads <= 0:
        raise ValueError("--max-threads must be positive.")
    if args.memory_limit_gb <= 0:
        raise ValueError("--memory-limit-gb must be positive.")

    registry_guardrails = validate_registry_guardrails(args.candidate_scheme_id, args.research_round_id)
    liquidity_guard = parse_liquidity_guard(registry_guardrails["preregistration"])

    run_dir = resolve_run_dir(args.run_id, args.input_dir)
    attempt_id = args.attempt_id or default_attempt_id()
    attempt_dir = prepare_attempt_dir(run_dir, attempt_id)

    source_label_panel = require_input(run_dir / "project_label_panel.parquet")
    source_sample_panel = require_input(run_dir / "project_sample_panel.parquet")
    source_execution_panel = require_input(run_dir / "project_execution_panel.parquet")
    source_scores_path = resolve_scores_path(run_dir, args.scores_path)
    source_base_audit_input = run_dir / "data_quality_audit.json"

    attempt_inputs_dir = attempt_dir / "inputs"
    attempt_inputs_dir.mkdir(parents=True, exist_ok=True)
    label_panel = link_or_copy(source_label_panel, attempt_inputs_dir / source_label_panel.name)
    sample_panel = link_or_copy(source_sample_panel, attempt_inputs_dir / source_sample_panel.name)
    execution_panel = link_or_copy(source_execution_panel, attempt_inputs_dir / source_execution_panel.name)
    scores_path = link_or_copy(source_scores_path, attempt_inputs_dir / source_scores_path.name)
    base_audit_input = (
        link_or_copy(source_base_audit_input, attempt_inputs_dir / source_base_audit_input.name)
        if source_base_audit_input.exists()
        else source_base_audit_input
    )

    ranking_output = attempt_dir / "ranking_state_daily.parquet"
    execution_output = attempt_dir / "execution_state_daily.parquet"
    ranking_inprogress = attempt_dir / "ranking_state_daily.inprogress.parquet"
    execution_inprogress = attempt_dir / "execution_state_daily.inprogress.parquet"
    audit_output = attempt_dir / "data_quality_audit.json"
    audit_inprogress = attempt_dir / "data_quality_audit.inprogress.json"
    attempt_manifest_output = attempt_dir / "run_state_attempt_manifest.json"
    latest_attempt_output = run_dir / "run_state_latest_attempt.json"
    temp_dir = attempt_dir / ".duckdb_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    for output_path in (ranking_inprogress, execution_inprogress, audit_inprogress):
        if output_path.exists():
            output_path.unlink()

    attempt_manifest = {
        "run_id": args.run_id,
        "attempt_id": attempt_id,
        "run_type": args.run_type,
        "research_round_id": args.research_round_id,
        "status": "running",
        "started_at": datetime.now().astimezone().isoformat(),
        "attempt_dir": attempt_dir.as_posix(),
        "input_paths": {
            "project_label_panel": label_panel.as_posix(),
            "project_sample_panel": sample_panel.as_posix(),
            "project_execution_panel": execution_panel.as_posix(),
            "model_scores_D0": scores_path.as_posix(),
            "base_data_quality_audit": base_audit_input.as_posix() if base_audit_input.exists() else None,
        },
        "source_input_paths": {
            "project_label_panel": source_label_panel.as_posix(),
            "project_sample_panel": source_sample_panel.as_posix(),
            "project_execution_panel": source_execution_panel.as_posix(),
            "model_scores_D0": source_scores_path.as_posix(),
            "base_data_quality_audit": source_base_audit_input.as_posix() if source_base_audit_input.exists() else None,
        },
        "output_paths": {
            "ranking_state_daily": ranking_output.as_posix(),
            "execution_state_daily": execution_output.as_posix(),
            "data_quality_audit": audit_output.as_posix(),
        },
        "parameters": {
            "topk": args.topk,
            "signal_date_chunk_size": args.signal_date_chunk_size,
            "max_threads": args.max_threads,
            "memory_limit_gb": args.memory_limit_gb,
            "candidate_scheme_id": args.candidate_scheme_id,
            "changed_dimension": registry_guardrails["changed_dimension"],
            "liquidity_guard": liquidity_guard,
        },
        "registry_preflight": {
            "candidate_scheme_id_registered": True,
            "research_round_id_registered": True,
            "changed_dimension": registry_guardrails["changed_dimension"],
            "change_control_rule": registry_guardrails["preregistration"]["change_control_rule"],
            "preregistration_path": preregistration_path(args.research_round_id).as_posix(),
        },
    }
    atomic_json_write(attempt_manifest_output, attempt_manifest)
    atomic_json_write(
        latest_attempt_output,
        {
            "run_id": args.run_id,
            "attempt_id": attempt_id,
            "status": "running",
            "attempt_dir": attempt_dir.as_posix(),
            "updated_at": attempt_manifest["started_at"],
        },
    )

    con = duckdb.connect()
    effective_candidate_scheme_id = args.candidate_scheme_id
    detected_snapshot_id: str | None = None
    try:
        cpu_count = os.cpu_count() or 4
        threads = max(1, min(args.max_threads, cpu_count - 1 if cpu_count > 1 else 1))
        con.execute(f"PRAGMA threads={threads}")
        con.execute(f"SET memory_limit = '{args.memory_limit_gb:.1f}GB'")
        con.execute("SET preserve_insertion_order = false")
        con.execute(f"SET temp_directory = {sql_path(temp_dir)}")
        con.execute(
            f"""
            CREATE TEMP TABLE project_sample_panel_t AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                ranking_eligible_D0,
                entry_tradeable
            FROM read_parquet({sql_path(sample_panel)})
            """
        )
        detected_snapshot_id = con.execute(
            "SELECT ANY_VALUE(snapshot_id) FROM project_sample_panel_t"
        ).fetchone()[0]
        con.execute(
            f"""
            CREATE TEMP TABLE project_execution_panel_t AS
            SELECT
                snapshot_id,
                instrument,
                signal_date,
                entry_date,
                planned_exit_date
            FROM read_parquet({sql_path(execution_panel)})
            """
        )

        score_reader = score_reader_sql(scores_path)
        score_columns = existing_columns(con, score_reader)
        required_score_columns = {"instrument", "signal_date", "model_score_D0"}
        if liquidity_guard is not None:
            required_score_columns.add("liquidity_rank")
        missing_score_columns = sorted(required_score_columns - score_columns)
        if missing_score_columns:
            raise ValueError(
                "Score input is missing required columns: "
                + ", ".join(missing_score_columns)
            )

        snapshot_select = (
            "CAST(snapshot_id AS VARCHAR) AS snapshot_id,"
            if "snapshot_id" in score_columns
            else "CAST(NULL AS VARCHAR) AS snapshot_id,"
        )
        candidate_select = (
            "CAST(candidate_scheme_id AS VARCHAR) AS candidate_scheme_id"
            if "candidate_scheme_id" in score_columns
            else "CAST(NULL AS VARCHAR) AS candidate_scheme_id"
        )
        liquidity_rank_select = (
            "CAST(liquidity_rank AS DOUBLE) AS liquidity_rank,"
            if "liquidity_rank" in score_columns
            else "CAST(NULL AS DOUBLE) AS liquidity_rank,"
        )
        con.execute(
            f"""
            CREATE TEMP TABLE model_scores_input_t AS
            SELECT
                {snapshot_select}
                CAST(instrument AS VARCHAR) AS instrument,
                CAST(signal_date AS VARCHAR) AS signal_date,
                CAST(model_score_D0 AS DOUBLE) AS model_score_D0,
                {liquidity_rank_select}
                {candidate_select}
            FROM {score_reader}
            """
        )
        distinct_candidates = [
            row[0]
            for row in con.execute(
                """
                SELECT DISTINCT candidate_scheme_id
                FROM model_scores_input_t
                WHERE candidate_scheme_id IS NOT NULL
                ORDER BY candidate_scheme_id
                """
            ).fetchall()
        ]
        if len(distinct_candidates) > 1:
            raise ValueError(
                "Score input contains more than one candidate_scheme_id: "
                + ", ".join(distinct_candidates)
            )
        inferred_candidate_scheme_id = distinct_candidates[0] if distinct_candidates else None
        if (
            args.candidate_scheme_id is not None
            and inferred_candidate_scheme_id is not None
            and args.candidate_scheme_id != inferred_candidate_scheme_id
        ):
            raise ValueError(
                "Provided --candidate-scheme-id does not match score input candidate_scheme_id: "
                f"{args.candidate_scheme_id} != {inferred_candidate_scheme_id}"
            )
        effective_candidate_scheme_id = args.candidate_scheme_id or inferred_candidate_scheme_id
        attempt_manifest["parameters"]["candidate_scheme_id"] = effective_candidate_scheme_id
        atomic_json_write(attempt_manifest_output, attempt_manifest)

        signal_dates = load_signal_dates(con)
        guard_condition = "TRUE"
        guard_pass_projection = "CAST(NULL AS BOOLEAN) AS liquidity_guard_pass_D0,"
        guard_reason_projection = "CAST(NULL AS VARCHAR) AS liquidity_guard_reason,"
        guard_universe_projection = "CAST(NULL AS BOOLEAN) AS universe_guard_pass_D0,"
        guard_kind = (
            liquidity_guard["guard_application_stage"] if liquidity_guard is not None else None
        )
        if liquidity_guard is not None:
            threshold = liquidity_guard["liquidity_min_percentile"]
            guard_condition = f"COALESCE(s.liquidity_rank >= {threshold}, FALSE)"
            guard_pass_projection = (
                f"CASE WHEN s.liquidity_rank IS NULL THEN FALSE "
                f"WHEN s.liquidity_rank >= {threshold} THEN TRUE ELSE FALSE END AS liquidity_guard_pass_D0,"
            )
            failed_reason = (
                "failed_universe_liquidity_guard"
                if guard_kind == "universe_eligibility_guard"
                else "failed_ranking_liquidity_guard"
            )
            guard_reason_projection = (
                f"CASE "
                f"WHEN s.liquidity_rank IS NULL THEN 'missing_liquidity_rank' "
                f"WHEN s.liquidity_rank < {threshold} THEN '{failed_reason}' "
                f"ELSE NULL END AS liquidity_guard_reason,"
            )
            if guard_kind == "universe_eligibility_guard":
                guard_universe_projection = (
                    f"CASE WHEN s.liquidity_rank IS NULL THEN FALSE "
                    f"WHEN s.liquidity_rank >= {threshold} THEN TRUE ELSE FALSE END AS universe_guard_pass_D0,"
                )

        def build_ranking_chunk_sql(date_chunk: list[str]) -> str:
            in_list = ", ".join(sql_quote(value) for value in date_chunk)
            return f"""
                WITH chunk_sample AS (
                    SELECT *
                    FROM project_sample_panel_t
                    WHERE signal_date IN ({in_list})
                ),
                chunk_scores AS (
                    SELECT *
                    FROM model_scores_input_t
                    WHERE signal_date IN ({in_list})
                ),
                ranked_candidates AS (
                    SELECT
                        p.snapshot_id,
                        p.instrument,
                        p.signal_date,
                        s.model_score_D0,
                        COALESCE(s.candidate_scheme_id, CAST({sql_quote(effective_candidate_scheme_id)} AS VARCHAR)) AS candidate_scheme_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY p.snapshot_id, p.signal_date
                            ORDER BY s.model_score_D0 DESC, p.instrument ASC
                        ) AS rank_position,
                        COUNT(*) OVER (
                            PARTITION BY p.snapshot_id, p.signal_date
                        ) AS rankable_count
                    FROM chunk_sample p
                    INNER JOIN chunk_scores s
                        ON p.instrument = s.instrument
                       AND p.signal_date = s.signal_date
                       AND (s.snapshot_id IS NULL OR p.snapshot_id = s.snapshot_id)
                    WHERE p.ranking_eligible_D0
                      AND s.model_score_D0 IS NOT NULL
                      AND isfinite(s.model_score_D0)
                      AND {guard_condition}
                )
                SELECT
                    CAST({sql_quote(args.run_id)} AS VARCHAR) AS run_id,
                    CAST({sql_quote(attempt_id)} AS VARCHAR) AS attempt_id,
                    CAST({sql_quote(args.run_type)} AS VARCHAR) AS run_type,
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    s.model_score_D0,
                    p.ranking_eligible_D0,
                    {guard_pass_projection}
                    {guard_reason_projection}
                    {guard_universe_projection}
                    r.rank_position,
                    CASE
                        WHEN r.rankable_count IS NULL THEN NULL
                        ELSE LEAST(r.rankable_count, {args.topk})
                    END AS topk_threshold_rank,
                    COALESCE(r.rank_position <= {args.topk}, FALSE) AS topk_frozen_D0,
                    COALESCE(s.candidate_scheme_id, CAST({sql_quote(effective_candidate_scheme_id)} AS VARCHAR)) AS candidate_scheme_id
                FROM chunk_sample p
                LEFT JOIN chunk_scores s
                    ON p.instrument = s.instrument
                   AND p.signal_date = s.signal_date
                   AND (s.snapshot_id IS NULL OR p.snapshot_id = s.snapshot_id)
                LEFT JOIN ranked_candidates r
                    ON p.snapshot_id = r.snapshot_id
                   AND p.instrument = r.instrument
                   AND p.signal_date = r.signal_date
            """

        def build_execution_chunk_sql() -> str:
            return f"""
                SELECT
                    r.run_id,
                    r.attempt_id,
                    r.run_type,
                    r.snapshot_id,
                    r.instrument,
                    r.signal_date,
                    e.entry_date,
                    e.planned_exit_date,
                    r.topk_frozen_D0 AS execution_attempt_D1,
                    (r.topk_frozen_D0 AND s.entry_tradeable) AS entry_filled_D1,
                    (r.topk_frozen_D0 AND s.entry_tradeable) AS backtest_executable,
                    CASE
                        WHEN r.topk_frozen_D0 THEN (1.0 / {args.topk})
                        ELSE CAST(NULL AS DOUBLE)
                    END AS target_weight_D0,
                    s.entry_tradeable AS entry_tradeable_shared_flag,
                    CASE
                        WHEN NOT r.ranking_eligible_D0 THEN 'not_ranking_eligible'
                        WHEN r.model_score_D0 IS NULL THEN 'missing_model_score'
                        WHEN NOT isfinite(r.model_score_D0) THEN 'nonfinite_model_score'
                        WHEN NOT r.topk_frozen_D0 THEN 'not_in_topk'
                        WHEN s.entry_tradeable THEN 'filled_D1_open'
                        ELSE 'blocked_D1_not_buyable'
                    END AS entry_filled_reason
                FROM chunk_ranking_t r
                INNER JOIN project_sample_panel_t s
                    ON r.snapshot_id = s.snapshot_id
                   AND r.instrument = s.instrument
                   AND r.signal_date = s.signal_date
                INNER JOIN project_execution_panel_t e
                    ON r.snapshot_id = e.snapshot_id
                   AND r.instrument = e.instrument
                   AND r.signal_date = e.signal_date
            """

        ranking_writer: pq.ParquetWriter | None = None
        execution_writer: pq.ParquetWriter | None = None
        try:
            for date_chunk in chunked(signal_dates, args.signal_date_chunk_size):
                con.execute("DROP TABLE IF EXISTS chunk_ranking_t")
                con.execute(f"CREATE TEMP TABLE chunk_ranking_t AS {build_ranking_chunk_sql(date_chunk)}")

                ranking_sql = "SELECT * FROM chunk_ranking_t"
                execution_sql = build_execution_chunk_sql()
                if ranking_writer is None:
                    ranking_writer = ensure_writer(con, ranking_writer, ranking_sql, ranking_inprogress)
                else:
                    append_query_to_writer(con, ranking_sql, ranking_writer)

                if execution_writer is None:
                    execution_writer = ensure_writer(con, execution_writer, execution_sql, execution_inprogress)
                else:
                    append_query_to_writer(con, execution_sql, execution_writer)
                con.execute("DROP TABLE chunk_ranking_t")
        finally:
            if ranking_writer is not None:
                ranking_writer.close()
            if execution_writer is not None:
                execution_writer.close()

        for output_path in (ranking_inprogress, execution_inprogress):
            if not output_path.exists():
                raise RuntimeError(f"Expected parquet output was not created: {output_path}")

        con.execute(
            f"""
            CREATE OR REPLACE VIEW ranking_state_daily_t AS
            SELECT * FROM read_parquet({sql_path(ranking_inprogress)})
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW execution_state_daily_t AS
            SELECT * FROM read_parquet({sql_path(execution_inprogress)})
            """
        )

        audit = load_existing_audit(base_audit_input)
        warnings = unique_strings(list(audit.get("warnings", [])))
        fatal_blockers = unique_strings(list(audit.get("fatal_blockers", [])))
        summary_counts = dict(audit.get("summary_counts", {}))

        ranking_rows, ranking_anomaly_rows, rankable_rows, null_score_rows, nonfinite_score_rows = con.execute(
            """
            SELECT
                COUNT(*) AS ranking_rows,
                SUM(
                    CASE
                        WHEN ranking_eligible_D0
                         AND (model_score_D0 IS NULL OR NOT isfinite(model_score_D0))
                        THEN 1 ELSE 0
                    END
                ) AS ranking_anomaly_rows,
                SUM(CASE WHEN topk_threshold_rank IS NOT NULL THEN 1 ELSE 0 END) AS rankable_rows,
                SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_score_rows,
                SUM(CASE WHEN model_score_D0 IS NOT NULL AND NOT isfinite(model_score_D0) THEN 1 ELSE 0 END) AS nonfinite_score_rows
            FROM ranking_state_daily_t
            """
        ).fetchone()

        topk_count, execution_state_rows = con.execute(
            """
            SELECT
                SUM(CASE WHEN topk_frozen_D0 THEN 1 ELSE 0 END) AS topk_count,
                COUNT(*) AS execution_state_rows
            FROM ranking_state_daily_t
            """
        ).fetchone()

        entry_filled_count = con.execute(
            """
            SELECT
                SUM(CASE WHEN entry_filled_D1 THEN 1 ELSE 0 END) AS entry_filled_count
            FROM execution_state_daily_t
            """
        ).fetchone()[0]

        per_signal_topk_breaches = con.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT
                    snapshot_id,
                    signal_date
                FROM ranking_state_daily_t
                WHERE topk_frozen_D0
                GROUP BY snapshot_id, signal_date
                HAVING COUNT(*) > {args.topk}
            )
            """
        ).fetchone()[0]

        topk_count = int(topk_count or 0)
        entry_filled_count = int(entry_filled_count or 0)
        unfilled_topk_count = topk_count - entry_filled_count

        summary_counts.update(
            {
                "ranking_state_rows": int(ranking_rows or 0),
                "execution_state_rows": int(execution_state_rows or 0),
                "ranking_anomaly_rows": int(ranking_anomaly_rows or 0),
                "rankable_rows": int(rankable_rows or 0),
                "null_model_score_rows": int(null_score_rows or 0),
                "nonfinite_model_score_rows": int(nonfinite_score_rows or 0),
                "topk_frozen_rows": topk_count,
                "execution_attempt_rows": topk_count,
                "entry_filled_rows": entry_filled_count,
                "backtest_executable_rows": entry_filled_count,
                "unfilled_topk_count": unfilled_topk_count,
                "unfilled_topk_weight": unfilled_topk_count * (1.0 / args.topk),
                "topk_per_signal_breach_count": int(per_signal_topk_breaches or 0),
                "topk_default_used": args.topk,
            }
        )
        if liquidity_guard is not None:
            guard_excluded_rows = con.execute(
                """
                SELECT COUNT(*)
                FROM ranking_state_daily_t
                WHERE ranking_eligible_D0
                  AND COALESCE(liquidity_guard_pass_D0, FALSE) = FALSE
                """
            ).fetchone()[0]
            summary_counts["liquidity_guard_excluded_rows"] = int(guard_excluded_rows or 0)

        if summary_counts["ranking_anomaly_rows"] > 0:
            warnings.append(
                "ranking_eligible_D0 rows with missing or nonfinite model_score_D0 were excluded from TopK."
            )
        if liquidity_guard is not None and summary_counts.get("liquidity_guard_excluded_rows", 0) > 0:
            if guard_kind == "universe_eligibility_guard":
                warnings.append(
                    "universe_eligibility_guard excluded rows from the effective universe before TopK freeze."
                )
            else:
                warnings.append(
                    "ranking_eligibility_guard excluded rows from the ranking universe before TopK freeze."
                )
        if summary_counts["topk_per_signal_breach_count"] > 0:
            fatal_blockers.append("Detected signal dates with more than TopK frozen names.")

        audit["run_id"] = args.run_id
        audit["attempt_id"] = attempt_id
        audit["run_type"] = args.run_type
        audit["research_round_id"] = args.research_round_id
        audit["candidate_scheme_id"] = effective_candidate_scheme_id
        if not audit.get("snapshot_id"):
            audit["snapshot_id"] = detected_snapshot_id
        audit["summary_counts"] = summary_counts
        audit["warnings"] = unique_strings(warnings)
        audit["fatal_blockers"] = unique_strings(fatal_blockers)
        con.commit()
        write_json(audit_inprogress, audit)
        os.replace(ranking_inprogress, ranking_output)
        os.replace(execution_inprogress, execution_output)
        os.replace(audit_inprogress, audit_output)
        completed_at = datetime.now().astimezone().isoformat()
        attempt_manifest["status"] = "completed"
        attempt_manifest["completed_at"] = completed_at
        atomic_json_write(attempt_manifest_output, attempt_manifest)
        atomic_json_write(
            latest_attempt_output,
            {
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "status": "completed",
                "attempt_dir": attempt_dir.as_posix(),
                "updated_at": completed_at,
            },
        )
        append_jsonl(
            SCHEME_ATTEMPT_LOG,
            {
                "logged_at": completed_at,
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "run_type": args.run_type,
                "research_round_id": args.research_round_id,
                "candidate_scheme_id": effective_candidate_scheme_id,
                "status": "completed",
                "snapshot_id": audit.get("snapshot_id"),
                "topk": args.topk,
                "signal_date_chunk_size": args.signal_date_chunk_size,
                "scores_path": source_scores_path.as_posix(),
                "attempt_manifest_path": attempt_manifest_output.as_posix(),
                "data_quality_audit_path": audit_output.as_posix(),
            },
        )
    except Exception as exc:
        failed_at = datetime.now().astimezone().isoformat()
        attempt_manifest["status"] = "failed"
        attempt_manifest["failed_at"] = failed_at
        atomic_json_write(attempt_manifest_output, attempt_manifest)
        atomic_json_write(
            latest_attempt_output,
            {
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "status": "failed",
                "attempt_dir": attempt_dir.as_posix(),
                "updated_at": failed_at,
            },
        )
        append_jsonl(
            SCHEME_ATTEMPT_LOG,
            {
                "logged_at": failed_at,
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "run_type": args.run_type,
                "research_round_id": args.research_round_id,
                "candidate_scheme_id": effective_candidate_scheme_id,
                "status": "failed",
                "snapshot_id": detected_snapshot_id,
                "scores_path": source_scores_path.as_posix(),
                "attempt_manifest_path": attempt_manifest_output.as_posix(),
            },
        )
        append_jsonl(
            FAILURE_EVIDENCE_LOG,
            {
                "logged_at": failed_at,
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "run_type": args.run_type,
                "research_round_id": args.research_round_id,
                "candidate_scheme_id": effective_candidate_scheme_id,
                "snapshot_id": detected_snapshot_id,
                "research_tier": "exploratory" if args.run_type == "exploratory" else None,
                "change_summary": "run_state build failed before successful artifact completion",
                "failure_reason": str(exc),
                "failure_class": exc.__class__.__name__,
                "attempt_manifest_path": attempt_manifest_output.as_posix(),
            },
        )
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()
