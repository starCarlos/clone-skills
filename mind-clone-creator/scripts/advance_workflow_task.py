#!/usr/bin/env python3
"""Advance a workflow task state based on current input and workflow blueprint."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


UTC_PLUS_8 = timezone(timedelta(hours=8))

COMPLETE_HINTS = (
    "已完成",
    "完成了",
    "done",
    "通过",
    "validated",
    "ready",
)
BLOCKER_HINTS = (
    "卡住",
    "阻塞",
    "缺少",
    "没有权限",
    "无权限",
    "失败",
    "高风险",
    "存在风险",
    "有风险",
    "blocked",
)
USER_HINTS = (
    "需要你决定",
    "需要拍板",
    "请确认",
    "需要确认",
    "要不要",
    "是否上线",
    "priority",
)


def now_iso() -> str:
    return datetime.now(UTC_PLUS_8).isoformat(timespec="seconds")


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


def dump_simple_yaml(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dump_simple_yaml(value, indent + 2))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.append(dump_simple_yaml(item, indent + 4))
                    else:
                        escaped = str(item).replace('"', '\\"')
                        lines.append(f'{prefix}  - "{escaped}"')
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{prefix}{key}: "{escaped}"')
    return "\n".join(lines)


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


def parse_workflow_blueprint(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    h2 = split_h2_sections(text)
    stages_raw = split_h3_sections(h2.get("阶段蓝图", ""))
    checkpoints_raw = split_h3_sections(h2.get("人工介入点", ""))
    stages: list[dict[str, str]] = []
    for title, body in stages_raw.items():
        name = clean_stage_title(title)
        info = {"name": name, "objective": "", "done_when": ""}
        for line in normalize_lines(body):
            if line.startswith("- 目标："):
                info["objective"] = line.replace("- 目标：", "", 1).strip()
            if line.startswith("- 完成判断："):
                info["done_when"] = line.replace("- 完成判断：", "", 1).strip()
        stages.append(info)
    checkpoints: list[dict[str, str]] = []
    for title, body in checkpoints_raw.items():
        item = {"stage": clean_stage_title(title), "trigger": "", "reason": ""}
        for line in normalize_lines(body):
            if line.startswith("- 触发条件："):
                item["trigger"] = line.replace("- 触发条件：", "", 1).strip()
            if line.startswith("- 需要人工介入的原因："):
                item["reason"] = line.replace("- 需要人工介入的原因：", "", 1).strip()
        checkpoints.append(item)
    return {"stages": stages, "checkpoints": checkpoints}


def stage_index(stages: list[dict[str, str]], current_stage: str) -> int:
    for idx, item in enumerate(stages):
        if item["name"] == current_stage:
            return idx
    return 0


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def infer_needs_user(current_stage: str, user_input: str, checkpoints: list[dict[str, str]]) -> tuple[bool, str, str]:
    if contains_any(user_input, USER_HINTS):
        return True, "检测到需要人工确认的表达", "输入中出现拍板/确认信号"
    for checkpoint in checkpoints:
        if checkpoint["stage"] == current_stage:
            trigger = checkpoint.get("trigger", "")
            if trigger and any(part.strip() and part.strip() in user_input for part in re.split(r"[、，,；;]", trigger)):
                return True, trigger, checkpoint.get("reason", "")
    return False, "", ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Advance workflow task state by one step based on current input."
    )
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--input", required=True, help="Current task update / message")
    parser.add_argument("--output-state", required=True)
    parser.add_argument("--output-result", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blueprint = parse_workflow_blueprint(Path(args.workflow_blueprint))
    state = load_simple_yaml(Path(args.state))
    user_input = args.input.strip()

    stages = blueprint["stages"]
    checkpoints = blueprint["checkpoints"]
    current_stage = str(state.get("current_stage", "")).strip() or (stages[0]["name"] if stages else "未定义阶段")
    idx = stage_index(stages, current_stage)
    stage = stages[idx] if stages else {"name": current_stage, "objective": "", "done_when": ""}

    needs_user, decision_needed, why_blocked = infer_needs_user(current_stage, user_input, checkpoints)
    blocked = contains_any(user_input, BLOCKER_HINTS)
    completed = contains_any(user_input, COMPLETE_HINTS)

    completed_stages = state.get("completed_stages", [])
    if not isinstance(completed_stages, list):
        completed_stages = []
    completed_actions = state.get("completed_actions", [])
    if not isinstance(completed_actions, list):
        completed_actions = []
    blockers = state.get("blockers", [])
    if not isinstance(blockers, list):
        blockers = []
    waiting_for_user = state.get("waiting_for_user", [])
    if not isinstance(waiting_for_user, list):
        waiting_for_user = []

    done_text = user_input
    deliverable = str(state.get("latest_deliverable", "")).strip()
    next_action = stage.get("objective", "") or state.get("next_step", "")
    status = "active"
    risk = ""

    if needs_user:
        status = "waiting_for_user"
        waiting_for_user = [decision_needed or "需要人工确认"]
        risk = why_blocked or "当前任务触发人工介入点"
        next_action = "暂停自动推进，等待人工确认后继续"
    elif blocked:
        status = "blocked"
        blockers = [user_input]
        next_action = "先清除阻塞，再继续当前阶段"
        risk = "当前输入显示存在阻塞或风险"
    elif completed and idx < len(stages) - 1:
        if current_stage not in completed_stages:
            completed_stages.append(current_stage)
        next_stage = stages[idx + 1]
        current_stage = next_stage["name"]
        next_action = next_stage["objective"] or "进入下一阶段"
        deliverable = f"已完成阶段：{stage['name']}"
    elif completed and idx == len(stages) - 1:
        if current_stage not in completed_stages:
            completed_stages.append(current_stage)
        status = "completed"
        next_action = "工作流已完成，整理最终交付"
        deliverable = f"已完成最终阶段：{stage['name']}"
    else:
        next_action = stage.get("objective", "") or "继续推进当前阶段"

    completed_actions.append(user_input)

    state["status"] = status
    state["current_stage"] = current_stage
    state["completed_stages"] = completed_stages
    state["completed_actions"] = completed_actions
    state["pending_actions"] = [next_action]
    state["blockers"] = blockers if status == "blocked" else []
    state["waiting_for_user"] = waiting_for_user if status == "waiting_for_user" else []
    state["latest_deliverable"] = deliverable
    state["next_step"] = next_action
    state["last_updated_at"] = now_iso()

    result = {
        "current_stage": current_stage,
        "objective": next((s["objective"] for s in stages if s["name"] == current_stage), ""),
        "done": done_text,
        "next_action": next_action,
        "needs_user": status == "waiting_for_user",
        "deliverable": deliverable or "暂无新增交付物",
    }
    if status == "waiting_for_user":
        result["risk"] = risk or "触发人工介入点"
        result["decision_needed"] = decision_needed or "需要人工确认"
        result["why_blocked"] = why_blocked or "当前不能自动继续"
    elif status == "blocked":
        result["risk"] = risk or "存在阻塞"
        result["decision_needed"] = ""
        result["why_blocked"] = "需要先解决阻塞问题"

    Path(args.output_state).write_text(dump_simple_yaml(state) + "\n", encoding="utf-8")
    Path(args.output_result).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
