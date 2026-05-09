from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import REPO_ROOT, load_module, read_text


SCRIPT_PATH = "scripts/diagnose_nonlinear_challenger_v2_model_edge.py"


def build_fixture_files(tmp_path: Path) -> dict[str, Path]:
    v2_scores = tmp_path / "v2_scores.parquet"
    confirmed5_scores = tmp_path / "confirmed5_scores.parquet"
    baseline_scores = tmp_path / "baseline_scores.parquet"
    label_panel = tmp_path / "label_panel.parquet"
    split_panel = tmp_path / "split_panel.parquet"
    v2_audit = tmp_path / "v2_audit.json"
    output_json = tmp_path / "diagnosis.json"
    output_md = tmp_path / "diagnosis.md"

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('snap','A','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.90),
                        ('snap','B','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.80),
                        ('snap','C','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.70),
                        ('snap','D','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.60),
                        ('snap','E','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.50),
                        ('snap','F','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.40),
                        ('snap','G','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.30),
                        ('snap','H','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.20),
                        ('snap','I','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.10),
                        ('snap','J','20200101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.00),
                        ('snap','A','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.90),
                        ('snap','B','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.80),
                        ('snap','C','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.70),
                        ('snap','D','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.60),
                        ('snap','E','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.50),
                        ('snap','F','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.40),
                        ('snap','G','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.30),
                        ('snap','H','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.20),
                        ('snap','I','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.10),
                        ('snap','J','20210101','nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42',0.00)
                ) AS t(snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0)
            ) TO '{v2_scores.as_posix()}' (FORMAT PARQUET)
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    '{EXPECTED_CONFIRMED5_CANDIDATE}' AS candidate_scheme_id,
                    model_score_D0
                FROM read_parquet('{v2_scores.as_posix()}')
            ) TO '{confirmed5_scores.as_posix()}' (FORMAT PARQUET)
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('A','20200101','multi_equal_weight_v1',0.80),('B','20200101','multi_equal_weight_v1',0.70),('C','20200101','multi_equal_weight_v1',0.60),('D','20200101','multi_equal_weight_v1',0.50),('E','20200101','multi_equal_weight_v1',0.40),
                        ('F','20200101','multi_equal_weight_v1',0.30),('G','20200101','multi_equal_weight_v1',0.20),('H','20200101','multi_equal_weight_v1',0.10),('I','20200101','multi_equal_weight_v1',0.05),('J','20200101','multi_equal_weight_v1',0.00),
                        ('A','20210101','multi_equal_weight_v1',0.80),('B','20210101','multi_equal_weight_v1',0.70),('C','20210101','multi_equal_weight_v1',0.60),('D','20210101','multi_equal_weight_v1',0.50),('E','20210101','multi_equal_weight_v1',0.40),
                        ('F','20210101','multi_equal_weight_v1',0.30),('G','20210101','multi_equal_weight_v1',0.20),('H','20210101','multi_equal_weight_v1',0.10),('I','20210101','multi_equal_weight_v1',0.05),('J','20210101','multi_equal_weight_v1',0.00)
                ) AS t(instrument, signal_date, candidate_scheme_id, model_score_D0)
            ) TO '{baseline_scores.as_posix()}' (FORMAT PARQUET)
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('snap','A','20200101', 0.10, true),('snap','B','20200101', 0.09, true),('snap','C','20200101', 0.08, true),
                        ('snap','D','20200101', 0.07, true),('snap','E','20200101', 0.06, true),('snap','F','20200101', 0.05, true),
                        ('snap','G','20200101', 0.04, true),('snap','H','20200101', 0.03, true),('snap','I','20200101', 0.02, true),
                        ('snap','J','20200101', 0.01, true),
                        ('snap','A','20210101', 0.10, true),('snap','B','20210101', 0.09, true),('snap','C','20210101', 0.08, true),
                        ('snap','D','20210101', 0.07, true),('snap','E','20210101', 0.06, true),('snap','F','20210101', 0.05, true),
                        ('snap','G','20210101', 0.04, true),('snap','H','20210101', 0.03, true),('snap','I','20210101', 0.02, true),
                        ('snap','J','20210101', 0.01, true)
                ) AS t(snapshot_id, instrument, signal_date, label_5d_next_open_close, label_defined)
            ) TO '{label_panel.as_posix()}' (FORMAT PARQUET)
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('snap','A','20200101', true, false),('snap','B','20200101', true, false),('snap','C','20200101', true, false),
                        ('snap','D','20200101', true, false),('snap','E','20200101', true, false),('snap','F','20200101', true, false),
                        ('snap','G','20200101', true, false),('snap','H','20200101', true, false),('snap','I','20200101', true, false),
                        ('snap','J','20200101', true, false),
                        ('snap','A','20210101', false, true),('snap','B','20210101', false, true),('snap','C','20210101', false, true),
                        ('snap','D','20210101', false, true),('snap','E','20210101', false, true),('snap','F','20210101', false, true),
                        ('snap','G','20210101', false, true),('snap','H','20210101', false, true),('snap','I','20210101', false, true),
                        ('snap','J','20210101', false, true)
                ) AS t(snapshot_id, instrument, signal_date, train_flag, validation_flag)
            ) TO '{split_panel.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()

    v2_audit.write_text(
        json.dumps(
            {
                "candidate_scheme_id": EXPECTED_V2_CANDIDATE,
                "training_performed": False,
                "frozen_test_accessed": False,
                "row_count": 20,
                "raw_input_null_score_rows": 3,
                "score_transform_policy_version": "cs_volatility_discount_v1",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "v2_scores": v2_scores,
        "confirmed5_scores": confirmed5_scores,
        "baseline_scores": baseline_scores,
        "label_panel": label_panel,
        "split_panel": split_panel,
        "v2_audit": v2_audit,
        "output_json": output_json,
        "output_md": output_md,
    }


EXPECTED_V2_CANDIDATE = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_CONFIRMED5_CANDIDATE = "reversal_tail_exclude_p98_v1"
EXPECTED_BASELINE_CANDIDATE = "multi_equal_weight_v1"


def run_script(repo_root: Path, files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--v2-scores",
            str(files["v2_scores"]),
            "--v2-audit",
            str(files["v2_audit"]),
            "--confirmed5-scores",
            str(files["confirmed5_scores"]),
            "--baseline-scores",
            str(files["baseline_scores"]),
            "--label-panel",
            str(files["label_panel"]),
            "--split-panel",
            str(files["split_panel"]),
            "--output-json",
            str(files["output_json"]),
            "--output-md",
            str(files["output_md"]),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_v2_model_edge_diagnosis_outputs_expected_shape(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["frozen_test_accessed"] is False
    assert payload["formal_metrics_generated"] is False
    assert payload["portfolio_run_executed"] is False
    assert "v2_train" in payload["diagnostics"]
    assert "v2_validation" in payload["diagnostics"]
    assert "confirmed5_train" in payload["diagnostics"]
    assert "baseline_validation" in payload["diagnostics"]
    assert payload["v2_transform_input_audit"]["raw_input_null_score_rows"] == 3


def test_v2_model_edge_diagnosis_recommends_portfolio_when_not_materially_worse(repo_root: Path, tmp_path: Path) -> None:
    files = build_fixture_files(tmp_path)
    result = run_script(repo_root, files)
    assert result.returncode == 0, result.stderr

    payload = json.loads(files["output_json"].read_text(encoding="utf-8"))
    assert payload["conclusion"]["materially_damages_confirmed5_model_edge"] is False
    assert payload["conclusion"]["recommendation"] == "eligible_for_portfolio_dry_run"


def test_script_text_excludes_portfolio_and_frozen_test_actions() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "holdings.csv" not in script_text
    assert "backtest_daily" not in script_text
    assert "portfolio_weights" not in script_text


def test_module_threshold_constants_are_exposed() -> None:
    module = load_module(SCRIPT_PATH, "diagnose_nonlinear_challenger_v2_model_edge_module")
    assert module.VALIDATION_RANKIC_DAMAGE_THRESHOLD == -0.005
    assert module.VALIDATION_ICIR_DAMAGE_THRESHOLD == -0.05
