from __future__ import annotations

from conftest import load_json


AUDIT_PATH = (
    "configs/nonlinear_challenger_v1/feature_sets/confirmed5_data_source_audit.json"
)

EXPECTED_FEATURES = [
    "reversal_5d",
    "cord30",
    "corr30",
    "vsumd60",
    "volatility_20d",
]


def test_confirmed5_data_source_audit_json_can_be_loaded() -> None:
    payload = load_json(AUDIT_PATH)

    assert isinstance(payload, dict)


def test_confirmed5_data_source_audit_marks_all_five_features_ready() -> None:
    payload = load_json(AUDIT_PATH)

    assert payload["feature_set_id"] == "nlc_v1_fset01_confirmed5"
    assert payload["candidate_scheme_id"] == "nlc_v1_confirmed5_lgbm_depth3_seed42"
    assert payload["data_source_status"] == "resolved"
    assert [feature["feature_name"] for feature in payload["features"]] == EXPECTED_FEATURES
    assert all(feature["ready_for_data_loading"] is True for feature in payload["features"])


def test_confirmed5_data_source_audit_points_to_shared_snapshot_and_sample_panel() -> None:
    payload = load_json(AUDIT_PATH)
    train_source = payload["train_data_source"]
    validation_source = payload["validation_data_source"]

    assert train_source["sample_panel_file"].endswith("project_sample_panel.parquet")
    assert validation_source["sample_panel_file"].endswith("project_sample_panel.parquet")
    assert train_source["source_db_file"].endswith(
        "warehouse_20260429_trainval_20211231/duckdb/warehouse.duckdb"
    )
    assert validation_source["source_view"] == "serving.vw_bars_daily"
    assert train_source["split_mask_fields"] == ["train_mask_v1", "eval_mask_v1"]

