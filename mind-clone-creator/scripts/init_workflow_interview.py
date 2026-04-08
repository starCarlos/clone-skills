#!/usr/bin/env python3
"""Initialize a fillable W1-W7 workflow interview markdown from a template."""

from __future__ import annotations

import argparse
from pathlib import Path


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a workflow interview markdown file.")
    parser.add_argument("--workflow-name", required=True, help="Workflow interview title.")
    parser.add_argument("--work-unit", required=True, help="One target recurring work unit.")
    parser.add_argument("--known-context", default="暂无", help="Known persona/profile/work context.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    template_path = skill_root / "templates" / "workflow_interview_template.md"
    if not template_path.exists():
        raise SystemExit(f"workflow interview template not found: {template_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_template(
            template_path,
            {
                "workflow_name": args.workflow_name.strip() or "未命名工作流访谈",
                "work_unit": args.work_unit.strip() or "未定义工作单元",
                "known_context": args.known_context.strip() or "暂无",
            },
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
