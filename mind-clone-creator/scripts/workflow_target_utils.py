#!/usr/bin/env python3
"""Shared helpers for persona-plus-workflow target state."""

from __future__ import annotations

from typing import Any


WORKFLOW_TARGET_PLACEHOLDER = "待确认的第一类典型工作"
WORKFLOW_NAME_PLACEHOLDER = "待确认工作流蓝图"
WORKFLOW_TARGET_PLACEHOLDERS = {"", WORKFLOW_TARGET_PLACEHOLDER, "未定义工作单元", "<work-unit>"}


def workflow_target_defined(work_unit: Any) -> bool:
    return str(work_unit or "").strip() not in WORKFLOW_TARGET_PLACEHOLDERS


def infer_workflow_name(work_unit: Any) -> str:
    if not workflow_target_defined(work_unit):
        return WORKFLOW_NAME_PLACEHOLDER
    return f"{str(work_unit).strip()}工作流蓝图"


def infer_workflow_target_defined(manifest: dict[str, Any], steps: dict[str, Any]) -> bool:
    return any(
        [
            bool(steps.get("workflow_target_defined", False)),
            workflow_target_defined(manifest.get("work_unit", "")),
            bool(steps.get("workflow_pipeline", False)),
            bool(steps.get("workflow_clone_skill", False)),
            bool(steps.get("workflow_runtime_bundle", False)),
        ]
    )
