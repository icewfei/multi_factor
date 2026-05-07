#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Shared orchestration helpers for single-signal discovery batch runners.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import duckdb


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CONTRACTS_DIR = ROOT / "contracts"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"
PREFLIGHT_SCRIPT = ROOT / "scripts" / "preflight_single_signal_round.py"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_scheme_id: str
    field_name: str
    ranking_direction: str
    interpretation: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_path(path: Path) -> str:
    return sql_quote(path.resolve().as_posix())


def materialize_ranked_single_signal(
    *,
    con: duckdb.DuckDBPyConnection,
    spec: CandidateSpec,
    run_dir: Path,
    score_builder_name: str,
) -> dict:
    score_path = run_dir / "model_scores_D0.parquet"
    audit_path = run_dir / "model_scores_D0_audit.json"
    order_direction = spec.ranking_direction.upper()
    if order_direction not in {"ASC", "DESC"}:
        raise ValueError(f"Unsupported ranking direction: {spec.ranking_direction}")

    con.execute(
        """
        CREATE OR REPLACE VIEW liquidity_ranks AS
        SELECT
            snapshot_id,
            instrument,
            signal_date,
            PERCENT_RANK() OVER (
                PARTITION BY snapshot_id, signal_date
                -- Higher liquidity must map to a higher rank. Ascending sort is
                -- correct because `liquidity_20d_raw` is a monotone proxy on amount.
                ORDER BY liquidity_20d_raw ASC, instrument ASC
            ) AS liquidity_rank
        FROM feature_frame
        WHERE ranking_eligible_D0
          AND liquidity_20d_raw IS NOT NULL
        """
    )

    con.execute(
        f"""
        COPY (
            WITH ranked AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    ranking_eligible_D0,
                    {spec.field_name} AS raw_signal_value,
                    PERCENT_RANK() OVER (
                        PARTITION BY snapshot_id, signal_date
                        ORDER BY {spec.field_name} {order_direction}, instrument ASC
                    ) AS rank_value
                FROM feature_frame
                WHERE ranking_eligible_D0
                  AND {spec.field_name} IS NOT NULL
            )
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                CAST({sql_quote(spec.candidate_scheme_id)} AS VARCHAR) AS candidate_scheme_id,
                CASE
                    WHEN p.ranking_eligible_D0 THEN r.rank_value
                    ELSE CAST(NULL AS DOUBLE)
                END AS model_score_D0,
                l.liquidity_rank,
                CASE
                    WHEN r.rank_value IS NOT NULL THEN 1 ELSE 0
                END AS score_component_count,
                r.raw_signal_value
            FROM project_sample_panel p
            LEFT JOIN ranked r
              ON p.snapshot_id = r.snapshot_id
             AND p.instrument = r.instrument
             AND p.signal_date = r.signal_date
            LEFT JOIN liquidity_ranks l
              ON p.snapshot_id = l.snapshot_id
             AND p.instrument = l.instrument
             AND p.signal_date = l.signal_date
        ) TO {sql_path(score_path)} (FORMAT PARQUET)
        """
    )

    audit_row = con.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN p.ranking_eligible_D0 THEN 1 ELSE 0 END) AS ranking_eligible_rows,
            SUM(CASE WHEN s.model_score_D0 IS NOT NULL THEN 1 ELSE 0 END) AS scored_rows,
            SUM(CASE WHEN p.ranking_eligible_D0 AND s.model_score_D0 IS NULL THEN 1 ELSE 0 END) AS eligible_unscored_rows,
            AVG(s.model_score_D0) AS avg_score,
            MIN(s.model_score_D0) AS min_score,
            MAX(s.model_score_D0) AS max_score
        FROM read_parquet({sql_path(score_path)}) s
        INNER JOIN project_sample_panel p
          ON s.snapshot_id = p.snapshot_id
         AND s.instrument = p.instrument
         AND s.signal_date = p.signal_date
        """
    ).fetchone()
    audit = {
        "candidate_scheme_id": spec.candidate_scheme_id,
        "field_name": spec.field_name,
        "ranking_direction": spec.ranking_direction,
        "score_builder": score_builder_name,
        "summary_counts": {
            "total_rows": int(audit_row[0] or 0),
            "ranking_eligible_rows": int(audit_row[1] or 0),
            "scored_rows": int(audit_row[2] or 0),
            "eligible_unscored_rows": int(audit_row[3] or 0),
        },
        "score_distribution": {
            "avg_score": float(audit_row[4]) if audit_row[4] is not None else None,
            "min_score": float(audit_row[5]) if audit_row[5] is not None else None,
            "max_score": float(audit_row[6]) if audit_row[6] is not None else None,
        },
        "notes": [
            "Single-signal discovery score file.",
            "Exactly one raw signal is ranked per candidate.",
            "Null scores are preserved for audit and no imputation is used.",
        ],
    }
    write_json(audit_path, audit)
    return audit


def ensure_base_inputs(base_run_dir: Path, round_label: str) -> tuple[Path, Path]:
    sample = base_run_dir / "project_sample_panel.parquet"
    label = base_run_dir / "project_label_panel.parquet"
    if not sample.exists() or not label.exists():
        raise FileNotFoundError(
            f"Shared {round_label} base panels are missing. Expected both {sample} and {label}."
        )
    return sample, label


def classify_signal(payload: dict) -> str:
    ic = payload["ic_readout"]["full_sample_corr_ic"]
    avg_daily = payload["ic_readout"]["avg_daily_ic"]
    positive_share = payload["ic_readout"]["positive_daily_ic_share"]
    top10 = payload["top_slice_readout"]["avg_label_top10"]
    rank11_20 = payload["top_slice_readout"]["avg_label_rank11_20"]
    bottom10 = payload["top_slice_readout"]["avg_label_bottom10"]

    if None in (ic, avg_daily, positive_share, top10, rank11_20, bottom10):
        return "signal_edge_mixed"

    if (
        ic > 0
        and avg_daily > 0
        and positive_share > 0.52
        and top10 > rank11_20
        and top10 > bottom10
    ):
        return "signal_edge_positive"

    if (
        ic <= 0
        and avg_daily <= 0
        and positive_share < 0.50
        and top10 <= rank11_20
    ):
        return "signal_edge_negative"

    return "signal_edge_mixed"


def ensure_symlink(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        return
    os.symlink(src, dst)


def run_round_preflight(research_round_id: str) -> None:
    result = subprocess.run(
        [
            PYTHON,
            str(PREFLIGHT_SCRIPT),
            "--research-round-id",
            research_round_id,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(
            f"Preflight failed for research_round_id={research_round_id}; fix preregistration intake issues before running the batch."
        )


def update_candidate_registry(
    *,
    candidate_registry_path: Path,
    result_rows: list[dict],
    research_round_id: str,
    score_builder_name: str,
    baseline_reference_candidate_scheme_id: str,
    status_question: str,
) -> None:
    registry = read_jsonl(candidate_registry_path)
    by_id = {row["candidate_scheme_id"]: row for row in registry}
    timestamp = now_iso()
    result_ids = {r["candidate_scheme_id"] for r in result_rows}
    for row in result_rows:
        candidate_scheme_id = row["candidate_scheme_id"]
        payload = {
            "registered_at": timestamp,
            "candidate_scheme_id": candidate_scheme_id,
            "scheme_family": "price_volume_single_signal_discovery",
            "status": row["classification"],
            "research_round_id": research_round_id,
            "research_tier": "exploratory",
            "owner": "codex",
            "score_builder": score_builder_name,
            "feature_source": "bars_daily_derived",
            "feature_set": [row["field_name"]],
            "score_rule": f"percentile_rank({row['field_name']} {row['ranking_direction']}); require min_feature_count >= 1",
            "baseline_reference_candidate_scheme_id": baseline_reference_candidate_scheme_id,
            "snapshot_id": "warehouse_20260418_181408",
            "execution_logic_version": "warehouse_execution_v3",
            "changed_dimension": "atomic_signal_choice",
            "score_family_rule": status_question,
            "notes": row["notes"],
            "status_updated_at": timestamp,
        }
        by_id[candidate_scheme_id] = payload
    ordered_ids = [row["candidate_scheme_id"] for row in registry if row.get("candidate_scheme_id") not in result_ids]
    new_rows = [by_id[cid] for cid in ordered_ids] + [by_id[r["candidate_scheme_id"]] for r in result_rows]
    write_jsonl(candidate_registry_path, new_rows)


def update_round_registry(
    *,
    round_registry_path: Path,
    research_round_id: str,
    candidate_ids: list[str],
    decision: dict,
    round_note_prefix: str,
) -> None:
    rows = read_jsonl(round_registry_path)
    updated: list[dict] = []
    timestamp = now_iso()
    for row in rows:
        if row.get("research_round_id") != research_round_id:
            updated.append(row)
            continue
        row["candidate_scheme_ids"] = candidate_ids
        row["status"] = "completed_phase_summary"
        row["status_updated_at"] = timestamp
        row["notes"] = (
            f"{round_note_prefix} "
            f"Decision: continue_pool_expansion={str(decision['continue_pool_expansion']).lower()}, "
            f"reopen_family_construction={str(decision['reopen_family_construction']).lower()}."
        )
        updated.append(row)
    write_jsonl(round_registry_path, updated)


def write_phase_summary(
    *,
    round_dir: Path,
    research_round_id: str,
    as_of_date: str,
    baseline_reference_candidate_scheme_id: str,
    results: list[dict],
    decision: dict,
    summary_intro: str,
) -> None:
    positive = [row for row in results if row["classification"] == "signal_edge_positive"]
    mixed = [row for row in results if row["classification"] == "signal_edge_mixed"]
    negative = [row for row in results if row["classification"] == "signal_edge_negative"]
    summary_json = round_dir / f"phase_summary_{as_of_date}.json"
    summary_md = round_dir / f"phase_summary_{as_of_date}.md"
    payload = {
        "research_round_id": research_round_id,
        "as_of_date": as_of_date,
        "baseline_reference_candidate_scheme_id": baseline_reference_candidate_scheme_id,
        "final_classification": {row["candidate_scheme_id"]: row["classification"] for row in results},
        "new_clean_positive_keepers": positive,
        "rejected_candidates": negative,
        "mixed_candidates": mixed,
        "decision": decision,
    }
    write_json(summary_json, payload)

    lines = [
        f"# {research_round_id} phase summary",
        "",
        "## Summary",
        "",
        summary_intro,
        "",
        "The final classification is:",
        "",
    ]
    for row in results:
        lines.append(f"- `{row['candidate_scheme_id']}`: `{row['classification']}`")

    if positive:
        lines.extend(["", "## Newly retained clean positive keepers", ""])
        for row in positive:
            lines.extend(
                [
                    f"- `{row['candidate_scheme_id']}`",
                    f"  - `full_sample_corr_ic(全样本IC) = {row['full_sample_corr_ic']:.6f}`",
                    f"  - `avg_daily_ic(平均日IC) = {row['avg_daily_ic']:.6f}`",
                    f"  - `positive_daily_ic_share(正IC日占比) = {row['positive_daily_ic_share']:.6f}`",
                    f"  - `avg_label_top10(前10平均标签) = {row['avg_label_top10']:.6f}`",
                    f"  - `avg_label_rank11_20(11-20名平均标签) = {row['avg_label_rank11_20']:.6f}`",
                    f"  - `avg_label_bottom10(后10平均标签) = {row['avg_label_bottom10']:.6f}`",
                    "",
                ]
            )

    if mixed:
        lines.extend(["## Mixed signals", ""])
        for row in mixed:
            lines.extend(
                [
                    f"- `{row['candidate_scheme_id']}`",
                    f"  - `full_sample_corr_ic(全样本IC) = {row['full_sample_corr_ic']:.6f}`",
                    f"  - `avg_daily_ic(平均日IC) = {row['avg_daily_ic']:.6f}`",
                    f"  - `positive_daily_ic_share(正IC日占比) = {row['positive_daily_ic_share']:.6f}`",
                    f"  - `avg_label_top10(前10平均标签) = {row['avg_label_top10']:.6f}`",
                    f"  - `avg_label_rank11_20(11-20名平均标签) = {row['avg_label_rank11_20']:.6f}`",
                    "",
                ]
            )

    if negative:
        lines.extend(["## Rejected signals", ""])
        for row in negative:
            lines.extend(
                [
                    f"- `{row['candidate_scheme_id']}`",
                    f"  - `full_sample_corr_ic(全样本IC) = {row['full_sample_corr_ic']:.6f}`",
                    f"  - `avg_daily_ic(平均日IC) = {row['avg_daily_ic']:.6f}`",
                    f"  - `positive_daily_ic_share(正IC日占比) = {row['positive_daily_ic_share']:.6f}`",
                    f"  - `avg_label_top10(前10平均标签) = {row['avg_label_top10']:.6f}`",
                    f"  - `avg_label_rank11_20(11-20名平均标签) = {row['avg_label_rank11_20']:.6f}`",
                    f"  - `avg_label_bottom10(后10平均标签) = {row['avg_label_bottom10']:.6f}`",
                    "",
                ]
            )

    lines.extend(
        [
            "## Decision",
            "",
            f"- `continue_pool_expansion(继续扩单信号池) = {str(decision['continue_pool_expansion']).lower()}`",
            f"- `reopen_family_construction(回到family构造) = {str(decision['reopen_family_construction']).lower()}`",
            f"- reason: {decision['reason']}",
            "",
        ]
    )
    summary_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_single_signal_batch(
    *,
    round_id: str,
    as_of_date: str,
    round_label: str,
    base_run_dir: Path,
    round_dir: Path,
    candidate_registry_path: Path,
    round_registry_path: Path,
    build_diagnosis_script: Path,
    score_builder_name: str,
    candidates: list[CandidateSpec],
    build_feature_views_fn: Callable[[duckdb.DuckDBPyConnection, Path, Path, str], None],
    materialize_single_signal_fn: Callable[[duckdb.DuckDBPyConnection, CandidateSpec, Path], dict],
    status_question: str,
    positive_reason: str,
    zero_reason: str,
    summary_intro: str,
    round_note_prefix: str,
    baseline_reference_candidate_scheme_id: str = "price_volume_v18_refresh_hysteresis",
) -> None:
    run_round_preflight(round_id)
    sample_panel, label_panel = ensure_base_inputs(base_run_dir, round_label)
    round_dir.mkdir(parents=True, exist_ok=True)

    run_input = read_json(CONTRACTS_DIR / "run_input_contract.current.json")
    snapshot_id = run_input["snapshot_id"]
    source_db_path = Path(run_input["source_root"]["snapshot_path"]) / "duckdb" / "warehouse.duckdb"
    if not source_db_path.exists():
        raise FileNotFoundError(f"Shared warehouse DB not found: {source_db_path}")

    con = duckdb.connect()
    try:
        build_feature_views_fn(con, sample_panel, source_db_path, snapshot_id)
        result_rows: list[dict] = []
        for spec in candidates:
            run_id = f"signaldiag_{spec.candidate_scheme_id}_{as_of_date}"
            run_dir = RUN_STATE_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            ensure_symlink(sample_panel, run_dir / "project_sample_panel.parquet")
            ensure_symlink(label_panel, run_dir / "project_label_panel.parquet")
            materialize_single_signal_fn(con, spec, run_dir)

            subprocess.run(
                [
                    PYTHON,
                    str(build_diagnosis_script),
                    "--run-id",
                    run_id,
                    "--candidate-scheme-id",
                    spec.candidate_scheme_id,
                    "--research-round-id",
                    round_id,
                    "--title",
                    spec.candidate_scheme_id,
                    "--as-of-date",
                    as_of_date,
                    "--input-dir",
                    str(run_dir),
                ],
                check=True,
            )

            diag_json = round_dir / f"{spec.candidate_scheme_id}_signal_edge_diagnosis_{as_of_date}.json"
            payload = read_json(diag_json)
            classification = classify_signal(payload)
            result_rows.append(
                {
                    "candidate_scheme_id": spec.candidate_scheme_id,
                    "field_name": spec.field_name,
                    "ranking_direction": spec.ranking_direction,
                    "classification": classification,
                    "full_sample_corr_ic": payload["ic_readout"]["full_sample_corr_ic"],
                    "avg_daily_ic": payload["ic_readout"]["avg_daily_ic"],
                    "positive_daily_ic_share": payload["ic_readout"]["positive_daily_ic_share"],
                    "avg_label_top10": payload["top_slice_readout"]["avg_label_top10"],
                    "avg_label_rank11_20": payload["top_slice_readout"]["avg_label_rank11_20"],
                    "avg_label_bottom10": payload["top_slice_readout"]["avg_label_bottom10"],
                    "notes": (
                        f"{round_label} atomic signal candidate built from {spec.field_name} under the frozen "
                        f"{baseline_reference_candidate_scheme_id} operational contract. "
                        f"Signal-edge diagnosis classified this candidate as {classification}."
                    ),
                }
            )
    finally:
        con.close()

    positive = [row for row in result_rows if row["classification"] == "signal_edge_positive"]
    decision = {
        "continue_pool_expansion": len(positive) == 0,
        "reopen_family_construction": len(positive) > 0,
        "reason": positive_reason if positive else zero_reason,
    }

    update_candidate_registry(
        candidate_registry_path=candidate_registry_path,
        result_rows=result_rows,
        research_round_id=round_id,
        score_builder_name=score_builder_name,
        baseline_reference_candidate_scheme_id=baseline_reference_candidate_scheme_id,
        status_question=status_question,
    )
    update_round_registry(
        round_registry_path=round_registry_path,
        research_round_id=round_id,
        candidate_ids=[row["candidate_scheme_id"] for row in result_rows],
        decision=decision,
        round_note_prefix=round_note_prefix,
    )
    write_phase_summary(
        round_dir=round_dir,
        research_round_id=round_id,
        as_of_date=as_of_date,
        baseline_reference_candidate_scheme_id=baseline_reference_candidate_scheme_id,
        results=result_rows,
        decision=decision,
        summary_intro=summary_intro,
    )

    print(json.dumps({"research_round_id": round_id, "decision": decision, "results": result_rows}, ensure_ascii=False, indent=2))
