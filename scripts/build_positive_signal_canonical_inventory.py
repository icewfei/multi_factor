#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
REGISTRY_DIR = ROOT / "artifacts" / "research_registry"
AUDIO_SOURCE = REGISTRY_DIR / "positive_signal_factor_card_audit_20260430.json"


CANONICAL_CLUSTERS = [
    {
        "canonical_id": "momentum_medium_term",
        "representative_candidate_scheme_id": "price_volume_single_signal_momentum_60_5_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "momentum",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_momentum_60_5_v1"],
        "reason": "Baseline medium-term momentum anchor; no duplicate positive horizon retained in the current 54-signal pool.",
    },
    {
        "canonical_id": "liquidity_trend",
        "representative_candidate_scheme_id": "price_volume_single_signal_liquidity_trend_20_60_v1",
        "secondary_candidate_scheme_ids": ["price_volume_single_signal_liquidity_trend_60_120_v1"],
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "liquidity_improvement",
        "relationship_type": "horizon_variant_cluster",
        "members": [
            "price_volume_single_signal_liquidity_trend_20_60_v1",
            "price_volume_single_signal_liquidity_trend_60_120_v1",
        ],
        "reason": "Same liquidity-improvement mechanism across two horizons; retain 20/60 as the primary canonical label and 60/120 only as a slower variant inside the same cluster.",
    },
    {
        "canonical_id": "turnover_acceleration",
        "representative_candidate_scheme_id": "price_volume_single_signal_turnover_acceleration_5_20_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "turnover",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_turnover_acceleration_5_20_v1"],
        "reason": "Distinct turnover-rate acceleration mechanism, not an alias of amount-based shock.",
    },
    {
        "canonical_id": "amount_shock",
        "representative_candidate_scheme_id": "price_volume_single_signal_amount_shock_5_20_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "liquidity_shock",
        "relationship_type": "alias_cluster",
        "members": [
            "price_volume_single_signal_amount_shock_5_20_v1",
            "price_volume_single_signal_volume_momentum_5_20_v1",
        ],
        "reason": "The two names describe the same 5/20 amount-expansion mechanism; canonical name is amount_shock_5_20.",
    },
    {
        "canonical_id": "price_volume_synchronicity",
        "representative_candidate_scheme_id": "price_volume_single_signal_volume_price_synchronicity_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "price_volume_confirmation",
        "relationship_type": "alias_cluster",
        "members": [
            "price_volume_single_signal_volume_price_synchronicity_20d_v1",
            "price_volume_single_signal_price_volume_corr_20d_v1",
        ],
        "reason": "The two labels are near-identical 20-day price-volume co-movement signals; canonical name is volume_price_synchronicity_20d.",
    },
    {
        "canonical_id": "up_amount_persistence",
        "representative_candidate_scheme_id": "price_volume_single_signal_up_amount_persistence_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "volume_persistence",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_up_amount_persistence_20d_v1"],
        "reason": "Distinct persistence-of-up-volume mechanism.",
    },
    {
        "canonical_id": "breakout_volume_confirmation",
        "representative_candidate_scheme_id": "price_volume_single_signal_breakout_volume_confirmation_20d_v1",
        "cluster_status": "historical_positive_retired",
        "mechanism_family": "breakout_confirmation",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_breakout_volume_confirmation_20d_v1"],
        "reason": "Historically positive but family-level promotion failed badly; keep as retired historical evidence only.",
    },
    {
        "canonical_id": "price_volume_beta",
        "representative_candidate_scheme_id": "price_volume_single_signal_price_volume_beta_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "price_volume_beta",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_price_volume_beta_20d_v1"],
        "reason": "Distinct return-to-volume-beta mechanism.",
    },
    {
        "canonical_id": "price_volume_rank_corr",
        "representative_candidate_scheme_id": "price_volume_single_signal_price_volume_rank_corr_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "price_volume_confirmation",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_price_volume_rank_corr_20d_v1"],
        "reason": "Rank/sign-based robust variant, not identical to Pearson co-movement.",
    },
    {
        "canonical_id": "intraday_trend_bias",
        "representative_candidate_scheme_id": "price_volume_single_signal_intraday_trend_bias_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "intraday_bias",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_intraday_trend_bias_20d_v1"],
        "reason": "Distinct intraday drift mechanism.",
    },
    {
        "canonical_id": "intraday_reversal_asymmetry",
        "representative_candidate_scheme_id": "price_volume_single_signal_intraday_reversal_asymmetry_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "intraday_resilience",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_intraday_reversal_asymmetry_20d_v1"],
        "reason": "Distinct intraday recovery-vs-fade asymmetry mechanism.",
    },
    {
        "canonical_id": "upside_range_share",
        "representative_candidate_scheme_id": "price_volume_single_signal_upside_range_share_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "intraday_structure",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_upside_range_share_20d_v1"],
        "reason": "Distinct up-day range participation mechanism.",
    },
    {
        "canonical_id": "high_open_hold_ratio",
        "representative_candidate_scheme_id": "price_volume_single_signal_high_open_hold_ratio_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "intraday_structure",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_high_open_hold_ratio_20d_v1"],
        "reason": "Distinct high-open quality mechanism.",
    },
    {
        "canonical_id": "lower_shadow_support",
        "representative_candidate_scheme_id": "price_volume_single_signal_lower_shadow_support_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "kline_shadow_support",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_lower_shadow_support_20d_v1"],
        "reason": "Distinct lower-shadow support mechanism.",
    },
    {
        "canonical_id": "downside_range_convexity",
        "representative_candidate_scheme_id": "price_volume_single_signal_downside_range_convexity_20d_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "downside_tail_shape",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_downside_range_convexity_20d_v1"],
        "reason": "Distinct downside-tail convexity mechanism.",
    },
    {
        "canonical_id": "trend_consistency",
        "representative_candidate_scheme_id": "price_volume_single_signal_trend_consistency_20d_v1",
        "cluster_status": "historical_positive_retired",
        "mechanism_family": "trend_consistency",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_trend_consistency_20d_v1"],
        "reason": "Historically positive, but explicitly retired from active keeper pool after later family evidence.",
    },
    {
        "canonical_id": "alpha158_low0",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_low0_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "alpha158_close_location_support",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_alpha158_low0_v1"],
        "reason": "Distinct Alpha158 close-location support mechanism.",
    },
    {
        "canonical_id": "alpha158_rsqr10",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_rsqr10_v1",
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "alpha158_trend_fit_quality",
        "relationship_type": "single",
        "members": ["price_volume_single_signal_alpha158_rsqr10_v1"],
        "reason": "Distinct Alpha158 short-trend fit-quality mechanism.",
    },
    {
        "canonical_id": "alpha158_path_ordering_breakout",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_imxd5_v1",
        "secondary_candidate_scheme_ids": ["price_volume_single_signal_alpha158_imax20_v1"],
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "alpha158_path_ordering_breakout",
        "relationship_type": "near_variant_cluster",
        "members": [
            "price_volume_single_signal_alpha158_imxd5_v1",
            "price_volume_single_signal_alpha158_imax20_v1",
        ],
        "reason": "Both describe breakout path ordering / freshness; retain imxd5 as the canonical representative and imax20 only as a nearby variant.",
    },
    {
        "canonical_id": "alpha158_price_volume_level_corr",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_corr30_v1",
        "secondary_candidate_scheme_ids": [
            "price_volume_single_signal_alpha158_corr20_v1",
            "price_volume_single_signal_alpha158_corr10_v1",
        ],
        "cluster_status": "reserve_atomic_keeper",
        "mechanism_family": "alpha158_price_volume_level_corr",
        "relationship_type": "horizon_cluster",
        "members": [
            "price_volume_single_signal_alpha158_corr5_v1",
            "price_volume_single_signal_alpha158_corr10_v1",
            "price_volume_single_signal_alpha158_corr20_v1",
            "price_volume_single_signal_alpha158_corr30_v1",
            "price_volume_single_signal_alpha158_corr60_v1",
        ],
        "reason": "All five are the same level-correlation mechanism across windows. corr30 is chosen as canonical because it survived furthest in confirmatory governance; corr20 and corr10 remain documented strong variants but not separate canonical entries.",
    },
    {
        "canonical_id": "alpha158_price_volume_change_corr",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_cord30_v1",
        "secondary_candidate_scheme_ids": [
            "price_volume_single_signal_alpha158_cord20_v1",
            "price_volume_single_signal_alpha158_cord10_v1",
        ],
        "cluster_status": "high_quality_reserve_atomic_keeper",
        "mechanism_family": "alpha158_price_volume_change_corr",
        "relationship_type": "horizon_cluster",
        "members": [
            "price_volume_single_signal_alpha158_cord5_v1",
            "price_volume_single_signal_alpha158_cord10_v1",
            "price_volume_single_signal_alpha158_cord20_v1",
            "price_volume_single_signal_alpha158_cord30_v1",
            "price_volume_single_signal_alpha158_cord60_v1",
        ],
        "reason": "All five are the same change-correlation mechanism across windows. cord30 is the canonical representative because it became the strongest and furthest-advanced reserve card.",
    },
    {
        "canonical_id": "alpha158_relative_volume_level",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_vma60_v1",
        "secondary_candidate_scheme_ids": ["price_volume_single_signal_alpha158_vma30_v1"],
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "alpha158_relative_volume_level",
        "relationship_type": "horizon_cluster",
        "members": [
            "price_volume_single_signal_alpha158_vma5_v1",
            "price_volume_single_signal_alpha158_vma10_v1",
            "price_volume_single_signal_alpha158_vma20_v1",
            "price_volume_single_signal_alpha158_vma30_v1",
            "price_volume_single_signal_alpha158_vma60_v1",
        ],
        "reason": "Same relative-volume-level mechanism across windows; retain vma60 as the slow canonical representative.",
    },
    {
        "canonical_id": "alpha158_volume_stability",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_vstd60_v1",
        "secondary_candidate_scheme_ids": ["price_volume_single_signal_alpha158_vstd30_v1"],
        "cluster_status": "historical_positive_canonical",
        "mechanism_family": "alpha158_volume_stability",
        "relationship_type": "horizon_cluster",
        "members": [
            "price_volume_single_signal_alpha158_vstd30_v1",
            "price_volume_single_signal_alpha158_vstd60_v1",
        ],
        "reason": "Same volume-stability mechanism across windows; retain vstd60 as the canonical representative.",
    },
    {
        "canonical_id": "alpha158_volume_expansion_balance",
        "representative_candidate_scheme_id": "price_volume_single_signal_alpha158_vsumd60_v1",
        "secondary_candidate_scheme_ids": [
            "price_volume_single_signal_alpha158_vsump60_v1",
            "price_volume_single_signal_alpha158_vsumn60_v1",
        ],
        "cluster_status": "reserve_atomic_keeper",
        "mechanism_family": "alpha158_volume_expansion_balance",
        "relationship_type": "same_mechanism_cluster",
        "members": [
            "price_volume_single_signal_alpha158_vsump20_v1",
            "price_volume_single_signal_alpha158_vsump30_v1",
            "price_volume_single_signal_alpha158_vsump60_v1",
            "price_volume_single_signal_alpha158_vsumn20_v1",
            "price_volume_single_signal_alpha158_vsumn30_v1",
            "price_volume_single_signal_alpha158_vsumn60_v1",
            "price_volume_single_signal_alpha158_vsumd20_v1",
            "price_volume_single_signal_alpha158_vsumd30_v1",
            "price_volume_single_signal_alpha158_vsumd60_v1",
        ],
        "reason": "The VSUMP / VSUMN / VSUMD set is a highly homologous volume-expansion-balance family. vsumd60 is retained as the single canonical entry because it advanced furthest in confirmatory work and best fits later family use.",
    },
    {
        "canonical_id": "alpha158_full_pilot_labels",
        "representative_candidate_scheme_id": None,
        "cluster_status": "retired_noncanonical_pilot_cluster",
        "mechanism_family": "alpha158_historical_pilot_slots",
        "relationship_type": "historical_pilot_cluster",
        "members": [
            "price_volume_single_signal_alpha158_full_003_v1",
            "price_volume_single_signal_alpha158_full_004_v1",
            "price_volume_single_signal_alpha158_full_019_v1",
            "price_volume_single_signal_alpha158_full_027_v1",
            "price_volume_single_signal_alpha158_full_036_v1",
        ],
        "reason": "These were pre-reconciliation slot labels from exploratory Alpha158 pilots. Keep them as historical evidence only; do not treat them as canonical signals after exact-definition reconciliation.",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".inprogress")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    audit = load_json(AUDIO_SOURCE)
    positive_rows = {row["candidate_scheme_id"]: row for row in audit["rows"]}
    positive_set = set(positive_rows)

    covered: list[str] = []
    enriched_clusters: list[dict] = []
    for cluster in CANONICAL_CLUSTERS:
        members = cluster["members"]
        covered.extend(members)
        cluster_copy = dict(cluster)
        cluster_copy["member_details"] = []
        for member in members:
            row = positive_rows.get(member)
            if row is None:
                raise RuntimeError(f"Member missing from positive audit: {member}")
            cluster_copy["member_details"].append(
                {
                    "candidate_scheme_id": member,
                    "current_keeper_tier": row["current_keeper_tier"],
                    "latest_registry_status": row["latest_registry_status"],
                    "family_label": row["formal_md_summary"]["family_label"],
                    "full_sample_corr_ic": row["formal_md_summary"]["full_sample_corr_ic"],
                    "avg_daily_ic": row["formal_md_summary"]["avg_daily_ic"],
                    "top10_minus_bottom10": row["formal_md_summary"]["top10_minus_bottom10"],
                }
            )
        enriched_clusters.append(cluster_copy)

    covered_set = set(covered)
    duplicates = sorted({member for member in covered if covered.count(member) > 1})
    missing = sorted(positive_set - covered_set)
    extra = sorted(covered_set - positive_set)
    if duplicates or missing or extra:
        raise RuntimeError(
            f"Canonical coverage check failed. duplicates={duplicates} missing={missing} extra={extra}"
        )

    summary = {
        "raw_positive_signal_count": len(positive_set),
        "canonical_cluster_count": len(enriched_clusters),
        "current_reserve_keeper_cluster_count": sum(
            c["cluster_status"] in {"reserve_atomic_keeper", "high_quality_reserve_atomic_keeper"}
            for c in enriched_clusters
        ),
        "historical_positive_canonical_cluster_count": sum(
            c["cluster_status"] == "historical_positive_canonical" for c in enriched_clusters
        ),
        "historical_positive_retired_cluster_count": sum(
            c["cluster_status"] == "historical_positive_retired" for c in enriched_clusters
        ),
        "retired_noncanonical_pilot_cluster_count": sum(
            c["cluster_status"] == "retired_noncanonical_pilot_cluster" for c in enriched_clusters
        ),
        "coverage_check": {
            "raw_positive_signal_count": len(positive_set),
            "covered_member_count": len(covered),
            "covered_unique_member_count": len(covered_set),
            "duplicate_member_count": len(duplicates),
            "missing_member_count": len(missing),
            "extra_member_count": len(extra),
        },
    }

    as_of_date = datetime.now().astimezone().strftime("%Y%m%d")
    payload = {
        "as_of_date": as_of_date,
        "source_audit": str(AUDIO_SOURCE),
        "summary": summary,
        "canonical_clusters": enriched_clusters,
    }
    json_output = REGISTRY_DIR / f"positive_signal_canonical_inventory_{as_of_date}.json"
    md_output = REGISTRY_DIR / f"positive_signal_canonical_inventory_{as_of_date}.md"
    write_json(json_output, payload)

    lines = [
        f"# 54只正向因子的去重后 Canonical 清单 ({as_of_date})",
        "",
        "## 一句话结论",
        "",
        f"- 原始 `signal_edge_positive(正向信号)` 共 `{summary['raw_positive_signal_count']}` 只。",
        f"- 物理去重收口后，压缩为 `{summary['canonical_cluster_count']}` 个 `canonical clusters(标准机制簇)`。",
        "- 今后工作因子池应以这份 canonical 清单为准，不再直接把 54 只原始正向标签当作独立机制池。",
        "",
        "## Summary",
        "",
        f"- `raw_positive_signal_count(原始正向信号数) = {summary['raw_positive_signal_count']}`",
        f"- `canonical_cluster_count(标准机制簇数) = {summary['canonical_cluster_count']}`",
        f"- `current_reserve_keeper_cluster_count(当前reserve簇数) = {summary['current_reserve_keeper_cluster_count']}`",
        f"- `historical_positive_canonical_cluster_count(历史正向但仍为标准簇数) = {summary['historical_positive_canonical_cluster_count']}`",
        f"- `historical_positive_retired_cluster_count(历史正向但已退休簇数) = {summary['historical_positive_retired_cluster_count']}`",
        f"- `retired_noncanonical_pilot_cluster_count(非标准pilot簇数) = {summary['retired_noncanonical_pilot_cluster_count']}`",
        "",
        "## Coverage Check",
        "",
        f"- `covered_unique_member_count(已覆盖唯一成员数) = {summary['coverage_check']['covered_unique_member_count']}`",
        f"- `duplicate_member_count(重复映射成员数) = {summary['coverage_check']['duplicate_member_count']}`",
        f"- `missing_member_count(遗漏成员数) = {summary['coverage_check']['missing_member_count']}`",
        f"- `extra_member_count(额外成员数) = {summary['coverage_check']['extra_member_count']}`",
        "",
        "## Canonical Clusters",
        "",
    ]

    for idx, cluster in enumerate(enriched_clusters, 1):
        lines += [
            f"### {idx}. `{cluster['canonical_id']}`",
            "",
            f"- `cluster_status(簇状态) = {cluster['cluster_status']}`",
            f"- `mechanism_family(机制家族) = {cluster['mechanism_family']}`",
            f"- `relationship_type(关系类型) = {cluster['relationship_type']}`",
            f"- `representative_candidate_scheme_id(代表候选) = {cluster['representative_candidate_scheme_id']}`",
        ]
        if cluster.get("secondary_candidate_scheme_ids"):
            lines.append(
                f"- `secondary_candidate_scheme_ids(次级变体) = {', '.join(cluster['secondary_candidate_scheme_ids'])}`"
            )
        lines.append(f"- `member_count(成员数) = {len(cluster['members'])}`")
        lines.append(f"- `members(成员) = {', '.join(cluster['members'])}`")
        lines.append(f"- reason: {cluster['reason']}")
        lines.append("")

    write_text(md_output, "\n".join(lines) + "\n")
    print(f"Wrote {json_output}")
    print(f"Wrote {md_output}")
    print(f"Canonical clusters: {len(enriched_clusters)}")


if __name__ == "__main__":
    main()
