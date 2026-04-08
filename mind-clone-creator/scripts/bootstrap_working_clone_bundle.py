#!/usr/bin/env python3
"""High-level entrypoint: build persona clone artifacts and, when enabled, the workflow clone chain."""

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
    from render_delivery_summary import (
        build_summary as build_delivery_summary,
        build_workflow_summary,
        render_markdown as render_delivery_markdown,
    )
    from stack_discovery import build_optional_stack_summary
    from workflow_target_utils import (
        WORKFLOW_NAME_PLACEHOLDER,
        WORKFLOW_TARGET_PLACEHOLDER,
        infer_workflow_name,
        workflow_target_defined,
    )
    from working_clone_dispatch import (
        choose_recommended_next_command,
        load_pending_actions,
        split_pending_actions,
    )
except ModuleNotFoundError:
    from scripts.manifest_utils import (
        build_refresh_cache,
        build_source_artifacts,
        restore_refresh_metadata_if_missing,
        snapshot_refresh_metadata,
    )
    from scripts.refresh_dependency_registry import build_refresh_dependency_index, resolve_refresh_dependencies
    from scripts.render_delivery_summary import (
        build_summary as build_delivery_summary,
        build_workflow_summary,
        render_markdown as render_delivery_markdown,
    )
    from scripts.stack_discovery import build_optional_stack_summary
    from scripts.workflow_target_utils import (
        WORKFLOW_NAME_PLACEHOLDER,
        WORKFLOW_TARGET_PLACEHOLDER,
        infer_workflow_name,
        workflow_target_defined,
    )
    from scripts.working_clone_dispatch import (
        choose_recommended_next_command,
        load_pending_actions,
        split_pending_actions,
    )


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def format_command(command: list[str]) -> str:
    return " ".join(command)


def repo_command(script: str, *args: str) -> list[str]:
    return ["python3", f"scripts/{script}", *args]


def format_pending_details(items: list[dict[str, Any]], scope: str) -> list[str]:
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        section = str(item.get("section", "")).strip()
        reason = str(item.get("reason", "")).strip() or "未最终确认"
        question = str(item.get("follow_up_question", "")).strip() or "无"
        hint = str(item.get("example_hint", "")).strip()
        line = f"- [{scope}] {section}: {reason} | follow_up: {question}"
        if hint:
            line += f" | hint: {hint}"
        lines.append(line)
    return lines


def summarize_bundle_snapshot(
    workflow_enabled: bool,
    workflow_target_ready: bool,
    steps: dict[str, Any],
    bundle_validation: dict[str, Any],
    recommended_next_command: dict[str, Any],
) -> dict[str, str]:
    blockers = bundle_validation.get("blockers", []) if isinstance(bundle_validation.get("blockers", []), list) else []
    blocker_summary = (
        "无"
        if not blockers
        else "；".join(
            f"{str(item.get('item', '<unknown>')).strip()}：{str(item.get('reason', '未就绪')).strip()}"
            for item in blockers
            if isinstance(item, dict)
        )
    )
    if not bool(steps.get("personal_clone_skill", False)):
        status = "人格层尚未生成"
    elif workflow_enabled and not workflow_target_ready:
        status = "人格层已交付，workflow 轨道已开启，等待确认第一类典型工作"
    elif workflow_enabled and not bool(steps.get("workflow_pipeline", False)):
        status = "人格层已交付，等待编译 workflow blueprint"
    elif workflow_enabled and not bool(steps.get("workflow_clone_skill", False)):
        status = "workflow blueprint 已生成，等待编译 workflow clone skill"
    elif workflow_enabled and not bool(steps.get("workflow_runtime_bundle", False)):
        status = "workflow clone skill 已生成，等待初始化 runtime"
    elif workflow_enabled:
        status = "人格层与 workflow 链路已就绪"
    else:
        status = "人格层交付已就绪"
    next_action = str(recommended_next_command.get("reason", "")).strip() or "无"
    return {
        "status": status,
        "next_action": next_action,
        "blocker_summary": blocker_summary,
    }


def build_user_usage_summary(
    workflow_enabled: bool,
    workflow_target_ready: bool,
    steps: dict[str, Any],
    recommended_next_command: dict[str, Any],
) -> dict[str, str]:
    if bool(steps.get("personal_clone_skill", False)):
        persona_usage_now = "人格层分身已经可用。"
    else:
        persona_usage_now = "人格层分身还未生成。"

    if not workflow_enabled:
        workflow_usage_now = "当前未启用 workflow 轨道。"
    elif not workflow_target_ready:
        workflow_usage_now = "workflow 轨道已开启，但还在等第一类典型工作。"
    elif bool(steps.get("workflow_runtime_bundle", False)):
        workflow_usage_now = "workflow runtime 已就绪，可以继续跑任务回合。"
    elif bool(steps.get("workflow_clone_skill", False)):
        workflow_usage_now = "workflow clone skill 已生成，下一步可初始化 runtime。"
    elif bool(steps.get("workflow_pipeline", False)):
        workflow_usage_now = "workflow blueprint 已生成，下一步可继续编译 clone skill / runtime。"
    else:
        workflow_usage_now = "workflow 轨道已开启，但还没完成 workflow blueprint。"

    edit_or_input = str(recommended_next_command.get("input_source", "")).strip()
    if not edit_or_input:
        if str(recommended_next_command.get("manual_edit_required", "")).strip() == "true":
            edit_or_input = "先编辑推荐文件后再刷新"
        else:
            edit_or_input = "直接运行下一条命令"

    return {
        "persona_usage_now": persona_usage_now,
        "workflow_usage_now": workflow_usage_now,
        "edit_or_input": edit_or_input,
    }


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_delivery_summaries(clone_config_path: Path, manifest_path: Path, output_paths: list[Path]) -> None:
    if not clone_config_path.exists():
        return
    try:
        from build_personal_clone_skill import load_simple_yaml
    except ModuleNotFoundError:
        from scripts.build_personal_clone_skill import load_simple_yaml

    summary = build_delivery_summary(load_simple_yaml(clone_config_path), build_workflow_summary(manifest_path))
    markdown = render_delivery_markdown(summary)
    for path in output_paths:
        path.write_text(markdown, encoding="utf-8")


