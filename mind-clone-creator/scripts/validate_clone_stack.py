#!/usr/bin/env python3
"""Aggregate validator for the full clone stack artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from validator_utils import validate_source_artifacts_block
except ModuleNotFoundError:
    from scripts.validator_utils import validate_source_artifacts_block


def maybe_run(command: list[str], workdir: Path) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=workdir, check=False, capture_output=True, text=True)
    stdout = proc.stdout.strip()
    payload: dict[str, Any]
    try:
        payload = json.loads(stdout) if stdout else {}
        if not isinstance(payload, dict):
            payload = {"raw_output": stdout}
    except json.JSONDecodeError:
        payload = {"raw_output": stdout, "stderr": proc.stderr.strip()}
    payload["exit_code"] = proc.returncode
    payload["ok"] = bool(payload.get("ok", proc.returncode == 0))
    return payload


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def resolve_file_hash(path_str: str) -> dict[str, Any]:
    if not path_str:
        return {"path": "", "exists": False}
    path = Path(path_str).resolve()
    info: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if path.exists() and path.is_file():
        info["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return info


def compare_file_equivalence(label: str, left_path: str, right_path: str) -> dict[str, Any]:
    left = resolve_file_hash(left_path)
    right = resolve_file_hash(right_path)
    ok = bool(
        left.get("exists")
        and right.get("exists")
        and left.get("sha256")
        and left.get("sha256") == right.get("sha256")
    )
    return {
        "label": label,
        "left": left,
        "right": right,
        "ok": ok,
    }


def build_linkage_report(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    bundle_manifest = load_json(args.bundle_manifest) if args.bundle_manifest else {}
    pipeline_manifest = load_json(args.pipeline_manifest) if args.pipeline_manifest else {}
    runtime_manifest = load_json(args.runtime_manifest) if args.runtime_manifest else {}

    personal_skill_manifest = (
        load_json(str(Path(args.personal_skill_dir).resolve() / "personal_clone_skill_manifest.json"))
        if args.personal_skill_dir
        else {}
    )
    workflow_skill_manifest = (
        load_json(str(Path(args.workflow_skill_dir).resolve() / "workflow_clone_skill_manifest.json"))
        if args.workflow_skill_dir
        else {}
    )

    personal_clone_config = str(Path(args.personal_skill_dir).resolve() / "clone_config.yaml") if args.personal_skill_dir else ""
    workflow_skill_files = workflow_skill_manifest.get("files", {}) if isinstance(workflow_skill_manifest.get("files"), dict) else {}

    if bundle_manifest and pipeline_manifest:
        checks.append(
            compare_file_equivalence(
                "bundle.workflow_blueprint == pipeline.blueprint",
                str(bundle_manifest.get("workflow_blueprint", "")),
                str(pipeline_manifest.get("blueprint", "")),
            )
        )
    if pipeline_manifest and personal_clone_config:
        checks.append(
            compare_file_equivalence(
                "pipeline.clone_config == personal_skill.clone_config",
                str(pipeline_manifest.get("clone_config", "")),
                personal_clone_config,
            )
        )
    if runtime_manifest and personal_clone_config:
        checks.append(
            compare_file_equivalence(
                "runtime.clone_config == personal_skill.clone_config",
                str(runtime_manifest.get("clone_config", "")),
                personal_clone_config,
            )
        )
    if runtime_manifest and pipeline_manifest:
        checks.append(
            compare_file_equivalence(
                "runtime.workflow_blueprint == pipeline.blueprint",
                str(runtime_manifest.get("workflow_blueprint", "")),
                str(pipeline_manifest.get("blueprint", "")),
            )
        )
    if workflow_skill_files and personal_clone_config:
        checks.append(
            compare_file_equivalence(
                "workflow_skill.clone_config == personal_skill.clone_config",
                str(workflow_skill_files.get("clone_config", "")),
                personal_clone_config,
            )
        )
    if workflow_skill_files and pipeline_manifest:
        checks.append(
            compare_file_equivalence(
                "workflow_skill.workflow_blueprint == pipeline.blueprint",
                str(workflow_skill_files.get("workflow_blueprint", "")),
                str(pipeline_manifest.get("blueprint", "")),
            )
        )

    ok = all(item.get("ok", False) for item in checks) if checks else False
    return {
        "artifact_sources": {
            "bundle_manifest": args.bundle_manifest,
            "bundle_summary": args.bundle_summary,
            "bundle_readme": args.bundle_readme,
            "pipeline_manifest": args.pipeline_manifest,
            "pipeline_readme": args.pipeline_readme,
            "runtime_manifest": args.runtime_manifest,
            "runtime_readme": args.runtime_readme,
            "personal_skill_dir": args.personal_skill_dir,
            "workflow_skill_dir": args.workflow_skill_dir,
        },
        "checks": checks,
        "ok": ok,
    }


def build_source_artifact_contract_report(args: argparse.Namespace) -> dict[str, Any]:
    bundle_manifest = load_json(args.bundle_manifest) if args.bundle_manifest else {}
    pipeline_manifest = load_json(args.pipeline_manifest) if args.pipeline_manifest else {}
    runtime_manifest = load_json(args.runtime_manifest) if args.runtime_manifest else {}
    reports: dict[str, Any] = {}

    if bundle_manifest:
        bundle_steps = bundle_manifest.get("steps", {}) if isinstance(bundle_manifest.get("steps", {}), dict) else {}
        required = ["personal_interview", "interview_state"]
        if bundle_steps.get("personal_clone_skill"):
            required.extend(["clone_config", "mind_profile", "system_prompt"])
        if bundle_steps.get("workflow_pipeline"):
            required.extend(["workflow_interview", "workflow_blueprint", "workflow_pipeline_dir"])
        if bundle_steps.get("workflow_runtime_bundle"):
            required.append("workflow_runtime_bundle_dir")
        reports["bundle"] = validate_source_artifacts_block(bundle_manifest, required_keys=required)

    if pipeline_manifest:
        pipeline_steps = pipeline_manifest.get("steps", {}) if isinstance(pipeline_manifest.get("steps", {}), dict) else {}
        required = ["interview"]
        if pipeline_steps.get("stage_confirmation"):
            required.append("stage_confirmation")
        if str(pipeline_manifest.get("clone_config", "")).strip():
            required.extend(["clone_config", "mind_profile", "system_prompt"])
        if pipeline_steps.get("blueprint"):
            required.append("blueprint")
        if pipeline_steps.get("workflow_clone_skill"):
            required.append("workflow_clone_skill_dir")
        if pipeline_steps.get("workflow_runtime_bundle"):
            required.append("workflow_runtime_bundle_dir")
        reports["pipeline"] = validate_source_artifacts_block(pipeline_manifest, required_keys=required)

    if runtime_manifest:
        reports["runtime"] = validate_source_artifacts_block(
            runtime_manifest,
            required_keys=["clone_config", "workflow_blueprint", "workflow_clone_skill_dir", "workflow_task_state"],
            expected_file_map={
                "clone_config": str(runtime_manifest.get("clone_config", "")),
                "workflow_blueprint": str(runtime_manifest.get("workflow_blueprint", "")),
                "workflow_task_state": str(runtime_manifest.get("state_path", "")),
            },
        )

    ok = all(item.get("ok", False) for item in reports.values()) if reports else False
    return {"reports": reports, "ok": ok}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the full clone stack with one command.")
    parser.add_argument("--bundle-manifest", default="")
    parser.add_argument("--bundle-summary", default="")
    parser.add_argument("--bundle-readme", default="")
    parser.add_argument("--pipeline-manifest", default="")
    parser.add_argument("--pipeline-readme", default="")
    parser.add_argument("--runtime-manifest", default="")
    parser.add_argument("--runtime-readme", default="")
    parser.add_argument("--personal-skill-dir", default="")
    parser.add_argument("--workflow-skill-dir", default="")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    report: dict[str, Any] = {"checks": {}}

    if args.bundle_manifest and args.bundle_summary and args.bundle_readme:
        report["checks"]["working_clone_dispatch"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_working_clone_dispatch.py"),
                "--manifest",
                args.bundle_manifest,
                "--summary",
                args.bundle_summary,
                "--readme",
                args.bundle_readme,
                "--format",
                "json",
            ],
            workdir,
        )
    if args.pipeline_manifest and args.pipeline_readme:
        report["checks"]["workflow_pipeline_dispatch"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_workflow_pipeline_dispatch.py"),
                "--manifest",
                args.pipeline_manifest,
                "--readme",
                args.pipeline_readme,
                "--format",
                "json",
            ],
            workdir,
        )
    if args.runtime_manifest and args.runtime_readme:
        report["checks"]["workflow_runtime_dispatch"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_workflow_runtime_dispatch.py"),
                "--manifest",
                args.runtime_manifest,
                "--readme",
                args.runtime_readme,
                "--format",
                "json",
            ],
            workdir,
        )
    if args.personal_skill_dir:
        skill_dir = Path(args.personal_skill_dir).resolve()
        report["checks"]["personal_skill_structure"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_personal_clone_skill.py"),
                "--manifest",
                str(skill_dir / "personal_clone_skill_manifest.json"),
                "--readme",
                str(skill_dir / "README.md"),
                "--format",
                "json",
            ],
            workdir,
        )
        report["checks"]["personal_skill_release"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_personal_clone_release.py"),
                "--skill-dir",
                str(skill_dir),
                "--format",
                "json",
            ],
            workdir,
        )
    if args.workflow_skill_dir:
        skill_dir = Path(args.workflow_skill_dir).resolve()
        report["checks"]["workflow_skill_structure"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_workflow_clone_skill.py"),
                "--manifest",
                str(skill_dir / "workflow_clone_skill_manifest.json"),
                "--readme",
                str(skill_dir / "README.md"),
                "--format",
                "json",
            ],
            workdir,
        )
        report["checks"]["workflow_skill_release"] = maybe_run(
            [
                "python3",
                str(workdir / "scripts" / "validate_workflow_clone_release.py"),
                "--skill-dir",
                str(skill_dir),
                "--format",
                "json",
            ],
            workdir,
        )

    if args.bundle_manifest or args.pipeline_manifest or args.runtime_manifest or args.personal_skill_dir or args.workflow_skill_dir:
        report["checks"]["cross_artifact_linkage"] = build_linkage_report(args)
    if args.bundle_manifest or args.pipeline_manifest or args.runtime_manifest:
        report["checks"]["source_artifact_contracts"] = build_source_artifact_contract_report(args)

    report["ok"] = all(bool(item.get("ok", False)) for item in report["checks"].values()) if report["checks"] else False
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
