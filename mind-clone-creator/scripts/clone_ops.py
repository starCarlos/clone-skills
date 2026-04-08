#!/usr/bin/env python3
"""Unified CLI entrypoint for common clone-stack operations."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    from stack_discovery import (
        build_stack_summary,
        build_stack_validation_command,
        diff_stack_summaries,
        discover_current_stack_from_bundle_report,
        discover_latest_coherent_stack_report,
        load_stack_summary,
        render_stack_summary_text,
    )
except ModuleNotFoundError:
    from scripts.stack_discovery import (
        build_stack_summary,
        build_stack_validation_command,
        diff_stack_summaries,
        discover_current_stack_from_bundle_report,
        discover_latest_coherent_stack_report,
        load_stack_summary,
        render_stack_summary_text,
    )


DEFAULT_SAMPLE_SUMMARY = "/tmp/mind-clone-sample-stack/SAMPLE_STACK_SUMMARY.json"

USAGE = """usage:
  python3 scripts/clone_ops.py bootstrap working-bundle ...
  python3 scripts/clone_ops.py bootstrap workflow-pipeline ...
  python3 scripts/clone_ops.py bootstrap workflow-runtime ...
  python3 scripts/clone_ops.py bootstrap sample-stack [--output-root PATH]
  python3 scripts/clone_ops.py refresh working-bundle ...
  python3 scripts/clone_ops.py refresh workflow-pipeline ...
  python3 scripts/clone_ops.py refresh workflow-runtime ...
  python3 scripts/clone_ops.py validate stack ...
  python3 scripts/clone_ops.py validate latest-stack [--stack-summary PATH] [--summary-json PATH]
  python3 scripts/clone_ops.py validate working-dispatch ...
  python3 scripts/clone_ops.py validate workflow-pipeline-dispatch ...
  python3 scripts/clone_ops.py validate workflow-runtime-dispatch ...
  python3 scripts/clone_ops.py validate workflow-blueprint --input PATH
  python3 scripts/clone_ops.py validate personal-skill ...
  python3 scripts/clone_ops.py validate workflow-skill ...
  python3 scripts/clone_ops.py validate personal-release ...
  python3 scripts/clone_ops.py validate workflow-release ...
  python3 scripts/clone_ops.py validate release-readiness [--output-root PATH] [--summary-json PATH]
  python3 scripts/clone_ops.py doctor sample-stack [--sample-summary PATH] [--explain] [--summary-json PATH]
  python3 scripts/clone_ops.py doctor latest-stack [--stack-summary PATH] [--explain] [--summary-json PATH]
  python3 scripts/clone_ops.py doctor current-stack --bundle-dir PATH [--explain] [--summary-json PATH]
  python3 scripts/clone_ops.py explain latest-stack [--stack-summary PATH] [--summary-json PATH]
  python3 scripts/clone_ops.py diff stack (--left-summary PATH --right-summary PATH | --left-bundle-dir PATH --right-bundle-dir PATH)
