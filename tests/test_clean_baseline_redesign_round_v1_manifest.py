from __future__ import annotations

from pathlib import Path

from conftest import load_json


MANIFEST_PATH = "configs/clean_baselines/redesign_round_v1/clean_baseline_redesign_manifest.json"
DESIGN_DOC_PATH = Path("docs/clean_baseline_redesign_round_v1_design.md")

EXPECTED_CANDIDATES = {
    "clean_reversal_5d_tradability_filtered_v1",
    "clean_reversal_5d_board_neutral_v1",
    "clean_reversal_5d_limit_aware_v1",
    "clean_reversal_5d_liquidity_quality_v1",
    "clean_reversal_5d_listing_age_calendar_v1",
    "clean_composite_reversal_tradability_v1",
}
BLOCKED_FIELDS = {"listing_age_trading_days", "newly_listed_flag"}


def test_redesign_manifest_contains_expected_candidates() -> None:
    manifest = load_json(MANIFEST_PATH)
    candidate_ids = {candidate["baseline_id"] for candidate in manifest["candidates"]}

    assert manifest["round_id"] == "clean_baseline_redesign_round_v1"
    assert candidate_ids == EXPECTED_CANDIDATES
    assert manifest["global_boundaries"]["no_p98"] is True
    assert manifest["global_boundaries"]["no_label_diagnostics_for_source_selection"] is True
    assert manifest["global_boundaries"]["no_frozen_test_access"] is True
    assert set(manifest["blocked_enrichment_fields"]) == BLOCKED_FIELDS


def test_redesign_manifest_candidate_governance_fields_complete() -> None:
    manifest = load_json(MANIFEST_PATH)
    required_keys = {
        "baseline_id",
        "score_formula",
        "allowed_fields",
        "forbidden_fields",
        "d0_visible",
        "no_p98",
        "no_label_diagnostics",
        "no_frozen_test",
        "fail_fast",
        "intended_diagnosis",
        "why_it_is_clean",
        "why_it_may_improve_topk_head_quality",
    }
    for candidate in manifest["candidates"]:
        assert required_keys <= set(candidate)
        assert candidate["d0_visible"] is True
        assert candidate["no_p98"] is True
        assert candidate["no_label_diagnostics"] is True
        assert candidate["no_frozen_test"] is True
        assert BLOCKED_FIELDS <= set(candidate["forbidden_fields"])
        assert not (BLOCKED_FIELDS & set(candidate["allowed_fields"]))
        assert "label_*" in candidate["forbidden_fields"]
        assert candidate["fail_fast"]


def test_design_doc_discloses_boundaries(repo_root: Path) -> None:
    text = (repo_root / DESIGN_DOC_PATH).read_text(encoding="utf-8")
    for phrase in [
        "No `p98`",
        "No frozen test access",
        "No portfolio run",
        "listing_age_trading_days",
        "newly_listed_flag",
        "not `listing_age_trading_days`",
        "conditional references",
    ]:
        assert phrase in text
