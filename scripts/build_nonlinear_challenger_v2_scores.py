#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import duckdb


EXPECTED_FEATURE_SET_ID = "nlc_v2_fset01_confirmed5_locked_inputs"
EXPECTED_MODEL_CONFIG_ID = "nlc_v2_lgbm_regressor_depth3_seed42_cs_volatility_discount_v1"
EXPECTED_CANDIDATE_SCHEME_ID = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_RESEARCH_ROUND_ID = "rr_nonlinear_challenger_v2_cs_volatility_discount_20260509"
EXPECTED_PARENT_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_SNAPSHOT_ID = "warehouse_20260429_trainval_20211231"
EXPECTED_TRANSFORMATION_ID = "cs_volatility_discount_v1"
EXPECTED_FIXED_FORMULA = (
    "adjusted_score_D0 = raw_model_score_percentile_rank_D0 * "
    "(1.0 - volatility_20d_percentile_rank_D0)"
)
MODEL_SCORES_FILENAME = "model_scores_D0.parquet"
AUDIT_FILENAME = "score_transform_audit.json"


class BuildError(Exception):
    """Raised when the v2 score transformer cannot produce auditable outputs."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build nonlinear challenger v2 adjusted scores from confirmed5 raw model_scores_D0."
    )
    parser.add_argument("--feature-set", required=True, type=Path, help="Path to the v2 feature_set manifest JSON.")
    parser.add_argument("--model-config", required=True, type=Path, help="Path to the v2 model_config manifest JSON.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to the v2 candidate manifest JSON.")
    parser.add_argument(
        "--confirmed5-scores",
        required=True,
        type=Path,
        help="Path to the confirmed5 raw model_scores_D0 parquet. The script will not retrain the model.",
    )
    parser.add_argument(
        "--source-db",
        default=None,
        type=Path,
        help="Optional warehouse.duckdb override. Defaults to the source path declared by the confirmed5 source audit.",
    )
    parser.add_argument(
        "--source-audit",
        default=None,
        type=Path,
        help="Optional confirmed5 data source audit override. Defaults to feature_set.source_audit_file.",
    )
    parser.add_argument("--run-id", required=True, help="Run identifier to stamp into the output rows.")
    parser.add_argument("--attempt-id", required=True, help="Attempt identifier to stamp into the audit JSON.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for parquet and audit JSON.")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BuildError(f"{label} must be a JSON object: {path}")
    return payload


def require_field(payload: dict[str, Any], field: str, label: str) -> Any:
    if field not in payload:
        raise BuildError(f"{label} missing required field: {field}")
    return payload[field]


def validate_manifest_ids(
    feature_set: dict[str, Any],
    model_config: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    feature_set_id = require_field(feature_set, "feature_set_id", "feature_set")
    model_config_id = require_field(model_config, "model_config_id", "model_config")
    candidate_scheme_id = require_field(candidate, "candidate_scheme_id", "candidate")
    research_round_id = require_field(candidate, "research_round_id", "candidate")

    if feature_set_id != EXPECTED_FEATURE_SET_ID:
        raise BuildError(f"feature_set_id mismatch: expected {EXPECTED_FEATURE_SET_ID!r}, got {feature_set_id!r}")
    if model_config_id != EXPECTED_MODEL_CONFIG_ID:
        raise BuildError(f"model_config_id mismatch: expected {EXPECTED_MODEL_CONFIG_ID!r}, got {model_config_id!r}")
    if candidate_scheme_id != EXPECTED_CANDIDATE_SCHEME_ID:
        raise BuildError(
            f"candidate_scheme_id mismatch: expected {EXPECTED_CANDIDATE_SCHEME_ID!r}, got {candidate_scheme_id!r}"
        )
    if research_round_id != EXPECTED_RESEARCH_ROUND_ID:
        raise BuildError(
            f"research_round_id mismatch: expected {EXPECTED_RESEARCH_ROUND_ID!r}, got {research_round_id!r}"
        )

    if require_field(candidate, "feature_set_id", "candidate") != feature_set_id:
        raise BuildError("candidate.feature_set_id must match feature_set.feature_set_id")
    if require_field(candidate, "model_config_id", "candidate") != model_config_id:
        raise BuildError("candidate.model_config_id must match model_config.model_config_id")
    if require_field(feature_set, "snapshot_id", "feature_set") != EXPECTED_SNAPSHOT_ID:
        raise BuildError("feature_set.snapshot_id must match the trainval research snapshot")
    if require_field(candidate, "snapshot_id", "candidate") != EXPECTED_SNAPSHOT_ID:
        raise BuildError("candidate.snapshot_id must match the trainval research snapshot")

    relation = require_field(candidate, "relation_to_confirmed5", "candidate")
    if not isinstance(relation, dict):
        raise BuildError("candidate.relation_to_confirmed5 must be a JSON object")
    if relation.get("parent_candidate_scheme_id") != EXPECTED_PARENT_CANDIDATE_SCHEME_ID:
        raise BuildError(
            "candidate.relation_to_confirmed5.parent_candidate_scheme_id must point to the confirmed5 parent"
        )

    post_score_transformation = require_field(model_config, "post_score_transformation", "model_config")
    if not isinstance(post_score_transformation, dict):
        raise BuildError("model_config.post_score_transformation must be a JSON object")
    if post_score_transformation.get("transformation_id") != EXPECTED_TRANSFORMATION_ID:
        raise BuildError("model_config.post_score_transformation.transformation_id mismatch")
    if post_score_transformation.get("fixed_formula") != EXPECTED_FIXED_FORMULA:
        raise BuildError("model_config.post_score_transformation.fixed_formula mismatch")


def resolve_source_audit_path(feature_set: dict[str, Any], override: Path | None) -> Path:
    if override is not None:
        return override
    source_audit_file = require_field(feature_set, "source_audit_file", "feature_set")
    path = Path(str(source_audit_file))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def resolve_source_db_path(source_audit: dict[str, Any], override: Path | None) -> Path:
    if override is not None:
        return override
    train_data_source = require_field(source_audit, "train_data_source", "source_audit")
    if not isinstance(train_data_source, dict):
        raise BuildError("source_audit.train_data_source must be a JSON object")
    path = Path(str(require_field(train_data_source, "source_db_file", "source_audit.train_data_source")))
    return path


def validate_source_audit(source_audit: dict[str, Any]) -> None:
    if require_field(source_audit, "data_source_status", "source_audit") != "resolved":
        raise BuildError("confirmed5 source audit must be resolved before v2 score transformation")
    if require_field(source_audit, "snapshot_id", "source_audit") != EXPECTED_SNAPSHOT_ID:
        raise BuildError("source_audit.snapshot_id mismatch")

    features = require_field(source_audit, "features", "source_audit")
    if not isinstance(features, list):
        raise BuildError("source_audit.features must be a list")
    volatility_feature = None
    for feature in features:
        if isinstance(feature, dict) and feature.get("feature_name") == "volatility_20d":
            volatility_feature = feature
            break
    if volatility_feature is None:
        raise BuildError("source_audit does not declare volatility_20d")
    if volatility_feature.get("ready_for_data_loading") is not True:
        raise BuildError("source_audit declares volatility_20d but not ready_for_data_loading=true")
    if volatility_feature.get("source_column") != "volatility_20d_raw":
        raise BuildError("source_audit volatility_20d source_column must be volatility_20d_raw")


def ensure_path_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise BuildError(f"{label} not found: {path}")


def build_adjusted_scores_or_fail(
    confirmed5_scores_path: Path,
    source_db_path: Path,
    candidate: dict[str, Any],
    model_config: dict[str, Any],
    output_dir: Path,
    run_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_scores_path = output_dir / MODEL_SCORES_FILENAME
    audit_path = output_dir / AUDIT_FILENAME
    source_relation = "warehouse_db.serving.vw_bars_daily"
    snapshot_id = EXPECTED_SNAPSHOT_ID.replace("'", "''")
    policy_version = str(model_config["post_score_transformation"]["transformation_id"]).replace("'", "''")
    fixed_formula = str(model_config["post_score_transformation"]["fixed_formula"]).replace("'", "''")
    candidate_scheme_id = str(candidate["candidate_scheme_id"]).replace("'", "''")
    run_id_sql = run_id.replace("'", "''")

    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source_db_path.as_posix()}' AS warehouse_db (READ_ONLY)")
        con.execute(
            f"""
            CREATE OR REPLACE VIEW confirmed5_scores AS
            SELECT *
            FROM read_parquet('{confirmed5_scores_path.as_posix()}')
            """
        )

        score_columns = {row[0] for row in con.execute("DESCRIBE confirmed5_scores").fetchall()}
        required_score_columns = {
            "snapshot_id",
            "instrument",
            "signal_date",
            "candidate_scheme_id",
            "model_score_D0",
        }
        missing_score_columns = sorted(required_score_columns - score_columns)
        if missing_score_columns:
            raise BuildError(
                "confirmed5 scores missing required columns: " + ", ".join(missing_score_columns)
            )

        snapshot_rows = con.execute(
            """
            SELECT COUNT(DISTINCT snapshot_id), MIN(snapshot_id), MAX(snapshot_id)
            FROM confirmed5_scores
            """
        ).fetchone()
        distinct_snapshot_count = int(snapshot_rows[0] or 0)
        if distinct_snapshot_count != 1 or snapshot_rows[1] != EXPECTED_SNAPSHOT_ID:
            raise BuildError(
                "confirmed5 scores snapshot_id mismatch: "
                f"expected one snapshot {EXPECTED_SNAPSHOT_ID!r}, got count={distinct_snapshot_count}, "
                f"min={snapshot_rows[1]!r}, max={snapshot_rows[2]!r}"
            )

        raw_null_score_rows = int(
            con.execute("SELECT SUM(CASE WHEN model_score_D0 IS NULL THEN 1 ELSE 0 END) FROM confirmed5_scores").fetchone()[0]
            or 0
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW confirmed5_scores_transformable AS
            SELECT *
            FROM confirmed5_scores
            WHERE model_score_D0 IS NOT NULL
            """
        )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW score_date_bounds AS
            SELECT
                MIN(strptime(signal_date, '%Y%m%d')) AS min_signal_date,
                MAX(strptime(signal_date, '%Y%m%d')) AS max_signal_date
            FROM confirmed5_scores_transformable
            """
        )
        con.execute(
            """
            CREATE OR REPLACE VIEW score_instruments AS
            SELECT DISTINCT instrument
            FROM confirmed5_scores_transformable
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW volatility_features AS
            WITH bars AS (
                SELECT
                    ts_code AS instrument,
                    trade_date AS signal_date,
                    pct_chg / 100.0 AS pct_ret
                FROM {source_relation}
                WHERE snapshot_id = '{snapshot_id}'
                  AND ts_code IN (SELECT instrument FROM score_instruments)
                  AND strptime(trade_date, '%Y%m%d') BETWEEN (
                        SELECT min_signal_date - INTERVAL 60 DAY FROM score_date_bounds
                  ) AND (
                        SELECT max_signal_date FROM score_date_bounds
                  )
            )
            SELECT
                instrument,
                signal_date,
                STDDEV_SAMP(pct_ret) OVER (
                    PARTITION BY instrument
                    ORDER BY signal_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS volatility_20d_raw
            FROM bars
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE VIEW transformed_scores AS
            WITH joined AS (
                SELECT
                    s.snapshot_id,
                    s.instrument,
                    s.signal_date,
                    s.model_score_D0 AS raw_model_score_D0,
                    v.volatility_20d_raw AS volatility_20d
                FROM confirmed5_scores_transformable s
                LEFT JOIN volatility_features v
                  ON s.instrument = v.instrument
                 AND s.signal_date = v.signal_date
            ),
            ranked AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    raw_model_score_D0,
                    volatility_20d,
                    PERCENT_RANK() OVER (
                        PARTITION BY signal_date
                        ORDER BY raw_model_score_D0 ASC, instrument ASC
                    ) AS raw_model_score_percentile_rank_D0,
                    PERCENT_RANK() OVER (
                        PARTITION BY signal_date
                        ORDER BY volatility_20d ASC, instrument ASC
                    ) AS volatility_20d_percentile_rank_D0
                FROM joined
            )
            SELECT
                '{run_id_sql}' AS run_id,
                snapshot_id,
                instrument,
                signal_date,
                '{candidate_scheme_id}' AS candidate_scheme_id,
                raw_model_score_D0,
                raw_model_score_percentile_rank_D0,
                volatility_20d,
                volatility_20d_percentile_rank_D0,
                raw_model_score_percentile_rank_D0 * (1.0 - volatility_20d_percentile_rank_D0) AS adjusted_score_D0,
                raw_model_score_percentile_rank_D0 * (1.0 - volatility_20d_percentile_rank_D0) AS model_score_D0,
                '{policy_version}' AS score_transform_policy_version
            FROM ranked
            """
        )

        validation_row = con.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN volatility_20d IS NULL THEN 1 ELSE 0 END) AS missing_volatility_rows,
                SUM(CASE WHEN raw_model_score_percentile_rank_D0 IS NULL THEN 1 ELSE 0 END) AS null_raw_rank_rows,
                SUM(CASE WHEN volatility_20d_percentile_rank_D0 IS NULL THEN 1 ELSE 0 END) AS null_vol_rank_rows,
                SUM(CASE WHEN adjusted_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_adjusted_score_rows,
                SUM(CASE WHEN isfinite(adjusted_score_D0) THEN 0 ELSE 1 END) AS nonfinite_adjusted_score_rows,
                MIN(adjusted_score_D0) AS adjusted_score_min,
                MAX(adjusted_score_D0) AS adjusted_score_max,
                MIN(raw_model_score_percentile_rank_D0) AS raw_rank_min,
                MAX(raw_model_score_percentile_rank_D0) AS raw_rank_max,
                MIN(volatility_20d_percentile_rank_D0) AS vol_rank_min,
                MAX(volatility_20d_percentile_rank_D0) AS vol_rank_max
            FROM transformed_scores
            """
        ).fetchone()

        row_count = int(validation_row[0] or 0)
        missing_volatility_rows = int(validation_row[1] or 0)
        null_raw_rank_rows = int(validation_row[2] or 0)
        null_vol_rank_rows = int(validation_row[3] or 0)
        null_adjusted_score_rows = int(validation_row[4] or 0)
        nonfinite_adjusted_score_rows = int(validation_row[5] or 0)

        if row_count <= 0:
            raise BuildError("confirmed5 scores produced zero transformed rows")
        if missing_volatility_rows > 0:
            raise BuildError(f"volatility_20d missing for transformed rows: {missing_volatility_rows}")
        if null_raw_rank_rows > 0 or null_vol_rank_rows > 0:
            raise BuildError(
                "percentile rank contains null rows: "
                f"raw={null_raw_rank_rows}, volatility={null_vol_rank_rows}"
            )
        if null_adjusted_score_rows > 0:
            raise BuildError(f"adjusted_score_D0 contains null rows: {null_adjusted_score_rows}")
        if nonfinite_adjusted_score_rows > 0:
            raise BuildError(f"adjusted_score_D0 contains nonfinite rows: {nonfinite_adjusted_score_rows}")

        con.execute(
            f"""
            COPY (
                SELECT
                    run_id,
                    snapshot_id,
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
                FROM transformed_scores
                ORDER BY signal_date, instrument
            ) TO '{output_scores_path.as_posix()}' (FORMAT PARQUET)
            """
        )

        audit_payload = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "candidate_scheme_id": candidate["candidate_scheme_id"],
            "research_round_id": candidate["research_round_id"],
            "snapshot_id": EXPECTED_SNAPSHOT_ID,
            "input_confirmed5_scores": str(confirmed5_scores_path),
            "source_db_path": str(source_db_path),
            "row_count": row_count,
            "null_score_rows": null_adjusted_score_rows,
            "nonfinite_score_rows": nonfinite_adjusted_score_rows,
            "raw_input_null_score_rows": raw_null_score_rows,
            "missing_volatility_rows": missing_volatility_rows,
            "null_raw_model_score_percentile_rank_rows": null_raw_rank_rows,
            "null_volatility_20d_percentile_rank_rows": null_vol_rank_rows,
            "score_transform_policy_version": model_config["post_score_transformation"]["transformation_id"],
            "fixed_formula": model_config["post_score_transformation"]["fixed_formula"],
            "score_transform_summary": {
                "adjusted_score_min": float(validation_row[6]),
                "adjusted_score_max": float(validation_row[7]),
                "raw_model_score_percentile_rank_min": float(validation_row[8]),
                "raw_model_score_percentile_rank_max": float(validation_row[9]),
                "volatility_20d_percentile_rank_min": float(validation_row[10]),
                "volatility_20d_percentile_rank_max": float(validation_row[11]),
            },
            "status": "transformed_scores_written_without_retraining",
            "training_performed": False,
            "frozen_test_accessed": False,
            "notes": [
                "This artifact reuses confirmed5 raw model_scores_D0 and does not retrain LightGBM.",
                "This artifact is score-transformation-only and does not imply any portfolio or OOS result.",
                "The fixed post-score formula is predeclared by the v2 model_config and is not validation-tuned.",
                "Rows with null raw_model_score_D0 are excluded from percentile ranking and counted in raw_input_null_score_rows.",
            ],
        }
        audit_path.write_text(json.dumps(audit_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return {
            "output_scores_path": output_scores_path,
            "audit_path": audit_path,
            "audit_payload": audit_payload,
        }
    finally:
        con.close()


def run_builder(args: argparse.Namespace) -> int:
    feature_set = load_json(args.feature_set, "feature_set manifest")
    model_config = load_json(args.model_config, "model_config manifest")
    candidate = load_json(args.candidate, "candidate manifest")
    validate_manifest_ids(feature_set, model_config, candidate)

    ensure_path_exists(args.confirmed5_scores, "confirmed5 scores")

    source_audit_path = resolve_source_audit_path(feature_set, args.source_audit)
    ensure_path_exists(source_audit_path, "confirmed5 source audit")
    source_audit = load_json(source_audit_path, "confirmed5 source audit")
    validate_source_audit(source_audit)

    source_db_path = resolve_source_db_path(source_audit, args.source_db)
    ensure_path_exists(source_db_path, "source DB")

    build_adjusted_scores_or_fail(
        confirmed5_scores_path=args.confirmed5_scores,
        source_db_path=source_db_path,
        candidate=candidate,
        model_config=model_config,
        output_dir=args.output_dir,
        run_id=args.run_id,
        attempt_id=args.attempt_id,
    )
    print(f"v2 transformed scores written to {args.output_dir / MODEL_SCORES_FILENAME}")
    print(f"v2 transform audit written to {args.output_dir / AUDIT_FILENAME}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return run_builder(args)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