"""


ROUTE = {
    ("bootstrap", "working-bundle"): "bootstrap_working_clone_bundle.py",
    ("bootstrap", "workflow-pipeline"): "bootstrap_workflow_blueprint.py",
    ("bootstrap", "workflow-runtime"): "bootstrap_workflow_clone_runtime.py",
    ("bootstrap", "sample-stack"): "rebuild_sample_stack.py",
    ("refresh", "working-bundle"): "refresh_working_clone_bundle.py",
    ("refresh", "workflow-pipeline"): "refresh_workflow_blueprint_pipeline.py",
    ("refresh", "workflow-runtime"): "refresh_workflow_runtime_bundle.py",
    ("validate", "stack"): "validate_clone_stack.py",
    ("validate", "working-dispatch"): "validate_working_clone_dispatch.py",
    ("validate", "workflow-pipeline-dispatch"): "validate_workflow_pipeline_dispatch.py",
    ("validate", "workflow-runtime-dispatch"): "validate_workflow_runtime_dispatch.py",
    ("validate", "workflow-blueprint"): "validate_workflow_blueprint.py",
    ("validate", "personal-skill"): "validate_personal_clone_skill.py",
    ("validate", "workflow-skill"): "validate_workflow_clone_skill.py",
    ("validate", "personal-release"): "validate_personal_clone_release.py",
    ("validate", "workflow-release"): "validate_workflow_clone_release.py",
    ("validate", "release-readiness"): "run_release_readiness.py",
}


def parse_flag_value(args: list[str], flag: str) -> tuple[str, list[str]]:
    if flag not in args:
        return "", args[:]
    idx = args.index(flag)
    if idx + 1 >= len(args):
        raise SystemExit(f"missing value for {flag}")
    value = args[idx + 1]
    cleaned = args[:idx] + args[idx + 2 :]
    return value, cleaned


def parse_bool_flag(args: list[str], flag: str) -> tuple[bool, list[str]]:
    present = flag in args
    cleaned = [item for item in args if item != flag]
    return present, cleaned


def emit_stack_summary(summary: dict[str, object], explain: bool, summary_json_path: str) -> None:
    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if explain:
        print(render_stack_summary_text(summary), file=sys.stderr)
    if summary_json_path:
        Path(summary_json_path).resolve().write_text(rendered + "\n", encoding="utf-8")


def run_validation_command_for_summary(
    candidate: tuple[Path, Path, Path, Path, Path],
    summary: dict[str, object],
    explain: bool,
    summary_json_path: str,
) -> int:
    workdir = Path(__file__).resolve().parent.parent
    emit_stack_summary(summary, explain, summary_json_path)
    proc = subprocess.run(build_stack_validation_command(workdir, *candidate), cwd=workdir, check=False)
    return proc.returncode


def sample_summary_to_candidate(summary: dict[str, object]) -> tuple[Path, Path, Path, Path, Path]:
    return (
        Path(str(summary.get("bundle_dir", ""))).resolve(),
        Path(str(summary.get("pipeline_dir", ""))).resolve(),
        Path(str(summary.get("runtime_dir", ""))).resolve(),
        Path(str(summary.get("personal_skill_dir", ""))).resolve(),
        Path(str(summary.get("workflow_skill_dir", ""))).resolve(),
    )


def load_candidate_from_summary(summary_path: str, default_selection_mode: str = "") -> tuple[tuple[Path, Path, Path, Path, Path], dict[str, object]]:
    summary = load_stack_summary(Path(summary_path).resolve())
    if default_selection_mode and not str(summary.get("selection_mode", "")).strip():
        summary["selection_mode"] = default_selection_mode
    return sample_summary_to_candidate(summary), summary


def run_sample_stack_doctor(remainder: list[str]) -> int:
    workdir = Path(__file__).resolve().parent.parent
    summary_json_path, remainder = parse_flag_value(remainder, "--summary-json")
    sample_summary_path, remainder = parse_flag_value(remainder, "--sample-summary")
    explain, remainder = parse_bool_flag(remainder, "--explain")
    if remainder:
        raise SystemExit(f"unexpected args for sample-stack: {' '.join(remainder)}")
    summary_path = Path(sample_summary_path or DEFAULT_SAMPLE_SUMMARY)
    if summary_path.exists():
        summary = load_stack_summary(summary_path)
        summary["selection_mode"] = "sample_stack_summary"
        return run_validation_command_for_summary(sample_summary_to_candidate(summary), summary, explain, summary_json_path)

    summary = {
        "bundle_dir": "/tmp/working-clone-bundle-v22",
        "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v3",
        "runtime_dir": "/tmp/workflow-runtime-v3",
        "personal_skill_dir": "/tmp/personal-clone-skill-v2",
        "workflow_skill_dir": "/tmp/workflow-clone-skill-v2",
        "selection_mode": "sample_stack_legacy",
    }
    emit_stack_summary(summary, explain, summary_json_path)
    command = [
        "python3",
        str(workdir / "scripts" / "validate_clone_stack.py"),
        "--bundle-manifest",
        "/tmp/working-clone-bundle-v22/working_clone_bundle_manifest.json",
        "--bundle-summary",
        "/tmp/working-clone-bundle-v22/working_clone_until_final_summary.json",
        "--bundle-readme",
        "/tmp/working-clone-bundle-v22/WORKING_CLONE_BUNDLE_README.md",
        "--pipeline-manifest",
        "/tmp/workflow-blueprint-pipeline-v3/workflow_blueprint_pipeline_manifest.json",
        "--pipeline-readme",
        "/tmp/workflow-blueprint-pipeline-v3/WORKFLOW_BLUEPRINT_PIPELINE_README.md",
        "--runtime-manifest",
        "/tmp/workflow-runtime-v3/workflow_runtime_manifest.json",
        "--runtime-readme",
        "/tmp/workflow-runtime-v3/WORKFLOW_RUNTIME_README.md",
        "--personal-skill-dir",
        "/tmp/personal-clone-skill-v2",
        "--workflow-skill-dir",
        "/tmp/workflow-clone-skill-v2",
        "--format",
        "json",
    ]
    proc = subprocess.run(command, cwd=workdir, check=False)
    return proc.returncode


def run_latest_stack_doctor(remainder: list[str]) -> int:
    summary_json_path, remainder = parse_flag_value(remainder, "--summary-json")
    stack_summary_path, remainder = parse_flag_value(remainder, "--stack-summary")
    explain, remainder = parse_bool_flag(remainder, "--explain")
    if remainder:
        raise SystemExit(f"unexpected args for latest-stack: {' '.join(remainder)}")
    if stack_summary_path:
        candidate, summary = load_candidate_from_summary(stack_summary_path, "latest_coherent_stack")
    else:
        workdir = Path(__file__).resolve().parent.parent
        candidate, discovery_report = discover_latest_coherent_stack_report(workdir)
        summary = build_stack_summary(*candidate, discovery_report=discovery_report)
        summary["selection_mode"] = "latest_coherent_stack"
    return run_validation_command_for_summary(candidate, summary, explain, summary_json_path)


def run_current_stack_doctor(remainder: list[str]) -> int:
    summary_json_path, remainder = parse_flag_value(remainder, "--summary-json")
    bundle_dir_value, remainder = parse_flag_value(remainder, "--bundle-dir")
    explain, remainder = parse_bool_flag(remainder, "--explain")
    if remainder:
        raise SystemExit(f"unexpected args for current-stack: {' '.join(remainder)}")
    if not bundle_dir_value:
        raise SystemExit("doctor current-stack requires --bundle-dir")
    workdir = Path(__file__).resolve().parent.parent
    candidate, discovery_report = discover_current_stack_from_bundle_report(workdir, Path(bundle_dir_value).resolve())
    summary = build_stack_summary(*candidate, discovery_report=discovery_report)
    summary["selection_mode"] = "bundle_anchored_stack"
    return run_validation_command_for_summary(candidate, summary, explain, summary_json_path)


def run_validate_latest_stack(remainder: list[str]) -> int:
    summary_json_path, remainder = parse_flag_value(remainder, "--summary-json")
    stack_summary_path, remainder = parse_flag_value(remainder, "--stack-summary")
    if remainder:
        raise SystemExit(f"unexpected args for validate latest-stack: {' '.join(remainder)}")
    if stack_summary_path:
        candidate, summary = load_candidate_from_summary(stack_summary_path, "latest_coherent_stack")
    else:
        workdir = Path(__file__).resolve().parent.parent
        candidate, discovery_report = discover_latest_coherent_stack_report(workdir)
        summary = build_stack_summary(*candidate, discovery_report=discovery_report)
        summary["selection_mode"] = "latest_coherent_stack"
    return run_validation_command_for_summary(candidate, summary, False, summary_json_path)


def run_explain_latest_stack(remainder: list[str]) -> int:
    summary_json_path, remainder = parse_flag_value(remainder, "--summary-json")
    stack_summary_path, remainder = parse_flag_value(remainder, "--stack-summary")
    if remainder:
        raise SystemExit(f"unexpected args for explain latest-stack: {' '.join(remainder)}")
    if stack_summary_path:
        _, summary = load_candidate_from_summary(stack_summary_path, "latest_coherent_stack")
    else:
        workdir = Path(__file__).resolve().parent.parent
        candidate, discovery_report = discover_latest_coherent_stack_report(workdir)
        summary = build_stack_summary(*candidate, discovery_report=discovery_report)
        summary["selection_mode"] = "latest_coherent_stack"
    emit_stack_summary(summary, False, summary_json_path)
    print(render_stack_summary_text(summary))
    return 0


def resolve_summary_input(summary_path: str, bundle_dir: str) -> dict[str, object]:
    workdir = Path(__file__).resolve().parent.parent
    if summary_path:
        return load_stack_summary(Path(summary_path).resolve())
    if bundle_dir:
        candidate, discovery_report = discover_current_stack_from_bundle_report(workdir, Path(bundle_dir).resolve())
        summary = build_stack_summary(*candidate, discovery_report=discovery_report)
        summary["selection_mode"] = "bundle_anchored_stack"
        return summary
    raise SystemExit("diff stack requires either --left-summary/--right-summary or --left-bundle-dir/--right-bundle-dir")


def run_diff_stack(remainder: list[str]) -> int:
    left_summary_path, remainder = parse_flag_value(remainder, "--left-summary")
    right_summary_path, remainder = parse_flag_value(remainder, "--right-summary")
    left_bundle_dir, remainder = parse_flag_value(remainder, "--left-bundle-dir")
    right_bundle_dir, remainder = parse_flag_value(remainder, "--right-bundle-dir")
    if remainder:
        raise SystemExit(f"unexpected args for diff stack: {' '.join(remainder)}")
    left = resolve_summary_input(left_summary_path, left_bundle_dir)
    right = resolve_summary_input(right_summary_path, right_bundle_dir)
    report = diff_stack_summaries(left, right)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok", False) else 1


def main() -> int:
    if len(sys.argv) < 3:
        print(USAGE, end="")
        return 2

    command = sys.argv[1]
    target = sys.argv[2]
    remainder = sys.argv[3:]

    if (command, target) == ("doctor", "sample-stack"):
        return run_sample_stack_doctor(remainder)
    if (command, target) == ("doctor", "latest-stack"):
        return run_latest_stack_doctor(remainder)
    if (command, target) == ("doctor", "current-stack"):
        return run_current_stack_doctor(remainder)
    if (command, target) == ("validate", "latest-stack"):
        return run_validate_latest_stack(remainder)
    if (command, target) == ("explain", "latest-stack"):
        return run_explain_latest_stack(remainder)
    if (command, target) == ("diff", "stack"):
        return run_diff_stack(remainder)

    script = ROUTE.get((command, target))
    if not script:
        print(USAGE, end="")
        return 2

    workdir = Path(__file__).resolve().parent.parent
    proc = subprocess.run(["python3", str(workdir / "scripts" / script), *remainder], cwd=workdir, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
