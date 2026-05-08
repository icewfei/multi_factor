from __future__ import annotations

from conftest import load_json


CONTRACT_PATH = "contracts/execution_exit_blocker_resolution.v1.json"


def test_contract_json_loads() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_version"] == "execution_exit_blocker_resolution_v1"


def test_three_blocker_types_exist() -> None:
    contract = load_json(CONTRACT_PATH)
    blockers = contract["blocker_types"]
    assert "terminal_event_unpriced" in blockers
    assert "exit_unresolved" in blockers
    assert "calendar_insufficient" in blockers
    assert len(blockers) == 3


def test_all_blocker_types_default_hard_blocker_true() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker_key, blocker in contract["blocker_types"].items():
        assert blocker["default_hard_blocker"] is True, f"{blocker_key} default_hard_blocker must be true"


def test_all_blocker_types_have_resolution_path() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker_key, blocker in contract["blocker_types"].items():
        assert "resolution_path" in blocker
        rp = blocker["resolution_path"]
        assert "primary" in rp
        assert "required_upstream_fields" in rp
        assert "auto_unblock_allowed" in rp
        assert "resolution_criteria" in rp
        assert "fallback_if_unresolvable" in rp


def test_no_blocker_allows_auto_unblock() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker_key, blocker in contract["blocker_types"].items():
        assert blocker["resolution_path"]["auto_unblock_allowed"] is False, (
            f"{blocker_key} auto_unblock_allowed must be false"
        )


def test_no_blocker_allows_portfolio_resolution() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker_key, blocker in contract["blocker_types"].items():
        assert blocker["portfolio_resolution_allowed"] is False, (
            f"{blocker_key} portfolio_resolution_allowed must be false"
        )


def test_global_prohibition_planned_exit_date_substitution_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["planned_exit_date_substitution_allowed"] is False


def test_global_prohibition_filter_unresolved_and_continue_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["filter_unresolved_and_continue"] is False


def test_global_prohibition_silent_zero_recovery_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["silent_zero_recovery_allowed"] is False


def test_global_prohibition_portfolio_workaround_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["portfolio_workaround"] is False


def test_global_prohibition_trainer_layer_handling_is_false() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["global_prohibitions"]["trainer_or_model_scores_layer_execution_blocker_handling"] is False


def test_required_portfolio_fields_are_actual_exit_date_sell_price_realized_return() -> None:
    contract = load_json(CONTRACT_PATH)
    required = contract["required_portfolio_fields_before_unblock"]
    assert "actual_exit_date" in required
    assert "actual_sell_price" in required
    assert "execution_delayed_realized_return" in required
    assert len(required) == 3


def test_terminal_event_unpriced_resolution_path_is_terminal_pricing_policy() -> None:
    contract = load_json(CONTRACT_PATH)
    rp = contract["blocker_types"]["terminal_event_unpriced"]["resolution_path"]
    assert rp["primary"] == "terminal_pricing_policy"
    assert "terminal_event_type" in rp["required_upstream_fields"]
    assert "terminal_event_date" in rp["required_upstream_fields"]
    assert "terminal_exit_pricing_method" in rp["required_upstream_fields"]
    pricing_fields = rp["required_pricing_fields_per_layer"]
    assert "cash_settlement" in pricing_fields
    assert "last_tradable_close" in pricing_fields
    assert "zero_recovery" in pricing_fields
    assert "cash_settlement_amount" in pricing_fields["cash_settlement"]


def test_exit_unresolved_resolution_path_is_execution_path_completion() -> None:
    contract = load_json(CONTRACT_PATH)
    rp = contract["blocker_types"]["exit_unresolved"]["resolution_path"]
    assert rp["primary"] == "execution_path_completion"
    assert "actual_exit_date" in rp["required_upstream_fields"]
    assert "actual_sell_price" in rp["required_upstream_fields"]
    assert "execution_delayed_realized_return" in rp["required_upstream_fields"]


def test_calendar_insufficient_resolution_path_is_source_repair() -> None:
    contract = load_json(CONTRACT_PATH)
    rp = contract["blocker_types"]["calendar_insufficient"]["resolution_path"]
    assert rp["primary"] == "calendar_or_tradability_source_repair"
    assert "trading_calendar_coverage" in rp["required_upstream_fields"]
    assert "tradability_source_coverage" in rp["required_upstream_fields"]


def test_implementation_order_has_four_steps() -> None:
    contract = load_json(CONTRACT_PATH)
    steps = contract["recommended_implementation_order"]
    assert len(steps) == 4
    assert steps[0]["step"] == 1
    assert steps[1]["step"] == 2
    assert steps[2]["step"] == 3
    assert steps[3]["step"] == 4


def test_references_point_to_policy_and_classification() -> None:
    contract = load_json(CONTRACT_PATH)
    refs = contract["references"]
    assert refs["terminal_exit_policy"] == "contracts/terminal_exit_policy.v1.json"
    assert "classification" in str(refs).lower() or "classification" in refs


def test_all_blockers_have_prohibited_workarounds() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker in contract["blocker_types"].values():
        assert "prohibited_workarounds" in blocker
        assert isinstance(blocker["prohibited_workarounds"], list)
        assert len(blocker["prohibited_workarounds"]) > 0


def test_each_blocker_fallback_keeps_hard_blocker() -> None:
    contract = load_json(CONTRACT_PATH)
    for blocker_key, blocker in contract["blocker_types"].items():
        fallback = blocker["resolution_path"]["fallback_if_unresolvable"]
        assert "hard_blocker=true" in fallback or "hard blocker" in fallback.lower()
