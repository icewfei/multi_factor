#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_PATH = ROOT / "artifacts" / "research_registry" / "candidate_scheme_registry.jsonl"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"


KEEPER_SPECS = {
    "price_volume_single_signal_alpha158_cord30_v1": {
        "keeper_tier": "high-quality reserve atomic keeper(高质量储备原子信号)",
        "keeper_source_doc": str(
            RESEARCH_REGISTRY_DIR / "alpha158_cord30_turnover_control_seed_closeout_and_pause_decision_20260430.md"
        ),
        "keeper_decision_reason": "Strict confirmatory winner is still none, but CORD30 remains the highest-quality Alpha158 reserve card after shortlist pass, strict recheck rejection on turnover, and turnover-control seed closeout.",
    },
    "price_volume_single_signal_alpha158_corr30_v1": {
        "keeper_tier": "reserve atomic keeper(储备原子信号)",
        "keeper_source_doc": str(
            RESEARCH_REGISTRY_DIR / "alpha158_confirmatory_line_phase_closeout_and_next_round_direction_20260430.md"
        ),
        "keeper_decision_reason": "CORR30 passed shortlist-level confirmatory screening but failed strict recheck on invested-weight floor, so it is frozen as a reserve atomic keeper rather than an active confirmatory winner.",
    },
    "price_volume_single_signal_alpha158_vsumd60_v1": {
        "keeper_tier": "reserve atomic keeper(储备原子信号)",
        "keeper_source_doc": str(
            RESEARCH_REGISTRY_DIR / "vsumd60_walk_forward_2022_2025_regime_diagnosis_20260430.md"
        ),
        "keeper_decision_reason": "VSUMD60 passed confirmatory rounds 1-2 but walk-forward regime diagnosis showed it should be retained only as a reserve atomic keeper rather than a standalone mainline.",
    },
}


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> None:
    rows = load_rows(REGISTRY_PATH)
    latest_by_candidate: dict[str, dict] = {}
    for row in rows:
        cid = row.get("candidate_scheme_id")
        if cid:
            latest_by_candidate[cid] = row

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    appended = 0
    output_lines = [json.dumps(row, ensure_ascii=False) for row in rows]

    for candidate_id, spec in KEEPER_SPECS.items():
        latest = latest_by_candidate.get(candidate_id)
        if latest is None:
            raise RuntimeError(f"Missing candidate in registry: {candidate_id}")

        if (
            latest.get("keeper_tier") == spec["keeper_tier"]
            and latest.get("keeper_source_doc") == spec["keeper_source_doc"]
        ):
            continue

        new_row = deepcopy(latest)
        new_row["status_updated_at"] = timestamp
        new_row["keeper_tier"] = spec["keeper_tier"]
        new_row["keeper_source_doc"] = spec["keeper_source_doc"]
        new_row["keeper_tier_updated_at"] = timestamp
        new_row["keep_in_reserve_pool"] = True
        new_row["active_confirmatory_winner"] = False
        new_row["strict_confirmatory_winner"] = False
        new_row["keeper_decision_reason"] = spec["keeper_decision_reason"]
        output_lines.append(json.dumps(new_row, ensure_ascii=False))
        appended += 1

    REGISTRY_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"Appended keeper tier rows: {appended}")


if __name__ == "__main__":
    main()
