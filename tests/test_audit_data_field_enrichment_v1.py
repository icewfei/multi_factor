from __future__ import annotations

import duckdb

from conftest import load_module
from test_build_data_field_enrichment_v1 import FIELD_CONTRACT_PATH, build_snapshot_fixture


BUILD_MODULE_PATH = "scripts/build_data_field_enrichment_v1.py"
AUDIT_MODULE_PATH = "scripts/audit_data_field_enrichment_v1.py"


def test_audit_reports_missing_source_and_blocked_field(tmp_path) -> None:
    build_module = load_module(BUILD_MODULE_PATH, "build_data_field_enrichment_v1_audit_missing")
    audit_module = load_module(AUDIT_MODULE_PATH, "audit_data_field_enrichment_v1_missing")
    _, run_input_contract = build_snapshot_fixture(
        tmp_path,
        is_st=True,
        include_st_interval=False,
    )
    artifact_dir = tmp_path / "artifact_missing"

    build_module.build_data_field_enrichment_v1(
        field_contract_path=FIELD_CONTRACT_PATH.resolve(),
        run_input_contract_path=run_input_contract,
        output_dir=artifact_dir,
    )
    audit_result = audit_module.audit_data_field_enrichment_v1(
        field_contract_path=FIELD_CONTRACT_PATH.resolve(),
        artifact_dir=artifact_dir,
    )

    report = audit_result["report"]
    assert report["final_status"] == "conditional_pass"
    assert "st_effective_start" in report["missing_source_fields"]
    assert "st_effective_start" in report["blocked_fields"]
    assert report["no_frozen_test_access"] is True
    assert report["d0_visible_all_true"] is True


def test_audit_blocks_forbidden_future_field(tmp_path) -> None:
    build_module = load_module(BUILD_MODULE_PATH, "build_data_field_enrichment_v1_audit_forbidden")
    audit_module = load_module(AUDIT_MODULE_PATH, "audit_data_field_enrichment_v1_forbidden")
    _, run_input_contract = build_snapshot_fixture(
        tmp_path,
        is_st=True,
        include_st_interval=True,
    )
    artifact_dir = tmp_path / "artifact_forbidden"

    build_result = build_module.build_data_field_enrichment_v1(
        field_contract_path=FIELD_CONTRACT_PATH.resolve(),
        run_input_contract_path=run_input_contract,
        output_dir=artifact_dir,
    )

    parquet_path = build_result["output_parquet_path"]
    rewritten_path = artifact_dir / "rewritten.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT *, TRUE AS entry_filled_D1
                FROM read_parquet('{parquet_path.as_posix()}')
            ) TO '{rewritten_path.as_posix()}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    rewritten_path.replace(parquet_path)

    audit_result = audit_module.audit_data_field_enrichment_v1(
        field_contract_path=FIELD_CONTRACT_PATH.resolve(),
        artifact_dir=artifact_dir,
    )
    report = audit_result["report"]
    assert report["final_status"] == "blocked"
    assert "entry_filled_D1" in report["forbidden_output_columns"]
