#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"

BASE_JSON = REGISTRY_DIR / "formal_factor_cards_20260429.json"
ALPHA_MD = REGISTRY_DIR / "formal_factor_cards_20260430.md"
OUTPUT_JSON = REGISTRY_DIR / "formal_factor_cards_20260430.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_bullets(block: str) -> list[str]:
    items: list[str] = []
    current: str | None = None
    for raw_line in block.strip().splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("- "):
            if current is not None:
                items.append(current.strip())
            current = line[2:].strip()
        else:
            if current is None:
                current = line.strip()
            else:
                current += " " + line.strip()
    if current is not None:
        items.append(current.strip())
    return items


def parse_number(text: str) -> float:
    return float(text.replace("%", ""))


def parse_alpha_md_cards(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    marker = "# Detailed Factor Cards — Alpha158 正向信号（29张）"
    start = text.index(marker)
    body = text[start + len(marker):].strip()
    raw_sections = [s.strip() for s in body.split("\n---\n") if s.strip()]

    cards: list[dict] = []
    for section in raw_sections:
        if not section.startswith("## "):
            continue
        lines = section.splitlines()
        candidate_scheme_id = lines[0].replace("## ", "").strip()

        family = re.search(r"\*\*Family:\*\*\s*(.+)", section).group(1).strip()
        field_name = re.search(r"\*\*Field:\*\*\s*`([^`]+)`", section).group(1).strip()
        ranking_direction = re.search(r"\*\*Ranking direction:\*\*\s*(.+)", section).group(1).strip()
        formula = re.search(r"### Formula\n\n```[\r\n]+(.*?)```", section, re.S).group(1).strip()

        econ_block = re.search(
            r"### Economic Explanation\n\n(.*?)\n\n### PIT Rule",
            section,
            re.S,
        ).group(1)
        economic_explanation = parse_bullets(econ_block)

        pit_rule = re.search(
            r"### PIT Rule\n\n(.*?)\n\n### Missing / Non-Finite Handling",
            section,
            re.S,
        ).group(1).strip()
        missing_handling = re.search(
            r"### Missing / Non-Finite Handling\n\n(.*?)\n\n### Expected Failure Modes",
            section,
            re.S,
        ).group(1).strip()
        failure_block = re.search(
            r"### Expected Failure Modes\n\n(.*?)\n\n### Diagnostic Summary",
            section,
            re.S,
        ).group(1)
        expected_failure_mode = parse_bullets(failure_block)

        diagnostic_block = re.search(
            r"### Diagnostic Summary\n\n(.*?)(?:\n\n>|\Z)",
            section,
            re.S,
        ).group(1)

        def extract_metric(label: str) -> str:
            match = re.search(rf"- {re.escape(label)}:\s*\*\*(.*?)\*\*", diagnostic_block)
            if not match:
                raise ValueError(f"Missing metric {label} in {candidate_scheme_id}")
            return match.group(1).strip()

        diagnostic_summary = {
            "full_sample_corr_ic": float(extract_metric("Full-sample correlation IC")),
            "avg_daily_ic": float(extract_metric("Average daily IC")),
            "positive_daily_ic_share": parse_number(extract_metric("Positive daily IC share")) / 100.0,
            "coverage_scored_with_label": int(float(extract_metric("Scored with label"))),
            "null_score_share": parse_number(extract_metric("Null score share")) / 100.0,
            "decile_monotonic_ok": extract_metric("Decile monotonic") == "Yes",
            "top10_avg_label": float(extract_metric("Top10 average label")),
            "top10_minus_rank11_20": float(extract_metric("Top10 minus 11-20")),
            "top10_minus_bottom10": float(extract_metric("Top10 minus Bottom10")),
        }

        memo_match = re.search(r"\n\n>\s*(.*?)\s*$", section, re.S)
        memo = memo_match.group(1).strip() if memo_match else None

        card = {
            "candidate_scheme_id": candidate_scheme_id,
            "family": family,
            "field_name": field_name,
            "ranking_direction": ranking_direction,
            "formula": formula,
            "economic_explanation": economic_explanation,
            "pit_rule": pit_rule,
            "missing_handling": missing_handling,
            "expected_failure_mode": expected_failure_mode,
            "diagnostic_summary": diagnostic_summary,
        }
        if memo:
            card["memo"] = memo
        cards.append(card)
    return cards


def main() -> None:
    base = load_json(BASE_JSON)
    base_cards = {row["candidate_scheme_id"]: row for row in base["cards"]}
    alpha_cards = {row["candidate_scheme_id"]: row for row in parse_alpha_md_cards(ALPHA_MD)}
    merged = {**base_cards, **alpha_cards}
    cards = sorted(merged.values(), key=lambda row: row["candidate_scheme_id"])

    payload = {
        "as_of_date": datetime.now().astimezone().strftime("%Y%m%d"),
        "total_cards": len(cards),
        "base_source_json": str(BASE_JSON),
        "supplement_source_markdown": str(ALPHA_MD),
        "cards": cards,
    }
    write_json(OUTPUT_JSON, payload)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Total cards: {len(cards)}")


if __name__ == "__main__":
    main()
