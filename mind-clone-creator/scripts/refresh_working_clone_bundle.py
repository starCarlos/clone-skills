#!/usr/bin/env python3
"""Refresh an existing working-clone bundle from its manifest."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

try:
    from manifest_utils import (
        apply_refresh_trigger,
        diff_refresh_cache,
        find_flag_value,
        has_flag,
        load_json,
        propagate_refresh_to_manifest,
    )
except ModuleNotFoundError:
    from scripts.manifest_utils import (
        apply_refresh_trigger,
        diff_refresh_cache,
        find_flag_value,
        has_flag,
        load_json,
        propagate_refresh_to_manifest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh working clone bundle from manifest.")
    parser.add_argument("--manifest", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = load_json(manifest_path)
    workdir = Path(__file__).resolve().parent.parent
    output_dir = manifest_path.parent
    refresh_report = diff_refresh_cache(manifest)

    if (
        not bool(refresh_report.get("changed", False))
        and str(manifest.get("bundle_validation_path", "")).strip()
        and Path(str(manifest.get("bundle_validation_path", "")).strip()).exists()
    ):
        return 0

    personal_cmd = manifest.get("entrypoints", {}).get("build_personal_clone_skill", [])
    workflow_cmd = manifest.get("entrypoints", {}).get("build_workflow_pipeline", [])
    if not isinstance(personal_cmd, list):
        raise SystemExit("manifest missing build_personal_clone_skill entrypoint")

    command = [
        "python3",
        str(workdir / "scripts" / "bootstrap_working_clone_bundle.py"),
        "--interview",
        str(manifest.get("interview", "")),
        "--output-dir",
        str(output_dir),
        "--name",
        str(manifest.get("clone_name", "未命名分身")),
    ]

    creator = find_flag_value(personal_cmd, "--creator")
    profession = str(manifest.get("profession", "")).strip() or find_flag_value(personal_cmd, "--profession")
    mind_profile = find_flag_value(personal_cmd, "--mind-profile")
    system_prompt = find_flag_value(personal_cmd, "--system-prompt")
    eval_report = find_flag_value(personal_cmd, "--eval-report")
    research_digest = find_flag_value(personal_cmd, "--research-digest")
    timestamp = find_flag_value(personal_cmd, "--timestamp")

    if creator:
        command.extend(["--creator", creator])
    if profession:
        command.extend(["--profession", profession])
    if mind_profile:
        command.extend(["--mind-profile", mind_profile])
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])
    if eval_report:
        command.extend(["--eval-report", eval_report])
    if research_digest:
        command.extend(["--research-digest", research_digest])
    if timestamp:
        command.extend(["--timestamp", timestamp])

    steps = manifest.get("steps", {}) if isinstance(manifest.get("steps", {}), dict) else {}
    target_mode = str(manifest.get("target_mode", "")).strip()
    if not target_mode:
        target_mode = "persona-plus-workflow" if bool(steps.get("workflow_enabled", False)) else "persona-only"
    command.extend(["--target-mode", target_mode])

    if bool(steps.get("workflow_enabled", False)) and isinstance(workflow_cmd, list):
        work_unit = find_flag_value(workflow_cmd, "--work-unit")
        workflow_name = find_flag_value(workflow_cmd, "--workflow-name")
        known_context = find_flag_value(workflow_cmd, "--known-context")
        workflow_interview = find_flag_value(workflow_cmd, "--interview")
        stage_confirmation = find_flag_value(workflow_cmd, "--stage-confirmation")
        task_id = find_flag_value(workflow_cmd, "--task-id")
        task_summary = find_flag_value(workflow_cmd, "--task-summary")
        workspace = find_flag_value(workflow_cmd, "--workspace")
        artifact_dir = find_flag_value(workflow_cmd, "--artifact-dir")
        max_turns = find_flag_value(workflow_cmd, "--max-turns")
        initial_input = find_flag_value(workflow_cmd, "--initial-input")

        if work_unit:
            command.extend(["--work-unit", work_unit])
        if workflow_name:
            command.extend(["--workflow-name", workflow_name])
        if known_context:
            command.extend(["--known-context", known_context])
        if workflow_interview:
            command.extend(["--workflow-interview", workflow_interview])
        if stage_confirmation:
            command.extend(["--stage-confirmation", stage_confirmation])
        if task_id:
            command.extend(["--task-id", task_id])
        if task_summary:
            command.extend(["--task-summary", task_summary])
        if workspace:
            command.extend(["--workspace", workspace])
        if artifact_dir:
            command.extend(["--artifact-dir", artifact_dir])
        if max_turns:
            command.extend(["--max-turns", max_turns])
        if initial_input:
            command.extend(["--initial-input", initial_input])
        if has_flag(workflow_cmd, "--run-until-stop"):
            command.append("--run-until-stop")
        if has_flag(workflow_cmd, "--execute-safe"):
            command.append("--execute-safe")
        if has_flag(workflow_cmd, "--skip-runtime-bundle"):
            command.append("--skip-runtime-bundle")

    subprocess.run(command, cwd=workdir, check=True)
    apply_refresh_trigger(
        manifest_path,
        manifest,
        refresh_report
        if bool(refresh_report.get("changed", False))
        else {
            "changed": False,
            "reason": "bundle_validation_missing_or_stale",
            "changed_count": 0,
            "changed_groups": [],
            "changed_classes": [],
            "changed_class_counts": {},
            "changed_files": [],
        }
    )
    if bool(refresh_report.get("changed", False)):
        pipeline_manifest_path = output_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json"
        runtime_manifest_path = (
            output_dir
            / "workflow-blueprint-pipeline"
            / "workflow-runtime-bundle"
            / "workflow_runtime_manifest.json"
        )
        propagate_refresh_to_manifest(
            pipeline_manifest_path,
            refresh_report,
            reason="propagated_from_bundle_refresh",
        )
        propagate_refresh_to_manifest(
            runtime_manifest_path,
            refresh_report,
            reason="propagated_from_bundle_refresh",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
