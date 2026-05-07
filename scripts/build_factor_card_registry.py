#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Build standardized factor card registry from all existing signal-edge diagnosis results.

Per 框架 14.4, each factor card includes:
- Factor name / candidate_scheme_id
- Signal field name & ranking direction
- Expected direction (economic rationale)
- Coverage (ranking-eligible, scored with label)
- IC metrics (full-sample corr IC, avg daily IC, positive daily IC share)
- Decile monotonicity (forward label by decile)
- Top-slice differentiation (top10 vs rank11-20 vs bottom10)
- Cutoff gap (rank 10/11 separation)
- Classification (positive / mixed / negative)
- Factor family categorization

Output:
- artifacts/research_registry/factor_card_registry_<as_of_date>.json
- artifacts/research_registry/factor_card_registry_<as_of_date>.md
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RESEARCH_ROUNDS_DIR = ROOT / "artifacts" / "research_registry" / "research_rounds"
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
CANDIDATE_REGISTRY = REGISTRY_DIR / "candidate_scheme_registry.jsonl"
FORMAL_FACTOR_CARDS_JSON = REGISTRY_DIR / "formal_factor_cards_20260430.json"


# Factor family classification rules based on signal name patterns
FAMILY_PATTERNS: list[tuple[str, str, str]] = [
    # (family, subfamily, pattern_regex)
    ("momentum", "medium_term", r"momentum_60_5|momentum_120_20|momentum_250_20"),
    ("momentum", "short_term", r"momentum_20_5"),
    ("reversal", "short_term", r"reversal_5d"),
    ("reversal", "followthrough", r"reversal_followthrough"),
    ("volatility", "realized_vol", r"volatility_20d|volatility_60d"),
    ("volatility", "regime", r"vol_regime"),
    ("liquidity", "level", r"liquidity_20d|amihud_illiquidity"),
    ("liquidity", "trend", r"liquidity_trend"),
    ("liquidity", "shock", r"liquidity_shock|amount_shock"),
    ("trend", "consistency", r"trend_consistency"),
    ("trend", "efficiency", r"trend_efficiency|path_efficiency"),
    ("price_volume", "correlation", r"price_volume_corr|price_volume_rank_corr|volume_price_synchronicity"),
    ("price_volume", "beta", r"price_volume_beta"),
    ("turnover", "level", r"turnover_stability|turnover_acceleration|volume_momentum"),
    ("turnover", "distribution", r"turnover_entropy|turnover_concentration_hhi|turnover_mean_reversion"),
    ("kline", "body", r"candle_body_efficiency|close_location_value|close_position_stability"),
    ("kline", "shadow", r"upper_shadow|lower_shadow|shadow_asymmetry"),
    ("kline", "range", r"range_compression|range_expansion|close_to_high_ratio|intraday_range"),
    ("gap", "level", r"gap_fill_rate|gap_followthrough|gap_to_range|overnight_gap|gap_reversal"),
    ("gap", "recovery", r"downside_gap|gap_fill|gap_recovery"),
    ("intraday", "bias", r"intraday_trend_bias|intraday_reversal|intraday_recovery|intraday_path"),
    ("intraday", "structure", r"intraday_curvature|intraday_efficiency|intraday_skew|overnight_intraday"),
    ("volume", "imbalance", r"signed_amount_imbalance|signed_turnover_imbalance|updown_volume|up_volume_share"),
    ("volume", "flow", r"signed_dollar_flow|amount_autocorr|amount_volatility|return_autocorr"),
    ("volume", "persistence", r"amount_persistence|volume_persistence|flow_persistence"),
    ("downside", "risk", r"downside_semivol|downside_tail|downside_absorption|downside_range_convexity"),
    ("downside", "recovery", r"downside_recovery|downside_gap_fill|breakdown_distance|low_break_recovery"),
    ("breakout", "proximity", r"breakout_proximity|breakout_distance"),
    ("breakout", "failure", r"breakout_failure|breakout_volume"),
    ("quality", "profitability", r"quality_profitability|roe|gross_margin"),
    ("value", "classic", r"value_|ep|bp|pe|pb"),
    ("alpha158", "full", r"alpha158_full"),
    ("alpha158", "named", r"alpha158_"),
]


