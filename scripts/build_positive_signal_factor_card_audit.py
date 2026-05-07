#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
RESEARCH_ROUNDS_DIR = REGISTRY_DIR / "research_rounds"

CANDIDATE_REGISTRY = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
FORMAL_MD_20260430 = REGISTRY_DIR / "formal_factor_cards_20260430.md"
FORMAL_JSON_20260430 = REGISTRY_DIR / "formal_factor_cards_20260430.json"
CURRENT_FACTOR_CARD_REGISTRY = REGISTRY_DIR / "factor_card_registry_20260430.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl_latest_by_candidate(path: Path) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        row = json.loads(line)
        candidate_id = row.get("candidate_scheme_id")
        if candidate_id:
            latest[candidate_id] = row
    return latest


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build_current_keeper_status_map() -> dict[str, dict[str, str]]:
    status_map: dict[str, dict[str, str]] = {}
    explicit_pattern = re.compile(
        r"`(?P<candidate>price_volume_single_signal_[^`]+_v1)\s*=\s*(?P<status>[^`]+)`"
    )
    source_docs = [
        REGISTRY_DIR / "alpha158_confirmatory_line_phase_closeout_and_next_round_direction_20260430.md",
        REGISTRY_DIR / "alpha158_cord30_strict_recheck_closeout_and_next_decision_20260430.md",
        REGISTRY_DIR / "alpha158_cord30_turnover_control_seed_closeout_and_pause_decision_20260430.md",
        REGISTRY_DIR / "vsumd60_walk_forward_2022_2025_regime_diagnosis_20260430.md",
    ]
    for doc in source_docs:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for match in explicit_pattern.finditer(text):
            candidate_id = match.group("candidate")
            status_map[candidate_id] = {
                "current_keeper_tier": match.group("status").strip(),
                "status_source_doc": str(doc),
            }

        if "`vsumd60 = reserve atomic keeper(储备原子信号)`" in text:
            status_map["price_volume_single_signal_alpha158_vsumd60_v1"] = {
                "current_keeper_tier": "reserve atomic keeper(储备原子信号)",
                "status_source_doc": str(doc),
            }
        if "`corr30 = reserve atomic keeper(储备原子信号)`" in text:
            status_map["price_volume_single_signal_alpha158_corr30_v1"] = {
                "current_keeper_tier": "reserve atomic keeper(储备原子信号)",
                "status_source_doc": str(doc),
            }
    return status_map


