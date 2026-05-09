from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import duckdb

from conftest import REPO_ROOT, load_json, load_module, read_text


FEATURE_SET_PATH = (
    "configs/nonlinear_challenger_v2/feature_sets/"
    "feature_set_nlc_v2_fset01_confirmed5_locked_inputs.json"
)
MODEL_CONFIG_PATH = (
    "configs/nonlinear_challenger_v2/model_configs/"
    "model_config_nlc_v2_lgbm_depth3_seed42_cs_volatility_discount_v1.json"
)
CANDIDATE_PATH = (
    "configs/nonlinear_challenger_v2/candidates/"
    "candidate_nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42.json"
)
SOURCE_AUDIT_PATH = "configs/nonlinear_challenger_v1/feature_sets/confirmed5_data_source_audit.json"
SCRIPT_PATH = "scripts/build_nonlinear_challenger_v2_scores.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_temp_manifests(tmp_path: Path) -> tuple[Path, Path, Path]:
    feature_set_path = tmp_path / "feature_set.json"
    model_config_path = tmp_path / "model_config.json"
    candidate_path = tmp_path / "candidate.json"

    write_json(feature_set_path, load_json(FEATURE_SET_PATH))
    write_json(model_config_path, load_json(MODEL_CONFIG_PATH))
    write_json(candidate_path, load_json(CANDIDATE_PATH))
    return feature_set_path, model_config_path, candidate_path


def write_temp_source_audit(
    tmp_path: Path,
    source_db_path: Path,
    *,
    data_source_status: str = "resolved",
    volatility_ready: bool = True,
) -> Path:
    payload = json.loads(json.dumps(load_json(SOURCE_AUDIT_PATH)))
    payload["data_source_status"] = data_source_status
    payload["train_data_source"]["source_db_file"] = str(source_db_path)
    payload["validation_data_source"]["source_db_file"] = str(source_db_path)
    for feature in payload["features"]:
        if feature["feature_name"] == "volatility_20d":
            feature["ready_for_data_loading"] = volatility_ready
    audit_path = tmp_path / "confirmed5_data_source_audit.json"
    write_json(audit_path, payload)
    return audit_path


def build_source_db_fixture(tmp_path: Path) -> Path:
    source_db_path = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(source_db_path))
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
                close DOUBLE,
                amount DOUBLE,
                vol DOUBLE,
                pct_chg DOUBLE,
                adj_factor DOUBLE
            )
            """
        )
        for inst_id, ts_code, amplitude in [
            (1, "AAA.SZ", 0.1),
            (2, "BBB.SZ", 1.0),
            (3, "CCC.SZ", 2.0),
        ]:
            rows = []
            for day_idx in range(25):
                trade_date = duckdb.sql(
                    f"SELECT strftime(DATE '2020-01-01' + {day_idx} * INTERVAL 1 DAY, '%Y%m%d')"
                ).fetchone()[0]
                sign = 1.0 if day_idx % 2 == 0 else -1.0
                pct_chg = sign * amplitude
                base_price = 10.0 + inst_id + day_idx * 0.05
                rows.append(
                    (
                        "warehouse_20260429_trainval_20211231",
                        ts_code,
                        trade_date,
                        base_price,
                        base_price + 0.1,
                        base_price - 0.1,
                        base_price + 0.02,
                        base_price + 0.02,
                        10000.0 + inst_id * 10.0 + day_idx,
                        1000.0 + inst_id * 10.0 + day_idx,
                        pct_chg,
                        1.0,
                    )
                )
            con.executemany(
                "INSERT INTO serving.vw_bars_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        con.close()
    return source_db_path


def build_confirmed5_scores_fixture(
    tmp_path: Path,
    *,
    include_missing_volatility_row: bool = False,
) -> Path:
    scores_path = tmp_path / "confirmed5_model_scores.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20200124', 'reversal_tail_exclude_p98_v1', 0.20),
                        ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20200124', 'reversal_tail_exclude_p98_v1', 0.50),
                        ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20200124', 'reversal_tail_exclude_p98_v1', 0.90),
                        ('warehouse_20260429_trainval_20211231', 'AAA.SZ', '20200125', 'reversal_tail_exclude_p98_v1', 0.30),
                        ('warehouse_20260429_trainval_20211231', 'BBB.SZ', '20200125', 'reversal_tail_exclude_p98_v1', 0.60),
                        ('warehouse_20260429_trainval_20211231', 'CCC.SZ', '20200125', 'reversal_tail_exclude_p98_v1', 0.95)
                ) AS t(snapshot_id, instrument, signal_date, candidate_scheme_id, model_score_D0)
            ) TO '{scores_path.as_posix()}' (FORMAT PARQUET)
            """
        )
        if include_missing_volatility_row:
            with_missing_path = tmp_path / "confirmed5_model_scores_missing_vol.parquet"
            con.execute(
                f"""
                COPY (
                    SELECT * FROM read_parquet('{scores_path.as_posix()}')
                    UNION ALL
                    SELECT
                        'warehouse_20260429_trainval_20211231',
                        'DDD.SZ',
                        '20200125',
                        'reversal_tail_exclude_p98_v1',
                        0.40
                ) TO '{with_missing_path.as_posix()}' (FORMAT PARQUET)
                """
            )
            return with_missing_path
    finally:
        con.close()
    return scores_path


