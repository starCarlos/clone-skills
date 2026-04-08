#!/usr/bin/env python3
"""High-level entrypoint: compile a workflow clone, initialize runtime state, and optionally run it."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from profession_adapter_runtime import resolve_profession_adapter

try:
    from manifest_utils import build_refresh_cache, build_source_artifacts
    from refresh_dependency_registry import build_refresh_dependency_index, resolve_refresh_dependencies
    from stack_discovery import build_optional_stack_summary
    from workflow_runtime_dispatch import choose_recommended_runtime_command
except ModuleNotFoundError:
    from scripts.manifest_utils import build_refresh_cache, build_source_artifacts
    from scripts.refresh_dependency_registry import build_refresh_dependency_index, resolve_refresh_dependencies
    from scripts.stack_discovery import build_optional_stack_summary
    from scripts.workflow_runtime_dispatch import choose_recommended_runtime_command


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def repo_command(script: str, *args: str) -> list[str]:
    return ["python3", f"scripts/{script}", *args]


def build_runtime_user_view(
    manifest: dict[str, Any],
    recommended_next_command: dict[str, Any],
    adapter: dict[str, Any],
) -> dict[str, str]:
    initial_run_mode = str(manifest.get("initial_run_mode", "")).strip()
    if initial_run_mode == "multi_turn":
        status = "runtime 已初始化，并配置为直接连续推进多轮 workflow"
        usage_now = "可以直接发起多轮 workflow run。"
    elif initial_run_mode == "single_turn":
        status = "runtime 已初始化，并配置为直接执行单轮 workflow turn"
        usage_now = "可以直接发起单轮 workflow turn。"
    else:
        status = "runtime 已初始化，等待输入第一轮任务"
        usage_now = "默认先跑单轮 turn，需要时再切到多轮模式。"

    edit_or_input = str(recommended_next_command.get("input_source", "")).strip() or "直接运行下一条命令"
    if adapter:
        adapter_state = "已匹配 profession adapter，可按当前 profession 配置执行。"
    else:
        adapter_state = "未匹配 profession adapter，将按通用 workflow runtime 执行。"

    return {
        "status": status,
        "usage_now": usage_now,
        "next_step": str(recommended_next_command.get("reason", "")).strip() or "无",
        "edit_or_input": edit_or_input,
        "adapter_state": adapter_state,
    }


def validate_adapters(skill_root: Path) -> dict[str, Any]:
    validator = skill_root / "scripts" / "validate_profession_adapters.py"
    if not validator.exists():
        return {"valid": True, "adapter_count": 0, "results": [], "skipped": True}
    with tempfile.TemporaryDirectory(prefix="profession-adapter-validation-") as tmpdir:
        output = Path(tmpdir) / "validation.json"
        proc = subprocess.run(
            ["python3", str(validator), "--workspace", str(skill_root), "--output", str(output)],
            cwd=skill_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if not output.exists():
            raise SystemExit(f"profession adapter validation did not produce output: {proc.stderr.strip()}")
        data = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit("profession adapter validation returned invalid JSON")
        if proc.returncode != 0 or not data.get("valid", False):
            errors: list[str] = []
            for item in data.get("results", []):
                if not isinstance(item, dict) or item.get("valid", False):
                    continue
                file_path = str(item.get("file", "")).strip() or "<unknown>"
                for error in item.get("errors", []):
                    errors.append(f"{file_path}: {error}")
            detail = "\n".join(errors) if errors else (proc.stderr.strip() or "unknown validation error")
            raise SystemExit(f"profession adapter validation failed:\n{detail}")
        return data


def format_adapter_summary(adapter: dict[str, Any]) -> str:
    if not adapter:
        return "未匹配到 profession adapter。"
    execution = adapter.get("execution_overrides", {})
    tool_preferences = execution.get("tool_preferences", {}) if isinstance(execution, dict) else {}
    artifact_templates = execution.get("artifact_templates", {}) if isinstance(execution, dict) else {}
    lines = [
        f"- aliases: {', '.join(str(item) for item in adapter.get('profession_aliases', [])) or '无'}",
        f"- notes: {'；'.join(str(item) for item in adapter.get('notes', [])) or '无'}",
        f"- stage_overrides: {', '.join(str(key) for key in adapter.get('stage_overrides', {}).keys()) or '无'}",
        f"- tool_preferences: {json.dumps(tool_preferences, ensure_ascii=False)}" if tool_preferences else "- tool_preferences: 无",
        f"- artifact_templates: {json.dumps(artifact_templates, ensure_ascii=False)}" if artifact_templates else "- artifact_templates: 无",
    ]
    return "\n".join(lines)


def infer_profession_from_clone_config(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^\s*profession:\s*"([^"]+)"\s*$', text, re.M)
    if match:
        return match.group(1).strip()
    match = re.search(r"^\s*profession:\s*([^\n#]+?)\s*$", text, re.M)
    return match.group(1).strip() if match else ""


def infer_blueprint_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^#\s+(.+)$", text, re.M)
    return match.group(1).strip() if match else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a workflow clone runtime from clone config and workflow blueprint."
    )
    parser.add_argument("--clone-config", required=True)
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts")
    parser.add_argument("--mind-profile")
    parser.add_argument("--system-prompt")
    parser.add_argument("--profession", default="")
    parser.add_argument("--task-id", default="task-001")
    parser.add_argument("--task-summary", default="新建工作流任务")
    parser.add_argument("--initial-input")
    parser.add_argument("--run-until-stop", action="store_true")
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--skip-adapter-validation", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve()
    clone_config_path = Path(args.clone_config).resolve()
    input_profession = args.profession.strip() or infer_profession_from_clone_config(clone_config_path)
    validation_summary = {"valid": True, "adapter_count": 0, "results": [], "skipped": True}
    if not args.skip_adapter_validation:
        validation_summary = validate_adapters(workdir)
    resolved = resolve_profession_adapter(
        workdir,
        input_profession,
        fallback_query=infer_blueprint_title(Path(args.workflow_blueprint).resolve()),
        allow_recommendation=True,
        auto_apply_recommendation=not bool(args.profession.strip()),
    )
    profession = str(resolved.get("profession", "")).strip()
    adapter = resolved.get("adapter", {}) if isinstance(resolved.get("adapter", {}), dict) else {}
    recommendation = resolved.get("recommendation", {}) if isinstance(resolved.get("recommendation", {}), dict) else {}
    resolution = resolved.get("resolution", {}) if isinstance(resolved.get("resolution", {}), dict) else {}

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = output_dir / "workflow-clone-runtime"
    state_path = output_dir / "workflow_task_state.yaml"

    build_cmd = [
        "python3",
        str(workdir / "scripts/build_workflow_clone_skill.py"),
        "--clone-config",
        str(clone_config_path),
        "--workflow-blueprint",
        args.workflow_blueprint,
        "--output-dir",
        str(runtime_dir),
    ]
    if args.mind_profile:
        build_cmd.extend(["--mind-profile", args.mind_profile])
    if args.system_prompt:
        build_cmd.extend(["--system-prompt", args.system_prompt])
    run_command(build_cmd, workdir)

    run_command(
        [
            "python3",
            str(workdir / "scripts/init_workflow_task_state.py"),
            "--workflow-blueprint",
            args.workflow_blueprint,
            "--task-id",
            args.task_id,
            "--task-summary",
            args.task_summary,
            "--output",
            str(state_path),
        ],
        workdir,
    )

    shutil.copy2(state_path, runtime_dir / "workflow_task_state.yaml")

    if args.initial_input:
        if args.run_until_stop:
            run_cmd = [
                "python3",
                str(workdir / "scripts/run_workflow_until_stop.py"),
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(state_path),
                "--initial-input",
                args.initial_input,
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                profession,
                "--max-turns",
                str(args.max_turns),
                "--output-dir",
                str(output_dir / "workflow-run-output"),
            ]
            if args.execute_safe:
                run_cmd.append("--execute-safe")
            run_command(run_cmd, workdir)
        else:
            run_cmd = [
                "python3",
                str(workdir / "scripts/run_workflow_turn.py"),
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(state_path),
                "--input",
                args.initial_input,
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                profession,
                "--output-dir",
                str(output_dir / "workflow-turn-output"),
            ]
            if args.execute_safe:
                run_cmd.append("--execute-safe")
            run_command(run_cmd, workdir)

    manifest = {
        "runtime_dir": str(runtime_dir),
        "state_path": str(state_path),
        "workflow_blueprint": str(Path(args.workflow_blueprint).resolve()),
        "clone_config": str(clone_config_path),
        "source_artifacts": build_source_artifacts(
            {
                "clone_config": clone_config_path,
                "workflow_blueprint": Path(args.workflow_blueprint).resolve(),
                "mind_profile": Path(args.mind_profile).resolve() if args.mind_profile else None,
                "system_prompt": Path(args.system_prompt).resolve() if args.system_prompt else None,
                "workflow_clone_skill_dir": runtime_dir,
                "workflow_task_state": state_path,
            }
        ),
        "artifact_dir": str((Path(args.workspace).resolve() / args.artifact_dir)),
        "profession": profession,
        "profession_input": input_profession,
        "profession_resolution": resolution,
        "adapter_validation": validation_summary,
        "adapter_recommendation": recommendation,
        "initial_run_mode": "multi_turn" if args.initial_input and args.run_until_stop else ("single_turn" if args.initial_input else ""),
        "initial_run_output": str(output_dir / ("workflow-run-output" if args.run_until_stop else "workflow-turn-output")) if args.initial_input else "",
        "default_turn_output": str(output_dir / "workflow-turn-output" / "workflow_turn_summary.json"),
        "profession_adapter": {
            "matched": bool(adapter),
            "profession_aliases": adapter.get("profession_aliases", []),
            "notes": adapter.get("notes", []),
            "stage_override_stages": list(adapter.get("stage_overrides", {}).keys()) if isinstance(adapter.get("stage_overrides", {}), dict) else [],
            "execution_overrides": adapter.get("execution_overrides", {}),
        },
        "entrypoints": {
            "single_turn": repo_command(
                "run_workflow_turn.py",
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(state_path),
                "--input",
                "<your-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                profession,
                "--output-dir",
                str(output_dir / "workflow-turn-output"),
            ),
            "multi_turn": repo_command(
                "run_workflow_until_stop.py",
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(state_path),
                "--initial-input",
                "<your-initial-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                profession,
                "--max-turns",
                str(args.max_turns),
                "--output-dir",
                str(output_dir / "workflow-run-output"),
            ),
            "refresh_workflow_runtime_bundle": repo_command(
                "refresh_workflow_runtime_bundle.py",
                "--manifest",
                str(output_dir / "workflow_runtime_manifest.json"),
            ),
        },
    }
    if args.execute_safe:
        manifest["entrypoints"]["single_turn"].append("--execute-safe")
        manifest["entrypoints"]["multi_turn"].append("--execute-safe")
    manifest["recommended_next_command"] = choose_recommended_runtime_command(manifest)
    manifest["command_style"] = "repo_relative_scripts"
    refresh_inputs = [clone_config_path, Path(args.workflow_blueprint).resolve()]
    if args.mind_profile:
        refresh_inputs.append(Path(args.mind_profile).resolve())
    if args.system_prompt:
        refresh_inputs.append(Path(args.system_prompt).resolve())
    refresh_dependency_groups = ["workflow_shared", "runtime_core"]
    refresh_inputs.extend(resolve_refresh_dependencies(workdir, *refresh_dependency_groups))
    manifest["refresh_dependency_groups"] = refresh_dependency_groups
    manifest["refresh_dependency_index"] = build_refresh_dependency_index(workdir, *refresh_dependency_groups)
    manifest["refresh_cache"] = build_refresh_cache(refresh_inputs)
    (output_dir / "workflow_runtime_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readme_template = workdir / "templates" / "workflow_runtime_readme_template.md"
    if readme_template.exists():
        user_view = build_runtime_user_view(manifest, manifest["recommended_next_command"], adapter)
        (output_dir / "WORKFLOW_RUNTIME_README.md").write_text(
            render_template(
                readme_template,
                {
                    "user_runtime_status": user_view["status"],
                    "user_runtime_usage_now": user_view["usage_now"],
                    "user_next_step": user_view["next_step"],
                    "user_edit_or_input": user_view["edit_or_input"],
                    "user_adapter_state": user_view["adapter_state"],
                    "runtime_dir": manifest["runtime_dir"],
                    "state_path": manifest["state_path"],
                    "workflow_blueprint": manifest["workflow_blueprint"],
                    "clone_config": manifest["clone_config"],
                    "artifact_dir": manifest["artifact_dir"],
                    "profession": manifest["profession"] or "未指定",
                    "profession_input": manifest["profession_input"] or "未指定",
                    "profession_resolution_json": json.dumps(manifest["profession_resolution"], ensure_ascii=False, indent=2),
                    "adapter_validation_json": json.dumps(manifest["adapter_validation"], ensure_ascii=False, indent=2),
                    "adapter_recommendation_json": json.dumps(manifest["adapter_recommendation"], ensure_ascii=False, indent=2),
                    "adapter_summary": format_adapter_summary(adapter),
                    "profession_adapter_json": json.dumps(manifest["profession_adapter"], ensure_ascii=False, indent=2),
                    "recommended_next_mode": str(manifest["recommended_next_command"].get("mode", "")) or "无",
                    "recommended_next_label": str(manifest["recommended_next_command"].get("label", "")) or "无",
                    "recommended_next_scope": str(manifest["recommended_next_command"].get("scope", "")) or "无",
                    "recommended_next_section": str(manifest["recommended_next_command"].get("section", "")) or "无",
                    "recommended_next_manual_edit_required": str(manifest["recommended_next_command"].get("manual_edit_required", "")) or "无",
                    "recommended_next_priority": str(manifest["recommended_next_command"].get("priority", "")) or "无",
                    "recommended_next_reason": str(manifest["recommended_next_command"].get("reason", "")) or "无",
                    "recommended_next_input_source": str(manifest["recommended_next_command"].get("input_source", "")) or "无",
                    "recommended_next_output_artifact": str(manifest["recommended_next_command"].get("output_artifact", "")) or "无",
                    "recommended_next_stop_condition": str(manifest["recommended_next_command"].get("stop_condition", "")) or "无",
                    "recommended_next_command": str(manifest["recommended_next_command"].get("command", "")) or "无",
                    "single_turn": " ".join(manifest["entrypoints"]["single_turn"]),
                    "multi_turn": " ".join(manifest["entrypoints"]["multi_turn"]),
                    "refresh_workflow_runtime_bundle": " ".join(manifest["entrypoints"]["refresh_workflow_runtime_bundle"]),
                },
            ),
            encoding="utf-8",
        )

    stack_summary = build_optional_stack_summary(
        runtime_dir=output_dir,
        personal_skill_dir=clone_config_path.parent,
        workflow_skill_dir=runtime_dir,
        selection_mode="runtime_bundle_output",
    )
    (output_dir / "STACK_SUMMARY.json").write_text(
        json.dumps(stack_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME

# SCRIPT_REFRESH_MARKER_RUNTIME
