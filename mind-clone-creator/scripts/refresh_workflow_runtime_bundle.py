#!/usr/bin/env python3
"""Refresh a workflow runtime bundle from its manifest."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

try:
    from manifest_utils import apply_refresh_trigger, diff_refresh_cache, find_flag_value, has_flag, load_json
except ModuleNotFoundError:
    from scripts.manifest_utils import apply_refresh_trigger, diff_refresh_cache, find_flag_value, has_flag, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh workflow runtime bundle from manifest.")
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
    multi_turn = entrypoints.get("multi_turn", [])
    command = [
        "python3",
        str(workdir / "scripts" / "bootstrap_workflow_clone_runtime.py"),
        "--clone-config",
        str(manifest.get("clone_config", "")),
        "--workflow-blueprint",
        str(manifest.get("workflow_blueprint", "")),
        "--output-dir",
        str(output_dir),
    ]
    for flag in ["--mind-profile", "--system-prompt", "--profession", "--task-id", "--task-summary", "--workspace", "--artifact-dir", "--max-turns"]:
        value = find_flag_value(multi_turn, flag)
        if value:
            command.extend([flag, value])
    initial_run_mode = str(manifest.get("initial_run_mode", "")).strip()
    if initial_run_mode == "multi_turn":
        initial_input = find_flag_value(multi_turn, "--initial-input")
        if initial_input:
            command.extend(["--initial-input", initial_input, "--run-until-stop"])
    elif initial_run_mode == "single_turn":
        single_turn = entrypoints.get("single_turn", [])
        initial_input = find_flag_value(single_turn, "--input")
        if initial_input and initial_input != "<your-update>":
            command.extend(["--initial-input", initial_input])
    if has_flag(multi_turn, "--execute-safe"):
        command.append("--execute-safe")

    subprocess.run(command, cwd=workdir, check=True)
    apply_refresh_trigger(manifest_path, manifest, refresh_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
