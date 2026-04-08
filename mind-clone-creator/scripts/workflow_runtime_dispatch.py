#!/usr/bin/env python3
"""Shared dispatch helpers for workflow runtime bundle orchestration."""

from __future__ import annotations

from typing import Any


def format_command(command: list[str]) -> str:
    return " ".join(str(x) for x in command)


def choose_recommended_runtime_command(manifest: dict[str, Any]) -> dict[str, str]:
    entrypoints = manifest.get("entrypoints", {}) if isinstance(manifest.get("entrypoints", {}), dict) else {}
    initial_run_mode = str(manifest.get("initial_run_mode", "")).strip()
    initial_run_output = str(manifest.get("initial_run_output", "")).strip()

    if initial_run_mode == "multi_turn":
        return {
            "mode": "ready_to_run",
            "label": "multi_turn",
            "command": format_command(entrypoints.get("multi_turn", [])),
            "scope": "workflow_runtime",
            "section": "multi_turn",
            "manual_edit_required": "false",
            "priority": "high",
            "reason": "当前 runtime bundle 已配置为直接连续推进多轮工作流。",
            "input_source": "<your-initial-update>",
            "output_artifact": initial_run_output,
            "stop_condition": "当 workflow run 返回 completed、needs_user 或达到 max_turns 时停止。",
        }
    if initial_run_mode == "single_turn":
        return {
            "mode": "ready_to_run",
            "label": "single_turn",
            "command": format_command(entrypoints.get("single_turn", [])),
            "scope": "workflow_runtime",
            "section": "single_turn",
            "manual_edit_required": "false",
            "priority": "high",
            "reason": "当前 runtime bundle 已配置为直接执行单轮 workflow turn。",
            "input_source": "<your-update>",
            "output_artifact": initial_run_output,
            "stop_condition": "当 workflow turn 返回 summary 后，判断是否继续多轮推进。",
        }
    return {
        "mode": "ready_to_run",
        "label": "single_turn",
        "command": format_command(entrypoints.get("single_turn", [])),
        "scope": "workflow_runtime",
        "section": "single_turn",
        "manual_edit_required": "false",
        "priority": "medium",
        "reason": "runtime bundle 已就绪，默认先跑单轮 workflow turn。",
        "input_source": "<your-update>",
        "output_artifact": str(manifest.get("default_turn_output", "")),
        "stop_condition": "当 workflow turn 返回 summary 后，再决定是否进入多轮模式。",
    }
