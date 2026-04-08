#!/usr/bin/env python3
"""High-level entrypoint for the generic workflow-blueprint interview pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from manifest_utils import (
        build_refresh_cache,
        build_source_artifacts,
        restore_refresh_metadata_if_missing,
        snapshot_refresh_metadata,
    )
    from refresh_dependency_registry import build_refresh_dependency_index, resolve_refresh_dependencies
    from stack_discovery import build_optional_stack_summary
    from workflow_pipeline_dispatch import choose_recommended_pipeline_command
except ModuleNotFoundError:
    from scripts.manifest_utils import (
        build_refresh_cache,
        build_source_artifacts,
        restore_refresh_metadata_if_missing,
        snapshot_refresh_metadata,
    )
    from scripts.refresh_dependency_registry import build_refresh_dependency_index, resolve_refresh_dependencies
    from scripts.stack_discovery import build_optional_stack_summary
    from scripts.workflow_pipeline_dispatch import choose_recommended_pipeline_command


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def infer_workflow_name(work_unit: str) -> str:
    cleaned = work_unit.strip()
    if not cleaned:
        return "未命名工作流蓝图"
    return f"{cleaned}工作流蓝图"


def infer_profession_from_clone_config(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^\s*profession:\s*"([^"]+)"\s*$', text, re.M)
    if match:
        return match.group(1).strip()
    match = re.search(r"^\s*profession:\s*([^\n#]+?)\s*$", text, re.M)
    return match.group(1).strip() if match else ""


def interview_has_substantive_answers(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        from plan_clone_interview_next import WORKFLOW_ITEMS, evaluate_sections
    except ModuleNotFoundError:
        from scripts.plan_clone_interview_next import WORKFLOW_ITEMS, evaluate_sections

    progress = evaluate_sections(path.resolve(), WORKFLOW_ITEMS, kind="workflow")
    return int(progress.get("answered", 0)) > 0


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def format_command(command: list[str]) -> str:
    return " ".join(command)


def repo_command(script: str, *args: str) -> list[str]:
    return ["python3", f"scripts/{script}", *args]


def build_pipeline_user_view(steps: dict[str, Any], recommended_next_command: dict[str, Any]) -> dict[str, str]:
    if not bool(steps.get("interview_substantive", False)):
        status = "workflow 访谈已初始化，等待补充第一批实质回答"
        usage_now = "先补 workflow interview，再继续阶段确认和 blueprint 编译。"
    elif not bool(steps.get("stage_confirmation", False)):
        status = "workflow interview 已有实质内容，等待生成阶段确认稿"
        usage_now = "可以直接生成 stage confirmation，准备确认阶段拆分。"
    elif not bool(steps.get("draft", False)):
        status = "阶段确认稿已生成，等待人工确认后提取结构化 draft"
        usage_now = "先确认或编辑 stage confirmation，再继续抽取 workflow draft。"
    elif not bool(steps.get("blueprint", False)):
        status = "workflow draft 已就绪，等待生成 blueprint"
        usage_now = "可以直接编译 workflow_blueprint.md。"
    elif not bool(steps.get("workflow_clone_skill", False)):
        status = "workflow blueprint 已生成，等待编译 workflow clone skill"
        usage_now = "流程蓝图已经可读，下一步继续生成 workflow clone skill。"
    elif not bool(steps.get("workflow_runtime_bundle", False)):
        status = "workflow clone skill 已生成，等待初始化 runtime"
        usage_now = "流程蓝图和 workflow clone skill 都已就绪，下一步初始化 runtime。"
    else:
        status = "workflow runtime 已就绪，可以直接推进任务回合"
        usage_now = "可以直接跑单轮或多轮 workflow 执行。"

    edit_or_input = str(recommended_next_command.get("input_source", "")).strip()
    if not edit_or_input:
        if str(recommended_next_command.get("manual_edit_required", "")).strip() == "true":
            edit_or_input = "先编辑推荐文件后再刷新"
        else:
            edit_or_input = "直接运行下一条命令"

    return {
        "status": status,
        "usage_now": usage_now,
        "next_step": str(recommended_next_command.get("reason", "")).strip() or "无",
        "edit_or_input": edit_or_input,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the generic workflow-blueprint pipeline.")
    parser.add_argument("--workflow-name", default="", help="Workflow name.")
    parser.add_argument("--work-unit", required=True, help="One recurring work unit to model.")
    parser.add_argument("--known-context", default="暂无", help="Known context from persona/profile/work clues.")
    parser.add_argument("--output-dir", required=True, help="Output directory for the blueprint pipeline bundle.")
    parser.add_argument("--clone-config", help="Optional clone_config.yaml path to compile a workflow clone skill.")
    parser.add_argument("--mind-profile", help="Optional mind_profile.md path for workflow clone compilation.")
    parser.add_argument("--system-prompt", help="Optional system_prompt.md path for workflow clone compilation.")
    parser.add_argument("--task-id", default="task-001", help="Task id for runtime bundle initialization.")
    parser.add_argument("--task-summary", default="新建工作流任务", help="Task summary for runtime bundle initialization.")
    parser.add_argument("--workspace", default=".", help="Workspace for runtime execution and artifact discovery.")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts", help="Artifact dir for runtime execution.")
    parser.add_argument("--profession", default="", help="Optional profession override for runtime bundle.")
    parser.add_argument("--initial-input", help="Optional initial runtime input.")
    parser.add_argument("--run-until-stop", action="store_true")
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--interview", help="Existing filled workflow interview markdown.")
    parser.add_argument("--stage-confirmation", help="Existing stage confirmation markdown.")
    parser.add_argument("--skip-init-interview", action="store_true")
    parser.add_argument("--skip-stage-confirmation", action="store_true")
    parser.add_argument("--skip-draft", action="store_true")
    parser.add_argument("--skip-blueprint", action="store_true")
    parser.add_argument("--skip-clone-skill", action="store_true")
    parser.add_argument("--skip-runtime-bundle", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    workflow_name = args.workflow_name.strip() or infer_workflow_name(args.work_unit)
    interview_path = Path(args.interview).resolve() if args.interview else (output_dir / "workflow_interview.md")
    stage_confirmation_path = (
        Path(args.stage_confirmation).resolve() if args.stage_confirmation else (output_dir / "stage_confirmation.md")
    )
    draft_path = output_dir / "workflow_blueprint_input.json"
    blueprint_path = output_dir / "workflow_blueprint.md"
    workflow_clone_skill_dir = output_dir / "workflow-clone-skill"
    workflow_runtime_bundle_dir = output_dir / "workflow-runtime-bundle"
    workflow_validation_json = output_dir / "workflow_interview_validation.json"
    runtime_profession = args.profession.strip()
    if not runtime_profession and args.clone_config:
        runtime_profession = infer_profession_from_clone_config(Path(args.clone_config).resolve())
    runtime_profession = runtime_profession or "<profession>"

    if not args.skip_init_interview and not args.interview:
        run_command(
            [
                "python3",
                str(skill_root / "scripts" / "init_workflow_interview.py"),
                "--workflow-name",
                workflow_name,
                "--work-unit",
                args.work_unit,
                "--known-context",
                args.known_context,
                "--output",
                str(interview_path),
            ],
            skill_root,
        )

    if (
        not args.skip_stage_confirmation
        and interview_path.exists()
        and not args.stage_confirmation
        and interview_has_substantive_answers(interview_path)
    ):
        run_command(
            [
                "python3",
                str(skill_root / "scripts" / "build_workflow_stage_confirmation.py"),
                "--interview",
                str(interview_path),
                "--workflow-name",
                workflow_name,
                "--work-unit",
                args.work_unit,
                "--output",
                str(stage_confirmation_path),
            ],
            skill_root,
        )

    validation_cmd = [
        "python3",
        str(skill_root / "scripts" / "validate_workflow_interview.py"),
        "--interview",
        str(interview_path),
        "--format",
        "json",
    ]
    validation_proc = subprocess.run(validation_cmd, cwd=skill_root, check=True, capture_output=True, text=True)
    workflow_validation = json.loads(validation_proc.stdout)
    workflow_validation_json.write_text(
        json.dumps(workflow_validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    can_continue_pipeline = interview_has_substantive_answers(interview_path)

    if not args.skip_draft and can_continue_pipeline:
        if not interview_path.exists():
            raise SystemExit(f"workflow interview not found: {interview_path}")
        draft_cmd = [
            "python3",
            str(skill_root / "scripts" / "extract_workflow_draft.py"),
            "--interview",
            str(interview_path),
            "--workflow-name",
            workflow_name,
            "--work-unit",
            args.work_unit,
            "--output",
            str(draft_path),
        ]
        if stage_confirmation_path.exists():
            draft_cmd.extend(["--stage-confirmation", str(stage_confirmation_path)])
        run_command(draft_cmd, skill_root)

    if not args.skip_blueprint and can_continue_pipeline:
        if not draft_path.exists():
            raise SystemExit(f"workflow draft not found: {draft_path}")
        run_command(
            [
                "python3",
                str(skill_root / "scripts" / "build_workflow_blueprint.py"),
                "--input",
                str(draft_path),
                "--output",
                str(blueprint_path),
            ],
            skill_root,
        )

    if args.clone_config and not args.skip_clone_skill and can_continue_pipeline:
        clone_config_path = Path(args.clone_config).resolve()
        if not clone_config_path.exists():
            raise SystemExit(f"clone config not found: {clone_config_path}")
        if not blueprint_path.exists():
            raise SystemExit(f"workflow blueprint not found: {blueprint_path}")
        clone_cmd = [
            "python3",
            str(skill_root / "scripts" / "build_workflow_clone_skill.py"),
            "--clone-config",
            str(clone_config_path),
            "--workflow-blueprint",
            str(blueprint_path),
            "--output-dir",
            str(workflow_clone_skill_dir),
        ]
        if args.mind_profile:
            clone_cmd.extend(["--mind-profile", str(Path(args.mind_profile).resolve())])
        if args.system_prompt:
            clone_cmd.extend(["--system-prompt", str(Path(args.system_prompt).resolve())])
        run_command(clone_cmd, skill_root)

    if args.clone_config and not args.skip_runtime_bundle and can_continue_pipeline:
        clone_config_path = Path(args.clone_config).resolve()
        if not clone_config_path.exists():
            raise SystemExit(f"clone config not found: {clone_config_path}")
        if not blueprint_path.exists():
            raise SystemExit(f"workflow blueprint not found: {blueprint_path}")
        runtime_manifest_path = workflow_runtime_bundle_dir / "workflow_runtime_manifest.json"
        runtime_refresh_snapshot = snapshot_refresh_metadata(runtime_manifest_path)
        runtime_cmd = [
            "python3",
            str(skill_root / "scripts" / "bootstrap_workflow_clone_runtime.py"),
            "--clone-config",
            str(clone_config_path),
            "--workflow-blueprint",
            str(blueprint_path),
            "--output-dir",
            str(workflow_runtime_bundle_dir),
            "--workspace",
            args.workspace,
            "--artifact-dir",
            args.artifact_dir,
            "--task-id",
            args.task_id,
            "--task-summary",
            args.task_summary,
            "--max-turns",
            str(args.max_turns),
        ]
        if args.mind_profile:
            runtime_cmd.extend(["--mind-profile", str(Path(args.mind_profile).resolve())])
        if args.system_prompt:
            runtime_cmd.extend(["--system-prompt", str(Path(args.system_prompt).resolve())])
        if args.profession.strip():
            runtime_cmd.extend(["--profession", args.profession.strip()])
        if args.initial_input:
            runtime_cmd.extend(["--initial-input", args.initial_input])
        if args.run_until_stop:
            runtime_cmd.append("--run-until-stop")
        if args.execute_safe:
            runtime_cmd.append("--execute-safe")
        run_command(runtime_cmd, skill_root)
        restore_refresh_metadata_if_missing(runtime_manifest_path, runtime_refresh_snapshot)

    manifest: dict[str, Any] = {
        "workflow_name": workflow_name,
        "work_unit": args.work_unit,
        "known_context": args.known_context,
        "clone_config": str(Path(args.clone_config).resolve()) if args.clone_config else "",
        "interview": str(interview_path),
        "stage_confirmation": str(stage_confirmation_path),
        "draft": str(draft_path),
        "blueprint": str(blueprint_path),
        "workflow_clone_skill": str(workflow_clone_skill_dir),
        "workflow_runtime_bundle": str(workflow_runtime_bundle_dir),
        "workflow_interview_validation": str(workflow_validation_json),
        "workflow_validation": workflow_validation,
        "steps": {
            "init_interview": interview_path.exists(),
            "interview_substantive": can_continue_pipeline,
            "stage_confirmation": stage_confirmation_path.exists(),
            "draft": draft_path.exists(),
            "blueprint": blueprint_path.exists(),
            "workflow_clone_skill": workflow_clone_skill_dir.exists(),
            "workflow_runtime_bundle": workflow_runtime_bundle_dir.exists(),
        },
        "entrypoints": {
            "init_interview": repo_command(
                "init_workflow_interview.py",
                "--workflow-name",
                workflow_name,
                "--work-unit",
                args.work_unit,
                "--known-context",
                args.known_context,
                "--output",
                str(interview_path),
            ),
            "build_stage_confirmation": repo_command(
                "build_workflow_stage_confirmation.py",
                "--interview",
                str(interview_path),
                "--workflow-name",
                workflow_name,
                "--work-unit",
                args.work_unit,
                "--output",
                str(stage_confirmation_path),
            ),
            "extract_draft": repo_command(
                "extract_workflow_draft.py",
                "--interview",
                str(interview_path),
                "--stage-confirmation",
                str(stage_confirmation_path),
                "--workflow-name",
                workflow_name,
                "--work-unit",
                args.work_unit,
                "--output",
                str(draft_path),
            ),
            "build_blueprint": repo_command(
                "build_workflow_blueprint.py",
                "--input",
                str(draft_path),
                "--output",
                str(blueprint_path),
            ),
            "build_workflow_clone_skill": repo_command(
                "build_workflow_clone_skill.py",
                "--clone-config",
                str(Path(args.clone_config).resolve()) if args.clone_config else "<clone_config.yaml>",
                "--workflow-blueprint",
                str(blueprint_path),
                "--output-dir",
                str(workflow_clone_skill_dir),
            ),
            "build_workflow_runtime_bundle": repo_command(
                "bootstrap_workflow_clone_runtime.py",
                "--clone-config",
                str(Path(args.clone_config).resolve()) if args.clone_config else "<clone_config.yaml>",
                "--workflow-blueprint",
                str(blueprint_path),
                "--output-dir",
                str(workflow_runtime_bundle_dir),
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--task-id",
                args.task_id,
                "--task-summary",
                args.task_summary,
                "--max-turns",
                str(args.max_turns),
            ),
            "run_workflow_turn": repo_command(
                "run_workflow_turn.py",
                "--workflow-blueprint",
                str(blueprint_path),
                "--state",
                str(workflow_runtime_bundle_dir / "workflow_task_state.yaml"),
                "--input",
                "<your-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                runtime_profession,
                "--output-dir",
                str(workflow_runtime_bundle_dir / "workflow-turn-output"),
            ),
            "run_workflow_until_stop": repo_command(
                "run_workflow_until_stop.py",
                "--workflow-blueprint",
                str(blueprint_path),
                "--state",
                str(workflow_runtime_bundle_dir / "workflow_task_state.yaml"),
                "--initial-input",
                "<your-initial-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                runtime_profession,
                "--max-turns",
                str(args.max_turns),
                "--output-dir",
                str(workflow_runtime_bundle_dir / "workflow-run-output"),
            ),
            "refresh_workflow_pipeline": repo_command(
                "refresh_workflow_blueprint_pipeline.py",
                "--manifest",
                str(output_dir / "workflow_blueprint_pipeline_manifest.json"),
            ),
        },
    }
    if args.mind_profile:
        manifest["entrypoints"]["build_workflow_clone_skill"].extend(["--mind-profile", str(Path(args.mind_profile).resolve())])
    if args.system_prompt:
        manifest["entrypoints"]["build_workflow_clone_skill"].extend(["--system-prompt", str(Path(args.system_prompt).resolve())])
    if args.mind_profile:
        manifest["entrypoints"]["build_workflow_runtime_bundle"].extend(["--mind-profile", str(Path(args.mind_profile).resolve())])
    if args.system_prompt:
        manifest["entrypoints"]["build_workflow_runtime_bundle"].extend(["--system-prompt", str(Path(args.system_prompt).resolve())])
    if args.profession.strip():
        manifest["entrypoints"]["build_workflow_runtime_bundle"].extend(["--profession", args.profession.strip()])
    if args.initial_input:
        manifest["entrypoints"]["build_workflow_runtime_bundle"].extend(["--initial-input", args.initial_input])
    if args.run_until_stop:
        manifest["entrypoints"]["build_workflow_runtime_bundle"].append("--run-until-stop")
    if args.execute_safe:
        manifest["entrypoints"]["build_workflow_runtime_bundle"].append("--execute-safe")
        manifest["entrypoints"]["run_workflow_turn"].append("--execute-safe")
        manifest["entrypoints"]["run_workflow_until_stop"].append("--execute-safe")
    recommended_next_command = choose_recommended_pipeline_command(manifest)
    manifest["recommended_next_command"] = recommended_next_command
    manifest["command_style"] = "repo_relative_scripts"
    manifest["source_artifacts"] = build_source_artifacts(
        {
            "interview": interview_path,
            "stage_confirmation": stage_confirmation_path if stage_confirmation_path.exists() else None,
            "clone_config": Path(args.clone_config).resolve() if args.clone_config else None,
            "mind_profile": Path(args.mind_profile).resolve() if args.mind_profile else None,
            "system_prompt": Path(args.system_prompt).resolve() if args.system_prompt else None,
            "blueprint": blueprint_path if blueprint_path.exists() else None,
            "workflow_clone_skill_dir": workflow_clone_skill_dir if workflow_clone_skill_dir.exists() else None,
            "workflow_runtime_bundle_dir": workflow_runtime_bundle_dir if workflow_runtime_bundle_dir.exists() else None,
        }
    )
    refresh_inputs = [interview_path]
    if stage_confirmation_path.exists():
        refresh_inputs.append(stage_confirmation_path)
    if args.clone_config:
        refresh_inputs.append(Path(args.clone_config).resolve())
    if args.mind_profile:
        refresh_inputs.append(Path(args.mind_profile).resolve())
    if args.system_prompt:
        refresh_inputs.append(Path(args.system_prompt).resolve())
    refresh_dependency_groups = ["workflow_shared"]
    refresh_inputs.extend(resolve_refresh_dependencies(skill_root, *refresh_dependency_groups))
    manifest["refresh_dependency_groups"] = refresh_dependency_groups
    manifest["refresh_dependency_index"] = build_refresh_dependency_index(skill_root, *refresh_dependency_groups)
    manifest["refresh_cache"] = build_refresh_cache(refresh_inputs)
    (output_dir / "workflow_blueprint_pipeline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readme_template = skill_root / "templates" / "workflow_blueprint_pipeline_readme_template.md"
    if readme_template.exists():
        user_view = build_pipeline_user_view(manifest["steps"], recommended_next_command)
        (output_dir / "WORKFLOW_BLUEPRINT_PIPELINE_README.md").write_text(
            render_template(
                readme_template,
                {
                    "user_pipeline_status": user_view["status"],
                    "user_pipeline_usage_now": user_view["usage_now"],
                    "user_next_step": user_view["next_step"],
                    "user_edit_or_input": user_view["edit_or_input"],
                    "workflow_name": workflow_name,
                    "work_unit": args.work_unit,
                    "known_context": args.known_context,
                    "interview_ready": "true" if manifest["steps"]["init_interview"] else "false",
                    "interview_substantive": "true" if manifest["steps"]["interview_substantive"] else "false",
                    "recommended_release": str(workflow_validation.get("recommended_release", "draft")),
                    "workflow_final_ready": "true" if workflow_validation.get("final_ready", False) else "false",
                    "workflow_blockers": (
                        "无"
                        if not workflow_validation.get("blockers")
                        else "；".join(
                            f"{item.get('section', '<unknown>')}：{item.get('reason', '未最终确认')}"
                            for item in workflow_validation["blockers"]
                        )
                    ),
                    "stage_confirmation_ready": "true" if manifest["steps"]["stage_confirmation"] else "false",
                    "draft_ready": "true" if manifest["steps"]["draft"] else "false",
                    "blueprint_ready": "true" if manifest["steps"]["blueprint"] else "false",
                    "clone_skill_ready": "true" if manifest["steps"]["workflow_clone_skill"] else "false",
                    "runtime_bundle_ready": "true" if manifest["steps"]["workflow_runtime_bundle"] else "false",
                    "interview": manifest["interview"],
                    "workflow_interview_validation": manifest["workflow_interview_validation"],
                    "stage_confirmation": manifest["stage_confirmation"],
                    "draft": manifest["draft"],
                    "blueprint": manifest["blueprint"],
                    "workflow_clone_skill": manifest["workflow_clone_skill"],
                    "workflow_runtime_bundle": manifest["workflow_runtime_bundle"],
                    "recommended_next_mode": str(recommended_next_command.get("mode", "")) or "无",
                    "recommended_next_label": str(recommended_next_command.get("label", "")) or "无",
                    "recommended_next_scope": str(recommended_next_command.get("scope", "")) or "无",
                    "recommended_next_section": str(recommended_next_command.get("section", "")) or "无",
                    "recommended_next_manual_edit_required": str(recommended_next_command.get("manual_edit_required", "")) or "无",
                    "recommended_next_priority": str(recommended_next_command.get("priority", "")) or "无",
                    "recommended_next_reason": str(recommended_next_command.get("reason", "")) or "无",
                    "recommended_next_input_source": str(recommended_next_command.get("input_source", "")) or "无",
                    "recommended_next_output_artifact": str(recommended_next_command.get("output_artifact", "")) or "无",
                    "recommended_next_stop_condition": str(recommended_next_command.get("stop_condition", "")) or "无",
                    "recommended_next_command": str(recommended_next_command.get("command", "")) or "无",
                    "init_interview": format_command(manifest["entrypoints"]["init_interview"]),
                    "build_stage_confirmation": format_command(manifest["entrypoints"]["build_stage_confirmation"]),
                    "extract_draft": format_command(manifest["entrypoints"]["extract_draft"]),
                    "build_blueprint": format_command(manifest["entrypoints"]["build_blueprint"]),
                    "build_workflow_clone_skill": format_command(manifest["entrypoints"]["build_workflow_clone_skill"]),
                    "build_workflow_runtime_bundle": format_command(manifest["entrypoints"]["build_workflow_runtime_bundle"]),
                    "run_workflow_turn": format_command(manifest["entrypoints"]["run_workflow_turn"]),
                    "run_workflow_until_stop": format_command(manifest["entrypoints"]["run_workflow_until_stop"]),
                    "refresh_workflow_pipeline": format_command(manifest["entrypoints"]["refresh_workflow_pipeline"]),
                },
            ),
            encoding="utf-8",
        )

    stack_summary = build_optional_stack_summary(
        pipeline_dir=output_dir,
        runtime_dir=workflow_runtime_bundle_dir if workflow_runtime_bundle_dir.exists() else None,
        personal_skill_dir=Path(args.clone_config).resolve().parent if args.clone_config else None,
        workflow_skill_dir=workflow_clone_skill_dir if workflow_clone_skill_dir.exists() else None,
        selection_mode="workflow_pipeline_output",
    )
    (output_dir / "STACK_SUMMARY.json").write_text(
        json.dumps(stack_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
