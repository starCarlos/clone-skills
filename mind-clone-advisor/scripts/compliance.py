#!/usr/bin/env python3
"""Runtime compliance gate helpers for mind-clone-advisor."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import (
    AUTH_STATUSES,
    SOURCE_LEGITIMACY,
    SUBJECT_TYPES,
    default_registry_path,
    evaluate_compliance_readiness,
    find_registry_record,
    infer_person_name,
    load_build_summary_compliance,
    load_registry_data,
    normalize_registry_record,
)


def add_compliance_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--subject-type", default="", choices=sorted(SUBJECT_TYPES))
    parser.add_argument("--authorization-status", default="", choices=sorted(AUTH_STATUSES))
    parser.add_argument("--authorization-note", default="")
    parser.add_argument("--authorization-checked-at", default="")
    parser.add_argument("--source-legitimacy", default="", choices=sorted(SOURCE_LEGITIMACY))


def apply_compliance_fields(record: dict, args: argparse.Namespace) -> dict:
    updated = dict(record)
    mapping = {
        "subject_type": "subject_type",
        "authorization_status": "authorization_status",
        "authorization_note": "authorization_note",
        "authorization_checked_at": "authorization_checked_at",
        "source_legitimacy": "source_legitimacy",
    }
    for arg_name, key in mapping.items():
        if not hasattr(args, arg_name):
            continue
        value = getattr(args, arg_name)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        updated[key] = value
    return normalize_registry_record(updated)


def lookup_registry_record(
    registry_path: Path,
    *,
    skill_dir: Path | None = None,
    slug: str = "",
    name: str = "",
) -> tuple[dict | None, str]:
    data = load_registry_data(registry_path)
    persons = data.get("persons", [])
    if skill_dir is not None:
        record, match = find_registry_record(persons, skill_dir, slug or skill_dir.name)
        if record is not None:
            return record, match
    if slug:
        for record in persons:
            if str(record.get("slug", "")).strip() == slug:
                return record, "slug"
    if name:
        for record in persons:
            if str(record.get("name", "")).strip() == name:
                return record, "name"
    return None, "missing"


def resolve_existing_skill_record(
    skill_dir: Path,
    registry_path: Path,
    *,
    slug: str = "",
    name: str = "",
) -> tuple[dict, str]:
    record, match = lookup_registry_record(registry_path, skill_dir=skill_dir, slug=slug, name=name)
    if record is not None:
        return normalize_registry_record(record), f"registry:{match}"

    summary_payload = load_build_summary_compliance(skill_dir)
    if summary_payload:
        record = {
            "name": name or infer_person_name(skill_dir),
            "slug": slug or skill_dir.name,
            "skill_dir": str(skill_dir.resolve()),
            **summary_payload,
        }
        return normalize_registry_record(record), "build_summary"

    inferred = {
        "name": name or infer_person_name(skill_dir),
        "slug": slug or skill_dir.name,
        "skill_dir": str(skill_dir.resolve()),
    }
    return normalize_registry_record(inferred), "inferred"


def enforce_build_gate(record: dict, *, context: str) -> dict:
    normalized = normalize_registry_record(record)
    readiness, reasons = evaluate_compliance_readiness(normalized)
    if readiness == "ready":
        return normalized
    reason_text = "; ".join(dict.fromkeys(reasons)) if reasons else "manual review required"
    raise SystemExit(f"COMPLIANCE_BLOCKED: {context}: {reason_text}")


def default_runtime_registry() -> str:
    return str(default_registry_path())
