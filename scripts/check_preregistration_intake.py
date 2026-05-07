#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Validate a research-round preregistration against the future signal naming and
intake governance rules.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
DEFAULT_RULES_PATH = REGISTRY_DIR / "future_signal_naming_and_intake_rules_20260425.json"
RESEARCH_ROUNDS_DIR = REGISTRY_DIR / "research_rounds"

VALID_RELATIONSHIP_TYPES = {
    "new_mechanism",
    "horizon_variant",
    "direction_variant",
    "naming_alias",
    "composite_variant",
}


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate preregistration intake rules.")
    parser.add_argument("--prereg-path", default=None, help="Path to preregistration.json")
    parser.add_argument("--research-round-id", default=None, help="Round id used to resolve preregistration path")
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES_PATH), help="Path to intake rules JSON")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_canonical_precedence(rules: dict) -> dict[str, str]:
    precedence: dict[str, str] = {
        row["retired_alias"]: row["canonical_field"]
        for row in rules.get("canonical_name_precedence", [])
        if isinstance(row, dict) and row.get("retired_alias") and row.get("canonical_field")
    }
    alias_map_ref = rules.get("canonical_alias_map_ref")
    if alias_map_ref:
        alias_payload = load_json(Path(alias_map_ref))
        for row in alias_payload.get("canonical_alias_map", []):
            if not isinstance(row, dict):
                continue
            canonical_field = row.get("canonical_field")
            aliases = row.get("aliases")
            if not canonical_field or not isinstance(aliases, list):
                continue
            for alias in aliases:
                if alias:
                    precedence[alias] = canonical_field
    return precedence


def resolve_prereg_path(args: argparse.Namespace) -> Path:
    if args.prereg_path:
        return Path(args.prereg_path)
    if args.research_round_id:
        return RESEARCH_ROUNDS_DIR / args.research_round_id / "preregistration.json"
    raise ValueError("Either --prereg-path or --research-round-id must be provided.")


