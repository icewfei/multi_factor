from __future__ import annotations

from conftest import load_json


CONTRACT_PATH = "contracts/post_delist_terminal_event_bridge.v1.json"


def test_contract_json_loads() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_version"] == "post_delist_terminal_event_bridge_v1"


def test_bridge_moves_exit_unresolved_to_terminal_event_unpriced() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["bridge_source_state"] == "exit_unresolved"
    assert contract["bridge_target_state"] == "terminal_event_unpriced"
    assert contract["bridge_marker"] == "terminal_event_bridge_required"


def test_eligibility_rule_requires_post_delist_full_coverage_gap() -> None:
    contract = load_json(CONTRACT_PATH)
    rule = contract["eligibility_rule"]["all_of"]
    assert any("delist terminal_event exists" in item for item in rule)
    assert any("zero rows" in item and "vw_tradability_daily" in item for item in rule)
    assert any("zero rows" in item and "vw_bars_daily" in item for item in rule)


def test_post_bridge_invariants_keep_row_as_hard_blocker() -> None:
    contract = load_json(CONTRACT_PATH)
    invariants = contract["post_bridge_invariants"]
    assert invariants["hard_blocker"] is True
    assert invariants["portfolio_allowed"] is False
    assert invariants["actual_exit_date_must_remain_null"] is True
    assert invariants["actual_sell_price_must_remain_null"] is True
    assert invariants["pricing_not_applied"] is True


def test_prohibited_actions_disallow_pricing_or_portfolio_workaround() -> None:
    contract = load_json(CONTRACT_PATH)
    prohibited = contract["prohibited_actions"]
    assert "Backfill actual_exit_date" in prohibited
    assert "Backfill actual_sell_price" in prohibited
    assert "Apply terminal_priced_last_tradable_close" in prohibited
    assert "Apply zero_recovery" in prohibited
    assert "Resolve the blocker at portfolio layer" in prohibited
