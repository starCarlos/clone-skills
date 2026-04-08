#!/usr/bin/env python3
"""Validate release readiness for a built workflow clone skill directory."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from workflow_blueprint_quality import analyze_blueprint
except ModuleNotFoundError:
    from scripts.workflow_blueprint_quality import analyze_blueprint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate workflow clone release package.")
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = Path(args.skill_dir).resolve()
    clone_config = skill_dir / "clone_config.yaml"
    workflow_blueprint = skill_dir / "workflow_blueprint.md"
    if not clone_config.exists():
        raise SystemExit(f"clone_config.yaml not found: {clone_config}")
    workdir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        ["python3", str(workdir / "scripts" / "validate_clone_config.py"), "--input", str(clone_config), "--format", "json"],
        cwd=workdir,
        check=True,
        capture_output=True,
        text=True,
    )
    clone_report = json.loads(proc.stdout)
    current_status = str(clone_report.get("current_draft_status", "")).strip()
    required_files = ["SKILL.md", "clone_config.yaml", "workflow_blueprint.md"]
    missing_required_files = [name for name in required_files if not (skill_dir / name).exists()]
    missing_final_files = [
        name for name in ["mind_profile.md", "system_prompt.md"] if current_status == "final" and not (skill_dir / name).exists()
    ]
    blueprint_quality = analyze_blueprint(workflow_blueprint)
    report = {
        "skill_dir": str(skill_dir),
        "current_draft_status": current_status,
        "recommended_draft_status": str(clone_report.get("recommended_draft_status", "")).strip(),
        "clone_config_final_ready": bool(clone_report.get("final_ready", False)),
        "workflow_blueprint_present": workflow_blueprint.exists(),
        "workflow_blueprint_quality": blueprint_quality,
        "missing_required_files": missing_required_files,
        "missing_final_files": missing_final_files,
        "release_valid": (
            not missing_required_files
            and bool(blueprint_quality.get("ok", False))
            and ((current_status != "final") or (bool(clone_report.get("final_ready", False)) and not missing_final_files))
        ),
        "clone_config_report": clone_report,
    }
    report["ok"] = bool(report["release_valid"])
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
