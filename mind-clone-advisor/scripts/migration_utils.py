#!/usr/bin/env python3
"""Shared helpers for mind-clone-advisor migration scripts."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from utils import get_project_root, load_jsonl, load_registry, parse_date_from_filename, slugify

SUBJECT_TYPES = {
    "historical",
    "deceased_public_figure",
    "living_public_figure",
    "private_person",
}

AUTH_STATUSES = {
    "not_required",
    "pending",
    "verified",
    "rejected",
}

SOURCE_LEGITIMACY = {
    "public_materials_verified",
    "mixed",
    "unclear",
}

TRIAGE_BUCKETS = {
    "ready",
    "source_review_only",
    "authorization_blocked",
    "metadata_fix",
}

KNOWN_SUBJECT_TYPES = {
    "arthur-hayes": "living_public_figure",
    "aswath-damodaran": "living_public_figure",
    "charlie-munger": "deceased_public_figure",
    "duan-yongping": "living_public_figure",
    "fu-peng": "living_public_figure",
    "george-soros": "living_public_figure",
    "howard-marks": "living_public_figure",
    "joel-greenblatt": "living_public_figure",
    "li-xunlei": "living_public_figure",
    "michael-saylor": "living_public_figure",
    "peter-lynch": "living_public_figure",
    "ray-dalio": "living_public_figure",
    "ren-zeping": "living_public_figure",
    "uncle-wan": "living_public_figure",
    "vitalik-buterin": "living_public_figure",
    "warren-buffett": "living_public_figure",
}

EVALUATION_LIMITATIONS = [
    "does_not_execute_live_persona_responses",
    "scores_supporting_artifacts_not_real_dialogue_quality",
]


def advisor_root() -> Path:
    return get_project_root()


def workspace_root() -> Path:
    return advisor_root().parent.parent


def default_registry_path() -> Path:
    return advisor_root() / "registry" / "persons.json"


def default_persona_root() -> Path:
    return workspace_root() / "skills" / "personas"


def default_report_path(name: str) -> Path:
    return workspace_root() / "temp" / name


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_registry_data(path: Path) -> dict:
    return load_registry(path)


def save_registry_data(path: Path, data: dict) -> None:
    write_json(path, data)


def list_persona_skill_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "SKILL.md").exists())


def _strip_suffixes(text: str) -> str:
    stripped = text.strip()
    patterns = [
        r"\s+Mind Clone$",
        r"\s+思维克隆$",
        r"\s+Mind Clone Advisor$",
        r"\s+思维顾问$",
    ]
    for pattern in patterns:
        stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def _frontmatter_value(text: str, key: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) != 3:
        return ""
    front = parts[1]
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", front)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def infer_person_name(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        header_name = _frontmatter_value(text, "name")
        if header_name and header_name != skill_dir.name and "-" not in header_name:
            return _strip_suffixes(header_name)
        for line in text.splitlines():
            if line.startswith("# "):
                heading = line[2:].strip()
                if heading:
                    return _strip_suffixes(heading)
    return skill_dir.name


def infer_slug(name: str, fallback: str = "") -> str:
    if fallback:
        return fallback
    try:
        return slugify(name)
    except Exception:
        return ""


def infer_subject_type(record: dict) -> str:
    subject_type = str(record.get("subject_type", "")).strip()
    if subject_type in SUBJECT_TYPES:
        return subject_type
    slug = str(record.get("slug", "")).strip()
    if not slug:
        name = str(record.get("name", "")).strip()
        slug = infer_slug(name, "")
    return KNOWN_SUBJECT_TYPES.get(slug, "")


def infer_authorization_status(subject_type: str, current: str = "") -> str:
    if current in AUTH_STATUSES:
        return current
    if subject_type in {"historical", "deceased_public_figure"}:
        return "not_required"
    if subject_type in {"living_public_figure", "private_person"}:
        return "pending"
    return ""


def normalize_registry_record(record: dict) -> dict:
    migrated = deepcopy(record)
    notes: list[str] = []

    initial_complete = (
        str(record.get("subject_type", "")).strip() in SUBJECT_TYPES
        and str(record.get("authorization_status", "")).strip() in AUTH_STATUSES
        and str(record.get("source_legitimacy", "")).strip() in SOURCE_LEGITIMACY
    )

    subject_type = infer_subject_type(migrated)
    if subject_type:
        if str(record.get("subject_type", "")).strip() not in SUBJECT_TYPES:
            notes.append(f"inferred subject_type={subject_type}")
        migrated["subject_type"] = subject_type
    else:
        migrated.setdefault("subject_type", "")
        notes.append("subject_type unresolved")

    authorization_status = infer_authorization_status(
        migrated.get("subject_type", ""),
        str(record.get("authorization_status", "")).strip(),
    )
    if authorization_status:
        if str(record.get("authorization_status", "")).strip() not in AUTH_STATUSES:
            notes.append(f"set authorization_status={authorization_status}")
        migrated["authorization_status"] = authorization_status
    else:
        migrated.setdefault("authorization_status", "")
        notes.append("authorization_status unresolved")

    source_legitimacy = str(record.get("source_legitimacy", "")).strip()
    if source_legitimacy not in SOURCE_LEGITIMACY:
        source_legitimacy = "unclear"
        notes.append("set source_legitimacy=unclear")
    migrated["source_legitimacy"] = source_legitimacy

    if not str(migrated.get("authorization_note", "")).strip():
        migrated["authorization_note"] = "legacy record migrated; manual review required"
        notes.append("seeded authorization_note")
    migrated.setdefault("authorization_checked_at", "")
    migrated["compliance_schema_version"] = 1

    needs_review = False
    if migrated.get("subject_type", "") not in SUBJECT_TYPES:
        needs_review = True
    if migrated.get("authorization_status", "") in {"", "pending"}:
        needs_review = True
    if migrated.get("source_legitimacy", "") == "unclear":
        needs_review = True

    if initial_complete and not notes:
        migrated["_legacy_compliance"] = bool(migrated.get("_legacy_compliance", False))
        migrated["_migration_status"] = "already_compliant"
    else:
        migrated["_legacy_compliance"] = True
        migrated["_migration_status"] = "needs_review" if needs_review else "normalized"
    if notes:
        migrated["_migration_notes"] = notes
    return migrated


def make_registry_record_from_skill(skill_dir: Path) -> dict:
    name = infer_person_name(skill_dir)
    record = {
        "name": name,
        "slug": skill_dir.name,
        "skill_dir": str(skill_dir.resolve()),
        "overwrite_outputs": True,
        # Safe default: do not automatically enroll newly backfilled skills into
        # scheduled update flows until compliance fields are reviewed.
        "enabled": False,
        "authorization_note": "registry entry backfilled from existing persona skill; manual review required",
        "_registry_backfill": True,
    }
    plain_text_dir = skill_dir / "kb" / "plain_text"
    if plain_text_dir.exists():
        record["input_corpus"] = str(plain_text_dir.resolve())
    return normalize_registry_record(record)


def evaluate_compliance_readiness(record: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    subject_type = str(record.get("subject_type", "")).strip()
    authorization_status = str(record.get("authorization_status", "")).strip()
    authorization_checked_at = str(record.get("authorization_checked_at", "")).strip()
    source_legitimacy = str(record.get("source_legitimacy", "")).strip()

    if subject_type not in SUBJECT_TYPES:
        reasons.append("subject_type missing_or_invalid")
    if authorization_status not in AUTH_STATUSES:
        reasons.append("authorization_status missing_or_invalid")
    if source_legitimacy not in SOURCE_LEGITIMACY:
        reasons.append("source_legitimacy missing_or_invalid")

    if source_legitimacy == "unclear":
        reasons.append("source_legitimacy=unclear")
    if authorization_status in {"verified", "not_required"} and not authorization_checked_at:
        reasons.append("authorization_checked_at missing")
    if subject_type in {"living_public_figure", "private_person"} and authorization_status != "verified":
        reasons.append(f"{subject_type} requires authorization_status=verified")
    if subject_type in {"historical", "deceased_public_figure"} and authorization_status not in {"not_required", "verified"}:
        reasons.append(f"{subject_type} requires authorization_status in {{not_required, verified}}")
    if authorization_status == "rejected":
        reasons.append("authorization_status=rejected")

    return ("ready" if not reasons else "needs_review"), reasons


def triage_compliance_review(record: dict) -> dict:
    normalized = normalize_registry_record(record)
    compliance_status, reasons = evaluate_compliance_readiness(normalized)
    subject_type = str(normalized.get("subject_type", "")).strip()
    authorization_status = str(normalized.get("authorization_status", "")).strip()
    authorization_checked_at = str(normalized.get("authorization_checked_at", "")).strip()
    source_legitimacy = str(normalized.get("source_legitimacy", "")).strip()

    if compliance_status == "ready":
        return {
            "bucket": "ready",
            "priority": 0,
            "can_review_now": True,
            "note": "无需人工补充，已满足 strict gate。",
            "suggested_authorization_status": authorization_status,
            "suggested_source_legitimacy": source_legitimacy,
        }

    if subject_type not in SUBJECT_TYPES:
        return {
            "bucket": "metadata_fix",
            "priority": 1,
            "can_review_now": True,
            "note": "先补全或修正 subject_type，再继续合规确认。",
            "suggested_authorization_status": "",
            "suggested_source_legitimacy": "",
        }

    if subject_type in {"historical", "deceased_public_figure"}:
        auth_target = authorization_status if authorization_status in {"not_required", "verified"} else "not_required"
        legitimacy_target = source_legitimacy if source_legitimacy != "unclear" else "<public_materials_verified|mixed>"
        note = "无需额外授权；确认来源确属合法公开材料后即可关闭。"
        if not authorization_checked_at:
            note += " 同时补上 authorization_checked_at。"
        return {
            "bucket": "source_review_only",
            "priority": 1,
            "can_review_now": True,
            "note": note,
            "suggested_authorization_status": auth_target,
            "suggested_source_legitimacy": legitimacy_target,
        }

    if subject_type in {"living_public_figure", "private_person"} and authorization_status != "verified":
        legitimacy_target = source_legitimacy if source_legitimacy != "unclear" else "<public_materials_verified|mixed>"
        note = "外部阻塞：必须先拿到明确授权，再做来源合法性确认。"
        if not authorization_checked_at:
            note += " 授权确认后记得补 authorization_checked_at。"
        return {
            "bucket": "authorization_blocked",
            "priority": 3 if subject_type == "private_person" else 2,
            "can_review_now": False,
            "note": note,
            "suggested_authorization_status": "verified",
            "suggested_source_legitimacy": legitimacy_target,
        }

    legitimacy_target = source_legitimacy if source_legitimacy != "unclear" else "<public_materials_verified|mixed>"
    note = "授权已就绪，补来源合法性即可。"
    if not authorization_checked_at:
        note += " 同时补上 authorization_checked_at。"
    return {
        "bucket": "source_review_only",
        "priority": 1,
        "can_review_now": True,
        "note": note,
        "suggested_authorization_status": authorization_status or "verified",
        "suggested_source_legitimacy": legitimacy_target,
    }


def find_registry_record(persons: list[dict], skill_dir: Path, slug: str = "") -> tuple[dict | None, str]:
    skill_dir_str = str(skill_dir.resolve())
    for record in persons:
        if str(record.get("skill_dir", "")).strip() == skill_dir_str:
            return record, "skill_dir"
    slug = slug or skill_dir.name
    for record in persons:
        if str(record.get("slug", "")).strip() == slug:
            return record, "slug"
    return None, "missing"


def build_summary_path(skill_dir: Path) -> Path:
    return skill_dir / "meta" / "build_summary.json"


def load_build_summary(skill_dir: Path) -> dict | None:
    data = load_json(build_summary_path(skill_dir))
    return data if isinstance(data, dict) else None


def load_corpus_summary(skill_dir: Path) -> dict | None:
    candidates = [
        skill_dir / "analysis" / "corpus_summary.json",
        skill_dir / "analysis" / "corpus_summary.json.auto.json",
    ]
    for path in candidates:
        data = load_json(path)
        if isinstance(data, dict):
            return data
    return None


def _parse_jsonl_records(lines: list[str]) -> tuple[list[dict], int]:
    items: list[dict] = []
    errors = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            errors += 1
            continue
        if not isinstance(obj, dict):
            errors += 1
            continue
        items.append(obj)
    return items, errors


def inspect_jsonl_integrity(path: Path) -> dict:
    if not path.exists():
        return {
            "status": "missing",
            "line_count": 0,
            "entry_count": 0,
            "error_count": 0,
            "recoverable": False,
            "entries": [],
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed, errors = _parse_jsonl_records(raw_lines)
    if raw_lines and errors == 0:
        return {
            "status": "valid",
            "line_count": len(raw_lines),
            "entry_count": len(parsed),
            "error_count": 0,
            "recoverable": False,
            "entries": parsed,
        }

    if len(raw_lines) == 1 and "\\n" in text:
        recovered_lines = [line.strip() for line in text.split("\\n") if line.strip()]
        recovered, recovered_errors = _parse_jsonl_records(recovered_lines)
        if recovered_lines and recovered_errors == 0:
            return {
                "status": "escaped_single_line",
                "line_count": 1,
                "entry_count": len(recovered),
                "error_count": max(1, errors),
                "recoverable": True,
                "entries": recovered,
            }

    status = "empty" if not raw_lines else "malformed"
    return {
        "status": status,
        "line_count": len(raw_lines),
        "entry_count": len(parsed),
        "error_count": errors,
        "recoverable": False,
        "entries": [],
    }


def load_manifest_entries(path: Path) -> list[dict]:
    report = inspect_jsonl_integrity(path)
    if report["status"] in {"valid", "escaped_single_line"}:
        return list(report["entries"])
    if path.exists():
        return load_jsonl(path)
    return []


def infer_languages(manifest_entries: list[dict]) -> list[str]:
    languages = sorted(
        {
            str(entry.get("language", "")).strip()
            for entry in manifest_entries
            if str(entry.get("language", "")).strip()
        }
    )
    return languages or ["unknown"]


def count_documents(skill_dir: Path, corpus_summary: dict | None, manifest_entries: list[dict]) -> int:
    if corpus_summary and isinstance(corpus_summary.get("total"), int):
        return int(corpus_summary["total"])
    if manifest_entries:
        return len(manifest_entries)
    plain_dir = skill_dir / "kb" / "plain_text"
    if not plain_dir.exists():
        return 0
    files = list(plain_dir.glob("*.md")) + list(plain_dir.glob("*.txt"))
    return len(files)


def infer_date_range(skill_dir: Path, corpus_summary: dict | None, manifest_entries: list[dict]) -> dict:
    if corpus_summary:
        date_range = corpus_summary.get("date_range")
        if isinstance(date_range, dict):
            start = str(date_range.get("start", "")).strip()
            end = str(date_range.get("end", "")).strip()
            if start or end:
                return {"start": start or "unknown", "end": end or "unknown"}

    dates = sorted(
        str(entry.get("date", "")).strip()
        for entry in manifest_entries
        if str(entry.get("date", "")).strip()
    )
    if not dates:
        plain_dir = skill_dir / "kb" / "plain_text"
        file_dates = []
        if plain_dir.exists():
            for path in list(plain_dir.glob("*.md")) + list(plain_dir.glob("*.txt")):
                parsed = parse_date_from_filename(path.name)
                if parsed:
                    file_dates.append(parsed)
        dates = sorted(file_dates)
    if dates:
        return {"start": dates[0], "end": dates[-1]}
    return {"start": "unknown", "end": "unknown"}


def artifact_relpath(skill_dir: Path, relative: str) -> str:
    path = skill_dir / relative
    return relative if path.exists() else ""


def collect_artifacts(skill_dir: Path) -> dict:
    return {
        "thinking_profile": artifact_relpath(skill_dir, "thinking_profile.md"),
        "system_prompt": artifact_relpath(skill_dir, "system_prompt.md"),
        "evaluation_plan": artifact_relpath(skill_dir, "evaluation_plan.md"),
        "evaluation_report": artifact_relpath(skill_dir, "evaluation_report.md"),
        "validation_report": artifact_relpath(skill_dir, "notes/validation_report.md"),
        "evidence_anchors": artifact_relpath(skill_dir, "evidence_anchors.md"),
    }


def make_build_summary(
    skill_dir: Path,
    record: dict | None,
    existing_summary: dict | None = None,
    match_type: str = "missing",
) -> tuple[dict, list[str]]:
    existing_summary = existing_summary or {}
    normalized = normalize_registry_record(record or {
        "name": infer_person_name(skill_dir),
        "slug": skill_dir.name,
        "skill_dir": str(skill_dir.resolve()),
    })
    notes = list(normalized.get("_migration_notes", []))
    if record is None:
        notes.append("registry record missing")

    corpus_summary = load_corpus_summary(skill_dir)
    manifest_path = skill_dir / "kb" / "manifest.jsonl"
    ingest_manifest_path = skill_dir / "kb" / "manifest.ingest.jsonl"
    manifest_entries = load_manifest_entries(manifest_path)
    readiness, readiness_reasons = evaluate_compliance_readiness(normalized)
    notes.extend(readiness_reasons)

    now = now_iso()
    skill_dir_resolved = str(skill_dir.resolve())
    summary = {
        "schema_version": 1,
        "scaffold_version": existing_summary.get("scaffold_version") or "migration-backfill-2026-03-16",
        "generated_at": existing_summary.get("generated_at") or now,
        "updated_at": now,
        "person": {
            "name": str(normalized.get("name", "")).strip() or infer_person_name(skill_dir),
            "slug": str(normalized.get("slug", "")).strip() or skill_dir.name,
            "subject_type": str(normalized.get("subject_type", "")).strip(),
        },
        "compliance": {
            "authorization_status": str(normalized.get("authorization_status", "")).strip(),
            "authorization_note": str(normalized.get("authorization_note", "")).strip(),
            "authorization_checked_at": str(normalized.get("authorization_checked_at", "")).strip(),
            "source_legitimacy": str(normalized.get("source_legitimacy", "")).strip(),
            "legacy_record": bool(normalized.get("_legacy_compliance", False)),
        },
        "inputs": {
            "skill_dir": skill_dir_resolved,
            "plain_text_dir": str((skill_dir / "kb" / "plain_text").resolve()),
            "full_archive_dir": str((skill_dir / "kb" / "full_archive").resolve()),
            "ingest_manifest": str(ingest_manifest_path.resolve()) if ingest_manifest_path.exists() else "",
            "kb_manifest": str(manifest_path.resolve()) if manifest_path.exists() else "",
        },
        "corpus": {
            "document_count": count_documents(skill_dir, corpus_summary, manifest_entries),
            "date_range": infer_date_range(skill_dir, corpus_summary, manifest_entries),
            "languages": infer_languages(manifest_entries),
            "min_word_count_threshold": 80,
        },
        "artifacts": collect_artifacts(skill_dir),
        "evaluation": {
            "mode": "artifact_coverage",
            "limitations": list(EVALUATION_LIMITATIONS),
        },
        "migration": {
            "source": "backfill_build_summary.py",
            "registry_match": match_type,
            "status": readiness,
            "notes": sorted(dict.fromkeys(note for note in notes if note)),
        },
    }
    return summary, summary["migration"]["notes"]


def load_build_summary_compliance(skill_dir: Path) -> dict:
    summary = load_build_summary(skill_dir) or {}
    compliance = summary.get("compliance")
    person = summary.get("person")
    evaluation = summary.get("evaluation")
    payload: dict = {}
    if isinstance(compliance, dict):
        payload.update(compliance)
    if isinstance(person, dict):
        payload["subject_type"] = person.get("subject_type", "")
    if isinstance(evaluation, dict):
        payload["evaluation_mode"] = evaluation.get("mode", "")
    return payload


def sync_build_summary_from_record(
    skill_dir: Path,
    record: dict,
    *,
    match_type: str = "registry:sync",
) -> bool:
    existing_summary = load_build_summary(skill_dir)
    if not existing_summary:
        return False
    summary, _ = make_build_summary(
        skill_dir,
        record,
        existing_summary=existing_summary,
        match_type=match_type,
    )
    write_json(build_summary_path(skill_dir), summary)
    return True
