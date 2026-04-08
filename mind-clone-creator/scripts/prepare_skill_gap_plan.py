#!/usr/bin/env python3
"""Prepare a confirmation-ready install plan for helper-skill gaps."""

from __future__ import annotations

import argparse
import json
from typing import Any


INSTALL_CATALOG = {
    "deep-research": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于职业深研、评测场景补充和知识建议增强。",
    },
    "content-harvester": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于整理用户已有内容并转成可复用材料。",
    },
    "docx": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于提取 Word 文档内容。",
    },
    "pdf": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于提取 PDF 内容。",
    },
    "xlsx": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于读取表格材料和结构化数据。",
    },
    "tikhub-api-helper": {
        "install_type": "already-known-skill",
        "source": "local/open agent ecosystem",
        "reason": "用于获取用户本人平台内容作为补充材料。",
    },
    "find-skills": {
        "install_type": "system-skill",
        "source": "preinstalled",
        "reason": "用于发现补足能力的外部 skill。",
    },
    "skill-installer": {
        "install_type": "system-skill",
        "source": "preinstalled",
        "reason": "用于执行 skill 安装。",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a confirmation-ready helper skill gap plan."
    )
    parser.add_argument(
        "--missing",
        nargs="+",
        required=True,
        help="Missing helper skill names.",
    )
    parser.add_argument(
        "--need-context",
        default="用户常用工作流程需要额外辅助能力。",
        help="Why the workflow needs these skills now.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def build_plan(missing: list[str], need_context: str) -> dict[str, Any]:
    items = []
    confirm_questions = []
    for name in missing:
        meta = INSTALL_CATALOG.get(
            name,
            {
                "install_type": "unknown",
                "source": "to-be-researched",
                "reason": "当前工作流程存在能力缺口，需要先搜索合适 skill。",
            },
        )
        items.append(
            {
                "name": name,
                "install_type": meta["install_type"],
                "source": meta["source"],
                "reason": meta["reason"],
                "requires_user_confirmation": True,
            }
        )
        confirm_questions.append(f"是否允许补装 `{name}`，用于：{meta['reason']}")
    return {
        "need_context": need_context,
        "install_plan": items,
        "confirm_questions": confirm_questions,
        "execution_rule": "只有用户明确同意后，才能继续安装或依赖这些 skill。",
    }


def render_text(plan: dict[str, Any]) -> str:
    lines = ["# skill_gap_plan", "", f"need_context: {plan['need_context']}", "", "install_plan:"]
    for item in plan["install_plan"]:
        lines.append(
            f"- {item['name']}: {item['reason']} "
            f"[source={item['source']}, install_type={item['install_type']}]"
        )
    lines.append("")
    lines.append("confirm_questions:")
    for question in plan["confirm_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    lines.append(f"execution_rule: {plan['execution_rule']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    plan = build_plan(args.missing, args.need_context)
    if args.format == "text":
        print(render_text(plan), end="")
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
