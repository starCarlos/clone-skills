#!/usr/bin/env python3
"""Build a structured action plan for the current workflow stage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from profession_adapter_runtime import resolve_profession_adapter


def parse_scalar(text: str) -> Any:
    if text == "null":
        return None
    if text in ("true", "false"):
        return text == "true"
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if text.isdigit():
        return int(text)
    return text


def load_simple_yaml(path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            value = parse_scalar(line[2:].strip())
            if isinstance(parent, list):
                parent.append(value)
            continue
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            next_nonempty = None
            for j in range(i, len(lines)):
                probe = lines[j]
                if probe.strip() and not probe.lstrip().startswith("#"):
                    next_nonempty = probe
                    break
            if next_nonempty is not None:
                next_indent = len(next_nonempty) - len(next_nonempty.lstrip(" "))
                next_line = next_nonempty.strip()
                container: Any = [] if next_indent > indent and next_line.startswith("- ") else {}
            else:
                container = {}
            if isinstance(parent, dict):
                parent[key] = container
            stack.append((indent, container))
            continue
        if isinstance(parent, dict):
            parent[key] = parse_scalar(rest)
    return root


def split_h2_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def clean_stage_title(title: str) -> str:
    return re.sub(r"^\d+\.\s*", "", title).strip()


def parse_prefixed_value(line: str, prefix: str) -> str:
    return line.replace(prefix, "", 1).strip()


def split_cn_items(text: str) -> list[str]:
    if not text:
        return []
    return [item.strip() for item in re.split(r"[、，,；;]", text) if item.strip()]


def dedupe_list(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def parse_workflow_blueprint(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    h2 = split_h2_sections(text)

    stages_raw = split_h3_sections(h2.get("阶段蓝图", ""))
    actions_raw = split_h3_sections(h2.get("阶段动作", ""))
    tools_raw = split_h3_sections(h2.get("工具映射", ""))

    stages: dict[str, dict[str, Any]] = {}
    for title, body in stages_raw.items():
        name = clean_stage_title(title)
        info: dict[str, Any] = {"name": name, "goal": "", "input": [], "output": [], "done_when": ""}
        for line in normalize_lines(body):
            if line.startswith("- 目标："):
                info["goal"] = parse_prefixed_value(line, "- 目标：")
            elif line.startswith("- 输入："):
                info["input"] = split_cn_items(parse_prefixed_value(line, "- 输入："))
            elif line.startswith("- 输出："):
                info["output"] = split_cn_items(parse_prefixed_value(line, "- 输出："))
            elif line.startswith("- 完成判断："):
                info["done_when"] = parse_prefixed_value(line, "- 完成判断：")
        stages[name] = info

    actions: dict[str, dict[str, Any]] = {}
    for title, body in actions_raw.items():
        info: dict[str, Any] = {"stage": clean_stage_title(title), "read": [], "produce": [], "tools": [], "save": ""}
        for line in normalize_lines(body):
            if line.startswith("- 读取："):
                info["read"] = split_cn_items(parse_prefixed_value(line, "- 读取："))
            elif line.startswith("- 生成："):
                info["produce"] = split_cn_items(parse_prefixed_value(line, "- 生成："))
            elif line.startswith("- 调用工具："):
                info["tools"] = split_cn_items(parse_prefixed_value(line, "- 调用工具："))
            elif line.startswith("- 中间结果保存："):
                info["save"] = parse_prefixed_value(line, "- 中间结果保存：")
        actions[info["stage"]] = info

    tools: dict[str, dict[str, str]] = {}
    for title, body in tools_raw.items():
        info = {"tool_name": clean_stage_title(title), "when_to_call": "", "expected_input": "", "expected_output": "", "fallback_if_missing": ""}
        for line in normalize_lines(body):
            if line.startswith("- 调用时机："):
                info["when_to_call"] = parse_prefixed_value(line, "- 调用时机：")
            elif line.startswith("- 预期输入："):
                info["expected_input"] = parse_prefixed_value(line, "- 预期输入：")
            elif line.startswith("- 预期输出："):
                info["expected_output"] = parse_prefixed_value(line, "- 预期输出：")
            elif line.startswith("- 缺失回退："):
                info["fallback_if_missing"] = parse_prefixed_value(line, "- 缺失回退：")
        tools[info["tool_name"]] = info

    return {"title": title_match.group(1).strip() if title_match else "", "stages": stages, "actions": actions, "tools": tools}


def infer_tool_details(action_tools: list[str], tool_map: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    plans: list[dict[str, str]] = []
    seen: set[str] = set()
    for action_tool in action_tools:
        matched = None
        for tool_name, tool in tool_map.items():
            if action_tool in tool_name or tool_name in action_tool:
                matched = tool
                break
        if matched is None:
            matched = {
                "tool_name": action_tool,
                "when_to_call": "",
                "expected_input": "",
                "expected_output": "",
                "fallback_if_missing": "缺失时改为人工分析或只输出方案",
            }
        tool_name = str(matched.get("tool_name", action_tool)).strip() or action_tool
        if tool_name in seen:
            continue
        seen.add(tool_name)
        plans.append(matched)
    return plans


def apply_stage_override(
    stage_name: str,
    stage: dict[str, Any],
    action: dict[str, Any],
    adapter: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    overrides = adapter.get("stage_overrides", {}) if isinstance(adapter, dict) else {}
    override = overrides.get(stage_name, {}) if isinstance(overrides, dict) else {}
    if not isinstance(override, dict):
        override = {}

    merged_stage = dict(stage)
    merged_action = {
        "stage": action.get("stage", stage_name),
        "read": list(action.get("read", [])),
        "produce": list(action.get("produce", [])),
        "tools": list(action.get("tools", [])),
        "save": action.get("save", ""),
    }

    merged_action["read"] = dedupe_list(merged_action["read"] + list(override.get("extra_read", [])))
    merged_action["produce"] = dedupe_list(merged_action["produce"] + list(override.get("extra_produce", [])))
    if override.get("preferred_tools"):
        merged_action["tools"] = dedupe_list(list(override.get("preferred_tools", [])) + merged_action["tools"])

    return merged_stage, merged_action, {
        "matched": bool(override),
        "notes": list(override.get("notes", [])) if isinstance(override.get("notes", []), list) else [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan executable actions for the current workflow stage.")
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--profession", default="")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blueprint = parse_workflow_blueprint(Path(args.workflow_blueprint))
    state = load_simple_yaml(Path(args.state))
    workspace = Path(__file__).resolve().parent.parent

    current_stage = str(state.get("current_stage", "")).strip()
    if not current_stage:
        raise SystemExit("current_stage missing in workflow state")

    stage = blueprint["stages"].get(current_stage, {"name": current_stage, "goal": "", "input": [], "output": [], "done_when": ""})
    action = blueprint["actions"].get(current_stage, {"stage": current_stage, "read": [], "produce": [], "tools": [], "save": ""})
    recommendation_query = "；".join(
        item for item in [blueprint.get("title", ""), current_stage, stage.get("goal", "")] if item
    )
    resolved = resolve_profession_adapter(
        workspace,
        args.profession,
        fallback_query=recommendation_query,
        allow_recommendation=True,
        auto_apply_recommendation=not bool(args.profession.strip()),
    )
    profession = str(resolved.get("profession", "")).strip()
    adapter = resolved.get("adapter", {}) if isinstance(resolved.get("adapter", {}), dict) else {}
    stage, action, adapter_info = apply_stage_override(current_stage, stage, action, adapter)
    tool_plan = infer_tool_details(action.get("tools", []), blueprint["tools"])

    plan = {
        "current_stage": current_stage,
        "profession": profession,
        "profession_input": args.profession,
        "profession_resolution": resolved.get("resolution", {}),
        "adapter_recommendation": resolved.get("recommendation", {}),
        "objective": stage.get("goal", ""),
        "required_inputs": stage.get("input", []),
        "expected_outputs": stage.get("output", []),
        "read": action.get("read", []),
        "produce": action.get("produce", []),
        "save": action.get("save", ""),
        "adapter_override": adapter_info,
        "tool_plan": tool_plan,
        "next_execution": [
            {
                "step": 1,
                "action": f"先读取：{'、'.join(action.get('read', [])) or '当前阶段输入'}",
            },
            {
                "step": 2,
                "action": f"再生成：{'、'.join(action.get('produce', [])) or '当前阶段产物'}",
            },
            {
                "step": 3,
                "action": f"最后保存：{action.get('save', '') or '记录当前阶段结果'}",
            },
        ],
    }

    Path(args.output).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
