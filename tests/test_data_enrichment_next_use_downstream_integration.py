from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


DOC_PATH = Path("docs/data_enrichment_next_use_downstream_integration.md")
DIVERGENCE_SCRIPT = Path("scripts/diagnose_baseline_divergence_exposure.py")
CLEAN_MODEL_SCRIPT = Path("scripts/diagnose_clean_baseline_family_model_edge.py")


def test_downstream_integration_decision_record_captures_policy_boundaries(repo_root: Path) -> None:
    text = (repo_root / DOC_PATH).read_text(encoding="utf-8")

    required_phrases = [
        "standalone validation tool into a downstream integration pattern",
        "requested_fields",
        "listing_age_trading_days",
        "newly_listed_flag",
        "Unknown fields",
        "`portfolio` or `screening`",
        "conditional_pass must be disclosed",
        "`declared_no_frozen_test_access=false`",
        "`allow_silent_fallback=true`",
        "does not approve alpha",
        "is not OOS",
        "Future clean baseline or challenger scripts",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_two_downstream_entrypoints_call_next_use_guardrail(repo_root: Path) -> None:
    for script in [DIVERGENCE_SCRIPT, CLEAN_MODEL_SCRIPT]:
        text = (repo_root / script).read_text(encoding="utf-8")
        assert "require_data_enrichment_next_use" in text
        assert "--enrichment-requested-fields" in text
        assert "--next-use-audit-path" in text
        assert "next_use_audit_path" in text


def test_downstream_script_fails_fast_on_blocked_field_before_data_reads(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "blocked_next_use_audit.json"
    output_json = tmp_path / "diagnosis.json"
    output_md = tmp_path / "diagnosis.md"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / DIVERGENCE_SCRIPT),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--next-use-audit-path",
            str(audit_path),
            "--enrichment-requested-fields",
            "listing_age_trading_days",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "blocked_fields_requested: listing_age_trading_days" in result.stderr
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == "blocked"
    assert audit["blocked_fields_requested"] == ["listing_age_trading_days"]
    assert not output_json.exists()
    assert not output_md.exists()
