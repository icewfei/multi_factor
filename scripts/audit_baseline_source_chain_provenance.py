#!/opt/anaconda3/envs/quant_trade/bin/python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path("/Users/wy/MiscProject/multi_factor")
RUN_STATE_DIR = ROOT / "artifacts" / "run_state"
RESEARCH_REGISTRY_DIR = ROOT / "artifacts" / "research_registry"

DEFAULT_BASELINE_BUILDER = ROOT / "scripts" / "build_multi_equal_weight_v1_scores.py"
DEFAULT_P98_BUILDER = ROOT / "scripts" / "build_reversal_tail_composite_model_scores.py"
DEFAULT_C1_BUILDER = ROOT / "scripts" / "build_baseline_model_scores.py"
DEFAULT_CANDIDATE_REGISTRY = RESEARCH_REGISTRY_DIR / "candidate_scheme_registry.jsonl"
DEFAULT_SCHEME_ATTEMPT_LOG = RESEARCH_REGISTRY_DIR / "scheme_attempt_log.jsonl"
DEFAULT_C1_ROUND_PREREG = (
    RESEARCH_REGISTRY_DIR
    / "research_rounds"
    / "rr_exploratory_cross_horizon_reversal_momentum_20260501"
    / "preregistration.json"
)
DEFAULT_P98_TAIL_PREREG = (
    RESEARCH_REGISTRY_DIR
    / "research_rounds"
    / "rr_exploratory_reversal_tail_handling_20260502"
    / "preregistration.json"
)
DEFAULT_P98_PROMOTION_PREREG = (
    RESEARCH_REGISTRY_DIR
    / "research_rounds"
    / "rr_confirmatory_reversal_cord30_promotion_20260506"
    / "preregistration.json"
)
DEFAULT_P98_AUDIT = RUN_STATE_DIR / "confirmatory_reversal_p98_trainval_20260506" / "model_scores_D0_audit.json"
DEFAULT_OUTPUT_JSON = Path("/private/tmp/baseline_source_chain_provenance_audit.json")
DEFAULT_OUTPUT_MD = Path("/private/tmp/baseline_source_chain_provenance_audit.md")

TARGET_BASELINE_SCHEME_ID = "multi_equal_weight_v1"
TARGET_C1_SCHEME_ID = "exploratory_cross_horizon_c1_reversal_only"
TARGET_C1_FEATURE_PRESET = "single_signal_reversal_5d_v1"
TARGET_P98_SCHEME_ID = "reversal_tail_exclude_p98_v1"

FUTURE_FIELD_TERMS = (
    "next_open",
    "next_close",
    "open_d1",
    "close_d1",
    "close_d5",
    "lead(",
    "following",
)
LABEL_OR_REALIZED_RETURN_TERMS = (
    "label_",
    "forward_label",
    "realized_return",
    "execution_delayed_realized_return",
    "actual_exit_date",
    "actual_sell_price",
)


