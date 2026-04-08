#!/usr/bin/env python3
"""End-to-end builder: markdown artifacts -> clone_config -> personal clone skill."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(cmd: list[str], workdir: Path) -> None:
    subprocess.run(cmd, cwd=workdir, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a personal clone skill end-to-end from markdown artifacts."
    )
    parser.add_argument("--interview", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--creator", default="")
    parser.add_argument("--profession", default="")
    parser.add_argument("--mind-profile")
    parser.add_argument("--system-prompt")
    parser.add_argument("--eval-report")
    parser.add_argument("--research-digest")
    parser.add_argument("--workflow-blueprint")
    parser.add_argument("--interview-state")
    parser.add_argument("--release-target", choices=["draft", "final"], default="draft")
    parser.add_argument("--timestamp")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    tmp_json = Path(args.output_dir).parent / (Path(args.output_dir).name + ".input.json")
    tmp_yaml = Path(args.output_dir).parent / (Path(args.output_dir).name + ".yaml")

    if args.interview_state:
        validation_cmd = [
            "python3",
            str(workdir / "scripts/validate_clone_interview_state.py"),
            "--input",
            args.interview_state,
            "--format",
            "json",
        ]
        proc = subprocess.run(validation_cmd, cwd=workdir, check=True, capture_output=True, text=True)
        report = json.loads(proc.stdout)
        if args.release_target == "final" and not report.get("final_ready", False):
            raise SystemExit("interview state is not final-ready; use --release-target draft or finalize interview sections")

    extract_cmd = [
        "python3",
        str(workdir / "scripts/extract_clone_draft.py"),
        "--interview",
        args.interview,
        "--output",
        str(tmp_json),
        "--name",
        args.name,
        "--creator",
        args.creator,
        "--profession",
        args.profession,
    ]
    if args.mind_profile:
        extract_cmd += ["--mind-profile", args.mind_profile]
    if args.system_prompt:
        extract_cmd += ["--system-prompt", args.system_prompt]
    if args.eval_report:
        extract_cmd += ["--eval-report", args.eval_report]
    if args.research_digest:
        extract_cmd += ["--research-digest", args.research_digest]
    if args.timestamp:
        extract_cmd += ["--timestamp", args.timestamp]
    run(extract_cmd, workdir)

    build_yaml_cmd = [
        "python3",
        str(workdir / "scripts/build_clone_config.py"),
        "--input",
        str(tmp_json),
        "--output",
        str(tmp_yaml),
    ]
    if args.timestamp:
        build_yaml_cmd += ["--timestamp", args.timestamp]
    run(build_yaml_cmd, workdir)

    pack_cmd = [
        "python3",
        str(workdir / "scripts/build_personal_clone_skill.py"),
        "--clone-config",
        str(tmp_yaml),
        "--output-dir",
        args.output_dir,
    ]
    if args.mind_profile:
        pack_cmd += ["--mind-profile", args.mind_profile]
    if args.system_prompt:
        pack_cmd += ["--system-prompt", args.system_prompt]
    if args.eval_report:
        pack_cmd += ["--eval-report", args.eval_report]
    if args.research_digest:
        pack_cmd += ["--research-digest", args.research_digest]
    if args.workflow_blueprint:
        pack_cmd += ["--workflow-blueprint", args.workflow_blueprint]
    run(pack_cmd, workdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
