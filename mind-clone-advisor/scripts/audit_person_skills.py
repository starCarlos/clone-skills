#!/usr/bin/env python3
"""Audit persona skills for registry linkage, build summary state, and report scope."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import (
    build_summary_path,
    default_persona_root,
    default_registry_path,
    default_report_path,
    evaluate_compliance_readiness,
    find_registry_record,
    inspect_jsonl_integrity,
    list_persona_skill_dirs,
    load_build_summary,
    load_build_summary_compliance,
    load_registry_data,
    normalize_registry_record,
    today_str,
    triage_compliance_review,
    write_text,
)

SCOPE_MARKERS = ("artifact coverage", "not live response quality")


def report_scope_ok(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return all(marker in text for marker in SCOPE_MARKERS)


def review_command(row: dict) -> str:
    if row["compliance_status"] == "ready":
        return "none"
    checked_at = row["authorization_checked_at"] or today_str()
    return (
        f"python3 scripts/person.py patch --person {row['slug']} "
        f"--authorization-status {row['suggested_authorization_status'] or '<verified-or-not_required>'} "
        f"--source-legitimacy {row['suggested_source_legitimacy'] or '<public_materials_verified|mixed>'} "
        f"--authorization-checked-at {checked_at}"
    )


def review_note(row: dict) -> str:
    if row["can_review_now"]:
        return row["triage_note"]
    return f"{row['triage_note']} 当前不建议进入默认 build/rebuild/dispatch。"


def build_report(rows: list[dict], registry_only: list[dict], persona_root: Path) -> str:
    linked = sum(1 for row in rows if row["match_type"] != "missing")
    build_summary_present = sum(1 for row in rows if row["build_summary_present"])
    scope_updated = sum(1 for row in rows if row["scope_ok"])
    manifest_ok = sum(1 for row in rows if row["manifest_status"] == "valid")
    ready = sum(1 for row in rows if row["ready_for_strict_gate"])
    needs_review = sum(1 for row in rows if row["compliance_status"] != "ready")
    source_review_only = sum(1 for row in rows if row["triage_bucket"] == "source_review_only")
    authorization_blocked = sum(1 for row in rows if row["triage_bucket"] == "authorization_blocked")
    metadata_fix = sum(1 for row in rows if row["triage_bucket"] == "metadata_fix")
    lines = [
        "# Persona Skills Audit Report",
        "",
        f"- Persona Root: {persona_root}",
        f"- Persona Skills: {len(rows)}",
        f"- Linked To Registry: {linked}",
        f"- Build Summary Present: {build_summary_present}",
        f"- Evaluation Scope Updated: {scope_updated}",
        f"- Manifest Integrity OK: {manifest_ok}",
        f"- Ready For Strict Gate: {ready}",
        f"- Needs Manual Review: {needs_review}",
        f"- Triage Source Review Only: {source_review_only}",
        f"- Triage Authorization Blocked: {authorization_blocked}",
        f"- Triage Metadata Fix: {metadata_fix}",
        f"- Registry Only Entries: {len(registry_only)}",
        "",
    ]
    quick_rows = [row for row in rows if row["can_review_now"] and row["compliance_status"] != "ready"]
    blocked_rows = [row for row in rows if not row["can_review_now"]]
    if quick_rows:
        lines.append("## Quick Review Candidates")
        lines.append("")
        for row in quick_rows:
            lines.append(f"- {row['slug']} [{row['triage_bucket']}] priority={row['triage_priority']}: {row['triage_note']}")
        lines.append("")
    if blocked_rows:
        lines.append("## External Blockers")
        lines.append("")
        for row in blocked_rows:
            lines.append(f"- {row['slug']} [{row['triage_bucket']}] priority={row['triage_priority']}: {row['triage_note']}")
        lines.append("")
    for row in rows:
        lines.append(f"## {row['slug']}")
        lines.append("")
        lines.append(f"- Skill Dir: {row['skill_dir']}")
        lines.append(f"- Registry Match: {row['match_type']}")
        lines.append(f"- Build Summary: {'present' if row['build_summary_present'] else 'missing'}")
        lines.append(f"- Evaluation Report Scope: {'updated' if row['scope_ok'] else 'legacy_or_missing'}")
        lines.append(f"- Manifest Integrity: {row['manifest_status']}")
        lines.append(f"- Compliance Status: {row['compliance_status']}")
        lines.append(f"- Build Summary Compliance Drift: {'yes' if row['build_summary_compliance_drift'] else 'no'}")
        lines.append(
            f"- Compliance Fields: subject_type={row['subject_type']}, "
            f"authorization_status={row['authorization_status']}, "
            f"source_legitimacy={row['source_legitimacy']}, "
            f"authorization_checked_at={row['authorization_checked_at'] or 'missing'}"
        )
        lines.append(
            f"- Registry Source: enabled={row['enabled']}, ingestor={row['ingestor'] or '-'}, "
            f"source_config={row['source_config'] or '-'}, input_corpus={row['input_corpus'] or '-'}"
        )
        lines.append(f"- Ready For Strict Gate: {'yes' if row['ready_for_strict_gate'] else 'no'}")
        lines.append(
            f"- Review Triage: bucket={row['triage_bucket']}, priority={row['triage_priority']}, "
            f"can_review_now={'yes' if row['can_review_now'] else 'no'}"
        )
        lines.append(f"- Review Note: {row['review_note']}")
        lines.append(f"- Review Command: `{row['review_command']}`")
        if row["notes"]:
            lines.append(f"- Notes: {'; '.join(row['notes'])}")
        lines.append("")
    if registry_only:
        lines.append("## Registry Only Entries")
        lines.append("")
        for record in registry_only:
            slug = record.get("slug", "") or record.get("name", "") or "unknown"
            lines.append(f"- {slug}: skill_dir={record.get('skill_dir', '')}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit persona skill migration state")
    parser.add_argument("--registry", default=str(default_registry_path()))
    parser.add_argument("--persona-root", default=str(default_persona_root()))
    parser.add_argument(
        "--report",
        default=str(default_report_path("person-skills-audit-report.md")),
    )
    parser.add_argument("--only", default="", help="audit only one slug")
    args = parser.parse_args()

    registry_data = load_registry_data(Path(args.registry))
    persons = registry_data.get("persons", [])
    persona_root = Path(args.persona_root)
    persona_dirs = list_persona_skill_dirs(persona_root)

    seen_registry = set()
    rows: list[dict] = []
    for skill_dir in persona_dirs:
        if args.only and skill_dir.name != args.only:
            continue
        record, match_type = find_registry_record(persons, skill_dir, skill_dir.name)
        if record is not None:
            seen_registry.add(id(record))
        normalized_record = normalize_registry_record(
            record
            or {
                "name": skill_dir.name,
                "slug": skill_dir.name,
                "skill_dir": str(skill_dir.resolve()),
            }
        )
        build_summary = load_build_summary(skill_dir)
        summary_path = build_summary_path(skill_dir)
        evaluation_report_path = skill_dir / "evaluation_report.md"
        manifest_path = skill_dir / "kb" / "manifest.jsonl"
        scope_ok = report_scope_ok(evaluation_report_path)
        manifest_report = inspect_jsonl_integrity(manifest_path)
        manifest_status = str(manifest_report["status"])
        build_summary_compliance = load_build_summary_compliance(skill_dir) if build_summary else {}
        build_summary_normalized = normalize_registry_record(
            {
                "name": str(normalized_record.get("name", "")).strip(),
                "slug": str(normalized_record.get("slug", "")).strip(),
                "skill_dir": str(skill_dir.resolve()),
                **build_summary_compliance,
            }
        ) if build_summary_compliance else {}

        if record is not None:
            compliance_payload = normalized_record
        elif build_summary:
            compliance_payload = build_summary_normalized
        else:
            compliance_payload = {}

        compliance_status, reasons = evaluate_compliance_readiness(compliance_payload)
        ready_for_strict_gate = bool(build_summary) and scope_ok and compliance_status == "ready"
        triage = triage_compliance_review(normalized_record)
        build_summary_compliance_drift = False
        if build_summary_compliance:
            compare_keys = (
                "subject_type",
                "authorization_status",
                "authorization_checked_at",
                "source_legitimacy",
            )
            build_summary_compliance_drift = any(
                str(build_summary_normalized.get(key, "")).strip() != str(normalized_record.get(key, "")).strip()
                for key in compare_keys
            )
        notes = list(reasons)
        if match_type == "missing":
            notes.append("registry record missing")
        if not summary_path.exists():
            notes.append("build_summary missing")
        if not scope_ok:
            notes.append("evaluation report scope note missing")
        if manifest_status != "valid":
            notes.append(f"manifest {manifest_status}")
        if build_summary_compliance_drift:
            notes.append("build_summary compliance drift")

        rows.append(
            {
                "slug": skill_dir.name,
                "skill_dir": str(skill_dir.resolve()),
                "match_type": match_type,
                "build_summary_present": bool(build_summary),
                "scope_ok": scope_ok,
                "manifest_status": manifest_status,
                "compliance_status": compliance_status,
                "build_summary_compliance_drift": build_summary_compliance_drift,
                "subject_type": str(normalized_record.get("subject_type", "")).strip(),
                "authorization_status": str(normalized_record.get("authorization_status", "")).strip(),
                "source_legitimacy": str(normalized_record.get("source_legitimacy", "")).strip(),
                "authorization_checked_at": str(normalized_record.get("authorization_checked_at", "")).strip(),
                "enabled": bool(normalized_record.get("enabled", True)),
                "ingestor": str(normalized_record.get("ingestor", "")).strip(),
                "source_config": str(normalized_record.get("source_config", "")).strip(),
                "input_corpus": str(normalized_record.get("input_corpus", "")).strip(),
                "triage_bucket": str(triage["bucket"]),
                "triage_priority": int(triage["priority"]),
                "can_review_now": bool(triage["can_review_now"]),
                "triage_note": str(triage["note"]),
                "suggested_authorization_status": str(triage["suggested_authorization_status"]),
                "suggested_source_legitimacy": str(triage["suggested_source_legitimacy"]),
                "ready_for_strict_gate": ready_for_strict_gate,
                "notes": sorted(dict.fromkeys(notes)),
            }
        )

        rows[-1]["review_command"] = review_command(rows[-1])
        rows[-1]["review_note"] = review_note(rows[-1])

    registry_only = [
        record
        for record in persons
        if record.get("skill_dir")
        and not any(str(record.get("skill_dir")).strip() == str(path.resolve()) for path in persona_dirs)
    ]

    report = build_report(rows, registry_only, persona_root)
    write_text(Path(args.report), report)
    print(f"[done] report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