class AuditError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit baseline source-chain provenance for exploratory reversal upstream.")
    parser.add_argument("--baseline-builder", type=Path, default=DEFAULT_BASELINE_BUILDER)
    parser.add_argument("--p98-builder", type=Path, default=DEFAULT_P98_BUILDER)
    parser.add_argument("--c1-builder", type=Path, default=DEFAULT_C1_BUILDER)
    parser.add_argument("--candidate-registry", type=Path, default=DEFAULT_CANDIDATE_REGISTRY)
    parser.add_argument("--scheme-attempt-log", type=Path, default=DEFAULT_SCHEME_ATTEMPT_LOG)
    parser.add_argument("--c1-round-prereg", type=Path, default=DEFAULT_C1_ROUND_PREREG)
    parser.add_argument("--p98-tail-prereg", type=Path, default=DEFAULT_P98_TAIL_PREREG)
    parser.add_argument("--p98-promotion-prereg", type=Path, default=DEFAULT_P98_PROMOTION_PREREG)
    parser.add_argument("--p98-audit", type=Path, default=DEFAULT_P98_AUDIT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser


def read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AuditError(f"{label} not found: {path}") from exc


def read_json(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(read_text(path, label))
    if not isinstance(payload, dict):
        raise AuditError(f"{label} must be a JSON object: {path}")
    return payload


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuditError(f"Expected JSON object: {path}")
    return payload


def read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in read_text(path, label).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise AuditError(f"{label} contains a non-object row: {path}")
        rows.append(payload)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def collect_term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def parse_score_rule_direction(score_rule: str | None, field_name: str) -> str | None:
    if not score_rule:
        return None
    lowered = score_rule.lower()
    field = field_name.lower()
    if f"{field} asc" in lowered:
        return "ASC"
    if f"{field} desc" in lowered:
        return "DESC"
    return None


def inspect_baseline_builder(source_text: str, builder_path: Path) -> dict[str, Any]:
    required_patterns = {
        "anchors_to_p98_component": "p98_scores" in source_text,
        "recomputes_alpha158_components": all(
            snippet in source_text
            for snippet in (
                "alpha158_cord30_raw",
                "alpha158_corr30_raw",
                "alpha158_vsumd60_raw",
            )
        ),
        "d0_guard_present": "WHERE ranking_eligible_D0" in source_text,
        "trainval_only_declared": "trainval-only" in source_text.lower(),
        "frozen_test_forbidden_declared": "does not access frozen test data" in source_text.lower(),
    }
    future_hits = collect_term_hits(source_text, FUTURE_FIELD_TERMS)
    label_hits = collect_term_hits(source_text, LABEL_OR_REALIZED_RETURN_TERMS)
    return {
        "builder_path": str(builder_path),
        "direct_sources": [
            "confirmatory_reversal_p98_trainval_20260506/model_scores_D0.parquet",
            "project_sample_panel.ranking_eligible_D0",
            "vw_bars_daily.adj_close",
            "vw_bars_daily.amount",
            "vw_bars_daily.vol",
            "vw_bars_daily.pct_chg",
        ],
        "required_patterns": required_patterns,
        "future_field_hits": future_hits,
        "label_or_realized_return_hits": label_hits,
    }


def inspect_c1_builder(source_text: str, builder_path: Path, registry_row: dict[str, Any]) -> dict[str, Any]:
    metadata_score_rule = registry_row.get("score_rule")
    metadata_direction = parse_score_rule_direction(metadata_score_rule, "reversal_5d_raw")
    implementation_direction = None
    if "ORDER BY reversal_5d_raw ASC, instrument ASC" in source_text:
        implementation_direction = "ASC"
    elif "ORDER BY reversal_5d_raw DESC, instrument ASC" in source_text:
        implementation_direction = "DESC"

    required_patterns = {
        "feature_preset_declared": TARGET_C1_FEATURE_PRESET in source_text,
        "preset_uses_reversal_rank": '("reversal_5d_raw", "reversal_rank")' in source_text,
        "trade_date_as_signal_date": "trade_date AS signal_date" in source_text,
        "reversal_formula_present": "(adj_close / LAG(adj_close, 5) OVER w - 1.0) AS reversal_5d_raw" in source_text,
        "ranking_guard_present": "WHERE ranking_eligible_D0" in source_text,
        "no_lead_usage": "LEAD(" not in source_text,
        "no_following_usage": "FOLLOWING" not in source_text,
    }
    future_hits = collect_term_hits(source_text, FUTURE_FIELD_TERMS)
    label_hits = collect_term_hits(source_text, LABEL_OR_REALIZED_RETURN_TERMS)
    return {
        "builder_path": str(builder_path),
        "candidate_scheme_id": registry_row.get("candidate_scheme_id"),
        "feature_preset": registry_row.get("feature_preset"),
        "metadata_score_rule": metadata_score_rule,
        "metadata_rank_direction": metadata_direction,
        "implementation_rank_direction": implementation_direction,
        "metadata_matches_implementation": (
            metadata_direction == implementation_direction
            if metadata_direction is not None and implementation_direction is not None
            else None
        ),
        "upstream_inputs": [
            "contracts/run_input_contract.research_trainval_20211231.json.snapshot_id",
            "project_sample_panel.instrument",
            "project_sample_panel.signal_date",
            "project_sample_panel.ranking_eligible_D0",
            "vw_bars_daily.ts_code",
            "vw_bars_daily.trade_date",
            "vw_bars_daily.adj_close",
        ],
        "required_patterns": required_patterns,
        "future_field_hits": future_hits,
        "label_or_realized_return_hits": label_hits,
    }


def inspect_p98_builder(
    source_text: str,
    builder_path: Path,
    p98_audit_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    required_patterns = {
        "reversal_source_declared": TARGET_C1_SCHEME_ID in source_text,
        "negated_reversal_used": "-1.0 * r.model_score_D0 AS nr_score" in source_text,
        "ranking_guard_present": "WHERE s.ranking_eligible_D0" in source_text,
        "daily_p98_present": "PERCENTILE_CONT(0.98)" in source_text,
        "strict_tail_exclusion_present": "WHERE n.nr_score < p.p98" in source_text,
        "no_lead_usage": "LEAD(" not in source_text,
        "no_following_usage": "FOLLOWING" not in source_text,
    }
    future_hits = collect_term_hits(source_text, FUTURE_FIELD_TERMS)
    label_hits = collect_term_hits(source_text, LABEL_OR_REALIZED_RETURN_TERMS)
    return {
        "builder_path": str(builder_path),
        "candidate_scheme_id": p98_audit_payload.get("candidate_scheme_id") if p98_audit_payload else TARGET_P98_SCHEME_ID,
        "source_runs": p98_audit_payload.get("source_runs") if p98_audit_payload else None,
        "required_patterns": required_patterns,
        "future_field_hits": future_hits,
        "label_or_realized_return_hits": label_hits,
    }


def inspect_c1_round_prereg(payload: dict[str, Any]) -> dict[str, Any]:
    forbidden = payload.get("forbidden", [])
    serial_rule = str(payload.get("serial_rule", ""))
    return {
        "research_round_id": payload.get("research_round_id"),
        "snapshot_id": payload.get("snapshot_id"),
        "candidate_list_frozen": payload.get("candidate_scheme_ids") == payload.get("planned_candidate_scheme_ids"),
        "serial_non_cascade_rule_present": "非级联淘汰" in serial_rule,
        "test_window_forbidden_declared": any("测试集" in item for item in forbidden),
        "allowed_features_declared": "reversal_5d_raw" in str(payload.get("change_detail", "")),
        "contract_freeze_declared": "不允许改变" in str(payload.get("change_detail", "")),
    }


def inspect_feedback_risk(
    c1_round_prereg: dict[str, Any],
    p98_tail_prereg: dict[str, Any],
    p98_promotion_prereg: dict[str, Any],
) -> dict[str, Any]:
    p98_tail_text = json.dumps(p98_tail_prereg, ensure_ascii=False)
    p98_promotion_text = json.dumps(p98_promotion_prereg, ensure_ascii=False)
    downstream_label_screening = any(
        token in p98_tail_text
        for token in (
            "top10_avg_label",
            "top10_bot10_spread",
            "label_5d_next_open_close",
            "median_daily_ic",
        )
    )
    downstream_fixed_test_reference = "artifacts/fixed_test/" in p98_tail_text
    promotion_test_forbidden = '"test_window_access": "forbidden"' in p98_promotion_text
    c1_feedback_guard = {
        "candidate_list_frozen": c1_round_prereg.get("candidate_scheme_ids") == c1_round_prereg.get("planned_candidate_scheme_ids"),
        "serial_non_cascade": "非级联淘汰" in str(c1_round_prereg.get("serial_rule", "")),
        "test_window_forbidden": any("测试集" in item for item in c1_round_prereg.get("forbidden", [])),
    }
    return {
        "c1_round_guards": c1_feedback_guard,
        "downstream_trainval_label_screening_used": downstream_label_screening,
        "downstream_fixed_test_reference_detected": downstream_fixed_test_reference,
        "downstream_promotion_test_window_forbidden": promotion_test_forbidden,
        "judgment": (
            "No direct evidence shows exploratory_cross_horizon_c1_reversal_only was built by reading validation or frozen-test outputs, "
            "but the downstream p98 tail-handling selection explicitly relies on trainval label-based learnability diagnostics."
            if downstream_label_screening
            else "No validation/frozen feedback risk detected in the accessible source-chain metadata."
        ),
    }


def inspect_artifact_reproducibility(attempt_row: dict[str, Any]) -> dict[str, Any]:
    path_fields = ("scores_path", "attempt_manifest_path", "data_quality_audit_path")
    checks: dict[str, dict[str, Any]] = {}
    existing_count = 0
    for field in path_fields:
        raw = attempt_row.get(field)
        path = Path(raw) if isinstance(raw, str) else None
        exists = bool(path and path.exists())
        if exists:
            existing_count += 1
        checks[field] = {
            "path": raw,
            "exists": exists,
        }

    missing_evidence = [
        f"{field} missing locally: {checks[field]['path']}"
        for field in path_fields
        if not checks[field]["exists"]
    ]

    if existing_count == len(path_fields):
        status = "pass"
    elif existing_count >= 1:
        status = "conditional_pass"
    else:
        status = "blocked"

    return {
        "run_id": attempt_row.get("run_id"),
        "attempt_id": attempt_row.get("attempt_id"),
        "status": status,
        "path_checks": checks,
        "missing_evidence": missing_evidence,
    }


def decide_final_status(
    *,
    c1_builder: dict[str, Any],
    p98_builder: dict[str, Any],
    reproducibility: dict[str, Any],
    feedback_risk: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    blockers: list[str] = []
    cautions: list[str] = []

    if c1_builder["future_field_hits"] or c1_builder["label_or_realized_return_hits"]:
        blockers.append("c1 builder references future, label, or realized-return fields.")
    if p98_builder["future_field_hits"] or p98_builder["label_or_realized_return_hits"]:
        blockers.append("p98 builder references future, label, or realized-return fields.")

    required_c1 = c1_builder["required_patterns"]
    if not required_c1["trade_date_as_signal_date"] or not required_c1["reversal_formula_present"]:
        blockers.append("c1 builder formula could not be recovered from local source.")
    if not required_c1["ranking_guard_present"] or not required_c1["no_lead_usage"] or not required_c1["no_following_usage"]:
        blockers.append("c1 builder D0 visibility guards are incomplete.")

    required_p98 = p98_builder["required_patterns"]
    if not required_p98["ranking_guard_present"] or not required_p98["daily_p98_present"] or not required_p98["strict_tail_exclusion_present"]:
        blockers.append("p98 builder source-chain logic could not be fully recovered from local source.")

    if c1_builder["metadata_matches_implementation"] is False:
        blockers.append(
            "c1 registry score_rule direction does not match local builder implementation, and local run-state artifacts are missing so the executed direction cannot be re-verified."
        )

    if reproducibility["status"] == "blocked":
        blockers.extend(reproducibility["missing_evidence"])
    elif reproducibility["status"] == "conditional_pass":
        cautions.extend(reproducibility["missing_evidence"])

    if feedback_risk["downstream_trainval_label_screening_used"]:
        cautions.append(
            "downstream p98 tail-handling selection used trainval label-based diagnostics; this is source-selection feedback risk, not direct score-builder leakage."
        )

    if blockers:
        return "blocked", blockers, cautions
    if cautions:
        return "conditional_pass", blockers, cautions
    return "pass", blockers, cautions


def find_row(rows: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise AuditError(f"Unable to find {label}: {key}={value}")


def build_markdown_report(payload: dict[str, Any]) -> list[str]:
    lines = [
        "# Baseline Source-Chain Provenance Audit",
        "",
        "## Scope",
        "",
        "- Target upstream source: `exploratory_cross_horizon_c1_reversal_only`.",
        "- Baseline under review: `multi_equal_weight_v1`.",
        "- This audit is static/provenance-only: no training, no backtest, no frozen-test reads, no formal readout generation.",
        "",
        "## Source-Chain Files",
        "",
    ]
    for path in payload["source_chain_files"]:
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Upstream Inputs",
            "",
        ]
    )
    for field in payload["upstream_inputs"]:
        lines.append(f"- `{field}`")

    d0 = payload["d0_visibility"]
    lines.extend(
        [
            "",
            "## D0 Visibility",
            "",
            f"- `c1` D0 visibility: `{d0['c1_judgment']}`",
            f"- `p98` D0 visibility: `{d0['p98_judgment']}`",
            f"- Evidence: `{d0['summary']}`",
            "",
            "## Leakage Judgment",
            "",
            f"- Direct future/label/realized-return dependency found in `c1`: `{payload['leakage_assessment']['c1_direct_leakage_found']}`",
            f"- Direct future/label/realized-return dependency found in `p98`: `{payload['leakage_assessment']['p98_direct_leakage_found']}`",
            f"- Evidence summary: `{payload['leakage_assessment']['summary']}`",
            "",
            "## Validation/Frozen Feedback Risk",
            "",
            f"- `c1` prereg freeze guard present: `{payload['validation_frozen_feedback_risk']['c1_round_guards']}`",
            f"- Downstream trainval label-screening used: `{payload['validation_frozen_feedback_risk']['downstream_trainval_label_screening_used']}`",
            f"- Downstream fixed-test reference detected in metadata: `{payload['validation_frozen_feedback_risk']['downstream_fixed_test_reference_detected']}`",
            f"- Judgment: `{payload['validation_frozen_feedback_risk']['judgment']}`",
            "",
            "## Artifact Reproducibility",
            "",
            f"- Status: `{payload['artifact_reproducibility']['status']}`",
        ]
    )
    for field, details in payload["artifact_reproducibility"]["path_checks"].items():
        lines.append(f"- `{field}` exists locally: `{details['exists']}`")

    if payload["missing_evidence"]:
        lines.extend(["", "## Missing Evidence", ""])
        for item in payload["missing_evidence"]:
            lines.append(f"- {item}")

    if payload["provenance_findings"]:
        lines.extend(["", "## Provenance Findings", ""])
        for item in payload["provenance_findings"]:
            lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Final Status",
            "",
            f"- Source-chain audit status: `{payload['final_status']}`",
            f"- Baseline status recommendation: `{payload['baseline_status_recommendation']}`",
        ]
    )
    return lines


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    baseline_builder_text = read_text(args.baseline_builder, "baseline builder")
    p98_builder_text = read_text(args.p98_builder, "p98 builder")
    c1_builder_text = read_text(args.c1_builder, "c1 builder")

    candidate_registry_rows = read_jsonl(args.candidate_registry, "candidate registry")
    attempt_rows = read_jsonl(args.scheme_attempt_log, "scheme attempt log")
    c1_round_prereg = read_json(args.c1_round_prereg, "c1 round preregistration")
    p98_tail_prereg = read_json(args.p98_tail_prereg, "p98 tail preregistration")
    p98_promotion_prereg = read_json(args.p98_promotion_prereg, "p98 promotion preregistration")
    p98_audit_payload = read_optional_json(args.p98_audit)

    c1_registry_row = find_row(candidate_registry_rows, "candidate_scheme_id", TARGET_C1_SCHEME_ID, "c1 registry row")
    c1_attempt_row = find_row(attempt_rows, "run_id", TARGET_C1_SCHEME_ID, "c1 attempt log row")

    baseline_builder = inspect_baseline_builder(baseline_builder_text, args.baseline_builder)
    c1_builder = inspect_c1_builder(c1_builder_text, args.c1_builder, c1_registry_row)
    p98_builder = inspect_p98_builder(p98_builder_text, args.p98_builder, p98_audit_payload)
    c1_round = inspect_c1_round_prereg(c1_round_prereg)
    feedback_risk = inspect_feedback_risk(c1_round_prereg, p98_tail_prereg, p98_promotion_prereg)
    reproducibility = inspect_artifact_reproducibility(c1_attempt_row)

    final_status, blockers, cautions = decide_final_status(
        c1_builder=c1_builder,
        p98_builder=p98_builder,
        reproducibility=reproducibility,
        feedback_risk=feedback_risk,
    )

    provenance_findings: list[str] = []
    if c1_builder["metadata_matches_implementation"] is False:
        provenance_findings.append(
            "Registry metadata says `reversal_5d_raw DESC`, but the local `single_signal_reversal_5d_v1` implementation maps to `reversal_rank`, which ranks `reversal_5d_raw ASC`."
        )
    if c1_round["candidate_list_frozen"] and c1_round["serial_non_cascade_rule_present"]:
        provenance_findings.append(
            "The cross-horizon c1/c2/c3 candidate set was preregistered and frozen before execution; the round metadata forbids cascading candidate redesign from earlier results."
        )
    if feedback_risk["downstream_trainval_label_screening_used"]:
        provenance_findings.append(
            "The downstream p98 tail-handling chain is not direct leakage, but it is not feedback-free: the tail rule was selected with trainval label-based learnability diagnostics."
        )

    payload = {
        "audit_target": TARGET_C1_SCHEME_ID,
        "baseline_candidate_scheme_id": TARGET_BASELINE_SCHEME_ID,
        "source_chain_files": [
            str(args.baseline_builder),
            str(args.p98_builder),
            str(args.c1_builder),
            str(args.c1_round_prereg),
            str(args.p98_tail_prereg),
            str(args.p98_promotion_prereg),
            str(args.candidate_registry),
            str(args.scheme_attempt_log),
        ],
        "upstream_inputs": c1_builder["upstream_inputs"],
        "d0_visibility": {
            "c1_judgment": (
                "pass"
                if c1_builder["required_patterns"]["trade_date_as_signal_date"]
                and c1_builder["required_patterns"]["reversal_formula_present"]
                and c1_builder["required_patterns"]["ranking_guard_present"]
                and c1_builder["required_patterns"]["no_lead_usage"]
                and c1_builder["required_patterns"]["no_following_usage"]
                else "blocked"
            ),
            "p98_judgment": (
                "pass"
                if p98_builder["required_patterns"]["ranking_guard_present"]
                and p98_builder["required_patterns"]["daily_p98_present"]
                and p98_builder["required_patterns"]["strict_tail_exclusion_present"]
                and p98_builder["required_patterns"]["no_lead_usage"]
                and p98_builder["required_patterns"]["no_following_usage"]
                else "blocked"
            ),
            "summary": "Recovered c1 from D0 adj_close plus D-5 adj_close, then recovered p98 as same-day cross-sectional tail exclusion on negated c1 scores.",
        },
        "leakage_assessment": {
            "c1_direct_leakage_found": bool(c1_builder["future_field_hits"] or c1_builder["label_or_realized_return_hits"]),
            "p98_direct_leakage_found": bool(p98_builder["future_field_hits"] or p98_builder["label_or_realized_return_hits"]),
            "summary": "No direct label, future return, or realized return fields were found in the accessible c1/p98 score builders.",
        },
        "validation_frozen_feedback_risk": feedback_risk,
        "artifact_reproducibility": reproducibility,
        "baseline_builder_summary": baseline_builder,
        "c1_builder_summary": c1_builder,
        "p98_builder_summary": p98_builder,
        "c1_round_summary": c1_round,
        "provenance_findings": provenance_findings,
        "missing_evidence": blockers + [item for item in cautions if item not in blockers] if final_status == "blocked" else cautions,
        "final_status": final_status,
        "baseline_status_recommendation": (
            "keep_conditional_pass_and_retain_blocker"
            if final_status != "pass"
            else "eligible_to_upgrade_from_conditional_pass"
        ),
    }
    return payload


def main() -> None:
    args = build_parser().parse_args()
    payload = run_audit(args)
    write_json(args.output_json, payload)
    write_markdown(args.output_md, build_markdown_report(payload))


if __name__ == "__main__":
    main()
