#!/usr/bin/env python3
"""Render a workflow_blueprint.md from structured workflow JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("workflow blueprint input must be a JSON object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def bullet_list(items: list[Any], default: str = "暂无") -> str:
    parts = [str(item).strip() for item in items if str(item).strip()]
    if not parts:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in parts)


def field_line(label: str, value: Any) -> str:
    text = str(value).strip()
    return f"- {label}：{text or '暂无'}"


def render_stages(stages: list[Any]) -> str:
    rendered: list[str] = []
    for idx, raw in enumerate(stages, start=1):
        stage = as_dict(raw)
        name = str(stage.get("name", "")).strip() or f"阶段{idx}"
        rendered.extend(
            [
                f"### {idx}. {name}",
                "",
                field_line("目标", stage.get("goal", "")),
                field_line("输入", "、".join(as_list(stage.get("input", [])))),
                field_line("输出", "、".join(as_list(stage.get("output", [])))),
                field_line("完成判断", stage.get("done_when", "")),
                "",
            ]
        )
    return "\n".join(rendered).strip() or "暂无阶段蓝图"


def render_stage_actions(stage_actions: list[Any]) -> str:
    rendered: list[str] = []
    for raw in stage_actions:
        item = as_dict(raw)
        stage = str(item.get("stage", "")).strip() or "未命名阶段"
        rendered.extend(
            [
                f"### {stage}",
                "",
                field_line("读取", "、".join(as_list(item.get("read", [])))),
                field_line("生成", "、".join(as_list(item.get("produce", [])))),
                field_line("调用工具", "、".join(as_list(item.get("tools", [])))),
                field_line("中间结果保存", item.get("save", "")),
                "",
            ]
        )
    return "\n".join(rendered).strip() or "暂无阶段动作"


def render_tool_map(tool_map: list[Any]) -> str:
    rendered: list[str] = []
    for raw in tool_map:
        item = as_dict(raw)
        name = str(item.get("tool_name", "")).strip() or "未命名工具"
        rendered.extend(
            [
                f"### {name}",
                "",
                field_line("调用时机", item.get("when_to_call", "")),
                field_line("预期输入", item.get("expected_input", "")),
                field_line("预期输出", item.get("expected_output", "")),
                field_line("缺失回退", item.get("fallback_if_missing", "")),
                "",
            ]
        )
    return "\n".join(rendered).strip() or "暂无工具映射"


def render_transition_rules(rules: list[Any]) -> str:
    rendered: list[str] = []
    for raw in rules:
        item = as_dict(raw)
        from_stage = str(item.get("from", "")).strip() or "未知阶段"
        to_stage = str(item.get("to", "")).strip() or "未知阶段"
        rendered.extend(
            [
                f"### {from_stage} -> {to_stage}",
                "",
                field_line("进入条件", item.get("when", "")),
                field_line("回退或失败处理", item.get("fallback", "")),
                "",
            ]
        )
    return "\n".join(rendered).strip() or "暂无阶段切换规则"


def render_human_checkpoints(checkpoints: list[Any]) -> str:
    rendered: list[str] = []
    for raw in checkpoints:
        item = as_dict(raw)
        stage = str(item.get("stage", "")).strip() or "未命名阶段"
        rendered.extend(
            [
                f"### {stage}",
                "",
                field_line("触发条件", item.get("trigger", "")),
                field_line("需要人工介入的原因", item.get("reason", "")),
                "",
            ]
        )
    return "\n".join(rendered).strip() or "暂无人工介入点"


def render_kv_map(data: dict[str, Any], empty_text: str) -> str:
    if not data:
        return empty_text
    return "\n".join(field_line(str(key), value) for key, value in data.items())


def render_stage_confirmation_notes(data: dict[str, Any], key: str, default: str = "暂无") -> str:
    notes = as_dict(data.get("stage_confirmation_notes"))
    return bullet_list(as_list(notes.get(key, [])), default)


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build workflow_blueprint.md from JSON input.")
    parser.add_argument("--input", required=True, help="Path to structured workflow JSON")
    parser.add_argument("--output", required=True, help="Path to output workflow_blueprint.md")
    parser.add_argument(
        "--template",
        default="templates/workflow_blueprint_template.md",
        help="Path to markdown template",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    template_path = Path(args.template)

    if not input_path.exists():
        raise SystemExit(f"workflow input not found: {input_path}")
    if not template_path.exists():
        raise SystemExit(f"template not found: {template_path}")

    data = load_json(input_path)
    answers = as_dict(data.get("workflow_interview_answers"))

    rendered = load_template(template_path).format(
        workflow_name=str(data.get("workflow_name", "")).strip() or "未命名工作流蓝图",
        work_unit=str(data.get("work_unit", "")).strip() or "暂无",
        success_condition=str(data.get("success_condition", "")).strip() or "暂无",
        stop_condition=str(data.get("stop_condition", "")).strip() or "暂无",
        trigger=str(answers.get("trigger", "")).strip() or "暂无",
        completion_standard=str(answers.get("completion_standard", "")).strip() or "暂无",
        stage_overview=bullet_list(as_list(answers.get("stage_overview", []))),
        stage_tools=bullet_list(as_list(answers.get("stage_tools", []))),
        common_blockers=bullet_list(as_list(answers.get("common_blockers", []))),
        human_only_decisions=bullet_list(as_list(answers.get("human_only_decisions", []))),
        final_deliverable=str(answers.get("final_deliverable", "")).strip() or "暂无",
        stage_draft=bullet_list(
            [as_dict(item).get("name", "") for item in as_list(data.get("stage_draft", []))],
            "暂无",
        ),
        confirmed_stages=bullet_list(as_list(data.get("confirmed_stages", [])), "暂无"),
        missing_stages=render_stage_confirmation_notes(data, "missing_stages"),
        sequence_adjustments=render_stage_confirmation_notes(data, "sequence_adjustments"),
        iteration_loops=render_stage_confirmation_notes(data, "iteration_loops"),
        human_signoffs=render_stage_confirmation_notes(data, "human_signoffs"),
        stages=render_stages(as_list(data.get("stages", []))),
        stage_actions=render_stage_actions(as_list(data.get("stage_actions", []))),
        tool_map=render_tool_map(as_list(data.get("tool_map", []))),
        transition_rules=render_transition_rules(as_list(data.get("transition_rules", []))),
        human_checkpoints=render_human_checkpoints(as_list(data.get("human_checkpoints", []))),
        workflow_state_schema=render_kv_map(
            as_dict(data.get("workflow_state_schema")),
            "暂无状态记录定义",
        ),
        delivery_contract=render_kv_map(
            as_dict(data.get("delivery_contract")),
            "暂无交付约定",
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE

# SCRIPT_REFRESH_MARKER_PIPELINE
