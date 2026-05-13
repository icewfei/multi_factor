from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from conftest import REPO_ROOT, load_module


SCRIPT_PATH = "scripts/rebuild_baseline_c1_p98_source_chain.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def build_source_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE SCHEMA serving")
        con.execute(
            """
            CREATE TABLE serving.vw_bars_daily (
                snapshot_id VARCHAR,
                ts_code VARCHAR,
                trade_date VARCHAR,
                adj_open DOUBLE,
                adj_high DOUBLE,
                adj_low DOUBLE,
                adj_close DOUBLE,
                amount DOUBLE,
                pct_chg DOUBLE
            )
            """
        )
        rows: list[tuple[str, str, str, float, float, float, float, float, float]] = []
        for day in range(1, 71):
            trade_date = f"202101{day:02d}"
            for idx, instrument in enumerate(("AAA.SZ", "BBB.SZ"), start=1):
                close = 10.0 + day * (0.1 + idx * 0.02)
                open_ = close - 0.05
                high = close + 0.10
                low = close - 0.10
                amount = close * (1000 + day * 5 + idx * 10)
                pct = 1.0 if day > 1 else 0.0
                rows.append(("snap", instrument, trade_date, open_, high, low, close, amount, pct))
        con.executemany(
            "INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    finally:
        con.close()


def write_project_panels(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210110", "20210170", "20210170"],
            "ranking_eligible_D0": [True, True, True],
        }
    )
    for name in (
        "project_sample_panel.parquet",
        "project_label_panel.parquet",
        "project_execution_panel.parquet",
    ):
        pq.write_table(table, dir_path / name)
    write_json(dir_path / "data_quality_audit.json", {"summary_counts": {"project_sample_panel_rows": 3}})


def write_registry(path: Path) -> None:
    write_jsonl(
        path,
        [
            {
                "candidate_scheme_id": "exploratory_cross_horizon_c1_reversal_only",
                "feature_preset": "single_signal_reversal_5d_v1",
                "score_rule": "percentile_rank(reversal_5d_raw DESC); require min_feature_count >= 1",
            }
        ],
    )


def write_preregs(c1_round: Path, p98_tail: Path) -> None:
    write_json(
        c1_round,
        {
            "candidate_scheme_ids": ["exploratory_cross_horizon_c1_reversal_only"],
            "planned_candidate_scheme_ids": ["exploratory_cross_horizon_c1_reversal_only"],
            "serial_rule": "非级联淘汰",
            "forbidden": ["不能查看 2022-2025 测试集"],
        },
    )
    write_json(
        p98_tail,
        {
            "success_rules": {
                "dimension_a_learnability": {"median_daily_ic": ">= 0.040"},
                "dimension_b_pipeline_compatibility": {
                    "top10_avg_label": "> 0",
                    "top10_bot10_spread": "> 0.003",
                },
                "ic_computation_method": "CORR of score vs oracle label_5d_next_open_close",
            }
        },
    )


def write_run_input_contract(path: Path, snapshot_root: Path) -> None:
    write_json(
        path,
        {
            "snapshot_id": "snap",
            "source_root": {"snapshot_path": str(snapshot_root)},
        },
    )