def main() -> None:
    args = parse_args()
    prereg_path = resolve_prereg_path(args)
    rules_path = Path(args.rules_path)
    prereg = load_json(prereg_path)
    rules = load_json(rules_path)

    errors: list[str] = []
    warnings: list[str] = []

    if prereg.get("changed_dimension") != "atomic_signal_choice":
        warnings.append("This checker is primarily intended for atomic single-signal discovery rounds.")

    discovery_contract = prereg.get("discovery_contract")
    if not isinstance(discovery_contract, dict) or discovery_contract.get("mode") != "single_signal_discovery":
        errors.append("discovery_contract.mode must be 'single_signal_discovery'.")
    signal_pool = discovery_contract.get("signal_pool") if isinstance(discovery_contract, dict) else None
    if not isinstance(signal_pool, list) or not signal_pool:
        errors.append("discovery_contract.signal_pool must be a non-empty list.")
        signal_pool = []

    planned_ids = prereg.get("planned_candidate_scheme_ids")
    if not isinstance(planned_ids, list) or not planned_ids:
        errors.append("planned_candidate_scheme_ids must be a non-empty list.")
        planned_ids = []

    pool_ids = [item.get("candidate_scheme_id") for item in signal_pool if isinstance(item, dict)]
    if sorted(planned_ids) != sorted(pool_ids):
        errors.append("planned_candidate_scheme_ids must match candidate_scheme_id values in signal_pool.")

    source_policy_rules = rules.get("source_whitelist_policy", {})
    whitelist_enforced = False
    enforcement_start = parse_iso_datetime(source_policy_rules.get("enforcement_start_datetime"))
    prereg_registered_at = parse_iso_datetime(prereg.get("registered_at"))
    if enforcement_start is None:
        whitelist_enforced = bool(source_policy_rules)
    elif prereg_registered_at is not None:
        whitelist_enforced = prereg_registered_at >= enforcement_start

    required_round_mode = source_policy_rules.get("required_round_source_mode", "alpha158_paper_whitelist_only")
    allowed_source_categories = set(source_policy_rules.get("allowed_source_categories", []))
    required_source_fields = source_policy_rules.get(
        "required_source_provenance_fields",
        ["source_category", "source_id", "source_title", "source_locator", "mechanism_mapping", "independent_implementation_note"],
    )

    if whitelist_enforced:
        round_source_policy = prereg.get("source_policy")
        if not isinstance(round_source_policy, dict):
            errors.append("source_policy is required after whitelist enforcement starts.")
        else:
            mode = round_source_policy.get("mode")
            if mode != required_round_mode:
                errors.append(
                    f"source_policy.mode must be '{required_round_mode}' after whitelist enforcement starts."
                )
            whitelist_ref = round_source_policy.get("whitelist_ref")
            if not whitelist_ref:
                errors.append("source_policy.whitelist_ref is required after whitelist enforcement starts.")
            else:
                whitelist_path = Path(whitelist_ref)
                if not whitelist_path.exists():
                    errors.append(f"source_policy.whitelist_ref does not exist: {whitelist_ref}")

    canonical_precedence = build_canonical_precedence(rules)

    for idx, item in enumerate(signal_pool, start=1):
        if not isinstance(item, dict):
            errors.append(f"signal_pool[{idx}] must be an object.")
            continue
        cid = item.get("candidate_scheme_id")
        field = item.get("field")
        direction = item.get("ranking_direction")
        interpretation = item.get("interpretation")
        dedup_note = item.get("dedup_note")

        if not cid:
            errors.append(f"signal_pool[{idx}] is missing candidate_scheme_id.")
        if not field:
            errors.append(f"signal_pool[{idx}] is missing field.")
        if direction not in {"ASC", "DESC"}:
            errors.append(f"signal_pool[{idx}] ranking_direction must be ASC or DESC.")
        if not interpretation:
            errors.append(f"signal_pool[{idx}] is missing interpretation.")

        if not isinstance(dedup_note, dict):
            errors.append(f"signal_pool[{idx}] is missing dedup_note.")
            continue
        nearest = dedup_note.get("nearest_canonical_signal")
        relationship = dedup_note.get("relationship_type")
        reason = dedup_note.get("independent_budget_reason")
        override_reason = dedup_note.get("override_reason", "")

        if not nearest:
            errors.append(f"signal_pool[{idx}] dedup_note.nearest_canonical_signal is required.")
        if relationship not in VALID_RELATIONSHIP_TYPES:
            errors.append(
                f"signal_pool[{idx}] dedup_note.relationship_type must be one of {sorted(VALID_RELATIONSHIP_TYPES)}."
            )
        if not reason:
            errors.append(f"signal_pool[{idx}] dedup_note.independent_budget_reason is required.")

        if relationship in {"horizon_variant", "direction_variant", "naming_alias", "composite_variant"} and not override_reason:
            errors.append(
                f"signal_pool[{idx}] dedup_note.override_reason is required for relationship_type={relationship}."
            )

        if field in canonical_precedence:
            errors.append(
                f"signal_pool[{idx}] field '{field}' is a retired alias; use canonical field '{canonical_precedence[field]}' instead."
            )

        if whitelist_enforced:
            source_provenance = item.get("source_provenance")
            if not isinstance(source_provenance, dict):
                errors.append(f"signal_pool[{idx}] source_provenance is required after whitelist enforcement starts.")
            else:
                for key in required_source_fields:
                    value = source_provenance.get(key)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(
                            f"signal_pool[{idx}] source_provenance.{key} is required after whitelist enforcement starts."
                        )
                category = source_provenance.get("source_category")
                if category and allowed_source_categories and category not in allowed_source_categories:
                    errors.append(
                        f"signal_pool[{idx}] source_provenance.source_category='{category}' is not in whitelist categories: {sorted(allowed_source_categories)}."
                    )

    report = {
        "prereg_path": prereg_path.as_posix(),
        "rules_path": rules_path.as_posix(),
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
