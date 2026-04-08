#!/usr/bin/env python3
"""Shared dispatch helpers for working-clone bundle orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from workflow_target_utils import infer_workflow_target_defined
except ModuleNotFoundError:
    from scripts.workflow_target_utils import infer_workflow_target_defined


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def load_pending_actions(manifest: dict[str, Any]) -> dict[str, Any]:
    path = str(manifest.get("pending_interview_actions_path", "")).strip()
    if path and Path(path).exists():
        return load_json(Path(path))
    return {"personal": [], "workflow": []}


def split_pending_actions(pending_actions: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    executable_now: list[dict[str, Any]] = []
    requires_manual_edit_first: list[dict[str, Any]] = []
    needs_content_edit: list[dict[str, Any]] = []
    needs_human_confirmation: list[dict[str, Any]] = []
    needs_build_step: list[dict[str, Any]] = []
    for scope in ["personal", "workflow"]:
        items = pending_actions.get(scope, []) if isinstance(pending_actions.get(scope, []), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            readiness = str(item.get("execution_readiness", "")).strip()
            if readiness == "current_executable_now":
                executable_now.append(item)
            else:
                requires_manual_edit_first.append(item)
                if readiness == "needs_content_edit":
                    needs_content_edit.append(item)
                elif readiness == "needs_human_confirmation":
                    needs_human_confirmation.append(item)
                else:
                    needs_build_step.append(item)
    return {
        "current_executable_now": executable_now,
        "requires_manual_edit_first": requires_manual_edit_first,
        "needs_content_edit": needs_content_edit,
        "needs_human_confirmation": needs_human_confirmation,
        "needs_build_step": needs_build_step,
    }


def format_command(command: list[str]) -> str:
    return " ".join(str(x) for x in command)
def choose_recommended_next_command(
    manifest: dict[str, Any],
    validation: dict[str, Any],
    pending_action_groups: dict[str, Any],
) -> dict[str, str]:
    entrypoints = manifest.get("entrypoints", {}) if isinstance(manifest.get("entrypoints", {}), dict) else {}
    steps = manifest.get("steps", {}) if isinstance(manifest.get("steps", {}), dict) else {}
    blockers = validation.get("blockers", []) if isinstance(validation.get("blockers", []), list) else []
    executable_now = (
        pending_action_groups.get("current_executable_now", [])
        if isinstance(pending_action_groups.get("current_executable_now", []), list)
        else []
    )
    requires_manual = (
        pending_action_groups.get("requires_manual_edit_first", [])
        if isinstance(pending_action_groups.get("requires_manual_edit_first", []), list)
        else []
    )
    workflow_target_defined = infer_workflow_target_defined(manifest, steps)

    if executable_now:
        first = executable_now[0] if isinstance(executable_now[0], dict) else {}
        contract = first.get("execution_contract", {}) if isinstance(first.get("execution_contract", {}), dict) else {}
        return {
            "mode": "ready_to_run",
            "label": str(contract.get("type", "")).strip() or "run_clone_interview_turn",
            "command": str(contract.get("command", "")).strip(),
            "scope": str(first.get("scope", "")).strip(),
            "section": str(first.get("section", "")).strip(),
            "manual_edit_required": "false",
            "priority": "high",
            "reason": str(first.get("execution_readiness_reason", "")).strip() or "当前存在可直接执行的访谈动作。",
            "input_source": str(contract.get("input_source", "")).strip(),
            "output_artifact": str(contract.get("output_artifact", "")).strip(),
            "stop_condition": str(contract.get("stop_condition", "")).strip(),
        }

    if requires_manual:
        first = requires_manual[0] if isinstance(requires_manual[0], dict) else {}
        contract = first.get("execution_contract", {}) if isinstance(first.get("execution_contract", {}), dict) else {}
        return {
            "mode": str(first.get("execution_mode", "")).strip() or "needs_manual_edit_first",
            "label": str(contract.get("type", "")).strip() or "edit_then_refresh",
            "command": str(contract.get("command", "")).strip() or format_command(entrypoints.get("refresh_working_clone_bundle", [])),
            "scope": str(first.get("scope", "")).strip(),
            "section": str(first.get("section", "")).strip(),
            "manual_edit_required": "true",
            "priority": "high",
            "reason": str(first.get("execution_readiness_reason", "")).strip() or "当前剩余动作需要先人工编辑。",
            "input_source": str(contract.get("input_source", "")).strip(),
            "output_artifact": str(contract.get("output_artifact", "")).strip(),
            "stop_condition": str(contract.get("stop_condition", "")).strip(),
        }

    if blockers:
        first = blockers[0] if isinstance(blockers[0], dict) else {}
        item = str(first.get("item", "")).strip()
        if item == "workflow_target":
            return {
                "mode": "needs_content_edit",
                "label": "edit_workflow_interview",
                "command": format_command(entrypoints.get("refresh_working_clone_bundle", [])),
                "scope": "workflow",
                "section": "workflow_target",
                "manual_edit_required": "true",
                "priority": "high",
                "reason": "目标已包含 workflow，但第一类典型工作还未确认；先编辑 workflow_interview.md 顶部的 target_work_unit，再刷新 bundle。",
                "input_source": str(manifest.get("workflow_interview", "")),
                "output_artifact": str(manifest.get("workflow_interview", "")),
                "stop_condition": "当 target_work_unit 明确后，刷新 bundle 并继续构建 workflow pipeline。",
            }
        if item == "personal_clone_skill":
            return {
                "mode": "needs_build_step",
                "label": "build_personal_clone_skill",
                "command": format_command(entrypoints.get("build_personal_clone_skill", [])),
                "scope": "bundle",
                "section": "personal_clone_skill",
                "manual_edit_required": "false",
                "priority": "medium",
                "reason": "人格层 skill 尚未生成，先补齐人格层构建。",
                "input_source": str(manifest.get("interview_state", "")),
                "output_artifact": str(manifest.get("personal_clone_skill", "")),
                "stop_condition": "当 personal clone skill 目录生成后，刷新 bundle validation。",
            }
        if item in {"workflow_pipeline", "workflow_clone_skill", "workflow_runtime_bundle"}:
            return {
                "mode": "needs_build_step",
                "label": "build_workflow_pipeline",
                "command": format_command(entrypoints.get("build_workflow_pipeline", [])),
                "scope": "bundle",
                "section": item,
                "manual_edit_required": "false",
                "priority": "medium",
                "reason": "工作流层产物未齐，先补齐 workflow blueprint / clone skill / runtime 链路。",
                "input_source": str(manifest.get("workflow_interview", "")),
                "output_artifact": str(manifest.get("workflow_clone_skill", "") or manifest.get("workflow_pipeline", "")),
                "stop_condition": "当 workflow pipeline、clone skill、runtime bundle 产物齐备后，刷新 bundle validation。",
            }

    if not bool(steps.get("personal_clone_skill", False)):
        return {
            "mode": "needs_build_step",
            "label": "build_personal_clone_skill",
            "command": format_command(entrypoints.get("build_personal_clone_skill", [])),
            "scope": "bundle",
            "section": "personal_clone_skill",
            "manual_edit_required": "false",
            "priority": "medium",
            "reason": "人格层 skill 还未构建。",
            "input_source": str(manifest.get("interview_state", "")),
            "output_artifact": str(manifest.get("personal_clone_skill", "")),
            "stop_condition": "当 personal clone skill 目录生成后，刷新 bundle validation。",
        }
    if bool(steps.get("workflow_enabled", False)) and not workflow_target_defined:
        return {
            "mode": "needs_content_edit",
            "label": "edit_workflow_interview",
            "command": format_command(entrypoints.get("refresh_working_clone_bundle", [])),
            "scope": "workflow",
            "section": "workflow_target",
            "manual_edit_required": "true",
            "priority": "high",
            "reason": "workflow 目标尚未明确；先在 workflow_interview.md 顶部填写 target_work_unit，再刷新 bundle。",
            "input_source": str(manifest.get("workflow_interview", "")),
            "output_artifact": str(manifest.get("workflow_interview", "")),
            "stop_condition": "当 target_work_unit 明确后，刷新 bundle 并继续构建 workflow pipeline。",
        }
    if bool(steps.get("workflow_enabled", False)) and (
        not bool(steps.get("workflow_pipeline", False)) or not bool(steps.get("workflow_clone_skill", False))
    ):
        return {
            "mode": "needs_build_step",
            "label": "build_workflow_pipeline",
            "command": format_command(entrypoints.get("build_workflow_pipeline", [])),
            "scope": "bundle",
            "section": "workflow_pipeline",
            "manual_edit_required": "false",
            "priority": "medium",
            "reason": "工作流 blueprint / clone skill / runtime 还未齐备。",
            "input_source": str(manifest.get("workflow_interview", "")),
            "output_artifact": str(manifest.get("workflow_clone_skill", "") or manifest.get("workflow_pipeline", "")),
            "stop_condition": "当 workflow pipeline、clone skill、runtime bundle 产物齐备后，刷新 bundle validation。",
        }
    if bool(steps.get("workflow_runtime_bundle", False)):
        return {
            "mode": "ready_to_run",
            "label": "run_workflow_turn",
            "command": format_command(entrypoints.get("run_workflow_turn", [])),
            "scope": "workflow",
            "section": "runtime_turn",
            "manual_edit_required": "false",
            "priority": "low",
            "reason": "bundle 已 final-ready 或至少 runtime 已就绪，可以继续跑 workflow turn。",
            "input_source": "<runtime task input>",
            "output_artifact": str(
                Path(str(manifest.get("workflow_runtime_bundle", "")).strip())
                / "workflow-turn-output"
                / "workflow_turn_summary.json"
            ),
            "stop_condition": "当 workflow turn 返回 needs_user 或任务完成时停止。",
        }
    return {
        "mode": "needs_build_step",
        "label": "refresh_working_clone_bundle",
        "command": format_command(entrypoints.get("refresh_working_clone_bundle", [])),
        "scope": "bundle",
        "section": "refresh",
        "manual_edit_required": "false",
        "priority": "low",
        "reason": "默认建议先刷新 bundle 状态。",
        "input_source": str(manifest.get("interview_state", "")),
        "output_artifact": str(manifest.get("bundle_validation_path", "")),
        "stop_condition": "当 bundle validation 更新后重新判断下一步。",
    }