def parse_positive_summary_from_formal_md(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    rows: dict[str, dict] = {}
    row_pattern = re.compile(
        r"^\|\s*\d+\s*\|\s*`(?P<candidate>[^`]+)`\s*\|\s*(?P<family>[^|]+?)\s*\|\s*"
        r"(?P<ic>-?\d+\.\d+)\s*\|\s*(?P<avg_ic>-?\d+\.\d+)\s*\|\s*(?P<top_bottom>-?\d+\.\d+)\s*\|$"
    )
    for line in text.splitlines():
        match = row_pattern.match(line.strip())
        if not match:
            continue
        rows[match.group("candidate")] = {
            "family_label": match.group("family").strip(),
            "full_sample_corr_ic": float(match.group("ic")),
            "avg_daily_ic": float(match.group("avg_ic")),
            "top10_minus_bottom10": float(match.group("top_bottom")),
        }
    return rows


def main() -> None:
    as_of_date = datetime.now().astimezone().strftime("%Y%m%d")
    latest_registry = load_jsonl_latest_by_candidate(CANDIDATE_REGISTRY)
    legacy_registry = load_json(CURRENT_FACTOR_CARD_REGISTRY)
    formal_json = load_json(FORMAL_JSON_20260430)
    formal_md_summary = parse_positive_summary_from_formal_md(FORMAL_MD_20260430)
    keeper_status_map = build_current_keeper_status_map()

    positive_candidates = sorted(formal_md_summary.keys())

    legacy_cards = {
        row["candidate_scheme_id"]: row
        for row in legacy_registry.get("factor_cards", [])
        if row.get("candidate_scheme_id")
    }
    legacy_positive_cards = {
        row["candidate_scheme_id"]
        for row in legacy_registry.get("factor_cards", [])
        if row.get("status") == "signal_edge_positive"
    }
    formal_json_cards = {
        row["candidate_scheme_id"]: row
        for row in formal_json.get("cards", [])
        if row.get("candidate_scheme_id")
    }

    rows: list[dict] = []
    for candidate_id in positive_candidates:
        latest = latest_registry.get(candidate_id, {})
        keeper_info = keeper_status_map.get(candidate_id, {})
        in_formal_md = candidate_id in formal_md_summary
        in_formal_json = candidate_id in formal_json_cards
        in_legacy_positive_registry = candidate_id in legacy_positive_cards
        row = {
            "candidate_scheme_id": candidate_id,
            "latest_registry_status": latest.get("status", "missing_from_candidate_registry"),
            "latest_research_round_id": latest.get("research_round_id"),
            "current_keeper_tier": keeper_info.get("current_keeper_tier", "historical_positive_only"),
            "status_source_doc": keeper_info.get("status_source_doc"),
            "factor_card_md_present": in_formal_md,
            "factor_card_json_present": in_formal_json,
            "legacy_positive_card_registry_present": in_legacy_positive_registry,
            "formal_md_summary": formal_md_summary.get(candidate_id),
            "legacy_registry_status": legacy_cards.get(candidate_id, {}).get("status"),
        }
        rows.append(row)

    rows.sort(
        key=lambda item: (
            0 if item["current_keeper_tier"] != "historical_positive_only" else 1,
            -(item["formal_md_summary"] or {}).get("full_sample_corr_ic", -999),
            item["candidate_scheme_id"],
        )
    )

    md_missing = [row["candidate_scheme_id"] for row in rows if not row["factor_card_md_present"]]
    json_missing = [row["candidate_scheme_id"] for row in rows if not row["factor_card_json_present"]]
    legacy_missing = [row["candidate_scheme_id"] for row in rows if not row["legacy_positive_card_registry_present"]]
    keeper_rows = [row for row in rows if row["current_keeper_tier"] != "historical_positive_only"]

    payload = {
        "as_of_date": as_of_date,
        "summary": {
            "historical_positive_signal_count": len(rows),
            "factor_card_md_present_count": sum(row["factor_card_md_present"] for row in rows),
            "factor_card_json_present_count": sum(row["factor_card_json_present"] for row in rows),
            "legacy_positive_card_registry_present_count": sum(
                row["legacy_positive_card_registry_present"] for row in rows
            ),
            "current_keeper_count": len(keeper_rows),
            "active_confirmatory_winner": "none",
            "strict_confirmatory_winner": "none",
        },
        "current_keepers": keeper_rows,
        "missing": {
            "missing_formal_factor_card_md": md_missing,
            "missing_formal_factor_card_json": json_missing,
            "missing_legacy_positive_card_registry_entry": legacy_missing,
        },
        "notes": [
            "formal_factor_cards_20260430.md is treated as the latest authoritative card body for positive signals.",
            "factor_card_registry_20260430.json is treated as the current structured factor-card registry snapshot.",
            "Candidate registry does not yet encode reserve atomic keeper tiers directly; those tiers are reconstructed from closeout documents.",
        ],
        "rows": rows,
    }

    json_output = REGISTRY_DIR / f"positive_signal_factor_card_audit_{as_of_date}.json"
    md_output = REGISTRY_DIR / f"positive_signal_factor_card_audit_{as_of_date}.md"
    write_json(json_output, payload)

    lines = [
        f"# Positive Signal Factor Card Audit ({as_of_date})",
        "",
        "## Summary",
        "",
        f"- `historical_positive_signal_count(历史正向信号数) = {payload['summary']['historical_positive_signal_count']}`",
        f"- `factor_card_md_present_count(正式因子卡Markdown已建数) = {payload['summary']['factor_card_md_present_count']}`",
        f"- `factor_card_json_present_count(正式因子卡JSON已建数) = {payload['summary']['factor_card_json_present_count']}`",
        f"- `legacy_positive_card_registry_present_count(旧正向因子卡注册表已覆盖数) = {payload['summary']['legacy_positive_card_registry_present_count']}`",
        f"- `current_keeper_count(当前保留信号数) = {payload['summary']['current_keeper_count']}`",
        f"- `active_confirmatory_winner(活跃确认性赢家) = {payload['summary']['active_confirmatory_winner']}`",
        f"- `strict_confirmatory_winner(严格确认性赢家) = {payload['summary']['strict_confirmatory_winner']}`",
        "",
        "## Current Keepers",
        "",
    ]

    if keeper_rows:
        for row in keeper_rows:
            lines.append(
                f"- `{row['candidate_scheme_id']}`: `{row['current_keeper_tier']}`"
            )
    else:
        lines.append("- None")

    lines += [
        "",
        "## Card Coverage Check",
        "",
        f"- `formal_factor_cards_20260430.md`: `{len(rows) - len(md_missing)}/{len(rows)}`",
        f"- `formal_factor_cards_20260430.json`: `{len(rows) - len(json_missing)}/{len(rows)}`",
        f"- `factor_card_registry_20260430.json` positive entries: `{len(rows) - len(legacy_missing)}/{len(rows)}`",
        "",
        "## Positive Signal Inventory",
        "",
        "| Candidate | Current Tier | Family | IC | AvgDailyIC | Formal MD Card | Formal JSON Card | Legacy Positive Registry |",
        "|---|---|---|---:|---:|---|---|---|",
    ]

    for row in rows:
        summary = row["formal_md_summary"] or {}
        lines.append(
            "| `{candidate}` | `{tier}` | {family} | {ic} | {avg_ic} | {md} | {json_card} | {legacy} |".format(
                candidate=row["candidate_scheme_id"],
                tier=row["current_keeper_tier"],
                family=summary.get("family_label", "n/a"),
                ic=f"{summary.get('full_sample_corr_ic', float('nan')):.6f}" if summary else "n/a",
                avg_ic=f"{summary.get('avg_daily_ic', float('nan')):.6f}" if summary else "n/a",
                md="yes" if row["factor_card_md_present"] else "no",
                json_card="yes" if row["factor_card_json_present"] else "no",
                legacy="yes" if row["legacy_positive_card_registry_present"] else "no",
            )
        )

    lines += [
        "",
        "## Gaps",
        "",
        f"- `formal_factor_cards_20260430.md` 已覆盖全部 `{len(rows)}` 只历史正向信号。",
        f"- `formal_factor_cards_20260430.json` 已覆盖 `{len(rows) - len(json_missing)}` 只，仍缺 `{len(json_missing)}` 只。",
        f"- `factor_card_registry_20260430.json` 已覆盖 `{len(rows) - len(legacy_missing)}` 只正向信号。",
        "- 当前 `reserve atomic keeper(储备原子信号)` / `high-quality reserve atomic keeper(高质量储备原子信号)` 的层级，主要写在阶段收口文档里，还没有完全回填到 candidate registry 的结构化状态字段。",
        "",
    ]

    write_text(md_output, "\n".join(lines) + "\n")
    print(f"Wrote {json_output}")
    print(f"Wrote {md_output}")


if __name__ == "__main__":
    main()
