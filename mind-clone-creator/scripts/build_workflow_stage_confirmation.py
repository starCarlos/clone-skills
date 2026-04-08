#!/usr/bin/env python3
"""Build a stage-confirmation markdown from a filled W1-W7 workflow interview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_h3_sections(text: str) -> dict[str, str]:
    import re

    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def clean_text(text: str) -> str:
    import re

    text = re.sub(r"^\-\s*", "", text, flags=re.M)
    return "\n".join(normalize_lines(text))


def strip_answer_preamble(text: str) -> str:
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        if raw.strip().startswith("回答："):
            return "\n".join(lines[idx + 1 :])
    return text


def find_section(sections: dict[str, str], *aliases: str) -> str:
    import re

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
    import re

    text = strip_answer_preamble(text)
    values: list[str] = []
    for line in normalize_lines(text):
        if line.startswith("- "):
            value = line[2:].strip()
            if value:
                values.append(value)
            continue
        if re.match(r"^\d+\.\s+", line):
            value = re.sub(r"^\d+\.\s+", "", line).strip()
            if value:
                values.append(value)
    return values if values else [line for line in normalize_lines(text) if line]


def first_line(text: str, default: str) -> str:
    lines = normalize_lines(strip_answer_preamble(text))
    return lines[0] if lines else default


def parse_interview(path: Path, workflow_name: str, work_unit: str) -> dict[str, Any]:
    sections = split_h3_sections(read_text(path))
    w1 = clean_text(find_section(sections, "W1. 这类工作从什么触发？", "W1", "触发条件"))
    w2 = clean_text(find_section(sections, "W2. 完成的标准是什么？", "W2", "完成标准"))
    w3 = clean_text(find_section(sections, "W3. 中间大概经过几个阶段？", "W3", "关键阶段"))
    w5 = clean_text(find_section(sections, "W5. 哪些环节最容易卡住？", "W5", "常见阻塞"))
    w6 = clean_text(find_section(sections, "W6. 哪些决策必须你本人来做？", "W6", "人工决策"))
    w7 = clean_text(find_section(sections, "W7. 最终交给对方的是什么？", "W7", "最终交付物"))
    return {
        "workflow_name": workflow_name or "未命名工作流阶段确认",
        "work_unit": work_unit or first_line(w1, "未定义工作单元"),
        "success_condition": first_line(w2, "暂无"),
        "stop_condition": "需求冲突、信息不足或关键权限缺失时暂停并请求人工确认",
        "stage_overview": extract_list(w3),
        "common_blockers": extract_list(w5),
        "human_only_decisions": extract_list(w6),
        "final_deliverable": extract_list(w7),
    }


def numbered_list(items: list[str], default: str) -> str:
    clean = [item.strip() for item in items if item.strip()]
    if not clean:
        return f"1. {default}"
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(clean, start=1))


def bullet_list(items: list[str], default: str) -> str:
    clean = [item.strip() for item in items if item.strip()]
    if not clean:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in clean)


def render_template(path: Path, values: dict[str, str]) -> str:
    return load_template(path).format(**values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build workflow stage confirmation markdown.")
    parser.add_argument("--interview", required=True, help="Path to filled W1-W7 workflow interview markdown.")
    parser.add_argument("--workflow-name", default="", help="Workflow name override.")
    parser.add_argument("--work-unit", default="", help="Work unit override.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    interview_path = Path(args.interview)
    if not interview_path.exists():
        raise SystemExit(f"workflow interview not found: {interview_path}")

    skill_root = Path(__file__).resolve().parent.parent
    template_path = skill_root / "templates" / "workflow_stage_confirmation_template.md"
    if not template_path.exists():
        raise SystemExit(f"workflow stage confirmation template not found: {template_path}")

    data = parse_interview(interview_path, args.workflow_name, args.work_unit)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_template(
            template_path,
            {
                "workflow_name": data["workflow_name"],
                "work_unit": data["work_unit"],
                "success_condition": data["success_condition"],
                "stop_condition": data["stop_condition"],
                "stage_sequence": numbered_list(data["stage_overview"], "待补充阶段"),
                "common_blockers": bullet_list(data["common_blockers"], "暂无"),
                "human_only_decisions": bullet_list(data["human_only_decisions"], "暂无"),
                "final_deliverable": bullet_list(data["final_deliverable"], "暂无"),
            },
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
