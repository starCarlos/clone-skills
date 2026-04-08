#!/usr/bin/env python3
"""Validate workflow clone skill manifest and README consistency."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from validator_utils import emit_report, extract_bullet_field, load_json, validate_source_artifacts_block
    from workflow_blueprint_quality import analyze_blueprint
except ModuleNotFoundError:
    from scripts.validator_utils import emit_report, extract_bullet_field, load_json, validate_source_artifacts_block
    from scripts.workflow_blueprint_quality import analyze_blueprint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate workflow clone skill directory.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--readme", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()
def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    readme_path = Path(args.readme).resolve()
    if not manifest_path.exists() or not readme_path.exists():
        report = {
            "manifest_exists": manifest_path.exists(),
            "readme_exists": readme_path.exists(),
            "ok": False,
        }
        emit_report(report, as_json=args.format == "json")
        return 1
    manifest = load_json(manifest_path)
    readme = readme_path.read_text(encoding="utf-8")
    files = manifest.get("files", {}) if isinstance(manifest.get("files", {}), dict) else {}
    required_manifest_fields = ["type", "clone_name", "profession", "workflow_name", "draft_status", "quality_score", "files"]
    missing_manifest_fields = [field for field in required_manifest_fields if field not in manifest]
    required_files = ["skill_md", "clone_config", "workflow_blueprint"]
    missing_file_entries = [field for field in required_files if not str(files.get(field, "")).strip()]
    source_artifacts = validate_source_artifacts_block(
        manifest,
        required_keys=["clone_config", "workflow_blueprint", "mind_profile", "system_prompt", "workflow_task_state"],
        expected_file_map={
            "clone_config": str(files.get("clone_config", "")),
            "workflow_blueprint": str(files.get("workflow_blueprint", "")),
            "mind_profile": str(files.get("mind_profile", "")),
            "system_prompt": str(files.get("system_prompt", "")),
            "workflow_task_state": str(files.get("workflow_task_state", "")),
        },
    )
    blueprint_quality = analyze_blueprint(Path(str(files.get("workflow_blueprint", "")).strip()))
    report = {
        "manifest_complete": not missing_manifest_fields and not missing_file_entries,
        "manifest_exists": True,
        "readme_exists": True,
        "missing_manifest_fields": missing_manifest_fields,
        "missing_file_entries": missing_file_entries,
        "source_artifacts": source_artifacts,
        "blueprint_quality": blueprint_quality,
        "identity_consistent": (
            extract_bullet_field(readme, "clone_name") == str(manifest.get("clone_name", "")).strip()
            and extract_bullet_field(readme, "profession") == str(manifest.get("profession", "")).strip()
            and extract_bullet_field(readme, "workflow_name") == str(manifest.get("workflow_name", "")).strip()
            and extract_bullet_field(readme, "draft_status") == str(manifest.get("draft_status", "")).strip()
        ),
        "file_refs_present": all(Path(str(path)).exists() for path in files.values() if str(path).strip()),
    }
    report["ok"] = bool(
        report["manifest_complete"]
        and report["identity_consistent"]
        and report["file_refs_present"]
        and source_artifacts.get("ok", False)
        and blueprint_quality.get("ok", False)
    )
    emit_report(report, as_json=args.format == "json")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
