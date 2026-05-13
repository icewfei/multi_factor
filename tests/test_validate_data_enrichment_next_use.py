from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import load_module


MODULE_PATH = "scripts/validate_data_enrichment_next_use.py"
POLICY_PATH = Path("configs/data_field_enrichment/enrichment_next_use_policy_v1.json")
POLICY_SCHEMA_PATH = Path("schemas/data_field_enrichment_next_use_policy.schema.json")


def build_request(
    *,
    requested_fields: list[str],
    intended_use: str = "diagnostic",
    consumer_name: str = "unit_test_consumer",
    run_scope: str = "trainval_only",
    declared_no_frozen_test_access: bool = True,
    declared_conditional_pass: bool = True,
    requested_layer_status: str | None = "conditional_pass",
    allow_silent_fallback: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "requested_fields": requested_fields,
        "intended_use": intended_use,
        "consumer_name": consumer_name,
        "run_scope": run_scope,
        "declared_no_frozen_test_access": declared_no_frozen_test_access,
        "declared_conditional_pass": declared_conditional_pass,
        "allow_silent_fallback": allow_silent_fallback,
    }
    if requested_layer_status is not None:
        payload["requested_layer_status"] = requested_layer_status
    return payload


def load_validator():
    return load_module(MODULE_PATH, "validate_data_enrichment_next_use_module")


def test_allowed_diagnostic_fields_pass() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(
            requested_fields=["instrument", "signal_date", "entry_buyable", "listing_age_days"],
            intended_use="diagnostic",
            consumer_name="diagnostic_smoke",
        ),
    )

    assert audit["status"] == "pass"
    assert audit["blocked_fields_requested"] == []
    assert audit["unknown_fields_requested"] == []
    assert audit["allowed_fields_used"] == ["instrument", "signal_date", "entry_buyable", "listing_age_days"]
    assert audit["conditional_pass"] is True
    assert audit["no_frozen_test_access"] is True


def test_blocked_listing_age_trading_days_is_fail_fast() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(requested_fields=["instrument", "listing_age_trading_days"]),
    )

    assert audit["status"] == "blocked"
    assert audit["blocked_fields_requested"] == ["listing_age_trading_days"]
    assert "blocked_fields_requested: listing_age_trading_days" in audit["fail_fast_reasons"]


def test_blocked_newly_listed_flag_is_fail_fast() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(requested_fields=["instrument", "newly_listed_flag"]),
    )

    assert audit["status"] == "blocked"
    assert audit["blocked_fields_requested"] == ["newly_listed_flag"]
    assert "blocked_fields_requested: newly_listed_flag" in audit["fail_fast_reasons"]


def test_unknown_field_is_blocked() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(requested_fields=["instrument", "mystery_factor"]),
    )

    assert audit["status"] == "blocked"
    assert audit["unknown_fields_requested"] == ["mystery_factor"]
    assert "unknown_fields_requested: mystery_factor" in audit["fail_fast_reasons"]


def test_portfolio_intended_use_is_blocked() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(
            requested_fields=["instrument", "entry_buyable"],
            intended_use="portfolio",
        ),
    )

    assert audit["status"] == "blocked"
    assert "intended_use_not_allowed_by_policy: portfolio" in audit["fail_fast_reasons"]


def test_missing_conditional_disclosure_is_blocked() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(
            requested_fields=["instrument", "entry_buyable"],
            declared_conditional_pass=False,
        ),
    )

    assert audit["status"] == "blocked"
    assert "declared_conditional_pass must be true" in audit["fail_fast_reasons"]


def test_full_pass_claim_is_blocked() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(
            requested_fields=["instrument", "entry_buyable"],
            requested_layer_status="full_pass",
        ),
    )

    assert audit["status"] == "blocked"
    assert "requested_layer_status must not promote conditional_pass to full_pass" in audit["fail_fast_reasons"]


def test_no_frozen_test_access_false_is_blocked() -> None:
    module = load_validator()
    policy = module.load_next_use_policy(POLICY_PATH.resolve(), POLICY_SCHEMA_PATH.resolve())
    audit = module.validate_next_use_request(
        policy,
        build_request(
            requested_fields=["instrument", "entry_buyable"],
            declared_no_frozen_test_access=False,
        ),
    )

    assert audit["status"] == "blocked"
    assert "declared_no_frozen_test_access must be true" in audit["fail_fast_reasons"]


def test_audit_json_fields_complete_and_cli_writes_output(tmp_path: Path, repo_root: Path) -> None:
    request_path = tmp_path / "request.json"
    audit_path = tmp_path / "audit.json"
    request_path.write_text(
        json.dumps(
            build_request(
                requested_fields=["instrument", "signal_date", "entry_buyable"],
                intended_use="diagnostic",
                consumer_name="cli_smoke",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str((repo_root / MODULE_PATH).resolve()),
            "--request-json",
            str(request_path),
            "--output-json",
            str(audit_path),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "status=pass" in result.stdout
    assert audit_path.exists()

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert {
        "status",
        "allowed_fields_used",
        "blocked_fields_requested",
        "unknown_fields_requested",
        "required_disclosure",
        "fail_fast_reasons",
        "policy_version",
        "no_frozen_test_access",
        "conditional_pass",
    } <= set(audit.keys())
    assert audit["status"] == "pass"
