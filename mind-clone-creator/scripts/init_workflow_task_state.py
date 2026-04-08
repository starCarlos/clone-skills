#!/usr/bin/env python3
"""Initialize a workflow task state YAML from workflow_blueprint.md."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


UTC_PLUS_8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(UTC_PLUS_8).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_h2_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_first_stage(blueprint_text: str) -> tuple[str, str]:
    h2 = split_h2_sections(blueprint_text)
    stages = split_h3_sections(h2.get("阶段蓝图", ""))
    if not stages:
        return ("未定义阶段", "先补全工作流阶段定义")
    first_title, first_body = next(iter(stages.items()))
    stage_name = re.sub(r"^\d+\.\s*", "", first_title).strip()
    next_step = "进入该阶段并完成首个明确输出"
    for line in normalize_lines(first_body):
        if line.startswith("- 目标："):
            next_step = line.replace("- 目标：", "", 1).strip() or next_step
            break
    return (stage_name, next_step)


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize workflow task state YAML from workflow blueprint."
    )
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--task-id", default="task-001")
    parser.add_argument("--task-summary", default="新建工作流任务")
    parser.add_argument(
        "--template",
        default="templates/workflow_task_state_template.yaml",
        help="Path to task state template",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blueprint_path = Path(args.workflow_blueprint)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not blueprint_path.exists():
        raise SystemExit(f"workflow blueprint not found: {blueprint_path}")
    if not template_path.exists():
        raise SystemExit(f"template not found: {template_path}")

    blueprint_text = read_text(blueprint_path)
    title_match = re.search(r"^#\s+(.+)$", blueprint_text, re.M)
    workflow_name = title_match.group(1).strip() if title_match else "未命名工作流"
    current_stage, next_step = extract_first_stage(blueprint_text)
    rendered = load_template(template_path).format(
        workflow_name=workflow_name,
        task_id=args.task_id,
        task_summary=args.task_summary,
        current_stage=current_stage,
        first_pending_action=next_step,
        next_step=next_step,
        last_updated_at=now_iso(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
