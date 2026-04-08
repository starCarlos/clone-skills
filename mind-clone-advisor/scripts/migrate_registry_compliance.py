#!/usr/bin/env python3
"""Backfill compliance metadata into registry/persons.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import (
    default_registry_path,
    default_report_path,
    evaluate_compliance_readiness,
    load_registry_data,
    normalize_registry_record,
    now_iso,
    save_registry_data,
    write_text,
)


def build_report(registry_path: Path, original: list[dict], migrated: list[dict]) -> str:
    changed = 0
    ready = 0
    needs_review = 0
    lines = [
        "# Registry Compliance Migration Report",
        "",
        f"- Generated at: {now_iso()}",
        f"- Registry: {registry_path}",
        f"- Records: {len(migrated)}",
        "",
    ]
    for before, after in zip(original, migrated):
        if before != after:
            changed += 1
        readiness, reasons = evaluate_compliance_readiness(after)
        if readiness == "ready":
            ready += 1
        else:
            needs_review += 1
        lines.append(f"## {after.get('slug') or after.get('name') or 'unknown'}")
        lines.append("")
        lines.append(f"- Name: {after.get('name', '')}")
        lines.append(f"- Action: {'changed' if before != after else 'unchanged'}")
        lines.append(f"- Subject Type: {after.get('subject_type', '') or '(missing)'}")
        lines.append(f"- Authorization Status: {after.get('authorization_status', '') or '(missing)'}")
        lines.append(f"- Source Legitimacy: {after.get('source_legitimacy', '') or '(missing)'}")
        lines.append(f"- Migration Status: {after.get('_migration_status', '') or '(missing)'}")
        lines.append(f"- Compliance Readiness: {readiness}")
        notes = after.get("_migration_notes") or []
        combined = list(notes) + list(reasons)
        if combined:
            lines.append(f"- Notes: {'; '.join(dict.fromkeys(combined))}")
        lines.append("")
    lines.insert(5, f"- Changed: {changed}")
    lines.insert(6, f"- Ready: {ready}")
    lines.insert(7, f"- Needs Review: {needs_review}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill compliance metadata into persons.json")
    parser.add_argument("--registry", default=str(default_registry_path()))
    parser.add_argument(
        "--report",
        default=str(default_report_path("mind-clone-registry-migration-report.md")),
    )
    parser.add_argument("--write", action="store_true", help="persist migrated registry to disk")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    data = load_registry_data(registry_path)
    original = list(data.get("persons", []))
    migrated = [normalize_registry_record(record) for record in original]

    report = build_report(registry_path, original, migrated)
    write_text(Path(args.report), report)

    if args.write:
        data["persons"] = migrated
        save_registry_data(registry_path, data)
        print(f"[done] registry updated: {registry_path}")
    else:
        print(f"[dry-run] registry unchanged: {registry_path}")
    print(f"[done] report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
