from __future__ import annotations

from conftest import load_json


CONTRACT_PATH = "contracts/terminal_event_source_repair_plan.v1.json"


def test_contract_json_loads() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_version"] == "terminal_event_source_repair_plan_v1"


def test_two_repair_cases_defined() -> None:
    contract = load_json(CONTRACT_PATH)
    cases = contract["repair_cases"]
    assert "degraded_terminal_source_with_auditable_bars" in cases
    assert "declared_last_tradable_date_suspended" in cases
    assert len(cases) == 2


def test_both_repair_cases_still_hard_blocker_true() -> None:
    contract = load_json(CONTRACT_PATH)
    for case_key, case in contract["repair_cases"].items():
        assert case["still_hard_blocker"] is True, (
            f"{case_key} still_hard_blocker must be true"
        )


def test_portfolio_repair_allowed_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["portfolio_repair_allowed"] is False


def test_zero_recovery_allowed_in_repair_plan_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["zero_recovery_allowed_in_repair_plan"] is False


def test_silent_zero_recovery_allowed_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["silent_zero_recovery_allowed"] is False


def test_planned_exit_date_substitution_allowed_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["planned_exit_date_substitution_allowed"] is False


def test_build_project_panels_price_invention_allowed_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["build_project_panels_price_invention_allowed"] is False


def test_trainer_layer_terminal_event_handling_allowed_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["trainer_or_model_scores_layer_terminal_event_handling_allowed"] is False


def test_must_record_declared_vs_actual_last_tradable_date_difference() -> None:
    contract = load_json(CONTRACT_PATH)
    case = contract["repair_cases"]["declared_last_tradable_date_suspended"]
    reqs = case["repair_requirements"]
    assert reqs["must_record_declared_vs_actual_last_tradable_date_difference"] is True
    diff_fields = reqs["declared_vs_actual_diff_required_fields"]
    assert "declared_last_tradable_date" in diff_fields
    assert "actual_last_tradable_date" in diff_fields
    assert "date_diff_trading_days" in diff_fields
    assert "reason_for_diff" in diff_fields


def test_degraded_source_case_must_retain_degraded_flag() -> None:
    contract = load_json(CONTRACT_PATH)
    case = contract["repair_cases"]["degraded_terminal_source_with_auditable_bars"]
    reqs = case["repair_requirements"]
    assert reqs["must_retain_terminal_event_source_degraded_flag"] is True
    assert "terminal_event_source_degraded_flag" in case["required_flags"]


def test_suspended_date_case_must_set_approximation_or_repair_flag() -> None:
    contract = load_json(CONTRACT_PATH)
    case = contract["repair_cases"]["declared_last_tradable_date_suspended"]
    reqs = case["repair_requirements"]
    assert reqs["must_set_terminal_exit_approximation_or_source_repair_flag"] is True
    assert "terminal_exit_approximation_flag" in case["required_flags"]
    assert "source_repair_flag" in case["required_flags"]


def test_both_repair_cases_have_required_flags() -> None:
    contract = load_json(CONTRACT_PATH)
    for case in contract["repair_cases"].values():
        assert "required_flags" in case
        assert isinstance(case["required_flags"], list)
        assert len(case["required_flags"]) > 0


def test_both_repair_cases_have_prohibited_actions() -> None:
    contract = load_json(CONTRACT_PATH)
    for case_key, case in contract["repair_cases"].items():
        assert "prohibited_actions" in case, f"{case_key} missing prohibited_actions"
        assert isinstance(case["prohibited_actions"], list)
        assert len(case["prohibited_actions"]) > 0


def test_implementation_order_has_four_steps() -> None:
    contract = load_json(CONTRACT_PATH)
    steps = contract["recommended_implementation_order"]
    assert len(steps) == 4
    for i, step in enumerate(steps):
        assert step["step"] == i + 1


def test_references_point_to_related_contracts() -> None:
    contract = load_json(CONTRACT_PATH)
    refs = contract["references"]
    assert refs["terminal_exit_policy"] == "contracts/terminal_exit_policy.v1.json"
    assert refs["execution_exit_blocker_resolution"] == "contracts/execution_exit_blocker_resolution.v1.json"
    assert refs["run_input_contract"] == "contracts/run_input_contract.current.json"


def test_both_repair_cases_have_entry_to_terminal_priced_condition() -> None:
    contract = load_json(CONTRACT_PATH)
    for case_key, case in contract["repair_cases"].items():
        reqs = case["repair_requirements"]
        assert "entry_to_terminal_priced_last_tradable_close" in reqs, (
            f"{case_key} missing entry_to_terminal_priced_last_tradable_close"
        )


def test_both_repair_cases_have_row_count() -> None:
    contract = load_json(CONTRACT_PATH)
    cases = contract["repair_cases"]
    assert cases["degraded_terminal_source_with_auditable_bars"]["row_count"] == 4
    assert cases["declared_last_tradable_date_suspended"]["row_count"] == 6


def test_suspended_date_case_requires_actual_date_has_close_adj_factor_volume() -> None:
    contract = load_json(CONTRACT_PATH)
    case = contract["repair_cases"]["declared_last_tradable_date_suspended"]
    reqs = case["repair_requirements"]
    assert reqs["actual_last_tradable_date_must_have_close_adj_factor_volume"] is True
