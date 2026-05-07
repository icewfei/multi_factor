#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Create a new single-signal discovery round skeleton from the canonical template.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
TEMPLATE_PATH = REGISTRY_DIR / "templates" / "single_signal_discovery_prereg_template_20260425.json"
ROUND_REGISTRY_PATH = REGISTRY_DIR / "research_round_registry.jsonl"
DEFAULT_SOURCE_MODE = "alpha158_paper_whitelist_only"
DEFAULT_SOURCE_WHITELIST_REF = (
    REGISTRY_DIR / "alpha158_paper_source_whitelist_20260428.json"
).as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a single-signal discovery round skeleton from the canonical prereg template."
    )
    parser.add_argument("--research-round-id", required=True, help="New research_round_id")
    parser.add_argument(
        "--baseline-reference-candidate-scheme-id",
        default="price_volume_v18_refresh_hysteresis",
        help="Frozen working reference candidate_scheme_id",
    )
    parser.add_argument(
        "--research-question",
        default="What new atomic signal should be tested under the frozen working reference contract?",
        help="Research question written into preregistration.json",
    )
    parser.add_argument(
        "--source-mode",
        default=DEFAULT_SOURCE_MODE,
        help="Round-level source policy mode for signal intake.",
    )
    parser.add_argument(
        "--source-whitelist-ref",
        default=DEFAULT_SOURCE_WHITELIST_REF,
        help="Path to the approved source whitelist reference JSON.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    round_dir = REGISTRY_DIR / "research_rounds" / args.research_round_id
    prereg_path = round_dir / "preregistration.json"
    if prereg_path.exists():
        raise FileExistsError(f"preregistration already exists: {prereg_path}")

    template = read_json(TEMPLATE_PATH)
    template["registered_at"] = now_iso()
    template["research_round_id"] = args.research_round_id
    template["baseline_reference_candidate_scheme_id"] = args.baseline_reference_candidate_scheme_id
    template["research_question"] = args.research_question
    template["planned_candidate_scheme_ids"] = []
    template["discovery_contract"]["signal_pool"] = []
    template["source_policy"] = {
        "mode": args.source_mode,
        "whitelist_ref": args.source_whitelist_ref,
        "notes": "Discovery intake is restricted to whitelist-approved literature/classic-definition sources.",
    }

    round_dir.mkdir(parents=True, exist_ok=False)
    write_json(prereg_path, template)

    rows = read_jsonl(ROUND_REGISTRY_PATH)
    rows.append(
        {
            "registered_at": template["registered_at"],
            "research_round_id": args.research_round_id,
            "status": "registered_not_started",
            "research_tier": template["research_tier"],
            "run_type": template["run_type"],
            "changed_dimension": template["changed_dimension"],
            "change_control_rule": template["change_control_rule"],
            "candidate_scheme_ids": [],
            "planned_candidate_scheme_ids": [],
            "baseline_reference_candidate_scheme_id": args.baseline_reference_candidate_scheme_id,
            "notes": "Created from canonical single-signal discovery prereg template; fill signal_pool/planned_candidate_scheme_ids and complete source_provenance for every candidate before execution.",
        }
    )
    write_jsonl(ROUND_REGISTRY_PATH, rows)

    print(
        json.dumps(
            {
                "status": "round_skeleton_created",
                "research_round_id": args.research_round_id,
                "preregistration_path": prereg_path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
