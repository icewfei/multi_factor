from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
VALIDATOR_PATH = SCRIPTS_DIR / "validate_nonlinear_challenger_manifests.py"
SOURCE_AUDIT_PATH = (
    ROOT
    / "configs"
    / "nonlinear_challenger_v1"
    / "feature_sets"
    / "feature_set_nlc_v1_fset01_source_audit.json"
)
CONFIRMED5_DATA_SOURCE_AUDIT_PATH = (
    ROOT
    / "configs"
    / "nonlinear_challenger_v1"
    / "feature_sets"
    / "confirmed5_data_source_audit.json"
)
DATA_LOADING_AUDIT_FILENAME = "data_loading_audit.json"
CONFIRMED5_FEATURE_SET_ID = "nlc_v1_fset01_confirmed5"
CONFIRMED5_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"
CONFIRMED5_REQUIRED_FEATURES = [
    "reversal_5d",
    "cord30",
    "corr30",
    "vsumd60",
    "volatility_20d",
]
CONFIRMED5_FEATURE_COLUMN_MAP = {
    "reversal_5d": "reversal_5d_raw",
    "cord30": "alpha158_cord30_raw",
    "corr30": "alpha158_corr30_raw",
    "vsumd60": "alpha158_vsumd60_raw",
    "volatility_20d": "volatility_20d_raw",
}
CONFIRMED5_REQUIRED_SAMPLE_COLUMNS = {
    "snapshot_id",
    "instrument",
    "signal_date",
    "ranking_eligible_D0",
}
CONFIRMED5_SPLIT_FIELD = "split"
CONFIRMED5_TRAIN_SPLIT_VALUES = ("train",)
CONFIRMED5_VALIDATION_SPLIT_VALUES = ("validation", "eval")
CONFIRMED5_REQUIRED_SOURCE_COLUMNS = {
    "snapshot_id",
    "ts_code",
    "trade_date",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "close",
    "amount",
    "vol",
    "pct_chg",
    "adj_factor",
}

MODEL_SCORES_FILENAME = "model_scores_D0.parquet"
MODEL_SCORES_AUDIT_FILENAME = "model_scores_D0_audit.json"
TRAINING_MANIFEST_FILENAME = "training_manifest.json"

MODEL_SCORES_COLUMNS = [
    "run_id",
    "candidate_scheme_id",
    "snapshot_id",
    "instrument",
    "signal_date",
    "model_score_D0",
    "feature_set_id",
    "model_config_id",
    "config_hash",
]

MODEL_SCORES_AUDIT_FIELDS = [
    "run_id",
    "attempt_id",
    "candidate_scheme_id",
    "snapshot_id",
    "row_count",
    "null_score_rows",
    "nonfinite_score_rows",
    "train_rows",
    "validation_rows",
    "feature_count",
    "feature_missing_summary",
    "feature_column_mapping_status",
    "baseline_candidate_scheme_id",
    "feature_set_hash",
    "model_config_hash",
    "config_hash",
    "status",
]

TRAINING_MANIFEST_FIELDS = [
    "run_id",
    "attempt_id",
    "candidate_scheme_id",
    "feature_set_id",
    "model_config_id",
    "snapshot_id",
    "config_hash",
    "random_seed",
    "training_started_at",
    "training_finished_at",
    "git_commit_hash",
    "environment_summary",
    "status",
]

FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE = (
    "feature source mapping is not yet implemented / feature columns cannot be resolved."
)
CONFIRMED5_DATA_SOURCE_AUDIT_NOT_RESOLVED_MESSAGE = "confirmed5 data source audit must be resolved"
CONFIRMED5_DATA_SOURCE_READY_FLAG_MESSAGE = "confirmed5 data source audit requires all features ready_for_data_loading=true"
CONFIRMED5_INPUT_PATH_NOT_FOUND_MESSAGE = "confirmed5 training data input path not found"
CONFIRMED5_REQUIRED_FEATURE_COLUMNS_MISSING_MESSAGE = "confirmed5 required feature columns missing"
CONFIRMED5_SPLIT_FIELD_NOT_AVAILABLE_MESSAGE = (
    "train validation split field is not available in confirmed5 data loading source"
)


class BuildError(Exception):
    """Raised when the model score builder cannot continue safely."""


