#!/usr/bin/env python3
"""Refresh a workflow-blueprint pipeline bundle from its manifest."""

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
    parser = argparse.ArgumentParser(description="Refresh workflow blueprint pipeline from manifest.")
    parser.add_argument("--manifest", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = load_json(manifest_path)
    workdir = Path(__file__).resolve().parent.parent
    output_dir = manifest_path.parent
    refresh_report = diff_refresh_cache(manifest)

    if not bool(refresh_report.get("changed", False)):
        return 0

    entrypoints = manifest.get("entrypoints", {}) if isinstance(manifest.get("entrypoints", {}), dict) else {}
    runtime_cmd = entrypoints.get("build_workflow_runtime_bundle", [])
    command = [
        "python3",
        str(workdir / "scripts" / "bootstrap_workflow_blueprint.py"),
        "--work-unit",
        str(manifest.get("work_unit", "")),
        "--output-dir",
        str(output_dir),
        "--known-context",
        str(manifest.get("known_context", "暂无")),
    ]

    workflow_name = str(manifest.get("workflow_name", "")).strip()
    clone_config = str(manifest.get("clone_config", "")).strip()
    interview = str(manifest.get("interview", "")).strip()
    stage_confirmation = str(manifest.get("stage_confirmation", "")).strip()
    if workflow_name:
        command.extend(["--workflow-name", workflow_name])
    if clone_config:
        command.extend(["--clone-config", clone_config])
    if interview:
        command.extend(["--interview", interview])
    if stage_confirmation and Path(stage_confirmation).exists():
        command.extend(["--stage-confirmation", stage_confirmation])

    for flag in ["--mind-profile", "--system-prompt", "--profession", "--initial-input", "--task-id", "--task-summary", "--workspace", "--artifact-dir", "--max-turns"]:
        value = find_flag_value(runtime_cmd, flag)
        if value:
            command.extend([flag, value])
    for flag in ["--run-until-stop", "--execute-safe"]:
        if has_flag(runtime_cmd, flag):
            command.append(flag)

    subprocess.run(command, cwd=workdir, check=True)
    apply_refresh_trigger(manifest_path, manifest, refresh_report)
    runtime_manifest_path = output_dir / "workflow-runtime-bundle" / "workflow_runtime_manifest.json"
    propagate_refresh_to_manifest(
        runtime_manifest_path,
        refresh_report,
        reason="propagated_from_pipeline_refresh",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