def write_p98_score(path: Path) -> None:
    table = pa.table(
        {
            "snapshot_id": ["snap", "snap", "snap"],
            "instrument": ["AAA.SZ", "AAA.SZ", "BBB.SZ"],
            "signal_date": ["20210110", "20210170", "20210170"],
            "candidate_scheme_id": [
                "reversal_tail_exclude_p98_v1",
                "reversal_tail_exclude_p98_v1",
                "reversal_tail_exclude_p98_v1",
            ],
            "model_score_D0": [0.3, 0.4, None],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_direction_audit_detects_registry_mismatch() -> None:
    module = load_module(SCRIPT_PATH, "rebuild_baseline_c1_p98_source_chain_module_direction")
    builder_text = """
    ("reversal_5d_raw", "reversal_rank")
    ORDER BY reversal_5d_raw ASC, instrument ASC
    """
    payload = module.inspect_c1_direction(
        builder_text,
        {"score_rule": "percentile_rank(reversal_5d_raw DESC); require min_feature_count >= 1"},
    )

    assert payload["registry_direction"] == "DESC"
    assert payload["implementation_direction"] == "ASC"
    assert payload["metadata_matches_implementation"] is False


def test_rebuild_script_end_to_end_success_fixture(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    build_source_db(snapshot_root / "duckdb" / "warehouse.duckdb")

    project_panels_dir = tmp_path / "project_panels"
    write_project_panels(project_panels_dir)

    run_dir = tmp_path / "rebuild_run"
    candidate_registry = tmp_path / "candidate_scheme_registry.jsonl"
    c1_round_prereg = tmp_path / "c1_round_prereg.json"
    p98_tail_prereg = tmp_path / "p98_tail_prereg.json"
    run_input_contract = tmp_path / "run_input_contract.json"
    p98_score_path = tmp_path / "p98" / "model_scores_D0.parquet"
    p98_audit_path = tmp_path / "p98" / "model_scores_D0_audit.json"

    write_registry(candidate_registry)
    write_preregs(c1_round_prereg, p98_tail_prereg)
    write_run_input_contract(run_input_contract, snapshot_root)
    write_p98_score(p98_score_path)
    write_json(
        p98_audit_path,
        {"source_runs": {"reversal_source_run_id": "exploratory_cross_horizon_c1_reversal_only"}},
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-id",
            "exploratory_cross_horizon_c1_reversal_only",
            "--run-dir",
            str(run_dir),
            "--project-panels-dir",
            str(project_panels_dir),
            "--run-input-contract",
            str(run_input_contract),
            "--candidate-registry",
            str(candidate_registry),
            "--c1-round-prereg",
            str(c1_round_prereg),
            "--p98-tail-prereg",
            str(p98_tail_prereg),
            "--p98-score-path",
            str(p98_score_path),
            "--p98-audit-path",
            str(p98_audit_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    assert (run_dir / "model_scores_D0.parquet").exists()
    assert (run_dir / "source_chain_audit.json").exists()
    assert (run_dir / "attempts" / "attempt_rebuild_source_chain_provenance" / "run_state_attempt_manifest.json").exists()
    assert (run_dir / "attempts" / "attempt_rebuild_source_chain_provenance" / "data_quality_audit.json").exists()

    audit = json.loads((run_dir / "source_chain_audit.json").read_text(encoding="utf-8"))
    assert audit["source_chain_status"] == "conditional_pass"
    assert audit["c1_rebuild"]["candidate_scheme_id"] == "exploratory_cross_horizon_c1_reversal_only"
    assert audit["c1_rebuild"]["row_count"] == 3
    assert audit["d0_visibility_audit"]["pass"] is True
    assert audit["leakage_audit"]["pass"] is True
    assert audit["score_direction_audit"]["registry_direction"] == "DESC"
    assert audit["score_direction_audit"]["implementation_direction"] == "ASC"
    assert audit["p98_provenance_audit"]["label_based_learnability_diagnostics_detected"] is True


def test_rebuild_script_writes_blocker_report_when_source_missing(tmp_path: Path) -> None:
    project_panels_dir = tmp_path / "project_panels"
    write_project_panels(project_panels_dir)

    run_dir = tmp_path / "rebuild_run"
    candidate_registry = tmp_path / "candidate_scheme_registry.jsonl"
    c1_round_prereg = tmp_path / "c1_round_prereg.json"
    p98_tail_prereg = tmp_path / "p98_tail_prereg.json"
    run_input_contract = tmp_path / "run_input_contract.json"
    p98_score_path = tmp_path / "p98" / "model_scores_D0.parquet"

    write_registry(candidate_registry)
    write_preregs(c1_round_prereg, p98_tail_prereg)
    write_run_input_contract(run_input_contract, tmp_path / "missing_snapshot")
    write_p98_score(p98_score_path)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / SCRIPT_PATH),
            "--run-dir",
            str(run_dir),
            "--project-panels-dir",
            str(project_panels_dir),
            "--run-input-contract",
            str(run_input_contract),
            "--candidate-registry",
            str(candidate_registry),
            "--c1-round-prereg",
            str(c1_round_prereg),
            "--p98-tail-prereg",
            str(p98_tail_prereg),
            "--p98-score-path",
            str(p98_score_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    audit = json.loads((run_dir / "source_chain_audit.json").read_text(encoding="utf-8"))
    assert audit["source_chain_status"] == "blocked"
    assert any("shared warehouse DB not found" in blocker for blocker in audit["blockers"])
