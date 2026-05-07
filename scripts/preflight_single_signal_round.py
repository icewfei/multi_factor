#!/opt/anaconda3/envs/quant_trade/bin/python
"""
Run the preregistration intake gate before a new single-signal discovery round
is allowed to start.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path("/Users/wy/MiscProject/multi_factor")
CHECKER = ROOT / "scripts" / "check_preregistration_intake.py"
PYTHON = "/opt/anaconda3/envs/quant_trade/bin/python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight a single-signal discovery round before execution."
    )
    parser.add_argument("--prereg-path", default=None, help="Path to preregistration.json")
    parser.add_argument("--research-round-id", default=None, help="Round id used to resolve preregistration path")
    return parser.parse_args()


def build_checker_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [PYTHON, CHECKER.as_posix()]
    if args.prereg_path:
        cmd += ["--prereg-path", args.prereg_path]
    elif args.research_round_id:
        cmd += ["--research-round-id", args.research_round_id]
    else:
        raise ValueError("Either --prereg-path or --research-round-id must be provided.")
    return cmd


def main() -> None:
    args = parse_args()
    cmd = build_checker_cmd(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    stdout = result.stdout.strip()
    if stdout:
        print(stdout)

    if result.returncode != 0:
        sys.exit(result.returncode)

    report = json.loads(stdout) if stdout else {}
    prereg_path = report.get("prereg_path", args.prereg_path or args.research_round_id)
    output = {
        "status": "preflight_passed",
        "message": "single-signal discovery prereg passed intake rules and is ready for execution",
        "prereg_path": prereg_path,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
