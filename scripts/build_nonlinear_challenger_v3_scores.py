#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import jsonschema


EXPECTED_FEATURE_SET_ID = "nlc_v3_fset01_confirmed5_locked_inputs"
EXPECTED_MODEL_CONFIG_ID = "nlc_v3_lgbm_regressor_depth3_seed42_locked_hparams_topk_head_quality_conditioned_capital_deployment"
EXPECTED_CANDIDATE_SCHEME_ID = (
    "nlc_v3_confirmed5_locked_topk_head_quality_conditioned_capital_deployment_lgbm_depth3_seed42"
)
EXPECTED_RESEARCH_ROUND_ID = "rr_nonlinear_challenger_v3_topk_head_quality_conditioned_capital_deployment_20260512"
EXPECTED_PARENT_CONFIRMED5_CANDIDATE_SCHEME_ID = "nlc_v1_confirmed5_lgbm_depth3_seed42"
EXPECTED_PARENT_V2_CANDIDATE_SCHEME_ID = "nlc_v2_confirmed5_locked_cs_volatility_discount_lgbm_depth3_seed42"
EXPECTED_SNAPSHOT_ID = "warehouse_20260429_trainval_20211231"
EXPECTED_PRIMARY_CHANGE_DIMENSION = "topk_head_quality_conditioned_capital_deployment"
EXPECTED_CONDITIONING_POLICY_VERSION = "nlc_v3_hqcd_v1"
EXPECTED_SOURCE_BINDING_ID = "nlc_v3_score_source_binding_v1"
MODEL_SCORES_FILENAME = "model_scores_D0.parquet"
AUDIT_FILENAME = "score_builder_audit.json"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_BINDING_PATH = (
    ROOT / "configs" / "nonlinear_challenger_v3" / "source_bindings" / "v3_score_source_binding.json"
)
ALLOWED_HEAD_QUALITY_CONDITIONING_SOURCES = {
    "train_window_frozen_calibration",
    "expanding_past_calibration",
}
ALLOWED_CALIBRATION_SCOPES = {
    "train_only",
    "expanding_past_only",
}
REQUIRED_LEAKAGE_AUDIT_FLAGS = {
    "train_only_or_expanding_past_only": True,
    "no_validation_lookup": True,
    "no_frozen_test_lookup": True,
    "no_future_signal_date_lookup": True,
    "no_portfolio_feedback_lookup": True,
    "state_inputs_d0_visible": True,
}
FORBIDDEN_INPUT_TAGS = {
    "validation",
    "frozen_test",
    "fixed_test",
    "future_signal_date",
    "future",
    "portfolio_feedback",
}
BASE_SCORE_SOURCE_SPECS = {
    "confirmed5_raw_score_D0": {
        "input_candidate_scheme_ids": {EXPECTED_PARENT_CONFIRMED5_CANDIDATE_SCHEME_ID},
        "input_score_column": "model_score_D0",
    },
    "v2_adjusted_score_D0": {
        "input_candidate_scheme_ids": {EXPECTED_PARENT_V2_CANDIDATE_SCHEME_ID},
        "input_score_column": "adjusted_score_D0",
    },
}


