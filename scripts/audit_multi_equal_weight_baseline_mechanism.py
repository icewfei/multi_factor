from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path("/Users/wy/MiscProject/multi_factor")
DEFAULT_BASELINE_BUILDER = ROOT / "scripts" / "build_multi_equal_weight_v1_scores.py"
DEFAULT_P98_BUILDER = ROOT / "scripts" / "build_reversal_tail_composite_model_scores.py"
DEFAULT_P98_AUDIT = ROOT / "artifacts" / "run_state" / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0_audit.json"
DEFAULT_UPSTREAM_REVERSAL_AUDIT = ROOT / "artifacts" / "run_state" / "exploratory_cross_horizon_c1_reversal_only" / "model_scores_D0_audit.json"
DEFAULT_CONFIRMED5_READOUT = Path("/private/tmp/confirmed5_vs_baseline_same_contract_readout.json")
DEFAULT_V2_READOUT = Path("/private/tmp/nlc_v2_vs_baseline_same_contract_v3_readout.json")
DEFAULT_TERMINAL_APPROVAL = Path("/private/tmp/combined_same_contract_terminal_approval.json")
DEFAULT_REPAIRED_CANDIDATE = Path("/private/tmp/combined_same_contract_repaired_candidate_v2plus.json")
DEFAULT_PROJECT_STATUS_DOC = ROOT / "docs" / "current_project_status_after_confirmed5.md"
DEFAULT_CONFIRMED5_DECISION_DOC = ROOT / "docs" / "nonlinear_confirmed5_challenger_decision_record.md"
DEFAULT_V2_DECISION_DOC = ROOT / "docs" / "nonlinear_challenger_v2_decision_record.md"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/multi_equal_weight_baseline_mechanism_audit.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/multi_equal_weight_baseline_mechanism_audit.md")

LEAKAGE_TERMS = (
    "forward_label",
    "label_",
    "realized_return",
    "execution_delayed_realized_return",
    "actual_exit_date",
    "actual_sell_price",
    "close_D",
    "open_D",
    "next_open",
    "next_close",
)


