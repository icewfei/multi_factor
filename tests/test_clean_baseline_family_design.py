from __future__ import annotations

from pathlib import Path

from conftest import load_json


DOC_PATH = Path("docs/clean_baseline_family_design.md")
MANIFEST_PATH = "configs/clean_baselines/clean_baseline_family_manifest.json"
REQUIRED_BASELINE_IDS = {
    "no_p98_reversal_baseline_v1",
    "clean_momentum_20d_baseline_v1",
    "clean_liquidity_adjusted_reversal_baseline_v1",
    "clean_equal_weight_random_eligible_baseline_v1",
}
REQUIRED_BASELINE_TERMS = (
    "no p98",
    "no label diagnostics",
    "no frozen test access",
    "D0 visible only",
)


def load_manifest() -> dict:
    return load_json(MANIFEST_PATH)


def flatten_baseline_payload(baseline: dict) -> str:
    parts: list[str] = []
    for value in baseline.values():
        if isinstance(value, dict):
            parts.extend(str(item) for item in value.values())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def test_design_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_design_doc_contains_family_boundaries_and_candidates() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for term in (
        "no p98",
        "no label diagnostics",
        "no trainval source-selection feedback",
        "D0 visible only",
        "no frozen test access",
    ):
        assert term in text

    for baseline_id in REQUIRED_BASELINE_IDS:
        assert baseline_id in text


def test_manifest_loads() -> None:
    payload = load_manifest()

    assert payload["family_id"] == "clean_baseline_family_v1"
    assert isinstance(payload["baselines"], list)
    assert payload["baselines"]


def test_each_baseline_id_is_unique_and_complete() -> None:
    baselines = load_manifest()["baselines"]
    baseline_ids = [baseline["baseline_id"] for baseline in baselines]

    assert len(baseline_ids) == len(set(baseline_ids))
    assert set(baseline_ids) == REQUIRED_BASELINE_IDS


def test_each_baseline_contains_required_clean_boundaries() -> None:
    baselines = load_manifest()["baselines"]

    for baseline in baselines:
        flattened = flatten_baseline_payload(baseline)
        for term in REQUIRED_BASELINE_TERMS:
            assert term in flattened, f"{baseline['baseline_id']} missing {term}"


def test_each_baseline_declares_required_fields() -> None:
    baselines = load_manifest()["baselines"]
    required_fields = {
        "baseline_id",
        "score_source",
        "allowed_inputs",
        "forbidden_inputs",
        "score_direction",
        "expected_artifacts",
        "fail_fast_conditions",
        "intended_role",
        "why_it_is_clean",
    }

    for baseline in baselines:
        assert required_fields.issubset(baseline.keys())