class BuildError(Exception):
    """Raised when the v3 score builder cannot produce auditable outputs."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build minimal nonlinear challenger v3 model_scores_D0 without training or portfolio execution."
    )
    parser.add_argument("--feature-set", required=True, type=Path, help="Path to the v3 feature_set manifest JSON.")
    parser.add_argument("--model-config", required=True, type=Path, help="Path to the v3 model_config manifest JSON.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to the v3 candidate manifest JSON.")
    parser.add_argument(
        "--base-scores",
        required=True,
        type=Path,
        help="Path to the manifest-bound confirmed5 or v2 model_scores_D0 parquet.",
    )
    parser.add_argument(
        "--conditioning-source",
        required=True,
        type=Path,
        help="Path to the train-only or expanding-past head-quality conditioning JSON.",
    )
    parser.add_argument(
        "--source-binding",
        default=DEFAULT_SOURCE_BINDING_PATH,
        type=Path,
        help="Path to the v3 source binding contract JSON.",
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


def ensure_path_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise BuildError(f"{label} not found: {path}")


def resolve_repo_path(path_value: str, *, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise BuildError(f"{label} not found: {path}")
    return path


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
    if require_field(candidate, "single_primary_change_dimension", "candidate") != EXPECTED_PRIMARY_CHANGE_DIMENSION:
        raise BuildError("candidate.single_primary_change_dimension mismatch")

    deployment_policy_interface = require_field(model_config, "deployment_policy_interface", "model_config")
    if not isinstance(deployment_policy_interface, dict):
        raise BuildError("model_config.deployment_policy_interface must be a JSON object")
    if deployment_policy_interface.get("single_primary_change_dimension") != EXPECTED_PRIMARY_CHANGE_DIMENSION:
        raise BuildError("model_config.deployment_policy_interface.single_primary_change_dimension mismatch")
    if deployment_policy_interface.get("new_model_inputs_allowed") is not False:
        raise BuildError("model_config.deployment_policy_interface.new_model_inputs_allowed must be false")
    if deployment_policy_interface.get("lightgbm_hyperparameter_changes_allowed") is not False:
        raise BuildError("model_config.deployment_policy_interface.lightgbm_hyperparameter_changes_allowed must be false")
    if deployment_policy_interface.get("execution_semantics_changes_allowed") is not False:
        raise BuildError("model_config.deployment_policy_interface.execution_semantics_changes_allowed must be false")
    if deployment_policy_interface.get("terminal_exit_policy_changes_allowed") is not False:
        raise BuildError("model_config.deployment_policy_interface.terminal_exit_policy_changes_allowed must be false")
    if deployment_policy_interface.get("portfolio_guard_changes_allowed") is not False:
        raise BuildError("model_config.deployment_policy_interface.portfolio_guard_changes_allowed must be false")

    relation_to_confirmed5 = require_field(candidate, "relation_to_confirmed5", "candidate")
    relation_to_v2 = require_field(candidate, "relation_to_v2", "candidate")
    if not isinstance(relation_to_confirmed5, dict):
        raise BuildError("candidate.relation_to_confirmed5 must be a JSON object")
    if not isinstance(relation_to_v2, dict):
        raise BuildError("candidate.relation_to_v2 must be a JSON object")
    if relation_to_confirmed5.get("parent_candidate_scheme_id") != EXPECTED_PARENT_CONFIRMED5_CANDIDATE_SCHEME_ID:
        raise BuildError("candidate.relation_to_confirmed5.parent_candidate_scheme_id mismatch")
    if relation_to_v2.get("parent_candidate_scheme_id") != EXPECTED_PARENT_V2_CANDIDATE_SCHEME_ID:
        raise BuildError("candidate.relation_to_v2.parent_candidate_scheme_id mismatch")


def validate_source_binding(
    source_binding: dict[str, Any],
    *,
    candidate: dict[str, Any],
) -> tuple[str, dict[str, Any], Path]:
    if require_field(source_binding, "source_binding_id", "source_binding") != EXPECTED_SOURCE_BINDING_ID:
        raise BuildError("source_binding.source_binding_id mismatch")
    if require_field(source_binding, "candidate_scheme_id", "source_binding") != candidate["candidate_scheme_id"]:
        raise BuildError("source_binding.candidate_scheme_id mismatch")
    if require_field(source_binding, "research_round_id", "source_binding") != candidate["research_round_id"]:
        raise BuildError("source_binding.research_round_id mismatch")
    if require_field(source_binding, "snapshot_id", "source_binding") != EXPECTED_SNAPSHOT_ID:
        raise BuildError("source_binding.snapshot_id mismatch")

    base_score_binding = require_field(source_binding, "base_score_binding", "source_binding")
    if not isinstance(base_score_binding, dict):
        raise BuildError("source_binding.base_score_binding must be a JSON object")
    bound_base_score_source = require_field(base_score_binding, "base_score_source", "source_binding.base_score_binding")
    if bound_base_score_source != "confirmed5_raw_score_D0":
        raise BuildError("source_binding.base_score_binding.base_score_source mismatch")

    bound_input_candidate_scheme_ids = require_field(
        base_score_binding,
        "bound_input_candidate_scheme_ids",
        "source_binding.base_score_binding",
    )
    if bound_input_candidate_scheme_ids != [EXPECTED_PARENT_CONFIRMED5_CANDIDATE_SCHEME_ID]:
        raise BuildError("source_binding.base_score_binding.bound_input_candidate_scheme_ids mismatch")
    if require_field(
        base_score_binding,
        "bound_input_score_column",
        "source_binding.base_score_binding",
    ) != "model_score_D0":
        raise BuildError("source_binding.base_score_binding.bound_input_score_column mismatch")

    prohibited_candidate_scheme_ids = require_field(
        base_score_binding,
        "prohibited_candidate_scheme_ids",
        "source_binding.base_score_binding",
    )
    if "reversal_tail_exclude_p98_v1" not in prohibited_candidate_scheme_ids:
        raise BuildError(
            "source_binding.base_score_binding.prohibited_candidate_scheme_ids must include reversal_tail_exclude_p98_v1"
        )

    long_term_prefixes = require_field(
        base_score_binding,
        "long_term_formal_source_must_not_use_path_prefixes",
        "source_binding.base_score_binding",
    )
    if "/private/tmp/" not in long_term_prefixes:
        raise BuildError(
            "source_binding.base_score_binding.long_term_formal_source_must_not_use_path_prefixes must include /private/tmp/"
        )

    conditioning_source_binding = require_field(source_binding, "conditioning_source_binding", "source_binding")
    if not isinstance(conditioning_source_binding, dict):
        raise BuildError("source_binding.conditioning_source_binding must be a JSON object")
    if require_field(
        conditioning_source_binding,
        "conditioning_policy_version",
        "source_binding.conditioning_source_binding",
    ) != EXPECTED_CONDITIONING_POLICY_VERSION:
        raise BuildError("source_binding.conditioning_source_binding.conditioning_policy_version mismatch")

    schema_path = resolve_repo_path(
        str(
            require_field(
                conditioning_source_binding,
                "required_schema_path",
                "source_binding.conditioning_source_binding",
            )
        ),
        label="conditioning source schema",
    )
    required_provenance_fields = require_field(
        conditioning_source_binding,
        "required_provenance_fields",
        "source_binding.conditioning_source_binding",
    )
    if not isinstance(required_provenance_fields, list) or not required_provenance_fields:
        raise BuildError("source_binding.conditioning_source_binding.required_provenance_fields must be a non-empty list")
    if "source_score_candidate_scheme_id" not in required_provenance_fields:
        raise BuildError(
            "source_binding.conditioning_source_binding.required_provenance_fields must include source_score_candidate_scheme_id"
        )
    if "source_binding_id" not in required_provenance_fields:
        raise BuildError(
            "source_binding.conditioning_source_binding.required_provenance_fields must include source_binding_id"
        )

    try:
        spec = BASE_SCORE_SOURCE_SPECS[bound_base_score_source]
    except KeyError as exc:
        raise BuildError(f"base score source spec is not registered: {bound_base_score_source!r}") from exc
    return bound_base_score_source, spec, schema_path


def validate_conditioning_source(
    conditioning_source: dict[str, Any],
    *,
    conditioning_source_schema: dict[str, Any],
    source_binding: dict[str, Any],
    candidate_scheme_id: str,
    bound_base_score_source: str,
) -> tuple[int, str, str]:
    try:
        jsonschema.validate(conditioning_source, conditioning_source_schema)
    except jsonschema.ValidationError as exc:
        raise BuildError(f"conditioning_source schema validation failed: {exc.message}") from exc

    if require_field(conditioning_source, "snapshot_id", "conditioning_source") != EXPECTED_SNAPSHOT_ID:
        raise BuildError("conditioning_source.snapshot_id mismatch")
    if require_field(conditioning_source, "candidate_scheme_id", "conditioning_source") != candidate_scheme_id:
        raise BuildError("conditioning_source.candidate_scheme_id mismatch")
    if require_field(conditioning_source, "base_score_source", "conditioning_source") != bound_base_score_source:
        raise BuildError("conditioning_source.base_score_source mismatch")

    conditioning_policy_version = require_field(
        conditioning_source, "conditioning_policy_version", "conditioning_source"
    )
    if conditioning_policy_version != EXPECTED_CONDITIONING_POLICY_VERSION:
        raise BuildError(
            "conditioning_source.conditioning_policy_version mismatch: "
            f"expected {EXPECTED_CONDITIONING_POLICY_VERSION!r}, got {conditioning_policy_version!r}"
        )

    head_quality_conditioning_source = require_field(
        conditioning_source, "head_quality_conditioning_source", "conditioning_source"
    )
    if head_quality_conditioning_source not in ALLOWED_HEAD_QUALITY_CONDITIONING_SOURCES:
        raise BuildError(
            "using validation/frozen/future/portfolio feedback is prohibited: "
            f"invalid head_quality_conditioning_source={head_quality_conditioning_source!r}"
        )

    calibration_scope = require_field(conditioning_source, "calibration_scope", "conditioning_source")
    if calibration_scope not in ALLOWED_CALIBRATION_SCOPES:
        raise BuildError(
            "conditioning_source.calibration_scope must be train_only or expanding_past_only, "
            f"got {calibration_scope!r}"
        )

    topk = require_field(conditioning_source, "topk", "conditioning_source")
    if not isinstance(topk, int) or topk <= 0:
        raise BuildError(f"conditioning_source.topk must be a positive integer, got {topk!r}")

    leakage_audit_flags = require_field(conditioning_source, "leakage_audit_flags", "conditioning_source")
    if not isinstance(leakage_audit_flags, dict):
        raise BuildError("conditioning_source.leakage_audit_flags must be a JSON object")
    for key, expected_value in REQUIRED_LEAKAGE_AUDIT_FLAGS.items():
        if leakage_audit_flags.get(key) is not expected_value:
            raise BuildError(f"conditioning_source.leakage_audit_flags[{key!r}] must be {expected_value!r}")

    forbidden_input_tags = require_field(conditioning_source, "forbidden_input_tags", "conditioning_source")
    if not isinstance(forbidden_input_tags, list):
        raise BuildError("conditioning_source.forbidden_input_tags must be a list")
    triggered_tags = sorted(FORBIDDEN_INPUT_TAGS & {str(tag).strip().lower() for tag in forbidden_input_tags})
    if triggered_tags:
        raise BuildError(
            "using validation/frozen/future/portfolio feedback is prohibited: "
            + ", ".join(triggered_tags)
        )

    calibration_rows = require_field(conditioning_source, "calibration_rows", "conditioning_source")
    if not isinstance(calibration_rows, list) or not calibration_rows:
        raise BuildError("conditioning source missing calibration_rows")

    conditioning_source_binding = source_binding["conditioning_source_binding"]
    provenance = require_field(conditioning_source, "provenance", "conditioning_source")
    if not isinstance(provenance, dict):
        raise BuildError("conditioning_source.provenance must be a JSON object")
    for field in conditioning_source_binding["required_provenance_fields"]:
        value = require_field(provenance, field, "conditioning_source.provenance")
        if isinstance(value, str) and not value.strip():
            raise BuildError(f"conditioning_source.provenance.{field} must be non-empty")
    if provenance["source_binding_id"] != source_binding["source_binding_id"]:
        raise BuildError("conditioning_source.provenance.source_binding_id mismatch")
    if provenance["source_score_candidate_scheme_id"] not in BASE_SCORE_SOURCE_SPECS[bound_base_score_source]["input_candidate_scheme_ids"]:
        raise BuildError("conditioning_source.provenance.source_score_candidate_scheme_id mismatch")
    if provenance["temporal_scope"] != calibration_scope:
        raise BuildError("conditioning_source.provenance.temporal_scope mismatch")
    if provenance["validation_used"] is not False:
        raise BuildError("conditioning_source.provenance.validation_used must be false")
    if provenance["frozen_test_used"] is not False:
        raise BuildError("conditioning_source.provenance.frozen_test_used must be false")
    if provenance["portfolio_feedback_used"] is not False:
        raise BuildError("conditioning_source.provenance.portfolio_feedback_used must be false")

    global_reference_count = 0
    for row in calibration_rows:
        if not isinstance(row, dict):
            raise BuildError("conditioning_source.calibration_rows entries must be JSON objects")
        topk_rank_bucket = require_field(row, "topk_rank_bucket", "conditioning_source.calibration_rows entry")
        head_quality_cell_id = require_field(row, "head_quality_cell_id", "conditioning_source.calibration_rows entry")
        percentile_rank = require_field(
            row,
            "head_quality_cell_percentile_rank",
            "conditioning_source.calibration_rows entry",
        )
        if not str(topk_rank_bucket).strip():
            raise BuildError("conditioning_source.calibration_rows topk_rank_bucket must be non-empty")
        if not str(head_quality_cell_id).strip():
            raise BuildError("conditioning_source.calibration_rows head_quality_cell_id must be non-empty")
        if not isinstance(percentile_rank, (int, float)) or not (0.0 <= float(percentile_rank) <= 1.0):
            raise BuildError(
                "conditioning_source.calibration_rows head_quality_cell_percentile_rank "
                f"must be within [0.0, 1.0], got {percentile_rank!r}"
            )
        if str(topk_rank_bucket) == "global_topk_train_reference":
            global_reference_count += 1

    if global_reference_count > 1:
        raise BuildError("conditioning_source may declare at most one global_topk_train_reference row")

    return topk, str(conditioning_policy_version), str(head_quality_conditioning_source)


def build_scores_or_fail(
    *,
    base_scores_path: Path,
    conditioning_source_path: Path,
    conditioning_source: dict[str, Any],
    conditioning_source_schema: dict[str, Any],
    source_binding: dict[str, Any],
    bound_base_score_source: str,
    base_score_spec: dict[str, Any],
    candidate: dict[str, Any],
    output_dir: Path,
    run_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_scores_path = output_dir / MODEL_SCORES_FILENAME
    audit_path = output_dir / AUDIT_FILENAME

    topk, conditioning_policy_version, head_quality_conditioning_source = validate_conditioning_source(
        conditioning_source,
        conditioning_source_schema=conditioning_source_schema,
        source_binding=source_binding,
        candidate_scheme_id=str(candidate["candidate_scheme_id"]),
        bound_base_score_source=bound_base_score_source,
    )

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            CREATE OR REPLACE VIEW base_scores AS
            SELECT *
            FROM read_parquet('{base_scores_path.as_posix()}')
            """
        )

        base_score_columns = {row[0] for row in con.execute("DESCRIBE base_scores").fetchall()}
        required_base_score_columns = {
            "snapshot_id",
            "instrument",
            "signal_date",
            "candidate_scheme_id",
            base_score_spec["input_score_column"],
        }
        missing_base_score_columns = sorted(required_base_score_columns - base_score_columns)
        if missing_base_score_columns:
            raise BuildError("base scores missing required columns: " + ", ".join(missing_base_score_columns))

        snapshot_rows = con.execute(
            """
            SELECT COUNT(DISTINCT snapshot_id), MIN(snapshot_id), MAX(snapshot_id)
            FROM base_scores
            """
        ).fetchone()
        distinct_snapshot_count = int(snapshot_rows[0] or 0)
        if distinct_snapshot_count != 1 or snapshot_rows[1] != EXPECTED_SNAPSHOT_ID:
            raise BuildError(
                "base scores snapshot_id mismatch: "
                f"expected one snapshot {EXPECTED_SNAPSHOT_ID!r}, got count={distinct_snapshot_count}, "
                f"min={snapshot_rows[1]!r}, max={snapshot_rows[2]!r}"
            )

        input_candidate_ids = {
            row[0]
            for row in con.execute("SELECT DISTINCT candidate_scheme_id FROM base_scores ORDER BY candidate_scheme_id").fetchall()
        }
        allowed_input_candidate_ids = set(base_score_spec["input_candidate_scheme_ids"])
        prohibited_input_candidate_ids = set(source_binding["base_score_binding"]["prohibited_candidate_scheme_ids"])
        prohibited_hits = sorted(input_candidate_ids & prohibited_input_candidate_ids)
        if prohibited_hits:
            raise BuildError(
                "base scores candidate_scheme_id is prohibited for v3 confirmed5 binding: " + ", ".join(prohibited_hits)
            )
        if input_candidate_ids != allowed_input_candidate_ids:
            raise BuildError(
                "base scores candidate_scheme_id mismatch: "
                f"expected {sorted(allowed_input_candidate_ids)!r}, got {sorted(input_candidate_ids)!r}"
            )

        base_score_column = str(base_score_spec["input_score_column"])
        base_score_validation_row = con.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN {base_score_column} IS NULL THEN 1 ELSE 0 END) AS null_base_score_rows,
                SUM(CASE WHEN isfinite(CAST({base_score_column} AS DOUBLE)) THEN 0 ELSE 1 END) AS nonfinite_base_score_rows,
                COUNT(*) - COUNT(DISTINCT instrument || '|' || signal_date) AS duplicate_instrument_date_rows
            FROM base_scores
            """
        ).fetchone()

        input_row_count = int(base_score_validation_row[0] or 0)
        null_base_score_rows = int(base_score_validation_row[1] or 0)
        nonfinite_base_score_rows = int(base_score_validation_row[2] or 0)
        duplicate_instrument_date_rows = int(base_score_validation_row[3] or 0)

        if input_row_count <= 0:
            raise BuildError("base scores produced zero rows")
        if null_base_score_rows > 0:
            raise BuildError(f"base score missing: null rows={null_base_score_rows}")
        if nonfinite_base_score_rows > 0:
            raise BuildError(f"base score contains nonfinite rows: {nonfinite_base_score_rows}")
        if duplicate_instrument_date_rows > 0:
            raise BuildError(f"base scores contain duplicate instrument/signal_date rows: {duplicate_instrument_date_rows}")

        con.execute(
            """
            CREATE TEMP TABLE conditioning_table (
                topk_rank_bucket VARCHAR,
                head_quality_cell_id VARCHAR,
                head_quality_cell_percentile_rank DOUBLE
            )
            """
        )
        con.executemany(
            "INSERT INTO conditioning_table VALUES (?, ?, ?)",
            [
                (
                    str(row["topk_rank_bucket"]),
                    str(row["head_quality_cell_id"]),
                    float(row["head_quality_cell_percentile_rank"]),
                )
                for row in conditioning_source["calibration_rows"]
            ],
        )

        candidate_scheme_id_sql = str(candidate["candidate_scheme_id"]).replace("'", "''")
        run_id_sql = run_id.replace("'", "''")
        conditioning_policy_version_sql = conditioning_policy_version.replace("'", "''")
        head_quality_conditioning_source_sql = head_quality_conditioning_source.replace("'", "''")
        leakage_audit_flags_json = json.dumps(REQUIRED_LEAKAGE_AUDIT_FLAGS, sort_keys=True, ensure_ascii=True).replace(
            "'",
            "''",
        )

        con.execute(
            f"""
            CREATE OR REPLACE VIEW v3_scores AS
            WITH ranked AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    CAST({base_score_column} AS DOUBLE) AS raw_score_D0,
                    ROW_NUMBER() OVER (
                        PARTITION BY signal_date
                        ORDER BY CAST({base_score_column} AS DOUBLE) DESC, instrument ASC
                    ) AS topk_rank_position
                FROM base_scores
            ),
            provisional AS (
                SELECT
                    snapshot_id,
                    instrument,
                    signal_date,
                    raw_score_D0,
                    topk_rank_position <= {topk} AS provisional_topk_member,
                    CASE
                        WHEN topk_rank_position <= {topk}
                        THEN 'top_' || CAST(topk_rank_position AS VARCHAR)
                        ELSE NULL
                    END AS topk_rank_bucket
                FROM ranked
            ),
            conditioned AS (
                SELECT
                    p.snapshot_id,
                    p.instrument,
                    p.signal_date,
                    p.raw_score_D0,
                    p.provisional_topk_member,
                    p.topk_rank_bucket,
                    COALESCE(exact_lookup.head_quality_cell_id, fallback_lookup.head_quality_cell_id) AS head_quality_cell_id,
                    COALESCE(
                        exact_lookup.head_quality_cell_percentile_rank,
                        fallback_lookup.head_quality_cell_percentile_rank
                    ) AS head_quality_cell_percentile_rank
                FROM provisional p
                LEFT JOIN conditioning_table exact_lookup
                  ON p.topk_rank_bucket = exact_lookup.topk_rank_bucket
                LEFT JOIN conditioning_table fallback_lookup
                  ON fallback_lookup.topk_rank_bucket = 'global_topk_train_reference'
            )
            SELECT
                '{run_id_sql}' AS run_id,
                snapshot_id,
                instrument,
                signal_date,
                '{candidate_scheme_id_sql}' AS candidate_scheme_id,
                raw_score_D0,
                provisional_topk_member,
                topk_rank_bucket,
                head_quality_cell_id,
                head_quality_cell_percentile_rank,
                CASE
                    WHEN provisional_topk_member
                    THEN LEAST(1.00, GREATEST(0.50, 0.50 + 0.50 * head_quality_cell_percentile_rank))
                    ELSE 0.0
                END AS capital_deployment_multiplier,
                CASE
                    WHEN provisional_topk_member
                    THEN raw_score_D0 * LEAST(1.00, GREATEST(0.50, 0.50 + 0.50 * head_quality_cell_percentile_rank))
                    ELSE 0.0
                END AS adjusted_score_D0,
                CASE
                    WHEN provisional_topk_member
                    THEN raw_score_D0 * LEAST(1.00, GREATEST(0.50, 0.50 + 0.50 * head_quality_cell_percentile_rank))
                    ELSE 0.0
                END AS model_score_D0,
                '{head_quality_conditioning_source_sql}' AS head_quality_conditioning_source,
                '{conditioning_policy_version_sql}' AS conditioning_policy_version,
                '{leakage_audit_flags_json}' AS leakage_audit_flags
            FROM conditioned
            """
        )

        validation_row = con.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN provisional_topk_member AND head_quality_cell_id IS NULL THEN 1 ELSE 0 END) AS missing_conditioning_rows,
                SUM(CASE WHEN provisional_topk_member AND (capital_deployment_multiplier < 0.50 OR capital_deployment_multiplier > 1.00) THEN 1 ELSE 0 END) AS multiplier_out_of_range_rows,
                SUM(CASE WHEN NOT provisional_topk_member AND capital_deployment_multiplier <> 0.0 THEN 1 ELSE 0 END) AS non_topk_nonzero_multiplier_rows,
                SUM(CASE WHEN adjusted_score_D0 IS NULL THEN 1 ELSE 0 END) AS null_adjusted_score_rows,
                SUM(CASE WHEN isfinite(adjusted_score_D0) THEN 0 ELSE 1 END) AS nonfinite_adjusted_score_rows,
                SUM(CASE WHEN provisional_topk_member THEN 1 ELSE 0 END) AS provisional_topk_rows,
                SUM(CASE WHEN NOT provisional_topk_member THEN 1 ELSE 0 END) AS non_topk_rows,
                SUM(
                    CASE
                        WHEN provisional_topk_member
                         AND ABS(
                            adjusted_score_D0
                            - raw_score_D0 * capital_deployment_multiplier
                         ) > 1e-12
                        THEN 1
                        ELSE 0
                    END
                ) AS formula_mismatch_rows,
                MIN(CASE WHEN provisional_topk_member THEN capital_deployment_multiplier ELSE NULL END) AS topk_multiplier_min,
                MAX(CASE WHEN provisional_topk_member THEN capital_deployment_multiplier ELSE NULL END) AS topk_multiplier_max
            FROM v3_scores
            """
        ).fetchone()

        row_count = int(validation_row[0] or 0)
        missing_conditioning_rows = int(validation_row[1] or 0)
        multiplier_out_of_range_rows = int(validation_row[2] or 0)
        non_topk_nonzero_multiplier_rows = int(validation_row[3] or 0)
        null_adjusted_score_rows = int(validation_row[4] or 0)
        nonfinite_adjusted_score_rows = int(validation_row[5] or 0)
        provisional_topk_rows = int(validation_row[6] or 0)
        non_topk_rows = int(validation_row[7] or 0)
        formula_mismatch_rows = int(validation_row[8] or 0)

        if row_count <= 0:
            raise BuildError("v3 score builder produced zero rows")
        if missing_conditioning_rows > 0:
            raise BuildError(f"conditioning source missing for provisional TopK rows: {missing_conditioning_rows}")
        if multiplier_out_of_range_rows > 0:
            raise BuildError(f"capital_deployment_multiplier out of [0.50, 1.00] for TopK rows: {multiplier_out_of_range_rows}")
        if non_topk_nonzero_multiplier_rows > 0:
            raise BuildError(f"non-TopK multiplier must be 0.0, found rows: {non_topk_nonzero_multiplier_rows}")
        if null_adjusted_score_rows > 0:
            raise BuildError(f"adjusted_score_D0 contains null rows: {null_adjusted_score_rows}")
        if nonfinite_adjusted_score_rows > 0:
            raise BuildError(f"adjusted_score_D0 contains nonfinite rows: {nonfinite_adjusted_score_rows}")
        if formula_mismatch_rows > 0:
            raise BuildError(f"fixed formula mismatch rows: {formula_mismatch_rows}")

        con.execute(
            f"""
            COPY (
                SELECT
                    run_id,
                    snapshot_id,
                    instrument,
                    signal_date,
                    candidate_scheme_id,
                    raw_score_D0,
                    provisional_topk_member,
                    topk_rank_bucket,
                    head_quality_cell_id,
                    head_quality_cell_percentile_rank,
                    capital_deployment_multiplier,
                    adjusted_score_D0,
                    model_score_D0,
                    head_quality_conditioning_source,
                    conditioning_policy_version,
                    leakage_audit_flags
                FROM v3_scores
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
            "base_score_source": bound_base_score_source,
            "base_score_input_path": str(base_scores_path),
            "conditioning_source_path": str(conditioning_source_path),
            "conditioning_policy_version": conditioning_policy_version,
            "head_quality_conditioning_source": head_quality_conditioning_source,
            "row_count": row_count,
            "null_score_rows": null_adjusted_score_rows,
            "nonfinite_score_rows": nonfinite_adjusted_score_rows,
            "provisional_topk_rows": provisional_topk_rows,
            "non_topk_rows": non_topk_rows,
            "topk": topk,
            "topk_multiplier_min": None if validation_row[9] is None else float(validation_row[9]),
            "topk_multiplier_max": None if validation_row[10] is None else float(validation_row[10]),
            "missing_conditioning_rows": missing_conditioning_rows,
            "input_null_base_score_rows": null_base_score_rows,
            "input_nonfinite_base_score_rows": nonfinite_base_score_rows,
            "duplicate_instrument_date_rows": duplicate_instrument_date_rows,
            "leakage_audit_flags": REQUIRED_LEAKAGE_AUDIT_FLAGS,
            "status": "scores_written_without_training_or_portfolio",
            "training_performed": False,
            "frozen_test_accessed": False,
            "portfolio_outputs_generated": False,
            "notes": [
                "This artifact reuses a manifest-bound base score source and does not retrain LightGBM.",
                "This artifact only writes v3 model_scores_D0 and score_builder_audit; it does not run portfolio or build metrics/readout.",
                "Provisional TopK membership is defined by raw_score_D0 cross-sectional ranking before conditioning.",
                "Non-TopK rows are hard-zeroed so conditioning cannot backfill names into the deployed head.",
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
    source_binding = load_json(args.source_binding, "source binding")
    validate_manifest_ids(feature_set, model_config, candidate)

    ensure_path_exists(args.base_scores, "base scores")
    ensure_path_exists(args.conditioning_source, "conditioning source")

    bound_base_score_source, base_score_spec, conditioning_schema_path = validate_source_binding(
        source_binding,
        candidate=candidate,
    )
    conditioning_source = load_json(args.conditioning_source, "conditioning source")
    conditioning_source_schema = load_json(conditioning_schema_path, "conditioning source schema")

    result = build_scores_or_fail(
        base_scores_path=args.base_scores,
        conditioning_source_path=args.conditioning_source,
        conditioning_source=conditioning_source,
        conditioning_source_schema=conditioning_source_schema,
        source_binding=source_binding,
        bound_base_score_source=bound_base_score_source,
        base_score_spec=base_score_spec,
        candidate=candidate,
        output_dir=args.output_dir,
        run_id=args.run_id,
        attempt_id=args.attempt_id,
    )
    print(f"v3 model scores written to {result['output_scores_path']}")
    print(f"v3 score builder audit written to {result['audit_path']}")
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
