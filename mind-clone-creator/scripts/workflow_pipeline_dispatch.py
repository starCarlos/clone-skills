#!/usr/bin/env python3
"""Shared dispatch helpers for workflow-blueprint pipeline orchestration."""

from __future__ import annotations

from typing import Any


def format_command(command: list[str]) -> str:
    return " ".join(str(x) for x in command)


def choose_recommended_pipeline_command(manifest: dict[str, Any]) -> dict[str, str]:
    steps = manifest.get("steps", {}) if isinstance(manifest.get("steps", {}), dict) else {}
    entrypoints = manifest.get("entrypoints", {}) if isinstance(manifest.get("entrypoints", {}), dict) else {}
    interview = str(manifest.get("interview", "")).strip()
    stage_confirmation = str(manifest.get("stage_confirmation", "")).strip()

    if not bool(steps.get("interview_substantive", False)):
        return {
            "mode": "needs_content_edit",
            "label": "build_stage_confirmation",
            "command": format_command(entrypoints.get("build_stage_confirmation", [])),
            "scope": "workflow",
            "section": "W1-W7",
            "manual_edit_required": "true",
            "priority": "high",
            "reason": f"先填写或补充 {interview} 的 W1-W7 回答，再进入阶段确认。",
            "input_source": interview,
            "output_artifact": stage_confirmation,
            "stop_condition": "当 workflow interview 出现实质性回答后，重新生成阶段确认稿。",
        }
    if not bool(steps.get("stage_confirmation", False)):
        return {
            "mode": "needs_build_step",
            "label": "build_stage_confirmation",
            "command": format_command(entrypoints.get("build_stage_confirmation", [])),
            "scope": "workflow",
            "section": "stage_confirmation",
            "manual_edit_required": "false",
            "priority": "high",
            "reason": "workflow interview 已有实质内容，先生成阶段确认稿。",
            "input_source": interview,
            "output_artifact": stage_confirmation,
            "stop_condition": "当 stage_confirmation.md 生成后，继续提取 draft。",
        }
    if not bool(steps.get("draft", False)):
        return {
            "mode": "needs_human_confirmation",
            "label": "extract_draft",
            "command": format_command(entrypoints.get("extract_draft", [])),
            "scope": "workflow",
            "section": "draft",
            "manual_edit_required": "true",
            "priority": "high",
            "reason": f"确认并补充 {stage_confirmation} 后，再提取结构化 draft。",
            "input_source": stage_confirmation,
            "output_artifact": str(manifest.get("draft", "")),
            "stop_condition": "当 workflow_blueprint_input.json 生成后，继续构建 blueprint。",
        }
    if not bool(steps.get("blueprint", False)):
        return {
            "mode": "needs_build_step",
            "label": "build_blueprint",
            "command": format_command(entrypoints.get("build_blueprint", [])),
            "scope": "workflow",
            "section": "blueprint",
            "manual_edit_required": "false",
            "priority": "medium",
            "reason": "draft 已就绪，下一步生成 workflow_blueprint.md。",
            "input_source": str(manifest.get("draft", "")),
            "output_artifact": str(manifest.get("blueprint", "")),
            "stop_condition": "当 workflow_blueprint.md 生成后，判断是否进入 clone skill/runtime。",
        }
    if str(manifest.get("clone_config", "")).strip() and not bool(steps.get("workflow_clone_skill", False)):
        return {
            "mode": "needs_build_step",
            "label": "build_workflow_clone_skill",
            "command": format_command(entrypoints.get("build_workflow_clone_skill", [])),
            "scope": "workflow",
            "section": "workflow_clone_skill",
            "manual_edit_required": "false",
            "priority": "medium",
            "reason": "workflow blueprint 已生成，下一步编译第一版 workflow clone skill。",
            "input_source": str(manifest.get("blueprint", "")),
            "output_artifact": str(manifest.get("workflow_clone_skill", "")),
            "stop_condition": "当 workflow clone skill 目录生成后，可继续构建 runtime bundle。",
        }
    if str(manifest.get("clone_config", "")).strip() and not bool(steps.get("workflow_runtime_bundle", False)):
        return {
            "mode": "needs_build_step",
            "label": "build_workflow_runtime_bundle",
            "command": format_command(entrypoints.get("build_workflow_runtime_bundle", [])),
            "scope": "workflow",
            "section": "workflow_runtime_bundle",
            "manual_edit_required": "false",
            "priority": "medium",
            "reason": "workflow clone skill 已生成，下一步构建 workflow runtime bundle。",
            "input_source": str(manifest.get("blueprint", "")),
            "output_artifact": str(manifest.get("workflow_runtime_bundle", "")),
            "stop_condition": "当 workflow runtime bundle 生成后，可直接执行 workflow turn。",
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
            "reason": "workflow runtime bundle 已生成，可以直接执行单轮任务推进。",
            "input_source": "<workflow input>",
            "output_artifact": str(manifest.get("workflow_runtime_bundle", "")),
            "stop_condition": "当 workflow turn 返回 needs_user 或任务完成时停止。",
        }
    return {
        "mode": "needs_build_step",
        "label": "build_blueprint",
        "command": format_command(entrypoints.get("build_blueprint", [])),
        "scope": "workflow",
        "section": "blueprint",
        "manual_edit_required": "false",
        "priority": "low",
        "reason": "workflow blueprint 已生成，可继续进入 workflow clone/runtime 构建。",
        "input_source": str(manifest.get("draft", "")),
        "output_artifact": str(manifest.get("blueprint", "")),
        "stop_condition": "当下游构建完成后，重新判断下一步。",
    }
