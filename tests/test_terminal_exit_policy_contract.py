from __future__ import annotations

from conftest import load_json


CONTRACT_PATH = "contracts/terminal_exit_policy.v1.json"


def test_contract_json_loads() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_version"] == "terminal_exit_policy_v1"


def test_hierarchy_order_is_cash_settlement_then_last_tradable_close_then_zero_recovery() -> None:
    contract = load_json(CONTRACT_PATH)
    order = contract["terminal_pricing_hierarchy"]["order"]
    assert order == ["cash_settlement", "last_tradable_close", "zero_recovery"]
    assert order[0] == "cash_settlement"
    assert order[1] == "last_tradable_close"
    assert order[2] == "zero_recovery"


def test_last_tradable_close_approval_policy_disables_zero_recovery_by_default() -> None:
    contract = load_json(CONTRACT_PATH)
    approval = contract["last_tradable_close_approval_policy"]

    assert approval["candidate_artifact"] == "repaired_terminal_event_candidate"
    assert approval["zero_recovery_default_enabled"] is False


def test_last_tradable_close_approval_policy_distinguishes_bridge_and_non_bridge_origin_cases() -> None:
    contract = load_json(CONTRACT_PATH)
    origin_cases = contract["last_tradable_close_approval_policy"]["origin_cases"]

    assert "no_terminal_pricing_source" in origin_cases
    assert "terminal_event_bridge_required" in origin_cases
    assert origin_cases["terminal_event_bridge_required"]["candidate_allowed_if_evidence_case_approved"] is True
    assert "terminal_event_bridge_required" in origin_cases["terminal_event_bridge_required"]["must_retain_markers"]


def test_last_tradable_close_approval_policy_distinguishes_two_evidence_cases() -> None:
    contract = load_json(CONTRACT_PATH)
    evidence_cases = contract["last_tradable_close_approval_policy"]["evidence_cases"]

    assert "degraded_terminal_source_with_auditable_bars" in evidence_cases
    assert "declared_last_tradable_date_suspended" in evidence_cases
    assert evidence_cases["degraded_terminal_source_with_auditable_bars"]["candidate_allowed"] is True
    assert evidence_cases["declared_last_tradable_date_suspended"]["candidate_allowed"] is True


def test_suspended_evidence_case_requires_approximation_and_source_repair_flags() -> None:
    contract = load_json(CONTRACT_PATH)
    suspended = contract["last_tradable_close_approval_policy"]["evidence_cases"][
        "declared_last_tradable_date_suspended"
    ]

    assert "terminal_exit_approximation_flag" in suspended["required_flags"]
    assert "source_repair_flag" in suspended["required_flags"]


def test_degraded_evidence_case_requires_degraded_and_source_repair_flags() -> None:
    contract = load_json(CONTRACT_PATH)
    degraded = contract["last_tradable_close_approval_policy"]["evidence_cases"][
        "degraded_terminal_source_with_auditable_bars"
    ]

    assert "terminal_event_source_degraded_flag" in degraded["required_flags"]
    assert "source_repair_flag" in degraded["required_flags"]


def test_hard_blocker_states_are_terminal_event_unpriced_exit_unresolved_calendar_insufficient() -> None:
    contract = load_json(CONTRACT_PATH)
    blockers = contract["hard_blocker_rules"]

    assert "terminal_event_unpriced" in blockers
    assert "exit_unresolved" in blockers
    assert "calendar_insufficient" in blockers

    for state in ("terminal_event_unpriced", "exit_unresolved", "calendar_insufficient"):
        assert blockers[state]["hard_blocker"] is True
        assert blockers[state]["portfolio_allowed"] is False


def test_zero_recovery_requires_terminal_exit_conservative_flag_true() -> None:
    contract = load_json(CONTRACT_PATH)
    layers = contract["terminal_pricing_hierarchy"]["layers"]

    zero = layers["zero_recovery"]
    assert zero["terminal_exit_conservative_flag"] is True
    assert "terminal_exit_conservative_flag" in zero["requires"]


def test_portfolio_can_price_terminal_exit_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    rules = contract["portfolio_consumption_rules"]

    assert rules["portfolio_can_price_terminal_exit"] is False
    assert rules["portfolio_can_filter_unresolved_and_continue"] is False
    assert rules["portfolio_behavior_on_unresolved"] == "fail_fast"


def test_portfolio_required_fields_are_actual_exit_date_actual_sell_price_execution_delayed_realized_return() -> None:
    contract = load_json(CONTRACT_PATH)
    required = contract["portfolio_consumption_rules"]["required_fields_for_portfolio"]

    assert "actual_exit_date" in required
    assert "actual_sell_price" in required
    assert "execution_delayed_realized_return" in required
    assert len(required) == 3


def test_all_six_states_are_defined() -> None:
    contract = load_json(CONTRACT_PATH)
    states = contract["state_definitions"]

    expected = {
        "terminal_priced_cash_settlement",
        "terminal_priced_last_tradable_close",
        "terminal_priced_zero_recovery",
        "terminal_event_unpriced",
        "exit_unresolved",
        "calendar_insufficient",
    }
    assert set(states.keys()) == expected


def test_implementation_boundary_pricing_owner_is_execution_path_upstream() -> None:
    contract = load_json(CONTRACT_PATH)
    boundary = contract["implementation_boundary"]

    assert "execution path" in boundary["terminal_pricing_owner"] or "execution" in boundary["terminal_pricing_owner"]
    assert "passthrough" in boundary["build_project_panels_role"] or "standardize" in boundary["build_project_panels_role"]
    assert boundary["terminal_pricing_owner"] is not None
