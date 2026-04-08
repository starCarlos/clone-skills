#!/usr/bin/env python3
"""Check local helper-skill availability for mind-clone-creator."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED = [
    "deep-research",
    "content-harvester",
    "docx",
    "pdf",
    "xlsx",
    "tikhub-api-helper",
    "find-skills",
    "skill-installer",
]

DEFAULT_SEARCH_ROOTS = [
    "/home/admin_wsl/.openclaw/workspace/skills",
    "/home/admin_wsl/.codex/skills",
]

FALLBACKS = {
    "deep-research": "跳过职业深研，改用本 skill 的访谈结果和本地 bundled multi-search-engine 做轻量补充。",
    "content-harvester": "要求用户直接上传整理后的材料，或转为 markdown/plain text 后再继续。",
    "docx": "要求用户先导出为 markdown 或纯文本。",
    "pdf": "要求用户先提供可复制文本，或转成 markdown/plain text。",
    "xlsx": "要求用户先导出为 CSV/TSV/plain text。",
    "tikhub-api-helper": "改为让用户手动提供平台内容导出或复制文本。",
    "find-skills": "由 mind-clone-creator 根据已知缺口给出人工检索建议。",
    "skill-installer": "只能输出安装建议和命令，无法在流程内代装。",
}


def parse_frontmatter_name(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def discover_skills(search_roots: list[Path]) -> dict[str, str]:
    discovered: dict[str, str] = {}
    for root in search_roots:
        if not root.exists():
            continue
        skill_files = sorted(root.rglob("SKILL.md"), key=lambda p: (".backup-" in str(p.parent), str(p)))
        for skill_md in skill_files:
            try:
                name = parse_frontmatter_name(skill_md.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            if not name:
                continue
            if name not in discovered or ".backup-" in discovered[name]:
                discovered[name] = str(skill_md.parent)
    return discovered


def build_result(required: list[str], discovered: dict[str, str]) -> dict[str, Any]:
    available_helpers = []
    missing_helpers = []
    fallback_plan = {}

    available_helpers.append(
        {
            "name": "multi-search-engine",
            "source": "bundled",
            "path": "references/multi-search-engine",
            "note": "本 skill 内置默认联网搜索助手。",
        }
    )

    for name in required:
        path = discovered.get(name)
        if path:
            available_helpers.append(
                {
                    "name": name,
                    "source": "local",
                    "path": path,
                }
            )
        else:
            missing_helpers.append(name)
            fallback_plan[name] = FALLBACKS.get(name, "改为手工降级处理。")

    return {
        "available_helpers": available_helpers,
        "missing_helpers": missing_helpers,
        "fallback_plan": fallback_plan,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check helper skill availability for mind-clone-creator."
    )
    parser.add_argument(
        "--required",
        nargs="*",
        default=DEFAULT_REQUIRED,
        help="Helper skill names to check.",
    )
    parser.add_argument(
        "--search-root",
        action="append",
        default=[],
        help="Additional root to scan for SKILL.md files.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def render_text(result: dict[str, Any]) -> str:
    lines = ["# skill_availability", "", "available_helpers:"]
    for item in result["available_helpers"]:
        lines.append(f"- {item['name']} [{item['source']}] {item['path']}")
    lines.append("")
    lines.append("missing_helpers:")
    for name in result["missing_helpers"]:
        lines.append(f"- {name}")
    lines.append("")
    lines.append("fallback_plan:")
    for name, plan in result["fallback_plan"].items():
        lines.append(f"- {name}: {plan}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    roots = [Path(path) for path in DEFAULT_SEARCH_ROOTS + args.search_root]
    discovered = discover_skills(roots)
    result = build_result(args.required, discovered)
    if args.format == "text":
        print(render_text(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
