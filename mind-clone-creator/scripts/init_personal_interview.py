#!/usr/bin/env python3
"""Initialize a fillable personal interview markdown from a template."""

from __future__ import annotations

import argparse
from pathlib import Path


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a personal interview markdown file.")
    parser.add_argument("--clone-name", required=True, help="Clone or persona name.")
    parser.add_argument("--profession", default="未显式指定", help="Profession label.")
    parser.add_argument("--known-context", default="暂无", help="Known identity/work context.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    template_path = skill_root / "templates" / "personal_interview_template.md"
    if not template_path.exists():
        raise SystemExit(f"personal interview template not found: {template_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_template(
            template_path,
            {
                "clone_name": args.clone_name.strip() or "未命名分身",
                "profession": args.profession.strip() or "未显式指定",
                "known_context": args.known_context.strip() or "暂无",
            },
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
