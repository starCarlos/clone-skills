#!/usr/bin/env python3
"""Extract a structured workflow draft JSON from a W1-W7 markdown interview."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            lines.append(line)
    return lines


PLACEHOLDER_LIST_ITEMS = {"-", "暂无", "待补充阶段"}


def clean_text(text: str) -> str:
    text = re.sub(r"^\-\s*", "", text, flags=re.M)
    return "\n".join(normalize_lines(text))


def strip_answer_preamble(text: str) -> str:
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        if raw.strip().startswith("回答："):
            return "\n".join(lines[idx + 1 :])
    return text


def is_placeholder_list_item(text: str) -> bool:
    cleaned = text.strip().strip("：: ")
    if not cleaned:
        return True
    if cleaned in PLACEHOLDER_LIST_ITEMS:
        return True
    if re.fullmatch(r"\d+\.", cleaned):
        return True
    if re.fullmatch(r"阶段\d+", cleaned):
        return True
    return False


def find_section(sections: dict[str, str], *aliases: str) -> str:
    compact = {re.sub(r"\s+", "", key): value for key, value in sections.items()}
    for alias in aliases:
        if alias in sections:
            return sections[alias]
        alias_compact = re.sub(r"\s+", "", alias)
        if alias_compact in compact:
            return compact[alias_compact]
    for key, value in sections.items():
        for alias in aliases:
            if alias in key or key in alias:
                return value
    return ""


def extract_list(text: str) -> list[str]:
    text = strip_answer_preamble(text)
    values: list[str] = []
    for line in normalize_lines(text):
        if line.startswith("- "):
            value = line[2:].strip()
            if value and not is_placeholder_list_item(value):
                values.append(value)
            continue
        numbered = re.match(r"^(\d+)\.\s*(.*)$", line)
        if numbered:
            value = numbered.group(2).strip()
            if value and not is_placeholder_list_item(value):
                values.append(value)
            continue
        if not is_placeholder_list_item(line):
            values.append(line)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def first_line(text: str, default: str) -> str:
    lines = normalize_lines(strip_answer_preamble(text))
    return lines[0] if lines else default


def stage_name_from_text(text: str, index: int) -> str:
    cleaned = re.sub(r"^[\-\d\.\s]+", "", text).strip("：: ")
    if not cleaned:
        return f"阶段{index}"
    parts = re.split(r"[：:，,。；;]", cleaned)
    return parts[0].strip() or f"阶段{index}"


def build_stage_draft(stage_overview: list[str], work_unit: str, success_condition: str, final_deliverable: str) -> list[dict[str, Any]]:
    stages = []
    total = len(stage_overview)
    for idx, item in enumerate(stage_overview, start=1):
        name = stage_name_from_text(item, idx)
        previous_name = stage_name_from_text(stage_overview[idx - 2], idx - 1) if idx > 1 else ""
        next_name = stage_name_from_text(stage_overview[idx], idx + 1) if idx < total else ""
        if idx == 1:
            goal = f"明确“{work_unit}”的起点输入、目标和限制，完成“{name}”阶段收束。"
            stage_input = ["当前触发信息", "已知背景与约束"]
            stage_output = ["阶段判断结论", "已确认目标与关键约束"]
            done_when = f"当前任务边界已经说清，且可以进入“{next_name or name}”。"
        elif idx == total:
            goal = f"收束前面阶段结果，完成“{name}”，并确保达到：{success_condition}。"
            stage_input = [f"上一阶段“{previous_name}”输出", "待交付结果与风险说明"]
            stage_output = extract_list(final_deliverable) or ["最终交付物", "风险与下一步建议"]
            done_when = success_condition or f"“{name}”阶段已形成可交付结果。"
        else:
            goal = f"围绕“{name}”推进当前工作单元，并为“{next_name}”准备可复用输出。"
            stage_input = [f"上一阶段“{previous_name}”输出", "当前已确认需求与约束"]
            stage_output = [f"{name}阶段结论", f"进入“{next_name}”所需输入"]
            done_when = f"“{name}”阶段结论清晰，且“{next_name}”可以直接开始。"
        stages.append(
            {
                "name": name,
                "goal": goal,
                "input": stage_input,
                "output": stage_output,
                "done_when": done_when,
            }
        )
    return stages


def select_tools_for_stage(stage_name: str, stage_tools: list[str], index: int, total: int) -> list[str]:
    if not stage_tools:
        return []
    if total <= 1:
        return stage_tools[: min(3, len(stage_tools))]
    if index == 1:
        return stage_tools[: min(2, len(stage_tools))]
    if index == total:
        return stage_tools[max(0, len(stage_tools) - 2) :]
    if len(stage_tools) <= 3:
        return stage_tools[:]
    center_start = max(0, min(len(stage_tools) - 2, index - 1))
    return stage_tools[center_start : center_start + 2]


def build_stage_actions(stages: list[dict[str, Any]], stage_tools: list[str]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    total = len(stages)
    for idx, stage in enumerate(stages, start=1):
        name = str(stage.get("name", "")).strip() or f"阶段{idx}"
        actions.append(
            {
                "stage": name,
                "read": as_list(stage.get("input")),
                "produce": as_list(stage.get("output")),
                "tools": select_tools_for_stage(name, stage_tools, idx, total),
                "save": f"将“{name}”阶段结论写入当前工作流状态与阶段产物。",
            }
        )
    return actions


def build_tool_map(stage_tools: list[str], stage_names: list[str]) -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    joined_stages = "、".join(stage_names[:4]) or "相关阶段"
    for tool in stage_tools:
        mapping.append(
            {
                "tool_name": tool,
                "when_to_call": f"当 {joined_stages} 需要补充输入、生成中间产物或留下证据时调用。",
                "expected_input": "当前阶段目标、已知输入、待产出内容",
                "expected_output": "可供下一阶段复用的内容、记录或结果",
                "fallback_if_missing": "工具不可用时，先记录缺口并改为人工整理或文本产物。",
            }
        )
    return mapping


def build_transition_rules(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for idx in range(len(stages) - 1):
        current = stages[idx]
        nxt = stages[idx + 1]
        rules.append(
            {
                "from": str(current.get("name", "")).strip(),
                "to": str(nxt.get("name", "")).strip(),
                "when": str(current.get("done_when", "")).strip(),
                "fallback": "若信息不足、结果不稳或命中人工拍板点，则停留在当前阶段并补齐缺口。",
            }
        )
    return rules


def choose_checkpoint_stage(item: str, stage_names: list[str], index: int, total: int) -> str:
    if not stage_names:
        return "未命名阶段"
    for stage_name in stage_names:
        if stage_name and stage_name in item:
            return stage_name
    if total <= 1:
        return stage_names[0]
    stage_index = round(index * (len(stage_names) - 1) / max(total - 1, 1))
    return stage_names[min(max(stage_index, 0), len(stage_names) - 1)]


def build_human_checkpoints(items: list[str], stage_names: list[str]) -> list[dict[str, Any]]:
    checkpoints: list[dict[str, Any]] = []
    total = len(items)
    for idx, item in enumerate(items):
        checkpoints.append(
            {
                "stage": choose_checkpoint_stage(item, stage_names, idx, total),
                "trigger": item,
                "reason": "这是必须由本人拍板的决策点，命中后暂停自动推进并请求确认。",
            }
        )
    return checkpoints


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def parse_stage_confirmation(path: Path) -> dict[str, Any]:
    sections = split_h3_sections(read_text(path))
    confirmed_stages = extract_list(find_section(sections, "你确认后的最终阶段", "最终确认阶段"))
    missing_stages = extract_list(find_section(sections, "缺失阶段"))
    sequence_adjustments = extract_list(find_section(sections, "顺序修正"))
    iteration_loops = extract_list(find_section(sections, "迭代或回环关系"))
    human_signoffs = extract_list(find_section(sections, "必须人工拍板的节点"))
    return {
        "confirmed_stages": confirmed_stages,
        "missing_stages": missing_stages,
        "sequence_adjustments": sequence_adjustments,
        "iteration_loops": iteration_loops,
        "human_signoffs": human_signoffs,
    }


def parse_interview(
    path: Path,
    workflow_name: str,
    work_unit: str,
    stage_confirmation_path: Path | None = None,
) -> dict[str, Any]:
    sections = split_h3_sections(read_text(path))

    w1 = clean_text(find_section(sections, "W1. 这类工作从什么触发？", "W1", "触发条件"))
    w2 = clean_text(find_section(sections, "W2. 完成的标准是什么？", "W2", "完成标准"))
    w3 = clean_text(find_section(sections, "W3. 中间大概经过几个阶段？", "W3", "关键阶段"))
    w4 = clean_text(find_section(sections, "W4. 每个阶段你主要用什么工具？", "W4", "阶段工具"))
    w5 = clean_text(find_section(sections, "W5. 哪些环节最容易卡住？", "W5", "常见阻塞"))
    w6 = clean_text(find_section(sections, "W6. 哪些决策必须你本人来做？", "W6", "人工决策"))
    w7 = clean_text(find_section(sections, "W7. 最终交给对方的是什么？", "W7", "最终交付物"))

    stage_overview = extract_list(w3)
    stage_tools = extract_list(w4)
    common_blockers = extract_list(w5)
    human_only_decisions = extract_list(w6)
    confirmed = {
        "confirmed_stages": [],
        "missing_stages": [],
        "sequence_adjustments": [],
        "iteration_loops": [],
        "human_signoffs": [],
    }
    if stage_confirmation_path is not None and stage_confirmation_path.exists():
        confirmed = parse_stage_confirmation(stage_confirmation_path)
    final_stage_order = confirmed["confirmed_stages"] or stage_overview
    final_deliverable = w7 or "暂无"
    stages = build_stage_draft(final_stage_order, work_unit or first_line(w1, "未定义工作单元"), first_line(w2, "暂无"), final_deliverable)
    stage_names = [str(item.get("name", "")).strip() for item in stages if str(item.get("name", "")).strip()]
    checkpoint_items = confirmed["human_signoffs"] or human_only_decisions

    return {
        "workflow_name": workflow_name or "未命名工作流蓝图",
        "work_unit": work_unit or first_line(w1, "未定义工作单元"),
        "success_condition": first_line(w2, "暂无"),
        "stop_condition": "需求冲突、信息不足或关键权限缺失时暂停并请求人工确认",
        "workflow_interview_answers": {
            "trigger": w1 or "暂无",
            "completion_standard": w2 or "暂无",
            "stage_overview": stage_overview,
            "stage_tools": stage_tools,
            "common_blockers": common_blockers,
            "human_only_decisions": human_only_decisions,
            "final_deliverable": final_deliverable,
        },
        "stage_draft": build_stage_draft(stage_overview, work_unit or first_line(w1, "未定义工作单元"), first_line(w2, "暂无"), final_deliverable),
        "confirmed_stages": final_stage_order,
        "stage_confirmation_notes": {
            "missing_stages": confirmed["missing_stages"],
            "sequence_adjustments": confirmed["sequence_adjustments"],
            "iteration_loops": confirmed["iteration_loops"],
            "human_signoffs": confirmed["human_signoffs"],
        },
        "stages": stages,
        "stage_actions": build_stage_actions(stages, stage_tools),
        "tool_map": build_tool_map(stage_tools, stage_names),
        "transition_rules": build_transition_rules(stages),
        "human_checkpoints": build_human_checkpoints(checkpoint_items, stage_names),
        "workflow_state_schema": {
            "current_stage": "当前阶段",
            "confirmed_requirements": "已确认需求",
            "completed_actions": "已完成动作",
            "blockers": "阻塞项",
            "waiting_for_user": "待本人确认事项",
        },
        "delivery_contract": {
            "outputs": w7 or "暂无",
            "review_points": "关键风险、未完成项、下一步建议",
            "unresolved_items": "待补充",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured workflow draft JSON from a workflow interview markdown file."
    )
    parser.add_argument("--interview", required=True, help="Path to W1-W7 markdown interview")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--workflow-name", default="", help="Workflow name override")
    parser.add_argument("--work-unit", default="", help="Work unit override")
    parser.add_argument("--stage-confirmation", help="Optional stage confirmation markdown path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    interview_path = Path(args.interview)
    if not interview_path.exists():
        raise SystemExit(f"workflow interview not found: {interview_path}")

    stage_confirmation_path = Path(args.stage_confirmation) if args.stage_confirmation else None
    if stage_confirmation_path is not None and not stage_confirmation_path.exists():
        raise SystemExit(f"stage confirmation not found: {stage_confirmation_path}")

    data = parse_interview(interview_path, args.workflow_name, args.work_unit, stage_confirmation_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
