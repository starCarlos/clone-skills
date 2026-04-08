#!/usr/bin/env python3
"""Quality checks for generated workflow_blueprint.md artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_SECTION_TEXT = {
    "阶段动作": "暂无阶段动作",
    "工具映射": "暂无工具映射",
    "阶段切换规则": "暂无阶段切换规则",
    "人工介入点": "暂无人工介入点",
}

PLACEHOLDER_VALUES = {"暂无", "未命名阶段", "未知阶段", "-"}


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


def extract_field_value(lines: list[str], label: str) -> str:
    prefix = f"- {label}："
    for line in lines:
        if line.startswith(prefix):
            return line.replace(prefix, "", 1).strip()
    return ""


def analyze_blueprint(path: Path | str) -> dict[str, Any]:
    resolved = Path(path).resolve()
    if not resolved.exists():
        return {"path": str(resolved), "exists": False, "ok": False}

    text = resolved.read_text(encoding="utf-8")
    h2 = split_h2_sections(text)
    stages = split_h3_sections(h2.get("阶段蓝图", ""))

    generic_stage_titles = [
        clean_stage_title(title)
        for title in stages
        if re.fullmatch(r"阶段\d+", clean_stage_title(title)) or clean_stage_title(title) in PLACEHOLDER_VALUES
    ]

    empty_stage_fields: list[dict[str, str]] = []
    for title, body in stages.items():
        stage_name = clean_stage_title(title)
        lines = normalize_lines(body)
        for label in ["目标", "输入", "输出", "完成判断"]:
            value = extract_field_value(lines, label)
            if not value or value in PLACEHOLDER_VALUES:
                empty_stage_fields.append({"stage": stage_name, "field": label, "value": value})

    placeholder_sections = [
        section
        for section, placeholder in PLACEHOLDER_SECTION_TEXT.items()
        if h2.get(section, "").strip() == placeholder
    ]

    checkpoint_titles = split_h3_sections(h2.get("人工介入点", ""))
    generic_checkpoint_titles = [
        clean_stage_title(title)
        for title in checkpoint_titles
        if clean_stage_title(title) in {"未命名阶段", "未知阶段"}
    ]

    report = {
        "path": str(resolved),
        "exists": True,
        "generic_stage_titles": generic_stage_titles,
        "empty_stage_fields": empty_stage_fields,
        "placeholder_sections": placeholder_sections,
        "generic_checkpoint_titles": generic_checkpoint_titles,
    }
    report["ok"] = not any(
        [
            report["generic_stage_titles"],
            report["empty_stage_fields"],
            report["placeholder_sections"],
            report["generic_checkpoint_titles"],
        ]
    )
    return report


def emit_report(report: dict[str, Any], as_json: bool) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
