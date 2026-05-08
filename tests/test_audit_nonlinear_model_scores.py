from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import load_module, read_text


SCRIPT_PATH = "scripts/audit_nonlinear_model_scores.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_scores_parquet(path: Path, *, duplicate_key: bool = False, identical_scores: bool = False) -> None:
    con = duckdb.connect()
    try:
        score_a = 0.25 if identical_scores else 0.10
        score_b = 0.25 if identical_scores else 0.30
        score_c = 0.25 if identical_scores else -0.20
        rows = [
            (
                "run_1",
                "nlc_v1_confirmed5_lgbm_depth3_seed42",
                "warehouse_20260429_trainval_20211231",
                "000001.SZ",
                "20200102",
                score_a,
                "nlc_v1_fset01_confirmed5",
                "nlc_v1_lgbm_regressor_depth3_seed42",
                "cfg_hash_1",
            ),
            (
                "run_1",
                "nlc_v1_confirmed5_lgbm_depth3_seed42",
                "warehouse_20260429_trainval_20211231",
                "000002.SZ",
                "20200102",
                score_b,
                "nlc_v1_fset01_confirmed5",
                "nlc_v1_lgbm_regressor_depth3_seed42",
                "cfg_hash_1",
            ),
            (
                "run_1",
                "nlc_v1_confirmed5_lgbm_depth3_seed42",
                "warehouse_20260429_trainval_20211231",
                "000003.SZ",
                "20200103",
                score_c,
                "nlc_v1_fset01_confirmed5",
                "nlc_v1_lgbm_regressor_depth3_seed42",
                "cfg_hash_1",
            ),
        ]
        if duplicate_key:
            rows.append(rows[0])

        values_sql = ", ".join(
            "(" + ", ".join(repr(value) for value in row) + ")" for row in rows
        )
        con.execute(
            f"""
            COPY (
                SELECT *
                FROM (
                    VALUES {values_sql}
                ) AS t(
                    run_id,
                    candidate_scheme_id,
                    snapshot_id,
                    instrument,
                    signal_date,
                    model_score_D0,
                    feature_set_id,
                    model_config_id,
                    config_hash
                )
            ) TO '{path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()


def run_audit(
    repo_root: Path,
    scores_path: Path,
    scores_audit_path: Path,
    training_manifest_path: Path,
    output_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--scores",
            str(scores_path),
            "--scores-audit",
            str(scores_audit_path),
            "--training-manifest",
            str(training_manifest_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_audit_script_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--scores" in result.stdout
    assert "--scores-audit" in result.stdout
    assert "--training-manifest" in result.stdout
    assert "--output" in result.stdout


def test_audit_model_scores_passes_for_valid_minimal_outputs(repo_root: Path, tmp_path: Path) -> None:
    scores_path = tmp_path / "model_scores_D0.parquet"
    scores_audit_path = tmp_path / "model_scores_D0_audit.json"
    training_manifest_path = tmp_path / "training_manifest.json"
    output_path = tmp_path / "nonlinear_model_scores_audit.json"

    write_scores_parquet(scores_path)
    write_json(
        scores_audit_path,
        {
            "row_count": 3,
            "frozen_test_access": False,
        },
    )
    write_json(
        training_manifest_path,
        {
            "status": "trained_and_scored_minimal",
        },
    )

    result = run_audit(repo_root, scores_path, scores_audit_path, training_manifest_path, output_path)

    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["row_count"] == 3
    assert payload["duplicate_count"] == 0
    assert payload["null_score_rows"] == 0
    assert payload["nonfinite_score_rows"] == 0
    assert payload["score_summary"]["all_scores_identical"] is False
    assert payload["candidate_scheme_id"] == "nlc_v1_confirmed5_lgbm_depth3_seed42"
    assert payload["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert payload["model_config_id"] == "nlc_v1_lgbm_regressor_depth3_seed42"
    assert payload["frozen_test_access"] is False
    assert payload["training_manifest_status"] == "trained_and_scored_minimal"


def test_audit_model_scores_fails_for_duplicate_keys_and_identical_scores(repo_root: Path, tmp_path: Path) -> None:
    scores_path = tmp_path / "model_scores_D0.parquet"
    scores_audit_path = tmp_path / "model_scores_D0_audit.json"
    training_manifest_path = tmp_path / "training_manifest.json"
    output_path = tmp_path / "nonlinear_model_scores_audit.json"

    write_scores_parquet(scores_path, duplicate_key=True, identical_scores=True)
    write_json(
        scores_audit_path,
        {
            "row_count": 4,
            "frozen_test_access": False,
        },
    )
    write_json(
        training_manifest_path,
        {
            "status": "trained_and_scored_minimal",
        },
    )

    result = run_audit(repo_root, scores_path, scores_audit_path, training_manifest_path, output_path)

    assert result.returncode != 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["duplicate_count"] == 1
    assert payload["score_summary"]["all_scores_identical"] is True
    assert payload["checks"]["primary_key_unique"] is False
    assert payload["checks"]["scores_not_all_identical"] is False


def test_audit_source_excludes_backtest_metrics_and_readout_paths() -> None:
    script_text = read_text(SCRIPT_PATH)

    assert "holdings.csv" not in script_text
    assert "metrics.json" not in script_text
    assert "portfolio_daily_summary.csv" not in script_text
    assert "backtest_daily.csv" not in script_text
    assert "validation_readout" not in script_text
    assert "fixed_test" not in script_text


def test_audit_model_scores_module_detects_row_count_mismatch(tmp_path: Path) -> None:
    module = load_module(SCRIPT_PATH, "audit_nonlinear_model_scores_module")
    scores_path = tmp_path / "model_scores_D0.parquet"
    scores_audit_path = tmp_path / "model_scores_D0_audit.json"
    training_manifest_path = tmp_path / "training_manifest.json"
    output_path = tmp_path / "nonlinear_model_scores_audit.json"

    write_scores_parquet(scores_path)
    write_json(scores_audit_path, {"row_count": 2, "frozen_test_access": False})
    write_json(training_manifest_path, {"status": "trained_and_scored_minimal"})

    payload = module.audit_model_scores_or_fail(
        scores_path=scores_path,
        scores_audit_path=scores_audit_path,
        training_manifest_path=training_manifest_path,
        output_path=output_path,
    )

    assert payload["status"] == "failed"
    assert payload["checks"]["row_count_matches_scores_audit"] is False
