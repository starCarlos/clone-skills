#!/usr/bin/env python3
"""Backfill missing registry entries from existing persona skill directories."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import (
    default_persona_root,
    default_registry_path,
    default_report_path,
    find_registry_record,
    list_persona_skill_dirs,
    load_registry_data,
    make_registry_record_from_skill,
    save_registry_data,
    write_text,
)


def build_report(registry_path: Path, rows: list[dict]) -> str:
    lines = [
        "# Missing Registry Entries Backfill Report",
        "",
        f"- Registry: {registry_path}",
        f"- Missing Personas Found: {len(rows)}",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['slug']}")
        lines.append("")
        lines.append(f"- Name: {row['name']}")
        lines.append(f"- Skill Dir: {row['skill_dir']}")
        lines.append(f"- Enabled Default: {row['enabled']}")
        lines.append(f"- Subject Type: {row['subject_type'] or '(missing)'}")
        lines.append(f"- Authorization Status: {row['authorization_status'] or '(missing)'}")
        lines.append(f"- Source Legitimacy: {row['source_legitimacy'] or '(missing)'}")
        if row["notes"]:
            lines.append(f"- Notes: {'; '.join(row['notes'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing registry entries from persona skills")
    parser.add_argument("--registry", default=str(default_registry_path()))
    parser.add_argument("--persona-root", default=str(default_persona_root()))
    parser.add_argument(
        "--report",
        default=str(default_report_path("missing-registry-entries-report.md")),
    )
    parser.add_argument("--write", action="store_true", help="append missing entries to registry")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    persona_root = Path(args.persona_root)
    data = load_registry_data(registry_path)
    persons = list(data.get("persons", []))

    new_records = []
    rows = []
    for skill_dir in list_persona_skill_dirs(persona_root):
        match, _ = find_registry_record(persons, skill_dir, skill_dir.name)
        if match is not None:
            continue
        record = make_registry_record_from_skill(skill_dir)
        new_records.append(record)
        rows.append(
            {
                "slug": record.get("slug", ""),
                "name": record.get("name", ""),
                "skill_dir": record.get("skill_dir", ""),
                "enabled": record.get("enabled", False),
                "subject_type": record.get("subject_type", ""),
                "authorization_status": record.get("authorization_status", ""),
                "source_legitimacy": record.get("source_legitimacy", ""),
                "notes": record.get("_migration_notes", []),
            }
        )

    report = build_report(registry_path, rows)
    write_text(Path(args.report), report)

    if args.write and new_records:
        persons.extend(new_records)
        data["persons"] = persons
        save_registry_data(registry_path, data)
        print(f"[done] appended missing registry entries: {len(new_records)}")
    elif args.write:
        print("[done] no missing registry entries to append")
    else:
        print(f"[dry-run] missing registry entries not written: {len(new_records)}")
    print(f"[done] report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
