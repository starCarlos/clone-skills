#!/usr/bin/env python3
"""Backfill meta/build_summary.json for persona skill directories."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import (
    build_summary_path,
    default_persona_root,
    default_registry_path,
    default_report_path,
    find_registry_record,
    list_persona_skill_dirs,
    load_build_summary,
    load_registry_data,
    make_build_summary,
    write_json,
    write_text,
)


def build_report(rows: list[dict], persona_root: Path) -> str:
    created = sum(1 for row in rows if row["action"] == "create")
    updated = sum(1 for row in rows if row["action"] == "update")
    missing_registry = sum(1 for row in rows if row["match_type"] == "missing")
    needs_review = sum(1 for row in rows if row["status"] == "needs_review")
    lines = [
        "# Build Summary Backfill Report",
        "",
        f"- Persona Root: {persona_root}",
        f"- Persona Skills: {len(rows)}",
        f"- To Create: {created}",
        f"- To Update: {updated}",
        f"- Missing Registry Records: {missing_registry}",
        f"- Needs Review: {needs_review}",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['slug']}")
        lines.append("")
        lines.append(f"- Skill Dir: {row['skill_dir']}")
        lines.append(f"- Action: {row['action']}")
        lines.append(f"- Registry Match: {row['match_type']}")
        lines.append(f"- Status: {row['status']}")
        lines.append(f"- Output: {row['output_path']}")
        if row["notes"]:
            lines.append(f"- Notes: {'; '.join(row['notes'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill meta/build_summary.json for persona skills")
    parser.add_argument("--registry", default=str(default_registry_path()))
    parser.add_argument("--persona-root", default=str(default_persona_root()))
    parser.add_argument(
        "--report",
        default=str(default_report_path("build-summary-backfill-report.md")),
    )
    parser.add_argument("--write", action="store_true", help="persist build_summary.json files")
    parser.add_argument("--only", default="", help="process only one slug")
    args = parser.parse_args()

    registry_data = load_registry_data(Path(args.registry))
    persons = registry_data.get("persons", [])
    persona_root = Path(args.persona_root)

    rows: list[dict] = []
    for skill_dir in list_persona_skill_dirs(persona_root):
        if args.only and skill_dir.name != args.only:
            continue
        existing_summary = load_build_summary(skill_dir)
        record, match_type = find_registry_record(persons, skill_dir, skill_dir.name)
        summary, notes = make_build_summary(skill_dir, record, existing_summary, match_type=match_type)
        output_path = build_summary_path(skill_dir)
        action = "update" if existing_summary else "create"
        rows.append(
            {
                "slug": skill_dir.name,
                "skill_dir": str(skill_dir.resolve()),
                "action": action,
                "match_type": match_type,
                "status": summary["migration"]["status"],
                "output_path": str(output_path.resolve()),
                "notes": notes,
            }
        )
        if args.write:
            write_json(output_path, summary)

    report = build_report(rows, persona_root)
    write_text(Path(args.report), report)

    if args.write:
        print(f"[done] build summaries written: {len(rows)}")
    else:
        print(f"[dry-run] build summaries not written: {len(rows)}")
    print(f"[done] report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
