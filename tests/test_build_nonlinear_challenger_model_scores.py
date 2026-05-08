from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from conftest import load_json, load_module, read_text


FEATURE_SET_PATH = "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01.json"
CONFIRMED5_FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/feature_set_nlc_v1_fset01_confirmed5.json"
)
MODEL_CONFIG_PATH = "configs/nonlinear_challenger_v1/model_configs/model_config_nlc_v1_lgbm_depth3_seed42.json"
CANDIDATE_PATH = "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_fset01_lgbm_depth3_seed42.json"
CONFIRMED5_CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v1/candidates/candidate_nlc_v1_confirmed5_lgbm_depth3_seed42.json"
)
CONFIRMED5_DATA_SOURCE_AUDIT_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/confirmed5_data_source_audit.json"
)
SCRIPT_PATH = "scripts/build_nonlinear_challenger_model_scores.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_temp_manifests(
    tmp_path: Path,
    feature_set_source: str = FEATURE_SET_PATH,
    candidate_source: str = CANDIDATE_PATH,
) -> tuple[Path, Path, Path]:
    feature_set_path = tmp_path / "feature_set.json"
    model_config_path = tmp_path / "model_config.json"
    candidate_path = tmp_path / "candidate.json"

    write_json(feature_set_path, load_json(feature_set_source))
    write_json(model_config_path, load_json(MODEL_CONFIG_PATH))
    write_json(candidate_path, load_json(candidate_source))

    return feature_set_path, model_config_path, candidate_path


def run_builder(
    repo_root: Path,
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / SCRIPT_PATH),
            "--feature-set",
            str(feature_set_path),
            "--model-config",
            str(model_config_path),
            "--candidate",
            str(candidate_path),
            "--run-id",
            "nonlinear_challenger_v1_fset01_lgbm_depth3_seed42_trainval",
            "--attempt-id",
            "attempt_manual_draft",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def write_temp_data_source_audit(
    tmp_path: Path,
    *,
    data_source_status: str = "resolved",
    ready_overrides: dict[str, bool] | None = None,
    sample_panel_path: Path | None = None,
    validation_sample_panel_path: Path | None = None,
    source_db_path: Path | None = None,
) -> Path:
    payload = json.loads(json.dumps(load_json(CONFIRMED5_DATA_SOURCE_AUDIT_PATH)))
    payload["data_source_status"] = data_source_status

    if ready_overrides:
        for feature in payload["features"]:
            feature_name = feature["feature_name"]
            if feature_name in ready_overrides:
                feature["ready_for_data_loading"] = ready_overrides[feature_name]

    if sample_panel_path is not None:
        payload["train_data_source"]["sample_panel_file"] = str(sample_panel_path)
    if validation_sample_panel_path is not None:
        payload["validation_data_source"]["sample_panel_file"] = str(validation_sample_panel_path)
    if source_db_path is not None:
        payload["train_data_source"]["source_db_file"] = str(source_db_path)
        payload["validation_data_source"]["source_db_file"] = str(source_db_path)

    audit_path = tmp_path / "confirmed5_data_source_audit.json"
    write_json(audit_path, payload)
    return audit_path