def run_builder(
    repo_root: Path,
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
    confirmed5_scores_path: Path,
    source_audit_path: Path,
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
            "--confirmed5-scores",
            str(confirmed5_scores_path),
            "--source-audit",
            str(source_audit_path),
            "--run-id",
            "nlc_v2_transform_fixture",
            "--attempt-id",
            "attempt_fixture",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_v2_transformer_formula_and_same_day_percentile_rank_are_correct(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    confirmed5_scores_path = build_confirmed5_scores_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        confirmed5_scores_path,
        source_audit_path,
        output_dir,
    )
    assert result.returncode == 0, result.stderr

    scores_path = output_dir / "model_scores_D0.parquet"
    audit_path = output_dir / "score_transform_audit.json"
    assert scores_path.exists()
    assert audit_path.exists()

    con = duckdb.connect()
    try:
        df = con.execute(
            f"""
            SELECT
                instrument,
                signal_date,
                candidate_scheme_id,
                raw_model_score_D0,
                raw_model_score_percentile_rank_D0,
                volatility_20d,
                volatility_20d_percentile_rank_D0,
                adjusted_score_D0,
                model_score_D0,
                score_transform_policy_version
            FROM read_parquet('{scores_path.as_posix()}')
            WHERE signal_date = '20200125'
            ORDER BY instrument
            """
        ).fetchdf()
    finally:
        con.close()

    assert list(df["instrument"]) == ["AAA.SZ", "BBB.SZ", "CCC.SZ"]
    assert list(df["candidate_scheme_id"]) == [
        "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
    ] * 3
    assert list(df["score_transform_policy_version"]) == ["cs_volatility_discount_v1"] * 3

    assert df.loc[0, "raw_model_score_percentile_rank_D0"] == 0.0
    assert df.loc[1, "raw_model_score_percentile_rank_D0"] == 0.5
    assert df.loc[2, "raw_model_score_percentile_rank_D0"] == 1.0

    assert df.loc[0, "volatility_20d_percentile_rank_D0"] == 0.0
    assert df.loc[1, "volatility_20d_percentile_rank_D0"] == 0.5
    assert df.loc[2, "volatility_20d_percentile_rank_D0"] == 1.0

    assert df.loc[0, "adjusted_score_D0"] == 0.0
    assert df.loc[1, "adjusted_score_D0"] == 0.25
    assert df.loc[2, "adjusted_score_D0"] == 0.0
    assert df.loc[1, "model_score_D0"] == df.loc[1, "adjusted_score_D0"]


def test_high_volatility_row_gets_lower_adjusted_score(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    confirmed5_scores_path = build_confirmed5_scores_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        confirmed5_scores_path,
        source_audit_path,
        output_dir,
    )
    assert result.returncode == 0, result.stderr

    con = duckdb.connect()
    try:
        rows = con.execute(
            f"""
            SELECT instrument, adjusted_score_D0
            FROM read_parquet('{(output_dir / "model_scores_D0.parquet").as_posix()}')
            WHERE signal_date = '20200125'
            ORDER BY instrument
            """
        ).fetchall()
    finally:
        con.close()

    adjusted_by_instrument = dict(rows)
    assert adjusted_by_instrument["CCC.SZ"] < adjusted_by_instrument["BBB.SZ"]


def test_transformer_fails_fast_when_volatility_is_missing(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    confirmed5_scores_path = build_confirmed5_scores_fixture(tmp_path, include_missing_volatility_row=True)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        confirmed5_scores_path,
        source_audit_path,
        output_dir,
    )

    assert result.returncode != 0
    assert "volatility_20d missing" in result.stderr


def test_transformer_fails_fast_when_manifest_id_mismatches(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_scheme_id"] = "wrong_candidate_id"
    write_json(candidate_path, candidate)

    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    confirmed5_scores_path = build_confirmed5_scores_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        confirmed5_scores_path,
        source_audit_path,
        output_dir,
    )

    assert result.returncode != 0
    assert "candidate_scheme_id mismatch" in result.stderr


def test_transformer_fails_fast_when_confirmed5_scores_are_missing(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        tmp_path / "missing_scores.parquet",
        source_audit_path,
        output_dir,
    )

    assert result.returncode != 0
    assert "confirmed5 scores not found" in result.stderr


def test_transformer_output_audit_marks_no_retraining(repo_root: Path, tmp_path: Path) -> None:
    feature_set_path, model_config_path, candidate_path = write_temp_manifests(tmp_path)
    source_db_path = build_source_db_fixture(tmp_path)
    source_audit_path = write_temp_source_audit(tmp_path, source_db_path)
    confirmed5_scores_path = build_confirmed5_scores_fixture(tmp_path)
    output_dir = tmp_path / "out"

    result = run_builder(
        repo_root,
        feature_set_path,
        model_config_path,
        candidate_path,
        confirmed5_scores_path,
        source_audit_path,
        output_dir,
    )
    assert result.returncode == 0, result.stderr

    audit = json.loads((output_dir / "score_transform_audit.json").read_text(encoding="utf-8"))
    assert audit["training_performed"] is False
    assert audit["frozen_test_accessed"] is False
    assert audit["candidate_scheme_id"] == "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
    assert audit["null_score_rows"] == 0
    assert audit["nonfinite_score_rows"] == 0


def test_transformer_script_does_not_retrain_model() -> None:
    script_text = read_text(SCRIPT_PATH).lower()
    assert "lgbmregressor" not in script_text
    assert ".fit(" not in script_text
    assert ".predict(" not in script_text


def test_module_level_constants_match_v2_ids() -> None:
    module = load_module(SCRIPT_PATH, "build_nonlinear_challenger_v2_scores_module")
    assert module.EXPECTED_CANDIDATE_SCHEME_ID == (
        "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
    )
    assert module.EXPECTED_TRANSFORMATION_ID == "cs_volatility_discount_v1"