def classify_family(candidate_scheme_id: str) -> tuple[str, str]:
    """Classify a candidate into (family, subfamily)."""
    for family, subfamily, pattern in FAMILY_PATTERNS:
        if re.search(pattern, candidate_scheme_id, re.IGNORECASE):
            return family, subfamily
    return ("uncategorized", "other")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".inprogress")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def fmt(v: float | None, decimals: int = 6) -> str:
    if v is None:
        return "null"
    return f"{v:.{decimals}f}"


def fmt_pct(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "null"
    return f"{v * 100:.{decimals}f}%"


def fmt_label(v: float | None) -> str:
    """Format a small decimal label value (like 0.0033)."""
    return fmt(v, 6)


def collect_diagnosis_files() -> list[tuple[str, Path]]:
    """Scan all research round directories for signal-edge diagnosis JSONs."""
    files: list[tuple[str, Path]] = []
    marker = "_signal_edge_diagnosis_"
    if not RESEARCH_ROUNDS_DIR.exists():
        return files
    for round_dir in sorted(RESEARCH_ROUNDS_DIR.iterdir()):
        if not round_dir.is_dir():
            continue
        for fpath in sorted(round_dir.iterdir()):
            fname = fpath.name
            if not fname.endswith(".json") or marker not in fname:
                continue
            stem = fname.removesuffix(".json")
            idx = stem.index(marker)
            candidate_id = stem[:idx]
            files.append((candidate_id, fpath))
    return files


def load_candidate_registry() -> dict[str, dict[str, Any]]:
    """Load candidate registry into a dict keyed by candidate_scheme_id."""
    rows = load_jsonl(CANDIDATE_REGISTRY)
    return {row.get("candidate_scheme_id", ""): row for row in rows}


def load_historical_positive_set() -> set[str]:
    """Use the latest formal factor-card universe as the authoritative positive inventory."""
    if not FORMAL_FACTOR_CARDS_JSON.exists():
        return set()
    payload = load_json(FORMAL_FACTOR_CARDS_JSON)
    return {
        row.get("candidate_scheme_id", "")
        for row in payload.get("cards", [])
        if row.get("candidate_scheme_id")
    }


def main() -> None:
    as_of_date = datetime.now().astimezone().strftime("%Y%m%d")
    output_stem = f"factor_card_registry_{as_of_date}"
    json_output = REGISTRY_DIR / f"{output_stem}.json"
    md_output = REGISTRY_DIR / f"{output_stem}.md"

    diagnosis_files = collect_diagnosis_files()
    candidate_registry = load_candidate_registry()
    historical_positive_set = load_historical_positive_set()

    if not diagnosis_files:
        print("No signal-edge diagnosis files found.")
        write_json(json_output, {"as_of_date": as_of_date, "factor_cards": [], "summary": {}})
        md_output.write_text(f"# Factor Card Registry ({as_of_date})\n\nNo diagnosis files found.\n", encoding="utf-8")
        return

    # Group by candidate_scheme_id (multiple rounds may have same candidate)
    by_candidate: dict[str, list[tuple[Path, dict]]] = {}
    for candidate_id, fpath in diagnosis_files:
        try:
            payload = load_json(fpath)
        except (json.JSONDecodeError, Exception):
            continue
        if candidate_id not in by_candidate:
            by_candidate[candidate_id] = []
        by_candidate[candidate_id].append((fpath, payload))

    # Build factor cards
    factor_cards: list[dict[str, Any]] = []
    for candidate_id in sorted(by_candidate.keys()):
        entries = by_candidate[candidate_id]
        # Use the latest entry (by file path sort gives deterministic order)
        latest_fpath, latest = entries[-1]

        family, subfamily = classify_family(candidate_id)

        # Get registration data
        reg = candidate_registry.get(candidate_id, {})
        ranking_direction = reg.get("score_rule", "")
        if "ranking_direction" in latest.get("notes", [])[0] if latest.get("notes") else "":
            pass

        # Extract core metrics
        coverage = latest.get("coverage", {})
        ic_readout = latest.get("ic_readout", {})
        decile_data = latest.get("decile_monotonicity", {})
        top_slice = latest.get("top_slice_readout", {})

        # Compute monotonicity score (handle both int-keyed and object-keyed formats)
        numeric_deciles = {}
        for k, v in decile_data.items():
            try:
                numeric_deciles[int(k)] = v
            except (ValueError, TypeError):
                pass
        sorted_deciles = sorted(numeric_deciles.items(), key=lambda x: x[0])
        decile_values = [v for _, v in sorted_deciles if v is not None]
        monotonic_ok = False
        if len(decile_values) >= 10:
            monotonic_ok = decile_values[0] > decile_values[-1]

        # Status from registry, with fallback inference from IC metrics
        status = "unknown"
        latest_registry_status = candidate_registry.get(candidate_id, {}).get("status", "unknown")
        keeper_tier = candidate_registry.get(candidate_id, {}).get("keeper_tier")
        if candidate_id in historical_positive_set:
            status = "signal_edge_positive"
        elif candidate_id in candidate_registry:
            status = latest_registry_status
        else:
            # Infer from IC
            ic = ic_readout.get("full_sample_corr_ic")
            avg_ic = ic_readout.get("avg_daily_ic")
            pos_share = ic_readout.get("positive_daily_ic_share")
            top10 = top_slice.get("avg_label_top10")
            rank11_20 = top_slice.get("avg_label_rank11_20")

            if ic is not None and avg_ic is not None and pos_share is not None:
                if ic > 0 and avg_ic > 0 and pos_share > 0.52 and top10 is not None and rank11_20 is not None and top10 > rank11_20:
                    status = "signal_edge_positive"
                elif ic <= 0 and avg_ic <= 0 and pos_share < 0.50:
                    status = "signal_edge_negative"
                else:
                    status = "signal_edge_mixed"
            else:
                status = "unknown"

        card = {
            "candidate_scheme_id": candidate_id,
            "family": family,
            "subfamily": subfamily,
            "ranking_direction": reg.get("changed_dimension", "unknown"),
            "status": status,
            "latest_registry_status": latest_registry_status,
            "keeper_tier": keeper_tier,
            "latest_as_of_date": latest.get("as_of_date", ""),
            "coverage": {
                "ranking_eligible_rows": coverage.get("ranking_eligible_rows"),
                "null_score_rows": coverage.get("null_score_rows"),
                "null_score_share": coverage.get("null_score_share"),
                "scored_with_label_rows": coverage.get("scored_with_label_rows"),
            },
            "ic": {
                "full_sample_corr_ic": ic_readout.get("full_sample_corr_ic"),
                "avg_daily_ic": ic_readout.get("avg_daily_ic"),
                "median_daily_ic": ic_readout.get("median_daily_ic"),
                "positive_daily_ic_share": ic_readout.get("positive_daily_ic_share"),
            },
            "decile_monotonicity": {
                str(k): v for k, v in sorted_deciles
            },
            "decile_monotonic_ok": monotonic_ok,
            "top_slice": {
                "avg_label_top10": top_slice.get("avg_label_top10"),
                "avg_label_rank11_20": top_slice.get("avg_label_rank11_20"),
                "avg_label_bottom10": top_slice.get("avg_label_bottom10"),
                "top10_minus_rank11_20": top_slice.get("top10_minus_rank11_20"),
                "top10_minus_bottom10": top_slice.get("top10_minus_bottom10"),
            },
            "cutoff_gap": {
                "avg_rank10_11_score_gap": latest.get("cutoff_gap", {}).get("avg_rank10_11_score_gap"),
                "median_rank10_11_score_gap": latest.get("cutoff_gap", {}).get("median_rank10_11_score_gap"),
            },
        }
        factor_cards.append(card)

    # Group by family
    by_family: dict[str, list[dict]] = defaultdict(list)
    for card in factor_cards:
        by_family[card["family"]].append(card)

    family_summary = {}
    for family, cards in sorted(by_family.items()):
        total = len(cards)
        positive = sum(1 for c in cards if c["status"] == "signal_edge_positive")
        negative = sum(1 for c in cards if c["status"] == "signal_edge_negative")
        mixed = sum(1 for c in cards if c["status"] == "signal_edge_mixed")
        unknown = sum(1 for c in cards if c["status"] == "unknown")
        monotonic = sum(1 for c in cards if c["decile_monotonic_ok"])
        family_summary[family] = {
            "total": total,
            "positive": positive,
            "negative": negative,
            "mixed": mixed,
            "unknown": unknown,
            "monotonic_decile_count": monotonic,
        }

    overall_summary = {
        "total_signals": len(factor_cards),
        "total_positive": sum(1 for c in factor_cards if c["status"] == "signal_edge_positive"),
        "total_negative": sum(1 for c in factor_cards if c["status"] == "signal_edge_negative"),
        "total_mixed": sum(1 for c in factor_cards if c["status"] == "signal_edge_mixed"),
        "total_unknown": sum(1 for c in factor_cards if c["status"] == "unknown"),
        "total_families": len(by_family),
        "families": family_summary,
    }

    payload = {
        "as_of_date": as_of_date,
        "factor_cards": factor_cards,
        "summary": overall_summary,
    }
    write_json(json_output, payload)

    # Generate markdown report
    md_lines = [
        f"# Factor Card Registry ({as_of_date})",
        "",
        f"Total signals: **{overall_summary['total_signals']}** | "
        f"Positive: **{overall_summary['total_positive']}** | "
        f"Negative: **{overall_summary['total_negative']}** | "
        f"Mixed: **{overall_summary['total_mixed']}** | "
        f"Unknown: **{overall_summary['total_unknown']}**",
        "",
        "---",
        "",
        "## Summary by Factor Family",
        "",
        "| Family | Total | Positive | Negative | Mixed | Monotonic Deciles |",
        "|--------|------:|--------:|--------:|------:|------------------:|",
    ]
    for family, fs in sorted(family_summary.items()):
        md_lines.append(
            f"| {family} | {fs['total']} | {fs['positive']} | {fs['negative']} | "
            f"{fs['mixed']} | {fs['monotonic_decile_count']} |"
        )
    md_lines.extend(["", "---", ""])

    # Per-family detail
    for family, cards in sorted(by_family.items()):
        md_lines.extend([
            f"## {family.replace('_', ' ').title()} ({len(cards)} signals)",
            "",
        ])

        # Sort: positive first, then mixed, then negative, then unknown
        def sort_key(c: dict) -> tuple:
            order = {"signal_edge_positive": 0, "signal_edge_mixed": 1, "signal_edge_negative": 2, "unknown": 3}
            return order.get(c["status"], 99)

        for card in sorted(cards, key=sort_key):
            cid = card["candidate_scheme_id"]
            status = card["status"].replace("signal_edge_", "")
            ic = card["ic"]
            cov = card["coverage"]
            top = card["top_slice"]

            md_lines.append(f"### {cid}")
            md_lines.append(f"- **Status**: {status} | **Family**: {family} > {card['subfamily']}")
            if card.get("latest_registry_status") and card["latest_registry_status"] != card["status"]:
                md_lines.append(f"- **Latest registry status**: {card['latest_registry_status']}")
            if card.get("keeper_tier"):
                md_lines.append(f"- **Keeper tier**: {card['keeper_tier']}")
            md_lines.append(f"- **Coverage**: {fmt(cov.get('scored_with_label_rows'))} scored with label "
                            f"(null share: {fmt_pct(cov.get('null_score_share'))})")
            md_lines.append(f"- **IC**: full-sample = {fmt(ic.get('full_sample_corr_ic'), 6)}, "
                            f"avg daily = {fmt(ic.get('avg_daily_ic'), 6)}, "
                            f"positive share = {fmt_pct(ic.get('positive_daily_ic_share'))}")
            md_lines.append(f"- **Decile monotonic**: {'yes' if card['decile_monotonic_ok'] else 'no'} | "
                            f"**Top10 label** = {fmt_label(top.get('avg_label_top10'))}, "
                            f"**11-20** = {fmt_label(top.get('avg_label_rank11_20'))}, "
                            f"**Bottom10** = {fmt_label(top.get('avg_label_bottom10'))}")
            md_lines.append(f"- **Top10 - 11-20** = {fmt_label(top.get('top10_minus_rank11_20'))}, "
                            f"**Top10 - Bottom10** = {fmt_label(top.get('top10_minus_bottom10'))}")
            md_lines.append("")

    write_json(json_output, payload)
    md_output.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Factor card registry created: {json_output}")
    print(f"Report: {md_output}")
    print(f"Total signals: {overall_summary['total_signals']}, "
          f"Positive: {overall_summary['total_positive']}, "
          f"Negative: {overall_summary['total_negative']}, "
          f"Mixed: {overall_summary['total_mixed']}")


if __name__ == "__main__":
    main()
