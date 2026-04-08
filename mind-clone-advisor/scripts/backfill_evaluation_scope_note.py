#!/usr/bin/env python3
"""Backfill artifact coverage scope notes into existing evaluation reports."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from migration_utils import default_persona_root, default_report_path, list_persona_skill_dirs, write_text

TITLE_PATTERN = re.compile(r"(?m)^#\s+Evaluation Report:\s*(.+?)\s*$")
SCOPE_LINES = [
    "This report scores artifact coverage, not live response quality.",
    "It evaluates whether the skill artifacts contain enough structured support for the tested questions.",
    "Evaluation mode: artifact_coverage",
]


def patch_report_text(text: str) -> tuple[str, bool]:
    lowered = text.lower()
    if "artifact coverage" in lowered and "not live response quality" in lowered:
        return text, False

    updated = text
    match = TITLE_PATTERN.search(updated)
    if match:
        title = match.group(1).strip()
        updated = TITLE_PATTERN.sub(f"# Artifact Coverage Report: {title}", updated, count=1)
    elif updated.startswith("# "):
        first_line, remainder = updated.split("\n", 1) if "\n" in updated else (updated, "")
        updated = f"{first_line}\n\n{remainder}".strip() + "\n"

    lines = updated.splitlines()
    if not lines:
        return updated, False

    insert_at = 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    block = [""] + SCOPE_LINES + [""]
    patched = lines[:insert_at] + block + lines[insert_at:]
    return "\n".join(patched).rstrip() + "\n", True


def build_report(rows: list[dict], persona_root: Path) -> str:
    lines = [
        "# Evaluation Scope Note Backfill Report",
        "",
        f"- Persona Root: {persona_root}",
        f"- Reports Scanned: {len(rows)}",
        f"- Reports Updated: {sum(1 for row in rows if row['updated'])}",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['slug']}")
        lines.append("")
        lines.append(f"- Report: {row['report_path']}")
        lines.append(f"- Action: {'updated' if row['updated'] else 'unchanged'}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill scope notes into evaluation reports")
    parser.add_argument("--persona-root", default=str(default_persona_root()))
    parser.add_argument(
        "--report",
        default=str(default_report_path("evaluation-scope-backfill-report.md")),
    )
    parser.add_argument("--write", action="store_true", help="persist updated evaluation reports")
    args = parser.parse_args()

    persona_root = Path(args.persona_root)
    rows = []
    for skill_dir in list_persona_skill_dirs(persona_root):
        report_path = skill_dir / "evaluation_report.md"
        if not report_path.exists():
            continue
        text = report_path.read_text(encoding="utf-8", errors="ignore")
        patched, updated = patch_report_text(text)
        rows.append(
            {
                "slug": skill_dir.name,
                "report_path": str(report_path.resolve()),
                "updated": updated,
            }
        )
        if args.write and updated:
            report_path.write_text(patched, encoding="utf-8")

    report = build_report(rows, persona_root)
    write_text(Path(args.report), report)

    if args.write:
        print(f"[done] evaluation reports updated: {sum(1 for row in rows if row['updated'])}")
    else:
        print(f"[dry-run] evaluation reports unchanged: {sum(1 for row in rows if row['updated'])} pending updates")
    print(f"[done] report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
