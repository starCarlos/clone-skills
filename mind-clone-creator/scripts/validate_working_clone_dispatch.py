#!/usr/bin/env python3
"""Validate consistency across working-clone manifest, README, and until-final summary."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from validator_utils import emit_report, extract_readme_command, load_json
except ModuleNotFoundError:
    from scripts.validator_utils import emit_report, extract_readme_command, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate working-clone dispatch consistency.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--readme", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(Path(args.manifest).resolve())
    summary = load_json(Path(args.summary).resolve())
    readme_command = extract_readme_command(Path(args.readme).resolve())

    contract = manifest.get("recommended_next_command", {}) if isinstance(manifest.get("recommended_next_command", {}), dict) else {}
    summary_contract = (
        summary.get("recommended_next_command", {})
        if isinstance(summary.get("recommended_next_command", {}), dict)
        else {}
    )
    required_fields = ["mode", "label", "command", "scope", "section", "manual_edit_required", "priority"]
    missing_manifest_fields = [field for field in required_fields if not str(contract.get(field, "")).strip()]
    missing_summary_fields = [field for field in required_fields if not str(summary_contract.get(field, "")).strip()]
    manifest_command = str(contract.get("command", "")).strip()
    summary_command = str(summary_contract.get("command", "")).strip()
    manifest_counts = manifest.get("pending_interview_action_group_counts", {})
    summary_groups = summary.get("pending_interview_action_groups", {})
    summary_counts = {
        "current_executable_now_count": len(summary_groups.get("current_executable_now", [])),
        "requires_manual_edit_first_count": len(summary_groups.get("requires_manual_edit_first", [])),
        "needs_content_edit_count": len(summary_groups.get("needs_content_edit", [])),
        "needs_human_confirmation_count": len(summary_groups.get("needs_human_confirmation", [])),
        "needs_build_step_count": len(summary_groups.get("needs_build_step", [])),
    }
    report = {
        "recommended_command_consistent": manifest_command == summary_command == readme_command,
        "group_counts_consistent": manifest_counts == summary_counts,
        "manifest_contract_complete": not missing_manifest_fields,
        "summary_contract_complete": not missing_summary_fields,
        "missing_manifest_fields": missing_manifest_fields,
        "missing_summary_fields": missing_summary_fields,
        "command_style_consistent": str(manifest.get("command_style", "")).strip() == "repo_relative_scripts",
        "manifest_command": manifest_command,
        "summary_command": summary_command,
        "readme_command": readme_command,
        "manifest_counts": manifest_counts,
        "summary_counts": summary_counts,
        "ok": (
            (manifest_command == summary_command == readme_command)
            and (manifest_counts == summary_counts)
            and not missing_manifest_fields
            and not missing_summary_fields
            and str(manifest.get("command_style", "")).strip() == "repo_relative_scripts"
        ),
    }
    emit_report(report, as_json=args.format == "json")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