def load_validator_symbols() -> tuple[type[Exception], Any, Any]:
    spec = importlib.util.spec_from_file_location("nlc_manifest_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load manifest validator from {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ValidationError, module.load_json_manifest, module.validate_manifests


ValidationError, load_json_manifest, validate_manifests = load_validator_symbols()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build minimal Nonlinear Challenger v1 model_scores_D0 artifacts."
    )
    parser.add_argument("--feature-set", required=True, type=Path, help="Path to feature_set manifest JSON.")
    parser.add_argument("--model-config", required=True, type=Path, help="Path to model_config manifest JSON.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to candidate manifest JSON.")
    parser.add_argument("--run-id", required=True, help="Run identifier for the model_scores build attempt.")
    parser.add_argument("--attempt-id", required=True, help="Attempt identifier for the model_scores build attempt.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Target output directory for future artifacts.")
    return parser


def load_and_validate_manifests(
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    feature_set = load_json_manifest(feature_set_path, "feature_set")
    model_config = load_json_manifest(model_config_path, "model_config")
    candidate = load_json_manifest(candidate_path, "candidate")
    validate_manifests(feature_set, model_config, candidate)
    return feature_set, model_config, candidate


def resolve_source_audit_path(feature_set: dict[str, Any]) -> Path:
    source_audit_value = feature_set.get("source_audit_file")
    if not source_audit_value:
        return SOURCE_AUDIT_PATH

    source_audit_path = Path(str(source_audit_value))
    if source_audit_path.is_absolute():
        return source_audit_path
    return ROOT / source_audit_path


def resolve_feature_sources_or_fail(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    _ = model_config
    _ = candidate

    requested_features = feature_set.get("feature_list")
    if not isinstance(requested_features, list):
        raise BuildError("feature_set.feature_list must be a list before source gating can proceed.")

    audit_path = resolve_source_audit_path(feature_set)
    audit_suffix = f" See source audit: {audit_path}"

    try:
        source_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc
    except json.JSONDecodeError as exc:
        raise BuildError(FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE + audit_suffix) from exc

    audit_features = source_audit.get("features")
    if not isinstance(audit_features, list):
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + audit_suffix
        )

    feature_ready_flags: dict[str, bool] = {}
    for feature in audit_features:
        feature_name = feature.get("feature_name")
        if not isinstance(feature_name, str):
            continue
        feature_ready_flags[feature_name] = feature.get("ready_for_training") is True

    missing_from_audit = sorted(
        feature_name for feature_name in requested_features if feature_name not in feature_ready_flags
    )
    if missing_from_audit:
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + " Requested features are missing from the source audit: "
            + ", ".join(missing_from_audit)
            + "."
            + audit_suffix
        )

    not_ready_features = sorted(
        feature_name for feature_name in requested_features if feature_ready_flags[feature_name] is not True
    )
    if not_ready_features:
        raise BuildError(
            FEATURE_SOURCE_MAPPING_NOT_IMPLEMENTED_MESSAGE
            + " Requested features are not ready_for_training=true: "
            + ", ".join(not_ready_features)
            + "."
            + audit_suffix
        )


