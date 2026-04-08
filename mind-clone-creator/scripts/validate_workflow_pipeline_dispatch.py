#!/usr/bin/env python3
"""Validate consistency across workflow pipeline manifest and README."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from validator_utils import emit_report, extract_readme_command, load_json
except ModuleNotFoundError:
    from scripts.validator_utils import emit_report, extract_readme_command, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate workflow pipeline dispatch consistency.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--readme", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(Path(args.manifest).resolve())
    readme_command = extract_readme_command(Path(args.readme).resolve())
    contract = manifest.get("recommended_next_command", {}) if isinstance(manifest.get("recommended_next_command", {}), dict) else {}
    required_fields = ["mode", "label", "command", "scope", "section", "manual_edit_required", "priority"]
    missing_fields = [field for field in required_fields if not str(contract.get(field, "")).strip()]
    manifest_command = str(contract.get("command", "")).strip()
    report = {
        "recommended_command_consistent": manifest_command == readme_command,
        "contract_complete": not missing_fields,
        "missing_fields": missing_fields,
        "command_style_consistent": str(manifest.get("command_style", "")).strip() == "repo_relative_scripts",
        "manifest_command": manifest_command,
        "readme_command": readme_command,
        "ok": manifest_command == readme_command and not missing_fields and str(manifest.get("command_style", "")).strip() == "repo_relative_scripts",
    }
    emit_report(report, as_json=args.format == "json")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