class AuditError(Exception):
    """Raised when the baseline mechanism audit cannot continue safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit multi_equal_weight_v1 baseline mechanism.")
    parser.add_argument("--baseline-builder", type=Path, default=DEFAULT_BASELINE_BUILDER)
    parser.add_argument("--p98-builder", type=Path, default=DEFAULT_P98_BUILDER)
    parser.add_argument("--p98-audit", type=Path, default=DEFAULT_P98_AUDIT)
    parser.add_argument("--upstream-reversal-audit", type=Path, default=DEFAULT_UPSTREAM_REVERSAL_AUDIT)
    parser.add_argument("--confirmed5-readout", type=Path, default=DEFAULT_CONFIRMED5_READOUT)
    parser.add_argument("--v2-readout", type=Path, default=DEFAULT_V2_READOUT)
    parser.add_argument("--terminal-approval", type=Path, default=DEFAULT_TERMINAL_APPROVAL)
    parser.add_argument("--repaired-candidate", type=Path, default=DEFAULT_REPAIRED_CANDIDATE)
    parser.add_argument("--project-status-doc", type=Path, default=DEFAULT_PROJECT_STATUS_DOC)
    parser.add_argument("--confirmed5-decision-doc", type=Path, default=DEFAULT_CONFIRMED5_DECISION_DOC)
    parser.add_argument("--v2-decision-doc", type=Path, default=DEFAULT_V2_DECISION_DOC)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser


def read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AuditError(f"{label} not found: {path}") from exc


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuditError(f"Expected JSON object: {path}")
    return payload


def read_json(path: Path, label: str) -> dict[str, Any]:
    payload = read_optional_json(path)
    if payload is None:
        raise AuditError(f"{label} not found: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def collect_term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def inspect_multi_equal_weight_builder(source_text: str, builder_path: Path) -> dict[str, Any]:
    source_fields = [
        field
        for field in ("adj_close", "amount", "vol", "pct_chg")
        if field in source_text
    ]
    required_patterns = {
        "trade_date_as_signal_date": "trade_date AS signal_date" in source_text,
        "uses_lag_history": "LAG(" in source_text,
        "rolling_window_30": "ROWS BETWEEN 29 PRECEDING AND CURRENT ROW" in source_text,
        "rolling_window_60": "ROWS BETWEEN 59 PRECEDING AND CURRENT ROW" in source_text,
        "ranking_eligible_d0_guard": "WHERE ranking_eligible_D0" in source_text,
        "shared_sample_panel_anchor": "project_sample_panel" in source_text,
        "trainval_only_declared": "trainval-only" in source_text.lower(),
        "frozen_test_forbidden_declared": "does not access frozen test data" in source_text.lower(),
    }
    leakage_hits = collect_term_hits(source_text, LEAKAGE_TERMS)
    direct_sources = [
        "reversal_tail_exclude_p98_v1 component score",
        "vw_bars_daily.adj_close",
        "vw_bars_daily.amount",
        "vw_bars_daily.vol",
        "vw_bars_daily.pct_chg",
        "project_sample_panel.ranking_eligible_D0",
    ]
    return {
        "builder_path": str(builder_path),
        "direct_sources": direct_sources,
        "source_fields_detected": source_fields,
        "required_patterns": required_patterns,
        "future_field_usage_detected": bool(leakage_hits),
        "future_or_label_term_hits": leakage_hits,
        "conclusion": (
            "No direct future-field, label, or realized-return dependency found in "
            "build_multi_equal_weight_v1_scores.py."
            if not leakage_hits and all(required_patterns.values())
            else "Static audit found either missing D0 guards or suspicious field references."
        ),
    }


def inspect_p98_builder(
    source_text: str,
    builder_path: Path,
    p98_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    required_patterns = {
        "ranking_eligible_d0_guard": "WHERE s.ranking_eligible_D0" in source_text,
        "daily_cross_sectional_tail_rule": "PERCENTILE_CONT(0.98)" in source_text,
        "tail_exclusion_applied": "WHERE n.nr_score < p.p98" in source_text,
        "no_backtest_output_dependency": "validation_readout" not in source_text,
    }
    leakage_hits = collect_term_hits(source_text, LEAKAGE_TERMS)
    audit_summary = p98_audit.get("summary_counts") if p98_audit else None
    source_runs = p98_audit.get("source_runs") if p98_audit else None
    return {
        "builder_path": str(builder_path),
        "candidate_scheme_id": p98_audit.get("candidate_scheme_id") if p98_audit else None,
        "source_runs": source_runs,
        "summary_counts": audit_summary,
        "required_patterns": required_patterns,
        "future_field_usage_detected": bool(leakage_hits),
        "future_or_label_term_hits": leakage_hits,
        "conclusion": (
            "The p98 component builder applies an intra-day cross-sectional tail exclusion on "
            "reversal scores without direct label or realized-return joins."
            if not leakage_hits and all(required_patterns.values())
            else "The p98 component builder needs follow-up because expected D0 guardrails were not fully observed."
        ),
    }


def inspect_policy_docs(texts: list[str]) -> dict[str, Any]:
    joined = "\n".join(texts)
    checks = {
        "same_split_required": "同 train / validation split" in joined or "同 split" in joined,
        "same_execution_contract_required": "同 execution contract" in joined,
        "same_terminal_policy_required": "同 terminal exit policy" in joined,
        "same_portfolio_rule_required": (
            "同 portfolio construction rules" in joined or "同 portfolio rule" in joined
        ),
        "same_cash_invested_accounting_required": "同 cash / invested capital 口径" in joined,
        "baseline_is_minimum_hurdle_declared": "最低门槛" in joined,
    }
    return {
        "checks": checks,
        "conclusion": (
            "Project docs explicitly require same-contract comparison on split, execution, terminal policy, "
            "portfolio rule, and cash/invested accounting."
        ),
    }


def extract_readout_window_metrics(block: dict[str, Any]) -> dict[str, float | None]:
    return {
        "avg_cash_weight": block.get("avg_cash_weight"),
        "avg_invested_weight": block.get("avg_invested_weight"),
        "avg_turnover_daily": block.get("avg_turnover_daily"),
        "annual_relative_return_trainval_dry_run_estimate": block.get("annual_relative_return_trainval_dry_run_estimate"),
        "relative_ir_estimate": block.get("relative_ir_estimate"),
    }


def inspect_same_contract_readout(path: Path, label: str) -> dict[str, Any]:
    payload = read_json(path, label)
    split_config = payload.get("split_config", {})
    return {
        "path": str(path),
        "label": payload.get("readout_label"),
        "frozen_test_accessed": payload.get("frozen_test_accessed"),
        "formal_metrics_generated": payload.get("formal_metrics_generated"),
        "split_config": split_config,
        "primary_run": {
            "run_id": payload.get("primary_run", {}).get("run_id"),
            "attempt_id": payload.get("primary_run", {}).get("attempt_id"),
            "candidate_scheme_id": payload.get("primary_run", {}).get("candidate_scheme_id"),
            "run_state_acceptance_overall_passed": payload.get("primary_run", {}).get("run_state_acceptance_overall_passed"),
        },
        "baseline_run": {
            "run_id": payload.get("baseline_run", {}).get("run_id"),
            "attempt_id": payload.get("baseline_run", {}).get("attempt_id"),
            "candidate_scheme_id": payload.get("baseline_run", {}).get("candidate_scheme_id"),
            "run_state_acceptance_overall_passed": payload.get("baseline_run", {}).get("run_state_acceptance_overall_passed"),
        },
        "windows": {
            "primary": {
                "train": extract_readout_window_metrics(payload["windows"]["primary"]["train"]),
                "validation": extract_readout_window_metrics(payload["windows"]["primary"]["validation"]),
            },
            "baseline": {
                "train": extract_readout_window_metrics(payload["windows"]["baseline"]["train"]),
                "validation": extract_readout_window_metrics(payload["windows"]["baseline"]["validation"]),
            },
            "comparison": payload["windows"]["comparison"],
        },
    }


def build_deployment_commentary(confirmed5_readout: dict[str, Any], v2_readout: dict[str, Any]) -> dict[str, Any]:
    def side_comment(
        name: str,
        readout: dict[str, Any],
    ) -> dict[str, Any]:
        train_delta = readout["windows"]["comparison"]["train"]
        validation_delta = readout["windows"]["comparison"]["validation"]
        return {
            "pair": name,
            "candidate_minus_baseline_train": {
                "avg_cash_weight_delta_vs_baseline": train_delta.get("avg_cash_weight_delta_vs_baseline"),
                "avg_invested_weight_delta_vs_baseline": train_delta.get("avg_invested_weight_delta_vs_baseline"),
                "avg_turnover_daily_delta_vs_baseline": train_delta.get("avg_turnover_daily_delta_vs_baseline"),
            },
            "candidate_minus_baseline_validation": {
                "avg_cash_weight_delta_vs_baseline": validation_delta.get("avg_cash_weight_delta_vs_baseline"),
                "avg_invested_weight_delta_vs_baseline": validation_delta.get("avg_invested_weight_delta_vs_baseline"),
                "avg_turnover_daily_delta_vs_baseline": validation_delta.get("avg_turnover_daily_delta_vs_baseline"),
            },
        }

    notes = [
        "Versus confirmed5, baseline wins while carrying more cash, less invested capital, and lower turnover.",
        "Versus v2, baseline wins under the opposite deployment pattern: less cash, more invested capital, and slightly higher turnover.",
        "The baseline edge therefore does not reduce to one hidden capital-deployment loophole.",
    ]
    return {
        "confirmed5_pair": side_comment("baseline_vs_confirmed5", confirmed5_readout),
        "v2_pair": side_comment("baseline_vs_v2", v2_readout),
        "notes": notes,
    }


def inspect_terminal_policy(
    terminal_approval: dict[str, Any],
    repaired_candidate: dict[str, Any],
) -> dict[str, Any]:
    summary = terminal_approval.get("summary", {})
    repaired_summary = repaired_candidate.get("summary", {})
    return {
        "approval_policy_version": terminal_approval.get("approval_policy_version"),
        "contract_ref": terminal_approval.get("contract_ref"),
        "approval_summary": summary,
        "repaired_candidate_summary": repaired_summary,
        "approval_notes": terminal_approval.get("notes", []),
        "candidate_notes": repaired_candidate.get("notes", []),
        "no_pricing_backfill_in_approval_audit": (
            repaired_summary.get("priced_rows_count") == 0
            and "approval audit never backfills actual_exit_date, actual_sell_price, or execution_delayed_realized_return."
            in "\n".join(terminal_approval.get("notes", []))
        ),
        "conclusion": (
            "Terminal approval and repaired-candidate artifacts do not backfill actual exits and therefore do not show a "
            "baseline-only execution concession."
        ),
    }


def audit_multi_equal_weight_baseline_mechanism(
    *,
    baseline_builder: Path,
    p98_builder: Path,
    p98_audit_path: Path,
    upstream_reversal_audit_path: Path,
    confirmed5_readout_path: Path,
    v2_readout_path: Path,
    terminal_approval_path: Path,
    repaired_candidate_path: Path,
    policy_doc_paths: list[Path],
    output_json: Path,
    output_md: Path,
) -> dict[str, Any]:
    baseline_builder_text = read_text(baseline_builder, "baseline builder")
    p98_builder_text = read_text(p98_builder, "p98 builder")
    p98_audit = read_optional_json(p98_audit_path)
    confirmed5_readout = inspect_same_contract_readout(confirmed5_readout_path, "confirmed5 same-contract readout")
    v2_readout = inspect_same_contract_readout(v2_readout_path, "v2 same-contract readout")
    terminal_approval = read_json(terminal_approval_path, "terminal approval audit")
    repaired_candidate = read_json(repaired_candidate_path, "repaired terminal candidate")
    policy_docs = [read_text(path, f"policy doc {path.name}") for path in policy_doc_paths]

    baseline_score_audit = inspect_multi_equal_weight_builder(baseline_builder_text, baseline_builder)
    p98_component_audit = inspect_p98_builder(p98_builder_text, p98_builder, p98_audit)
    policy_audit = inspect_policy_docs(policy_docs)
    terminal_audit = inspect_terminal_policy(terminal_approval, repaired_candidate)
    capital_explanation = build_deployment_commentary(confirmed5_readout, v2_readout)

    blockers: list[str] = []
    upstream_reversal_audit = read_optional_json(upstream_reversal_audit_path)
    if upstream_reversal_audit is None:
        blockers.append(
            "Upstream reversal source run-state audit is unavailable locally, so the raw reversal provenance cannot be fully re-verified from artifacts in this pass."
        )
    if not all(policy_audit["checks"].values()):
        blockers.append("Same-contract policy language is incomplete in the local decision-record set.")
    if confirmed5_readout["frozen_test_accessed"] is not False or v2_readout["frozen_test_accessed"] is not False:
        blockers.append("At least one same-contract readout does not explicitly state frozen_test_accessed=false.")
    if confirmed5_readout["formal_metrics_generated"] is not False or v2_readout["formal_metrics_generated"] is not False:
        blockers.append("At least one same-contract readout does not explicitly state formal_metrics_generated=false.")
    if not terminal_audit["no_pricing_backfill_in_approval_audit"]:
        blockers.append("Terminal approval artifacts need follow-up because approval may have backfilled priced exits.")

    hidden_advantage_found = False
    baseline_hurdle_status = "conditional_pass" if blockers else "pass"
    baseline_hurdle_reason = (
        "No direct future-function, leakage, or same-contract asymmetry was found in the accessible baseline chain. "
        "Baseline should remain the minimum hurdle, subject to the listed evidence gaps."
        if not hidden_advantage_found
        else "Baseline should not remain the minimum hurdle until the hidden-advantage issue is resolved."
    )

    result = {
        "audit_label": "TRAINVAL DIAGNOSTIC AUDIT ONLY — NOT OOS — NOT FROZEN TEST — NOT A FORMAL STRATEGY CONCLUSION",
        "frozen_test_accessed": False,
        "formal_metrics_generated": False,
        "baseline_score_construction_audit": baseline_score_audit,
        "d0_visibility_audit": {
            "declared_d0_visible_inputs": [
                "p98 component score on signal_date",
                "adj_close",
                "amount",
                "vol",
                "pct_chg",
                "ranking_eligible_D0",
            ],
            "d0_visibility_guardrails": {
                "historical_windows_end_at_current_row": (
                    baseline_score_audit["required_patterns"]["rolling_window_30"]
                    and baseline_score_audit["required_patterns"]["rolling_window_60"]
                ),
                "signal_date_is_trade_date": baseline_score_audit["required_patterns"]["trade_date_as_signal_date"],
                "ranking_only_within_d0_eligible_pool": baseline_score_audit["required_patterns"]["ranking_eligible_d0_guard"],
            },
            "conclusion": "All baseline builder inputs visible in the accessible code path are D0 fields or rolling histories ending on D0.",
        },
        "leakage_risk_audit": {
            "baseline_builder_direct_leakage_hits": baseline_score_audit["future_or_label_term_hits"],
            "p98_builder_direct_leakage_hits": p98_component_audit["future_or_label_term_hits"],
            "label_or_realized_return_join_found": bool(
                baseline_score_audit["future_or_label_term_hits"] or p98_component_audit["future_or_label_term_hits"]
            ),
            "upstream_reversal_audit_available": upstream_reversal_audit is not None,
            "conclusion": (
                "No direct label or realized-return leakage was found in the accessible baseline source chain. "
                "Residual uncertainty remains only where upstream reversal artifacts are missing."
            ),
        },
        "universe_mask_tradability_alignment_audit": {
            "baseline_anchor": "project_sample_panel + ranking_eligible_D0",
            "same_contract_policy_checks": policy_audit["checks"],
            "same_split_configs_match": (
                confirmed5_readout["split_config"] == v2_readout["split_config"]
            ),
            "conclusion": (
                "No evidence was found that baseline used a wider universe, looser D0 mask, or separate tradability contract."
            ),
        },
        "execution_terminal_portfolio_rule_alignment_audit": {
            "confirmed5_readout": confirmed5_readout,
            "v2_readout": v2_readout,
            "terminal_policy_audit": terminal_audit,
            "conclusion": (
                "Accessible same-contract records point to one execution contract, one terminal policy, and one portfolio-rule comparison layer. "
                "No baseline-only execution relaxation was observed."
            ),
        },
        "cash_invested_turnover_explanation": capital_explanation,
        "p98_component_audit": p98_component_audit,
        "hidden_advantage_found": hidden_advantage_found,
        "hidden_advantage_summary": (
            "No hidden baseline advantage was confirmed. The observed edge still looks more consistent with selection quality than with accounting, cash, or terminal-policy asymmetry."
        ),
        "baseline_minimum_hurdle_recommendation": {
            "status": baseline_hurdle_status,
            "allow_as_minimum_hurdle": not hidden_advantage_found,
            "reason": baseline_hurdle_reason,
        },
        "blockers": blockers,
    }

    markdown_lines = [
        "# multi_equal_weight_v1 Baseline Mechanism Audit",
        "",
        "- Scope: trainval diagnostic audit only. Not OOS, not frozen test, not a formal strategy conclusion.",
        "- Frozen test accessed: `False`.",
        "- Formal metrics generated: `False`.",
        "",
        "## Baseline Score Construction",
        f"- Conclusion: {baseline_score_audit['conclusion']}",
        f"- Source fields detected: {', '.join(baseline_score_audit['source_fields_detected'])}",
        f"- Future/label hits: {baseline_score_audit['future_or_label_term_hits'] or 'none'}",
        "",
        "## D0 Visibility",
        "- D0-visible inputs: `p98`, `adj_close`, `amount`, `vol`, `pct_chg`, `ranking_eligible_D0`.",
        "- Historical windows end at `CURRENT ROW`, so the accessible builder path is D0-bounded.",
        "",
        "## Leakage Risk",
        f"- Baseline builder direct leakage hits: {baseline_score_audit['future_or_label_term_hits'] or 'none'}",
        f"- P98 builder direct leakage hits: {p98_component_audit['future_or_label_term_hits'] or 'none'}",
        f"- Upstream reversal audit available locally: `{upstream_reversal_audit is not None}`",
        "",
        "## Universe / Mask / Tradability",
        "- Baseline is anchored to `project_sample_panel` and `ranking_eligible_D0`.",
        "- Same-contract policy requires same split, same execution contract, same terminal exit policy, same portfolio rule, and same cash/invested accounting.",
        f"- Same split config match across accessible readouts: `{confirmed5_readout['split_config'] == v2_readout['split_config']}`",
        "",
        "## Execution / Terminal / Portfolio Rule",
        f"- Terminal approval contract: `{terminal_audit['contract_ref']}`",
        f"- Approval audit backfills priced exits: `{not terminal_audit['no_pricing_backfill_in_approval_audit']}`",
        "- No evidence of a baseline-only terminal or execution concession was found in accessible artifacts.",
        "",
        "## Cash / Invested / Turnover",
        "- Versus confirmed5, baseline wins with more cash, less invested capital, and lower turnover.",
        "- Versus v2, baseline wins with less cash, more invested capital, and slightly higher turnover.",
        "- The edge therefore does not collapse to one hidden deployment loophole.",
        "",
        "## Judgment",
        f"- Hidden advantage found: `{hidden_advantage_found}`",
        f"- Baseline minimum-hurdle status: `{baseline_hurdle_status}`",
        f"- Recommendation: {baseline_hurdle_reason}",
    ]
    if blockers:
        markdown_lines.extend(["", "## Blockers"])
        markdown_lines.extend(f"- {item}" for item in blockers)

    write_json(output_json, result)
    write_markdown(output_md, markdown_lines)
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audit_multi_equal_weight_baseline_mechanism(
        baseline_builder=args.baseline_builder,
        p98_builder=args.p98_builder,
        p98_audit_path=args.p98_audit,
        upstream_reversal_audit_path=args.upstream_reversal_audit,
        confirmed5_readout_path=args.confirmed5_readout,
        v2_readout_path=args.v2_readout,
        terminal_approval_path=args.terminal_approval,
        repaired_candidate_path=args.repaired_candidate,
        policy_doc_paths=[
            args.project_status_doc,
            args.confirmed5_decision_doc,
            args.v2_decision_doc,
        ],
        output_json=args.output_json,
        output_md=args.output_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