def build_data_loading_audit(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
    output_dir: Path,
    status: str,
    load_plan: dict[str, Any] | None = None,
    train_rows: int | None = None,
    validation_rows: int | None = None,
    feature_missing_summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    _ = model_config
    requested_features = feature_set.get("feature_list")
    if not isinstance(requested_features, list):
        requested_features = []

    audit_payload = {
        "stage": "data_loading",
        "status": status,
        "feature_set_id": feature_set.get("feature_set_id"),
        "candidate_scheme_id": candidate.get("candidate_scheme_id"),
        "snapshot_id": candidate.get("snapshot_id"),
        "requested_feature_count": len(requested_features),
        "requested_features": requested_features,
        "source_gate_status": "passed",
        "resolved_train_data_source": None if load_plan is None else str(load_plan["train_sample_panel_path"]),
        "resolved_validation_data_source": None if load_plan is None else str(load_plan["validation_sample_panel_path"]),
        "output_dir": str(output_dir),
    }
    if load_plan is not None:
        audit_payload["source_db_path"] = str(load_plan["source_db_path"])
        audit_payload["source_view"] = load_plan["source_view"]
        audit_payload["feature_columns"] = load_plan["feature_columns"]
        audit_payload["split_mask_fields"] = load_plan["split_mask_fields"]
    if train_rows is not None:
        audit_payload["train_rows"] = train_rows
    if validation_rows is not None:
        audit_payload["validation_rows"] = validation_rows
    if feature_missing_summary is not None:
        audit_payload["feature_missing_summary"] = feature_missing_summary
    return audit_payload


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"{label} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"{label} is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise BuildError(f"{label} must be a JSON object: {path}")
    return payload


def resolve_confirmed5_data_source_audit_path() -> Path:
    override = os.environ.get("NLC_CONFIRMED5_DATA_SOURCE_AUDIT_PATH")
    if override:
        return Path(override)
    return CONFIRMED5_DATA_SOURCE_AUDIT_PATH


def load_confirmed5_data_source_audit(
    feature_set: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if feature_set.get("feature_set_id") != CONFIRMED5_FEATURE_SET_ID:
        raise BuildError("training data loading is only implemented for confirmed5.")
    if candidate.get("candidate_scheme_id") != CONFIRMED5_CANDIDATE_SCHEME_ID:
        raise BuildError("training data loading is only implemented for the confirmed5 candidate.")

    audit_path = resolve_confirmed5_data_source_audit_path()
    payload = load_json_file(audit_path, "confirmed5 data source audit")
    if payload.get("feature_set_id") != CONFIRMED5_FEATURE_SET_ID:
        raise BuildError(f"confirmed5 data source audit feature_set_id mismatch: {audit_path}")
    if payload.get("candidate_scheme_id") != CONFIRMED5_CANDIDATE_SCHEME_ID:
        raise BuildError(f"confirmed5 data source audit candidate_scheme_id mismatch: {audit_path}")
    return payload


def resolve_runtime_input_path(raw_value: str, env_var_name: str) -> Path:
    override = os.environ.get(env_var_name)
    resolved = override if override else raw_value
    return Path(resolved)


def build_confirmed5_data_loading_plan_or_fail(
    feature_set: dict[str, Any],
    candidate: dict[str, Any],
    data_source_audit: dict[str, Any],
) -> dict[str, Any]:
    if data_source_audit.get("data_source_status") != "resolved":
        raise BuildError(
            f"{CONFIRMED5_DATA_SOURCE_AUDIT_NOT_RESOLVED_MESSAGE}: "
            f"{data_source_audit.get('data_source_status')!r}"
        )

    audit_features = data_source_audit.get("features")
    if not isinstance(audit_features, list):
        raise BuildError(CONFIRMED5_DATA_SOURCE_READY_FLAG_MESSAGE)

    feature_readiness = {
        feature.get("feature_name"): feature.get("ready_for_data_loading") is True
        for feature in audit_features
        if isinstance(feature.get("feature_name"), str)
    }
    requested_features = feature_set.get("feature_list")
    if not isinstance(requested_features, list):
        raise BuildError("feature_set.feature_list must be a list before data loading can proceed.")
    if requested_features != CONFIRMED5_REQUIRED_FEATURES:
        raise BuildError(f"confirmed5 feature_list mismatch: {requested_features!r}")

    not_ready_features = [
        feature_name
        for feature_name in requested_features
        if feature_readiness.get(feature_name) is not True
    ]
    if not_ready_features:
        raise BuildError(
            f"{CONFIRMED5_DATA_SOURCE_READY_FLAG_MESSAGE}: " + ", ".join(not_ready_features)
        )

    train_source = data_source_audit.get("train_data_source")
    validation_source = data_source_audit.get("validation_data_source")
    if not isinstance(train_source, dict) or not isinstance(validation_source, dict):
        raise BuildError("confirmed5 data source audit must define train_data_source and validation_data_source")

    train_sample_panel_path = resolve_runtime_input_path(
        str(train_source.get("sample_panel_file", "")),
        "NLC_CONFIRMED5_SAMPLE_PANEL_PATH",
    )
    validation_sample_panel_path = resolve_runtime_input_path(
        str(validation_source.get("sample_panel_file", "")),
        "NLC_CONFIRMED5_VALIDATION_SAMPLE_PANEL_PATH",
    )
    source_db_path = resolve_runtime_input_path(
        str(train_source.get("source_db_file", "")),
        "NLC_CONFIRMED5_SOURCE_DB_PATH",
    )
    source_view = str(train_source.get("source_view", ""))

    missing_paths = [
        path
        for path in (train_sample_panel_path, validation_sample_panel_path, source_db_path)
        if not path.exists()
    ]
    if missing_paths:
        raise BuildError(
            f"{CONFIRMED5_INPUT_PATH_NOT_FOUND_MESSAGE}: "
            + ", ".join(str(path) for path in missing_paths)
        )

    return {
        "train_sample_panel_path": train_sample_panel_path,
        "validation_sample_panel_path": validation_sample_panel_path,
        "source_db_path": source_db_path,
        "source_view": source_view,
        "snapshot_id": candidate.get("snapshot_id"),
        "join_key": train_source.get("join_key", ["instrument", "signal_date"]),
        "split_mask_fields": train_source.get("split_mask_fields", ["train_mask_v1", "eval_mask_v1"]),
        "feature_columns": [CONFIRMED5_FEATURE_COLUMN_MAP[name] for name in CONFIRMED5_REQUIRED_FEATURES],
    }


def describe_columns(con: duckdb.DuckDBPyConnection, relation_name: str) -> set[str]:
    rows = con.execute(f"DESCRIBE {relation_name}").fetchall()
    return {str(row[0]) for row in rows}


def ensure_required_columns_or_fail(
    available_columns: set[str],
    required_columns: set[str],
    relation_label: str,
) -> None:
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise BuildError(
            f"{CONFIRMED5_REQUIRED_FEATURE_COLUMNS_MISSING_MESSAGE}: "
            f"{relation_label} missing " + ", ".join(missing_columns)
        )


def ensure_confirmed5_split_field_or_fail(available_columns: set[str]) -> None:
    if CONFIRMED5_SPLIT_FIELD not in available_columns:
        raise BuildError(CONFIRMED5_SPLIT_FIELD_NOT_AVAILABLE_MESSAGE)


def build_confirmed5_feature_frame(
    load_plan: dict[str, Any],
) -> tuple[int, int, dict[str, int]]:
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{load_plan['source_db_path'].as_posix()}' AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW project_sample_panel AS
            SELECT * FROM read_parquet('{load_plan["train_sample_panel_path"].as_posix()}')
            """
        )
        sample_columns = describe_columns(con, "project_sample_panel")
        ensure_required_columns_or_fail(sample_columns, CONFIRMED5_REQUIRED_SAMPLE_COLUMNS, "project_sample_panel")
        ensure_confirmed5_split_field_or_fail(sample_columns)

        source_relation = f"warehouse_db.{load_plan['source_view']}"
        source_columns = describe_columns(con, source_relation)
        ensure_required_columns_or_fail(source_columns, CONFIRMED5_REQUIRED_SOURCE_COLUMNS, source_relation)

        snapshot_id = str(load_plan["snapshot_id"]).replace("'", "''")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW bar_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    adj_open,
                    adj_high,
                    adj_low,
                    adj_close,
                    close,
                    amount,
                    vol,
                    COALESCE(
                        adj_factor,
                        CASE
                            WHEN close > 1e-12 THEN adj_close / close
                            ELSE NULL
                        END
                    ) AS adj_factor_used,
                    pct_chg / 100.0 AS pct_ret
                FROM {source_relation}
                WHERE snapshot_id = '{snapshot_id}'
            ),
            enriched AS (
                SELECT
                    instrument,
                    signal_date,
                    adj_open,
                    adj_high,
                    adj_low,
                    adj_close,
                    amount,
                    vol,
                    pct_ret,
                    LN(GREATEST(vol, 0.0) + 1.0) AS log_volume,
                    CASE
                        WHEN LAG(adj_close, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) > 1e-12
                        THEN adj_close / LAG(adj_close, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        )
                        ELSE NULL
                    END AS close_rel1,
                    CASE
                        WHEN LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) > 1e-12
                        THEN LN(vol / LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) + 1.0)
                        ELSE NULL
                    END AS log_volume_rel1,
                    GREATEST(
                        vol - LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ),
                        0.0
                    ) AS pos_vol_delta,
                    GREATEST(
                        LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        ) - vol,
                        0.0
                    ) AS neg_vol_delta,
                    ABS(
                        vol - LAG(vol, 1) OVER (
                            PARTITION BY instrument ORDER BY signal_date
                        )
                    ) AS abs_vol_delta
                FROM bars
            )
            SELECT
                instrument,
                signal_date,
                (adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw,
                CORR(close_rel1, log_volume_rel1) OVER w30 AS alpha158_cord30_raw,
                CORR(adj_close, log_volume) OVER w30 AS alpha158_corr30_raw,
                CASE
                    WHEN SUM(abs_vol_delta) OVER w60 > 0
                    THEN (
                        SUM(pos_vol_delta) OVER w60 - SUM(neg_vol_delta) OVER w60
                    ) / (SUM(abs_vol_delta) OVER w60 + 1e-12)
                    ELSE NULL
                END AS alpha158_vsumd60_raw,
                STDDEV_SAMP(pct_ret) OVER w20 AS volatility_20d_raw
            FROM enriched
            WINDOW
                w AS (PARTITION BY instrument ORDER BY signal_date),
                w20 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ),
                w30 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                ),
                w60 AS (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                )
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW feature_frame AS
            SELECT
                p.snapshot_id,
                p.instrument,
                p.signal_date,
                p.ranking_eligible_D0,
                p.split,
                b.reversal_5d_raw,
                b.alpha158_cord30_raw,
                b.alpha158_corr30_raw,
                b.alpha158_vsumd60_raw,
                b.volatility_20d_raw
            FROM project_sample_panel p
            LEFT JOIN bar_features b
              ON p.instrument = b.instrument
             AND p.signal_date = b.signal_date
            """
        )
        feature_frame_columns = describe_columns(con, "feature_frame")
        ensure_required_columns_or_fail(
            feature_frame_columns,
            set(load_plan["feature_columns"]) | CONFIRMED5_REQUIRED_SAMPLE_COLUMNS,
            "feature_frame",
        )

        train_rows, validation_rows = con.execute(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN ranking_eligible_D0
                         AND LOWER(split) IN ({", ".join(repr(value) for value in CONFIRMED5_TRAIN_SPLIT_VALUES)})
                        THEN 1
                        ELSE 0
                    END
                ) AS train_rows,
                SUM(
                    CASE
                        WHEN ranking_eligible_D0
                         AND LOWER(split) IN ({", ".join(repr(value) for value in CONFIRMED5_VALIDATION_SPLIT_VALUES)})
                        THEN 1
                        ELSE 0
                    END
                ) AS validation_rows
            FROM feature_frame
            """
        ).fetchone()

        feature_missing_summary_rows = con.execute(
            """
            SELECT
                SUM(CASE WHEN reversal_5d_raw IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN alpha158_cord30_raw IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN alpha158_corr30_raw IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN alpha158_vsumd60_raw IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN volatility_20d_raw IS NULL THEN 1 ELSE 0 END)
            FROM feature_frame
            WHERE ranking_eligible_D0
            """
        ).fetchone()
    finally:
        con.close()

    feature_missing_summary = {
        "reversal_5d_raw": int(feature_missing_summary_rows[0] or 0),
        "alpha158_cord30_raw": int(feature_missing_summary_rows[1] or 0),
        "alpha158_corr30_raw": int(feature_missing_summary_rows[2] or 0),
        "alpha158_vsumd60_raw": int(feature_missing_summary_rows[3] or 0),
        "volatility_20d_raw": int(feature_missing_summary_rows[4] or 0),
    }
    return int(train_rows or 0), int(validation_rows or 0), feature_missing_summary


def write_data_loading_audit(output_dir: Path, audit_payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / DATA_LOADING_AUDIT_FILENAME
    audit_path.write_text(json.dumps(audit_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return audit_path


def load_training_data_or_fail(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    data_source_audit = load_confirmed5_data_source_audit(feature_set, candidate)
    load_plan = build_confirmed5_data_loading_plan_or_fail(feature_set, candidate, data_source_audit)
    train_rows, validation_rows, feature_missing_summary = build_confirmed5_feature_frame(load_plan)
    audit_payload = build_data_loading_audit(
        feature_set,
        model_config,
        candidate,
        output_dir,
        status="loaded_feature_frame_only",
        load_plan=load_plan,
        train_rows=train_rows,
        validation_rows=validation_rows,
        feature_missing_summary=feature_missing_summary,
    )
    write_data_loading_audit(output_dir, audit_payload)
    return audit_payload


def run_builder(
    feature_set_path: Path,
    model_config_path: Path,
    candidate_path: Path,
    run_id: str,
    attempt_id: str,
    output_dir: Path,
) -> int:
    _ = run_id
    _ = attempt_id

    feature_set, model_config, candidate = load_and_validate_manifests(
        feature_set_path,
        model_config_path,
        candidate_path,
    )
    resolve_feature_sources_or_fail(feature_set, model_config, candidate)
    load_training_data_or_fail(feature_set, model_config, candidate, output_dir)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run_builder(
            feature_set_path=args.feature_set,
            model_config_path=args.model_config,
            candidate_path=args.candidate,
            run_id=args.run_id,
            attempt_id=args.attempt_id,
            output_dir=args.output_dir,
        )
    except ValidationError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