def build_confirmed5_loader_fixture(tmp_path: Path, *, omit_source_column: str | None = None) -> tuple[Path, Path]:
    source_db_path = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(source_db_path))
    try:
        con.execute("CREATE SCHEMA serving")
        source_columns = [
            "'warehouse_20260429_trainval_20211231' AS snapshot_id",
            "CASE inst_id WHEN 1 THEN '000001.SZ' ELSE '000002.SZ' END AS ts_code",
            "strftime(DATE '2020-01-01' + day_idx * INTERVAL 1 DAY, '%Y%m%d') AS trade_date",
            "(10.0 + inst_id + day_idx * 0.1) AS adj_open",
            "(10.3 + inst_id + day_idx * 0.1) AS adj_high",
            "(9.7 + inst_id + day_idx * 0.1) AS adj_low",
            "(10.1 + inst_id + day_idx * 0.1 + inst_id * 0.02) AS adj_close",
            "(10.1 + inst_id + day_idx * 0.1 + inst_id * 0.02) AS close",
            "(10000.0 + inst_id * 200.0 + day_idx * 20.0) AS amount",
            "(1000.0 + inst_id * 50.0 + day_idx * 5.0) AS vol",
            "(CASE WHEN day_idx = 0 THEN 0.0 ELSE 0.2 + inst_id * 0.01 END) AS pct_chg",
            "1.0 AS adj_factor",
        ]
        if omit_source_column is not None:
            source_columns = [column for column in source_columns if f" AS {omit_source_column}" not in column]

        con.execute(
            f"""
            CREATE TABLE serving.vw_bars_daily AS
            SELECT
                {", ".join(source_columns)}
            FROM range(70) AS days(day_idx)
            CROSS JOIN (VALUES (1), (2)) AS instruments(inst_id)
            """
        )

        sample_panel_path = tmp_path / "project_sample_panel.parquet"
        con.execute(
            f"""
            COPY (
                SELECT
                    snapshot_id,
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    TRUE AS ranking_eligible_D0,
                    day_idx < 50 AS train_mask_v1,
                    day_idx >= 50 AS eval_mask_v1
                FROM (
                    SELECT
                        *,
                        date_diff(
                            'day',
                            DATE '2020-01-01',
                            strptime(trade_date, '%Y%m%d')
                        ) AS day_idx
                    FROM serving.vw_bars_daily
                )
            ) TO '{sample_panel_path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()

    return sample_panel_path, source_db_path


def test_builder_script_exists(repo_root: Path) -> None:
    assert (repo_root / SCRIPT_PATH).exists()


def test_builder_cli_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / SCRIPT_PATH), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--feature-set" in result.stdout
    assert "--output-dir" in result.stdout


def test_builder_calls_manifest_validator_before_feature_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module")
    call_order: list[str] = []

    def fake_load_json_manifest(path: Path, label: str) -> dict:
        _ = path
        call_order.append(f"load:{label}")
        return {"label": label}

    def fake_validate_manifests(feature_set: dict, model_config: dict, candidate: dict) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        call_order.append("validate")

    def fake_resolve_feature_sources_or_fail(feature_set: dict, model_config: dict, candidate: dict) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        call_order.append("resolve")
        raise module.BuildError("stub unresolved mapping")

    monkeypatch.setattr(module, "load_json_manifest", fake_load_json_manifest)
    monkeypatch.setattr(module, "validate_manifests", fake_validate_manifests)
    monkeypatch.setattr(module, "resolve_feature_sources_or_fail", fake_resolve_feature_sources_or_fail)

    with pytest.raises(module.BuildError, match="stub unresolved mapping"):
        module.run_builder(
            feature_set_path=Path("feature.json"),
            model_config_path=Path("model.json"),
            candidate_path=Path("candidate.json"),
            run_id="run_id",
            attempt_id="attempt_id",
            output_dir=Path("output"),
        )

    assert call_order == [
        "load:feature_set",
        "load:model_config",
        "load:candidate",
        "validate",
        "resolve",
    ]


def test_builder_calls_data_loading_stage_after_feature_source_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module_gate_to_data_loading")
    call_order: list[str] = []

    def fake_load_and_validate_manifests(
        feature_set_path: Path,
        model_config_path: Path,
        candidate_path: Path,
    ) -> tuple[dict, dict, dict]:
        _ = feature_set_path
        _ = model_config_path
        _ = candidate_path
        call_order.append("load_validate")
        return (
            {"feature_set_id": "nlc_v1_fset01_confirmed5", "feature_list": ["reversal_5d"]},
            {"model_config_id": "nlc_v1_lgbm_regressor_depth3_seed42"},
            {"candidate_scheme_id": "nlc_v1_confirmed5_lgbm_depth3_seed42"},
        )

    def fake_resolve_feature_sources_or_fail(feature_set: dict, model_config: dict, candidate: dict) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        call_order.append("resolve")

    def fake_load_training_data_or_fail(
        feature_set: dict,
        model_config: dict,
        candidate: dict,
        output_dir: Path,
    ) -> None:
        _ = feature_set
        _ = model_config
        _ = candidate
        _ = output_dir
        call_order.append("data_loading")
        raise module.BuildError("stub data loading stop")

    monkeypatch.setattr(module, "load_and_validate_manifests", fake_load_and_validate_manifests)
    monkeypatch.setattr(module, "resolve_feature_sources_or_fail", fake_resolve_feature_sources_or_fail)
    monkeypatch.setattr(module, "load_training_data_or_fail", fake_load_training_data_or_fail)

    with pytest.raises(module.BuildError, match="stub data loading stop"):
        module.run_builder(
            feature_set_path=Path("feature.json"),
            model_config_path=Path("model.json"),
            candidate_path=Path("candidate.json"),
            run_id="run_id",
            attempt_id="attempt_id",
            output_dir=Path("output"),
        )

    assert call_order == ["load_validate", "resolve", "data_loading"]


def test_confirmed5_data_source_audit_gate_accepts_resolved_ready_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module_plan_gate")
    feature_set = load_json(CONFIRMED5_FEATURE_SET_PATH)
    candidate = load_json(CONFIRMED5_CANDIDATE_PATH)
    sample_panel_path, source_db_path = build_confirmed5_loader_fixture(tmp_path)
    audit_path = write_temp_data_source_audit(
        tmp_path,
        sample_panel_path=sample_panel_path,
        validation_sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
    )
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))

    data_source_audit = module.load_confirmed5_data_source_audit(feature_set, candidate)
    plan = module.build_confirmed5_data_loading_plan_or_fail(feature_set, candidate, data_source_audit)

    assert plan["train_sample_panel_path"] == sample_panel_path
    assert plan["validation_sample_panel_path"] == sample_panel_path
    assert plan["source_db_path"] == source_db_path
    assert plan["feature_columns"] == [
        "reversal_5d_raw",
        "alpha158_cord30_raw",
        "alpha158_corr30_raw",
        "alpha158_vsumd60_raw",
        "volatility_20d_raw",
    ]


def test_confirmed5_data_source_audit_gate_fails_when_status_is_not_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module_plan_unresolved")
    feature_set = load_json(CONFIRMED5_FEATURE_SET_PATH)
    candidate = load_json(CONFIRMED5_CANDIDATE_PATH)
    audit_path = write_temp_data_source_audit(tmp_path, data_source_status="partial")
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))

    data_source_audit = module.load_confirmed5_data_source_audit(feature_set, candidate)

    with pytest.raises(module.BuildError, match="confirmed5 data source audit must be resolved"):
        module.build_confirmed5_data_loading_plan_or_fail(feature_set, candidate, data_source_audit)


def test_confirmed5_data_source_audit_gate_fails_when_any_feature_is_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module_plan_not_ready")
    feature_set = load_json(CONFIRMED5_FEATURE_SET_PATH)
    candidate = load_json(CONFIRMED5_CANDIDATE_PATH)
    audit_path = write_temp_data_source_audit(tmp_path, ready_overrides={"corr30": False})
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))

    data_source_audit = module.load_confirmed5_data_source_audit(feature_set, candidate)

    with pytest.raises(
        module.BuildError,
        match="confirmed5 data source audit requires all features ready_for_data_loading=true",
    ):
        module.build_confirmed5_data_loading_plan_or_fail(feature_set, candidate, data_source_audit)


def test_builder_fails_when_frozen_access_is_enabled(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    model_config = json.loads(model_config_path.read_text(encoding="utf-8"))
    model_config["frozen_test_access"] = True
    write_json(model_config_path, model_config)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "frozen_test_access" in result.stderr


def test_builder_fails_when_baseline_is_placeholder(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["baseline_candidate_scheme_id"] = "<to_be_bound_before_training>"
    write_json(candidate_path, candidate)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "baseline_candidate_scheme_id" in result.stderr


def test_builder_fails_fast_when_feature_source_mapping_is_not_ready(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, tmp_path / "out")

    assert result.returncode != 0
    assert "feature source mapping is not yet implemented / feature columns cannot be resolved." in result.stderr
    assert "Requested features are not ready_for_training=true" in result.stderr


def test_confirmed5_builder_fails_when_input_path_is_missing(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(
        tmp_path,
        feature_set_source=CONFIRMED5_FEATURE_SET_PATH,
        candidate_source=CONFIRMED5_CANDIDATE_PATH,
    )
    audit_path = write_temp_data_source_audit(
        tmp_path,
        sample_panel_path=tmp_path / "missing_project_sample_panel.parquet",
        validation_sample_panel_path=tmp_path / "missing_project_sample_panel.parquet",
        source_db_path=tmp_path / "missing_warehouse.duckdb",
    )
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))
    output_dir = tmp_path / "out"

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, output_dir)

    assert result.returncode != 0
    assert "confirmed5 training data input path not found" in result.stderr
    assert "feature source mapping is not yet implemented" not in result.stderr
    assert not output_dir.exists()
    assert not (output_dir / "model_scores_D0.parquet").exists()
    assert not (output_dir / "metrics.json").exists()
    assert not (output_dir / "holdings.csv").exists()
    assert not (output_dir / "validation_readout.json").exists()


def test_confirmed5_builder_fails_when_required_source_columns_are_missing(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(
        tmp_path,
        feature_set_source=CONFIRMED5_FEATURE_SET_PATH,
        candidate_source=CONFIRMED5_CANDIDATE_PATH,
    )
    sample_panel_path, source_db_path = build_confirmed5_loader_fixture(tmp_path, omit_source_column="vol")
    audit_path = write_temp_data_source_audit(
        tmp_path,
        sample_panel_path=sample_panel_path,
        validation_sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
    )
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))
    output_dir = tmp_path / "out_missing_col"

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, output_dir)

    assert result.returncode != 0
    assert "confirmed5 required feature columns missing" in result.stderr
    assert "vol" in result.stderr
    assert not output_dir.exists()


def test_confirmed5_builder_loads_feature_frame_and_writes_only_data_loading_audit(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(
        tmp_path,
        feature_set_source=CONFIRMED5_FEATURE_SET_PATH,
        candidate_source=CONFIRMED5_CANDIDATE_PATH,
    )
    sample_panel_path, source_db_path = build_confirmed5_loader_fixture(tmp_path)
    audit_path = write_temp_data_source_audit(
        tmp_path,
        sample_panel_path=sample_panel_path,
        validation_sample_panel_path=sample_panel_path,
        source_db_path=source_db_path,
    )
    monkeypatch.setenv("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH", str(audit_path))
    output_dir = tmp_path / "out_loaded"

    result = run_builder(repo_root, feature_set_path, model_config_path, candidate_path, output_dir)

    assert result.returncode == 0
    assert (output_dir / "data_loading_audit.json").exists()
    assert not (output_dir / "model_scores_D0.parquet").exists()
    assert not (output_dir / "metrics.json").exists()
    assert not (output_dir / "holdings.csv").exists()
    assert not (output_dir / "validation_readout.json").exists()

    payload = json.loads((output_dir / "data_loading_audit.json").read_text(encoding="utf-8"))
    assert payload["status"] == "loaded_feature_frame_only"
    assert payload["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert payload["candidate_scheme_id"] == "nlc_v1_confirmed5_lgbm_depth3_seed42"
    assert payload["source_gate_status"] == "passed"
    assert payload["train_rows"] > 0
    assert payload["validation_rows"] > 0
    assert payload["resolved_train_data_source"].endswith("project_sample_panel.parquet")
    assert payload["resolved_validation_data_source"].endswith("project_sample_panel.parquet")
    assert set(payload["feature_columns"]) == {
        "reversal_5d_raw",
        "alpha158_cord30_raw",
        "alpha158_corr30_raw",
        "alpha158_vsumd60_raw",
        "volatility_20d_raw",
    }


def test_build_data_loading_audit_records_loaded_feature_frame_status() -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_model_scores_module_data_loading_audit")
    feature_set = load_json(CONFIRMED5_FEATURE_SET_PATH)
    model_config = load_json(MODEL_CONFIG_PATH)
    candidate = load_json(CONFIRMED5_CANDIDATE_PATH)
    load_plan = {
        "train_sample_panel_path": Path("train_sample.parquet"),
        "validation_sample_panel_path": Path("validation_sample.parquet"),
        "source_db_path": Path("warehouse.duckdb"),
        "source_view": "serving.vw_bars_daily",
        "feature_columns": [
            "reversal_5d_raw",
            "alpha158_cord30_raw",
            "alpha158_corr30_raw",
            "alpha158_vsumd60_raw",
            "volatility_20d_raw",
        ],
        "split_mask_fields": ["train_mask_v1", "eval_mask_v1"],
    }

    audit = module.build_data_loading_audit(
        feature_set,
        model_config,
        candidate,
        Path("tmp_out"),
        status="loaded_feature_frame_only",
        load_plan=load_plan,
        train_rows=10,
        validation_rows=4,
        feature_missing_summary={"reversal_5d_raw": 0},
    )

    assert audit["stage"] == "data_loading"
    assert audit["status"] == "loaded_feature_frame_only"
    assert audit["source_gate_status"] == "passed"
    assert audit["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert audit["candidate_scheme_id"] == "nlc_v1_confirmed5_lgbm_depth3_seed42"
    assert audit["requested_feature_count"] == 5
    assert audit["requested_features"] == [
        "reversal_5d",
        "cord30",
        "corr30",
        "vsumd60",
        "volatility_20d",
    ]
    assert audit["resolved_train_data_source"] == "train_sample.parquet"
    assert audit["resolved_validation_data_source"] == "validation_sample.parquet"
    assert audit["source_db_path"] == "warehouse.duckdb"
    assert audit["train_rows"] == 10
    assert audit["validation_rows"] == 4


def test_builder_source_excludes_portfolio_metrics_and_readout_paths() -> None:
    script_text = read_text(SCRIPT_PATH)

    assert "holdings.csv" not in script_text
    assert "metrics.json" not in script_text
    assert "portfolio_daily_summary.csv" not in script_text
    assert "backtest_daily.csv" not in script_text
    assert "validation_readout" not in script_text
    assert "build_portfolio_artifacts.py" not in script_text
    assert "build_fixed_test_minimal.py" not in script_text