def personal_interview_has_substantive_answers(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    placeholders = {
        "-",
        "1.",
        "2.",
        "3.",
        "1. 问：",
        "2. 问：",
        "3. 问：",
        "答：",
        "例子：",
        "",
    }
    for line in lines:
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if line in placeholders:
            continue
        if line.startswith("- ") and line[2:].strip() == "":
            continue
        if "：" in line:
            _, value = line.split("：", 1)
            if value.strip():
                return True
            continue
        if re.match(r"^\d+\.\s*$", line):
            continue
        if line not in {"问：", "答："}:
            return True
    return False


def parse_workflow_interview_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {}
    title_match = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    if title_match:
        metadata["workflow_name"] = title_match.group(1).strip()
    for key in ["target_work_unit", "known_context"]:
        match = re.search(rf"^\-\s*{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
        if match:
            metadata[key] = match.group(1).strip()
    if "target_work_unit" not in metadata:
        section_match = re.search(r"^##\s+目标工作单元\s+(.+?)(?=^##\s+|^###\s+|\Z)", text, re.M | re.S)
        if section_match:
            lines = [line.strip(" -") for line in section_match.group(1).splitlines() if line.strip()]
            if lines:
                metadata["target_work_unit"] = lines[0].rstrip("。")
    return metadata
def resolve_target_mode(args: argparse.Namespace) -> str:
    requested = str(getattr(args, "target_mode", "auto") or "auto").strip()
    if requested in {"persona-only", "persona-plus-workflow"}:
        return requested
    if bool(getattr(args, "skip_workflow", False)):
        return "persona-only"
    if any(
        [
            str(getattr(args, "work_unit", "") or "").strip(),
            str(getattr(args, "workflow_name", "") or "").strip(),
            bool(getattr(args, "workflow_interview", "")),
            bool(getattr(args, "stage_confirmation", "")),
            bool(getattr(args, "initial_input", "")),
        ]
    ):
        return "persona-plus-workflow"
    return "persona-only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a personal clone bundle and, when requested, the workflow clone chain."
    )
    parser.add_argument("--interview", help="Path to the personal interview markdown. If omitted, initialize one.")
    parser.add_argument("--output-dir", required=True, help="Output directory for the combined bundle.")
    parser.add_argument("--name", required=True, help="Clone display name.")
    parser.add_argument("--creator", default="", help="Optional creator name.")
    parser.add_argument("--profession", default="", help="Optional profession override.")
    parser.add_argument("--mind-profile", help="Optional mind_profile.md path.")
    parser.add_argument("--system-prompt", help="Optional system_prompt.md path.")
    parser.add_argument("--eval-report", help="Optional eval_report.md path.")
    parser.add_argument("--research-digest", help="Optional research_digest.md path.")
    parser.add_argument("--timestamp", help="Optional timestamp override.")
    parser.add_argument(
        "--target-mode",
        choices=["auto", "persona-only", "persona-plus-workflow"],
        default="auto",
        help="Whether the bundle should target persona only or persona + workflow together.",
    )
    parser.add_argument("--workflow-name", default="", help="Optional workflow name override.")
    parser.add_argument("--work-unit", default="", help="Optional recurring work unit for workflow modeling.")
    parser.add_argument("--known-context", default="", help="Known workflow context.")
    parser.add_argument("--workflow-interview", help="Optional filled workflow_interview.md.")
    parser.add_argument("--stage-confirmation", help="Optional filled stage_confirmation.md.")
    parser.add_argument("--task-id", default="task-001")
    parser.add_argument("--task-summary", default="新建工作流任务")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts")
    parser.add_argument("--initial-input")
    parser.add_argument("--run-until-stop", action="store_true")
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--skip-workflow", action="store_true")
    parser.add_argument("--skip-runtime-bundle", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    personal_interview_path = Path(args.interview).resolve() if args.interview else (output_dir / "personal_interview.md")
    personal_clone_dir = output_dir / "personal-clone-skill"
    workflow_pipeline_dir = output_dir / "workflow-blueprint-pipeline"
    workflow_blueprint_path = workflow_pipeline_dir / "workflow_blueprint.md"
    workflow_clone_skill_dir = workflow_pipeline_dir / "workflow-clone-skill"
    workflow_runtime_bundle_dir = workflow_pipeline_dir / "workflow-runtime-bundle"
    workflow_interview_path = (
        Path(args.workflow_interview).resolve() if args.workflow_interview else (output_dir / "workflow_interview.md")
    )
    interview_status_json = output_dir / "clone_interview_status.json"
    interview_status_md = output_dir / "CLONE_INTERVIEW_STATUS.md"
    interview_state_path = output_dir / "clone_interview_state.json"
    interview_validation_path = output_dir / "clone_interview_validation.json"
    bundle_validation_path = output_dir / "working_clone_bundle_validation.json"
    until_final_summary_path = output_dir / "working_clone_until_final_summary.json"
    next_interview_update_path = output_dir / "NEXT_INTERVIEW_UPDATE.md"
    next_interview_update_json_path = output_dir / "NEXT_INTERVIEW_UPDATE.json"
    pending_interview_actions_path = output_dir / "PENDING_INTERVIEW_ACTIONS.json"
    personal_clone_config = personal_clone_dir / "clone_config.yaml"
    personal_mind_profile = personal_clone_dir / "mind_profile.md"
    personal_system_prompt = personal_clone_dir / "system_prompt.md"
    resolved_target_mode = resolve_target_mode(args)
    workflow_requested = resolved_target_mode == "persona-plus-workflow" and not args.skip_workflow
    workflow_metadata = parse_workflow_interview_metadata(workflow_interview_path)
    resolved_known_context = (
        args.known_context.strip()
        or str(workflow_metadata.get("known_context", "")).strip()
        or f"{args.name} / {args.profession or '未显式指定 profession'}"
    )
    resolved_work_unit = args.work_unit.strip()
    if not workflow_target_defined(resolved_work_unit):
        existing_work_unit = str(workflow_metadata.get("target_work_unit", "")).strip()
        if workflow_target_defined(existing_work_unit):
            resolved_work_unit = existing_work_unit
    if workflow_requested and not workflow_target_defined(resolved_work_unit):
        resolved_work_unit = WORKFLOW_TARGET_PLACEHOLDER
    resolved_workflow_name = (
        args.workflow_name.strip()
        or str(workflow_metadata.get("workflow_name", "")).strip()
        or infer_workflow_name(resolved_work_unit)
    )
    workflow_target_ready = workflow_requested and workflow_target_defined(resolved_work_unit)

    init_personal_interview_cmd = [
        "python3",
        str(workdir / "scripts" / "init_personal_interview.py"),
        "--clone-name",
        args.name,
        "--profession",
        args.profession or "未显式指定",
        "--known-context",
        args.known_context or "暂无",
        "--output",
        str(personal_interview_path),
    ]
    if not args.interview:
        run_command(init_personal_interview_cmd, workdir)

    init_workflow_interview_cmd = [
        "python3",
        str(workdir / "scripts" / "init_workflow_interview.py"),
        "--workflow-name",
        resolved_workflow_name,
        "--work-unit",
        resolved_work_unit or WORKFLOW_TARGET_PLACEHOLDER,
        "--known-context",
        resolved_known_context,
        "--output",
        str(workflow_interview_path),
    ]
    if workflow_requested and not workflow_interview_path.exists():
        run_command(init_workflow_interview_cmd, workdir)

    personal_cmd = [
        "python3",
        str(workdir / "scripts" / "build_clone_from_artifacts.py"),
        "--interview",
        str(personal_interview_path),
        "--output-dir",
        str(personal_clone_dir),
        "--name",
        args.name,
    ]
    if args.creator:
        personal_cmd.extend(["--creator", args.creator])
    if args.profession:
        personal_cmd.extend(["--profession", args.profession])
    if args.mind_profile:
        personal_cmd.extend(["--mind-profile", str(Path(args.mind_profile).resolve())])
    if args.system_prompt:
        personal_cmd.extend(["--system-prompt", str(Path(args.system_prompt).resolve())])
    if args.eval_report:
        personal_cmd.extend(["--eval-report", str(Path(args.eval_report).resolve())])
    if args.research_digest:
        personal_cmd.extend(["--research-digest", str(Path(args.research_digest).resolve())])
    if args.timestamp:
        personal_cmd.extend(["--timestamp", args.timestamp])
    personal_interview_ready = personal_interview_has_substantive_answers(personal_interview_path)
    if personal_interview_ready:
        run_command(personal_cmd, workdir)

    workflow_enabled = workflow_requested
    workflow_cmd: list[str] = []
    if workflow_enabled and workflow_target_ready and personal_interview_ready:
        pipeline_manifest_path = workflow_pipeline_dir / "workflow_blueprint_pipeline_manifest.json"
        pipeline_refresh_snapshot = snapshot_refresh_metadata(pipeline_manifest_path)
        workflow_cmd = [
            "python3",
            str(workdir / "scripts" / "bootstrap_workflow_blueprint.py"),
            "--work-unit",
            resolved_work_unit,
            "--output-dir",
            str(workflow_pipeline_dir),
            "--clone-config",
            str(personal_clone_config),
            "--mind-profile",
            str(personal_mind_profile),
            "--system-prompt",
            str(personal_system_prompt),
            "--task-id",
            args.task_id,
            "--task-summary",
            args.task_summary,
            "--workspace",
            args.workspace,
            "--artifact-dir",
            args.artifact_dir,
            "--max-turns",
            str(args.max_turns),
        ]
        if resolved_workflow_name:
            workflow_cmd.extend(["--workflow-name", resolved_workflow_name])
        workflow_cmd.extend(["--known-context", resolved_known_context])
        workflow_cmd.extend(["--interview", str(workflow_interview_path)])
        if args.stage_confirmation:
            workflow_cmd.extend(["--stage-confirmation", str(Path(args.stage_confirmation).resolve())])
        if args.profession:
            workflow_cmd.extend(["--profession", args.profession])
        if args.initial_input:
            workflow_cmd.extend(["--initial-input", args.initial_input])
        if args.run_until_stop:
            workflow_cmd.append("--run-until-stop")
        if args.execute_safe:
            workflow_cmd.append("--execute-safe")
        if args.skip_runtime_bundle:
            workflow_cmd.append("--skip-runtime-bundle")
        run_command(workflow_cmd, workdir)
        restore_refresh_metadata_if_missing(pipeline_manifest_path, pipeline_refresh_snapshot)

    plan_interview_cmd = [
        "python3",
        str(workdir / "scripts" / "plan_clone_interview_next.py"),
        "--personal-interview",
        str(personal_interview_path),
        "--output-json",
        str(interview_status_json),
        "--output-md",
        str(interview_status_md),
    ]
    if workflow_enabled:
        plan_interview_cmd.extend(["--workflow-interview", str(workflow_interview_path)])
    run_command(plan_interview_cmd, workdir)
    init_interview_state_cmd = [
        "python3",
        str(workdir / "scripts" / "init_clone_interview_state.py"),
        "--personal-interview",
        str(personal_interview_path),
        "--output",
        str(interview_state_path),
        "--clone-name",
        args.name,
    ]
    if workflow_enabled:
        init_interview_state_cmd.extend(["--workflow-interview", str(workflow_interview_path)])
    run_command(init_interview_state_cmd, workdir)
    build_next_update_cmd = [
        "python3",
        str(workdir / "scripts" / "build_next_interview_update.py"),
        "--state",
        str(interview_state_path),
        "--output-md",
        str(next_interview_update_path),
        "--output-json",
        str(next_interview_update_json_path),
    ]
    run_command(build_next_update_cmd, workdir)
    build_pending_actions_cmd = [
        "python3",
        str(workdir / "scripts" / "build_pending_interview_actions.py"),
        "--state",
        str(interview_state_path),
        "--output",
        str(pending_interview_actions_path),
        "--personal-interview",
        str(personal_interview_path),
        "--workflow-interview",
        str(workflow_interview_path),
        "--next-update-json",
        str(next_interview_update_json_path),
        "--run-turn-command",
        format_command(
            [
                "python3",
                "scripts/run_clone_interview_turn.py",
                "--state",
                str(interview_state_path),
                "--personal-interview",
                str(personal_interview_path),
                "--input-json",
                str(next_interview_update_json_path),
                "--output-dir",
                str(output_dir / "clone-interview-turn-output"),
            ]
            + (["--workflow-interview", str(workflow_interview_path)] if workflow_enabled else [])
        ),
        "--run-turn-output",
        str(output_dir / "clone-interview-turn-output" / "clone_interview_turn_summary.json"),
        "--refresh-command",
        format_command(
            [
                "python3",
                str(workdir / "scripts" / "refresh_working_clone_bundle.py"),
                "--manifest",
                str(output_dir / "working_clone_bundle_manifest.json"),
            ]
        ),
        "--refresh-output",
        str(bundle_validation_path),
    ]
    run_command(build_pending_actions_cmd, workdir)
    interview_validation_cmd = [
        "python3",
        str(workdir / "scripts" / "validate_clone_interview_state.py"),
        "--input",
        str(interview_state_path),
        "--format",
        "json",
    ]
    proc = subprocess.run(interview_validation_cmd, cwd=workdir, check=True, capture_output=True, text=True)
    interview_validation = json.loads(proc.stdout)
    interview_validation_path.write_text(
        json.dumps(interview_validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest: dict[str, Any] = {
        "clone_name": args.name,
        "profession": args.profession,
        "target_mode": resolved_target_mode,
        "workflow_name": resolved_workflow_name if workflow_enabled else "",
        "work_unit": resolved_work_unit if workflow_enabled else "",
        "known_context": resolved_known_context if workflow_enabled else (args.known_context or ""),
        "interview": str(personal_interview_path),
        "personal_clone_skill": str(personal_clone_dir),
        "workflow_pipeline": str(workflow_pipeline_dir),
        "workflow_blueprint": str(workflow_pipeline_dir / "workflow_blueprint.md"),
        "workflow_clone_skill": str(workflow_clone_skill_dir),
        "workflow_runtime_bundle": str(workflow_pipeline_dir / "workflow-runtime-bundle"),
        "workflow_interview": str(workflow_interview_path),
        "interview_status_json": str(interview_status_json),
        "interview_status_md": str(interview_status_md),
        "interview_state": str(interview_state_path),
        "interview_validation_path": str(interview_validation_path),
        "next_interview_update_path": str(next_interview_update_path),
        "next_interview_update_json_path": str(next_interview_update_json_path),
        "pending_interview_actions_path": str(pending_interview_actions_path),
        "interview_validation": interview_validation,
        "steps": {
            "personal_interview": personal_interview_path.exists(),
            "personal_interview_ready": personal_interview_ready,
            "workflow_interview": workflow_interview_path.exists() if workflow_enabled else False,
            "personal_clone_skill": personal_clone_dir.exists(),
            "workflow_enabled": workflow_enabled,
            "workflow_target_defined": workflow_target_ready if workflow_enabled else False,
            "workflow_pipeline": workflow_pipeline_dir.exists() and (workflow_pipeline_dir / "workflow_blueprint_pipeline_manifest.json").exists(),
            "workflow_clone_skill": workflow_clone_skill_dir.exists(),
            "workflow_runtime_bundle": (workflow_pipeline_dir / "workflow-runtime-bundle").exists(),
        },
        "entrypoints": {
            "init_personal_interview": repo_command(
                "init_personal_interview.py",
                "--clone-name",
                args.name,
                "--profession",
                args.profession or "未显式指定",
                "--known-context",
                args.known_context or "暂无",
                "--output",
                str(personal_interview_path),
            ),
            "init_workflow_interview": repo_command(
                "init_workflow_interview.py",
                "--workflow-name",
                resolved_workflow_name,
                "--work-unit",
                resolved_work_unit or WORKFLOW_TARGET_PLACEHOLDER,
                "--known-context",
                resolved_known_context,
                "--output",
                str(workflow_interview_path),
            ),
            "plan_clone_interview_next": repo_command(
                "plan_clone_interview_next.py",
                "--personal-interview",
                str(personal_interview_path),
                "--output-json",
                str(interview_status_json),
                "--output-md",
                str(interview_status_md),
                *(["--workflow-interview", str(workflow_interview_path)] if workflow_enabled else []),
            ),
            "init_clone_interview_state": repo_command(
                "init_clone_interview_state.py",
                "--personal-interview",
                str(personal_interview_path),
                "--output",
                str(interview_state_path),
                "--clone-name",
                args.name,
                *(["--workflow-interview", str(workflow_interview_path)] if workflow_enabled else []),
            ),
            "build_next_interview_update": repo_command(
                "build_next_interview_update.py",
                "--state",
                str(interview_state_path),
                "--output-md",
                str(next_interview_update_path),
                "--output-json",
                str(next_interview_update_json_path),
            ),
            "build_pending_interview_actions": repo_command(
                "build_pending_interview_actions.py",
                "--state",
                str(interview_state_path),
                "--output",
                str(pending_interview_actions_path),
                "--personal-interview",
                str(personal_interview_path),
                "--workflow-interview",
                str(workflow_interview_path),
                "--next-update-json",
                str(next_interview_update_json_path),
                "--run-turn-command",
                format_command(
                    repo_command(
                        "run_clone_interview_turn.py",
                        "--state",
                        str(interview_state_path),
                        "--personal-interview",
                        str(personal_interview_path),
                        "--input-json",
                        str(next_interview_update_json_path),
                        "--output-dir",
                        str(output_dir / "clone-interview-turn-output"),
                        *(["--workflow-interview", str(workflow_interview_path)] if workflow_enabled else []),
                    )
                ),
                "--run-turn-output",
                str(output_dir / "clone-interview-turn-output" / "clone_interview_turn_summary.json"),
                "--refresh-command",
                format_command(
                    repo_command(
                        "refresh_working_clone_bundle.py",
                        "--manifest",
                        str(output_dir / "working_clone_bundle_manifest.json"),
                    )
                ),
                "--refresh-output",
                str(bundle_validation_path),
            ),
            "refresh_working_clone_bundle": repo_command(
                "refresh_working_clone_bundle.py",
                "--manifest",
                str(output_dir / "working_clone_bundle_manifest.json"),
            ),
            "run_working_clone_until_final": repo_command(
                "run_working_clone_until_final.py",
                "--manifest",
                str(output_dir / "working_clone_bundle_manifest.json"),
                "--output",
                str(output_dir / "working_clone_until_final_summary.json"),
                "--max-cycles",
                "5",
            ),
            "run_clone_interview_turn": repo_command(
                "run_clone_interview_turn.py",
                "--state",
                str(interview_state_path),
                "--personal-interview",
                str(personal_interview_path),
                "--input-json",
                str(next_interview_update_json_path),
                "--output-dir",
                str(output_dir / "clone-interview-turn-output"),
            ),
            "build_personal_clone_skill": repo_command(
                "build_clone_from_artifacts.py",
                "--interview",
                str(personal_interview_path),
                "--output-dir",
                str(personal_clone_dir),
                "--name",
                args.name,
                *(["--creator", args.creator] if args.creator else []),
                *(["--profession", args.profession] if args.profession else []),
                *(["--mind-profile", str(Path(args.mind_profile).resolve())] if args.mind_profile else []),
                *(["--system-prompt", str(Path(args.system_prompt).resolve())] if args.system_prompt else []),
                *(["--eval-report", str(Path(args.eval_report).resolve())] if args.eval_report else []),
                *(["--research-digest", str(Path(args.research_digest).resolve())] if args.research_digest else []),
                *(["--timestamp", args.timestamp] if args.timestamp else []),
            ),
            "build_workflow_pipeline": workflow_cmd
            if workflow_cmd
            else repo_command(
                "bootstrap_workflow_blueprint.py",
                "--work-unit",
                resolved_work_unit or "<work-unit>",
                "--output-dir",
                str(workflow_pipeline_dir),
                "--clone-config",
                str(personal_clone_config),
                "--mind-profile",
                str(personal_mind_profile),
                "--system-prompt",
                str(personal_system_prompt),
                *(["--workflow-name", resolved_workflow_name] if resolved_workflow_name else []),
                "--known-context",
                resolved_known_context,
                "--interview",
                str(workflow_interview_path),
            ),
            "run_workflow_turn": repo_command(
                "run_workflow_turn.py",
                "--workflow-blueprint",
                str(workflow_pipeline_dir / "workflow_blueprint.md"),
                "--state",
                str(workflow_pipeline_dir / "workflow-runtime-bundle" / "workflow_task_state.yaml"),
                "--input",
                "<your-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                args.profession or "<profession>",
                "--output-dir",
                str(workflow_pipeline_dir / "workflow-runtime-bundle" / "workflow-turn-output"),
            ),
            "run_workflow_until_stop": repo_command(
                "run_workflow_until_stop.py",
                "--workflow-blueprint",
                str(workflow_pipeline_dir / "workflow_blueprint.md"),
                "--state",
                str(workflow_pipeline_dir / "workflow-runtime-bundle" / "workflow_task_state.yaml"),
                "--initial-input",
                "<your-initial-update>",
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                args.profession or "<profession>",
                "--max-turns",
                str(args.max_turns),
                "--output-dir",
                str(workflow_pipeline_dir / "workflow-runtime-bundle" / "workflow-run-output"),
            ),
        },
    }
    if args.execute_safe:
        manifest["entrypoints"]["run_workflow_turn"].append("--execute-safe")
        manifest["entrypoints"]["run_workflow_until_stop"].append("--execute-safe")
    if workflow_enabled:
        manifest["entrypoints"]["run_clone_interview_turn"].extend(["--workflow-interview", str(workflow_interview_path)])
    if workflow_enabled:
        manifest["entrypoints"]["build_workflow_pipeline"] = repo_command(
            "bootstrap_workflow_blueprint.py",
            "--work-unit",
            resolved_work_unit or "<work-unit>",
            "--output-dir",
            str(workflow_pipeline_dir),
            "--clone-config",
            str(personal_clone_config),
            "--mind-profile",
            str(personal_mind_profile),
            "--system-prompt",
            str(personal_system_prompt),
            "--task-id",
            args.task_id,
            "--task-summary",
            args.task_summary,
            "--workspace",
            args.workspace,
            "--artifact-dir",
            args.artifact_dir,
            "--max-turns",
            str(args.max_turns),
            *(["--workflow-name", resolved_workflow_name] if resolved_workflow_name else []),
            "--known-context",
            resolved_known_context,
            "--interview",
            str(workflow_interview_path),
            *(["--stage-confirmation", str(Path(args.stage_confirmation).resolve())] if args.stage_confirmation else []),
            *(["--profession", args.profession] if args.profession else []),
            *(["--initial-input", args.initial_input] if args.initial_input else []),
            *(["--run-until-stop"] if args.run_until_stop else []),
            *(["--execute-safe"] if args.execute_safe else []),
            *(["--skip-runtime-bundle"] if args.skip_runtime_bundle else []),
        )
    manifest["entrypoints"]["build_personal_clone_skill"].extend(
        [
            "--interview-state",
            str(interview_state_path),
            "--release-target",
            str(interview_validation.get("recommended_release", "draft")),
        ]
    )

    manifest_path = output_dir / "working_clone_bundle_manifest.json"
    bundle_validation_cmd = [
        "python3",
        str(workdir / "scripts" / "validate_working_clone_bundle.py"),
        "--manifest",
        str(manifest_path),
        "--format",
        "json",
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bundle_proc = subprocess.run(bundle_validation_cmd, cwd=workdir, check=True, capture_output=True, text=True)
    bundle_validation = json.loads(bundle_proc.stdout)
    bundle_validation_path.write_text(
        json.dumps(bundle_validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["bundle_validation_path"] = str(bundle_validation_path)
    manifest["bundle_validation"] = bundle_validation
    pending_actions = load_pending_actions(manifest)
    pending_action_groups = split_pending_actions(pending_actions)
    recommended_next_command = choose_recommended_next_command(manifest, bundle_validation, pending_action_groups)
    manifest["pending_interview_action_groups"] = pending_action_groups
    manifest["pending_interview_action_group_counts"] = {
        "current_executable_now_count": len(pending_action_groups["current_executable_now"]),
        "requires_manual_edit_first_count": len(pending_action_groups["requires_manual_edit_first"]),
        "needs_content_edit_count": len(pending_action_groups["needs_content_edit"]),
        "needs_human_confirmation_count": len(pending_action_groups["needs_human_confirmation"]),
        "needs_build_step_count": len(pending_action_groups["needs_build_step"]),
    }
    manifest["recommended_next_command"] = recommended_next_command
    manifest["command_style"] = "repo_relative_scripts"
    manifest["source_artifacts"] = build_source_artifacts(
        {
            "personal_interview": personal_interview_path,
            "interview_state": interview_state_path,
            "clone_config": personal_clone_config if personal_clone_config.exists() else None,
            "mind_profile": personal_mind_profile if personal_mind_profile.exists() else None,
            "system_prompt": personal_system_prompt if personal_system_prompt.exists() else None,
            "workflow_interview": workflow_interview_path if workflow_interview_path.exists() else None,
            "workflow_blueprint": workflow_blueprint_path if workflow_blueprint_path.exists() else None,
            "workflow_pipeline_dir": workflow_pipeline_dir if workflow_pipeline_dir.exists() else None,
            "workflow_clone_skill_dir": workflow_clone_skill_dir if workflow_clone_skill_dir.exists() else None,
            "workflow_runtime_bundle_dir": workflow_runtime_bundle_dir if workflow_runtime_bundle_dir.exists() else None,
        }
    )
    refresh_inputs = [personal_interview_path]
    if args.mind_profile:
        refresh_inputs.append(Path(args.mind_profile).resolve())
    if args.system_prompt:
        refresh_inputs.append(Path(args.system_prompt).resolve())
    if args.eval_report:
        refresh_inputs.append(Path(args.eval_report).resolve())
    if args.research_digest:
        refresh_inputs.append(Path(args.research_digest).resolve())
    if workflow_enabled:
        refresh_inputs.append(workflow_interview_path)
    if args.stage_confirmation:
        refresh_inputs.append(Path(args.stage_confirmation).resolve())
    refresh_dependency_groups = ["bundle_core", *(["workflow_shared"] if workflow_enabled else [])]
    refresh_inputs.extend(resolve_refresh_dependencies(workdir, *refresh_dependency_groups))
    manifest["refresh_dependency_groups"] = refresh_dependency_groups
    manifest["refresh_dependency_index"] = build_refresh_dependency_index(workdir, *refresh_dependency_groups)
    manifest["refresh_cache"] = build_refresh_cache(refresh_inputs)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_delivery_summaries(
        personal_clone_config,
        manifest_path,
        [
            output_dir / "DELIVERY_SUMMARY.md",
            personal_clone_dir / "DELIVERY_SUMMARY.md",
        ],
    )

    until_final_summary = {
        "stop_reason": "bootstrap_snapshot",
        "cycle_count": 0,
        "manifest": str(manifest_path),
        "bundle_validation_path": str(bundle_validation_path),
        "next_interview_update_path": str(next_interview_update_path),
        "next_interview_update": load_optional_json(next_interview_update_json_path),
        "pending_interview_actions_path": str(pending_interview_actions_path),
        "pending_interview_actions": pending_actions,
        "pending_interview_action_groups": pending_action_groups,
        "recommended_next_command": recommended_next_command,
        "final_recommended_release": str(bundle_validation.get("recommended_release", "draft")),
        "final_ready": bool(bundle_validation.get("final_ready", False)),
        "blockers": bundle_validation.get("blockers", []),
        "cycles": [],
    }
    until_final_summary_path.write_text(
        json.dumps(until_final_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    readme_template = workdir / "templates" / "working_clone_bundle_readme_template.md"
    if readme_template.exists():
        snapshot = summarize_bundle_snapshot(
            workflow_enabled,
            workflow_target_ready,
            manifest["steps"],
            bundle_validation,
            recommended_next_command,
        )
        user_usage = build_user_usage_summary(
            workflow_enabled,
            workflow_target_ready,
            manifest["steps"],
            recommended_next_command,
        )
        (output_dir / "WORKING_CLONE_BUNDLE_README.md").write_text(
            render_template(
                readme_template,
                {
                    "clone_name": args.name,
                    "profession": args.profession or "未显式指定",
                    "target_mode": resolved_target_mode,
                    "workflow_name": resolved_workflow_name if workflow_enabled else "未启用",
                    "work_unit": resolved_work_unit if workflow_enabled else "未启用",
                    "personal_interview": str(personal_interview_path),
                    "workflow_enabled": "true" if workflow_enabled else "false",
                    "workflow_target_defined": "true" if workflow_target_ready else "false",
                    "personal_interview_ready": "true" if personal_interview_ready else "false",
                    "recommended_release": str(interview_validation.get("recommended_release", "draft")),
                    "interview_final_ready": "true" if interview_validation.get("final_ready", False) else "false",
                    "bundle_recommended_release": str(bundle_validation.get("recommended_release", "draft")),
                    "bundle_final_ready": "true" if bundle_validation.get("final_ready", False) else "false",
                    "snapshot_status": snapshot["status"],
                    "snapshot_next_action": snapshot["next_action"],
                    "snapshot_blocker_summary": snapshot["blocker_summary"],
                    "user_persona_usage_now": user_usage["persona_usage_now"],
                    "user_workflow_usage_now": user_usage["workflow_usage_now"],
                    "user_edit_or_input": user_usage["edit_or_input"],
                    "personal_clone_ready": "true" if manifest["steps"]["personal_clone_skill"] else "false",
                    "workflow_pipeline_ready": "true" if manifest["steps"]["workflow_pipeline"] else "false",
                    "workflow_clone_skill_ready": "true" if manifest["steps"]["workflow_clone_skill"] else "false",
                    "runtime_bundle_ready": "true" if manifest["steps"]["workflow_runtime_bundle"] else "false",
                    "personal_clone_skill": manifest["personal_clone_skill"],
                    "workflow_interview": manifest["workflow_interview"],
                    "workflow_pipeline": manifest["workflow_pipeline"],
                    "workflow_blueprint": manifest["workflow_blueprint"],
                    "workflow_clone_skill": manifest["workflow_clone_skill"],
                    "workflow_runtime_bundle": manifest["workflow_runtime_bundle"],
                    "interview_status_md": manifest["interview_status_md"],
                    "interview_state": manifest["interview_state"],
                    "interview_validation_path": manifest["interview_validation_path"],
                    "bundle_validation_path": manifest["bundle_validation_path"],
                    "next_interview_update_path": manifest["next_interview_update_path"],
                    "next_interview_update_json_path": manifest["next_interview_update_json_path"],
                    "pending_interview_actions_path": manifest["pending_interview_actions_path"],
                    "bundle_blockers": (
                        "无"
                        if not bundle_validation.get("blockers")
                        else "；".join(
                            f"{item.get('item', '<unknown>')}：{item.get('reason', '未就绪')}"
                            for item in bundle_validation["blockers"]
                        )
                    ),
                    "pending_personal_sections": ", ".join(bundle_validation.get("personal_interview_sections_pending", [])) or "无",
                    "pending_workflow_sections": ", ".join(bundle_validation.get("workflow_interview_sections_pending", [])) or "无",
                    "needs_content_edit_count": str(manifest["pending_interview_action_group_counts"]["needs_content_edit_count"]),
                    "needs_human_confirmation_count": str(manifest["pending_interview_action_group_counts"]["needs_human_confirmation_count"]),
                    "needs_build_step_count": str(manifest["pending_interview_action_group_counts"]["needs_build_step_count"]),
                    "current_executable_now_count": str(manifest["pending_interview_action_group_counts"]["current_executable_now_count"]),
                    "requires_manual_edit_first_count": str(manifest["pending_interview_action_group_counts"]["requires_manual_edit_first_count"]),
                    "current_executable_now_details": "\n".join(
                        format_pending_details(manifest["pending_interview_action_groups"].get("current_executable_now", []), "current_executable_now")
                    )
                    or "无",
                    "requires_manual_edit_first_details": "\n".join(
                        format_pending_details(manifest["pending_interview_action_groups"].get("requires_manual_edit_first", []), "requires_manual_edit_first")
                    )
                    or "无",
                    "pending_details": "\n".join(
                        format_pending_details(bundle_validation.get("personal_pending_details", []), "personal")
                        + format_pending_details(bundle_validation.get("workflow_pending_details", []), "workflow")
                    )
                    or "无",
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
                    "init_personal_interview": format_command(manifest["entrypoints"]["init_personal_interview"]),
                    "init_workflow_interview": format_command(manifest["entrypoints"]["init_workflow_interview"]),
                    "plan_clone_interview_next": format_command(manifest["entrypoints"]["plan_clone_interview_next"]),
                    "init_clone_interview_state": format_command(manifest["entrypoints"]["init_clone_interview_state"]),
                    "build_next_interview_update": format_command(manifest["entrypoints"]["build_next_interview_update"]),
                    "build_pending_interview_actions": format_command(manifest["entrypoints"]["build_pending_interview_actions"]),
                    "refresh_working_clone_bundle": format_command(manifest["entrypoints"]["refresh_working_clone_bundle"]),
                    "run_working_clone_until_final": format_command(manifest["entrypoints"]["run_working_clone_until_final"]),
                    "run_clone_interview_turn": format_command(manifest["entrypoints"]["run_clone_interview_turn"]),
                    "build_personal_clone_skill": format_command(manifest["entrypoints"]["build_personal_clone_skill"]),
                    "build_workflow_pipeline": format_command(manifest["entrypoints"]["build_workflow_pipeline"]),
                    "run_workflow_turn": format_command(manifest["entrypoints"]["run_workflow_turn"]),
                    "run_workflow_until_stop": format_command(manifest["entrypoints"]["run_workflow_until_stop"]),
                },
            ),
            encoding="utf-8",
        )
    stack_summary = build_optional_stack_summary(
        bundle_dir=output_dir,
        pipeline_dir=workflow_pipeline_dir if workflow_pipeline_dir.exists() else None,
        runtime_dir=workflow_runtime_bundle_dir if workflow_runtime_bundle_dir.exists() else None,
        personal_skill_dir=personal_clone_dir if personal_clone_dir.exists() else None,
        workflow_skill_dir=(workflow_pipeline_dir / "workflow-clone-skill") if (workflow_pipeline_dir / "workflow-clone-skill").exists() else None,
        selection_mode="working_bundle_output",
    )
    (output_dir / "STACK_SUMMARY.json").write_text(
        json.dumps(stack_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
