from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_module


MODULE_PATH = "scripts/data_enrichment_next_use_guardrail_adapter.py"


def load_adapter():
    return load_module(MODULE_PATH, "data_enrichment_next_use_guardrail_adapter_module")


def request_kwargs(**overrides):
    kwargs = {
        "requested_fields": ["is_st", "is_suspended", "entry_buyable", "limit_rule_version"],
        "intended_use": "diagnostic",
        "consumer_name": "adapter_unit_test",
        "run_scope": "fixture_only",
        "declared_no_frozen_test_access": True,
        "declared_conditional_pass": True,
        "requested_layer_status": "conditional_pass",
        "allow_silent_fallback": False,
    }
    kwargs.update(overrides)
    return kwargs


def assert_blocked(adapter, **overrides):
    with pytest.raises(adapter.DataEnrichmentNextUseGuardrailError) as exc_info:
        adapter.require_data_enrichment_next_use(**request_kwargs(**overrides))
    audit = exc_info.value.audit
    assert audit["status"] == "blocked"
    return audit


def test_allowed_diagnostic_fields_pass(tmp_path: Path) -> None:
    adapter = load_adapter()
    audit_path = tmp_path / "audit.json"

    audit = adapter.require_data_enrichment_next_use(
        **request_kwargs(audit_json=audit_path)
    )

    assert audit["status"] == "pass"
    assert audit["allowed_fields_used"] == ["is_st", "is_suspended", "entry_buyable", "limit_rule_version"]
    assert audit["blocked_fields_requested"] == []
    assert audit["unknown_fields_requested"] == []
    assert audit["no_frozen_test_access"] is True
    assert audit["conditional_pass"] is True
    assert json.loads(audit_path.read_text(encoding="utf-8"))["status"] == "pass"


def test_listing_age_trading_days_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, requested_fields=["listing_age_trading_days"])
    assert audit["blocked_fields_requested"] == ["listing_age_trading_days"]


def test_newly_listed_flag_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, requested_fields=["newly_listed_flag"])
    assert audit["blocked_fields_requested"] == ["newly_listed_flag"]


def test_unknown_field_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, requested_fields=["mystery_enrichment_field"])
    assert audit["unknown_fields_requested"] == ["mystery_enrichment_field"]


def test_portfolio_intended_use_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, intended_use="portfolio")
    assert "intended_use_not_allowed_by_policy: portfolio" in audit["fail_fast_reasons"]


def test_no_frozen_test_access_false_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, declared_no_frozen_test_access=False)
    assert "declared_no_frozen_test_access must be true" in audit["fail_fast_reasons"]


def test_conditional_pass_false_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, declared_conditional_pass=False)
    assert "declared_conditional_pass must be true" in audit["fail_fast_reasons"]


def test_allow_silent_fallback_true_raises_blocked() -> None:
    adapter = load_adapter()
    audit = assert_blocked(adapter, allow_silent_fallback=True)
    assert "allow_silent_fallback must be false" in audit["fail_fast_reasons"]


def test_audit_json_fields_complete(tmp_path: Path) -> None:
    adapter = load_adapter()
    audit_path = tmp_path / "next_use_audit.json"
    adapter.require_data_enrichment_next_use(**request_kwargs(audit_json=audit_path))
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
    } <= set(audit)
