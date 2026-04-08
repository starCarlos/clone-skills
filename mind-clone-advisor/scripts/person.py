#!/usr/bin/env python3
"""Manage mind-clone person registry and dispatch builds/updates."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from compliance import add_compliance_fields, apply_compliance_fields
from migration_utils import (
    AUTH_STATUSES,
    SOURCE_LEGITIMACY,
    SUBJECT_TYPES,
    build_summary_path,
    evaluate_compliance_readiness,
    normalize_registry_record,
    sync_build_summary_from_record,
    today_str,
    triage_compliance_review,
)
from utils import get_project_root, load_registry, slugify

BASE_DIR = get_project_root()
DEFAULT_REGISTRY = BASE_DIR / "registry" / "persons.json"
DEFAULT_OUT_ROOT = str(BASE_DIR.parent)
REVIEW_EXPORT_FIELDS = [
    "apply",
    "slug",
    "name",
    "compliance_status",
    "reasons",
    "triage_bucket",
    "triage_priority",
    "can_review_now",
    "triage_note",
    "suggested_authorization_status",
    "suggested_source_legitimacy",
    "current_subject_type",
    "current_authorization_status",
    "current_source_legitimacy",
    "current_authorization_checked_at",
    "current_authorization_note",
    "current_enabled",
    "review_subject_type",
    "review_authorization_status",
    "review_source_legitimacy",
    "review_authorization_checked_at",
    "review_authorization_note",
    "review_enabled",
    "ingestor",
    "source_config",
    "input_corpus",
    "skill_dir",
    "review_comment",
]
TRUTHY = {"1", "true", "yes", "y"}
FALSY = {"0", "false", "no", "n"}


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_person_index(persons: list[dict], key: str) -> int:
    for i, p in enumerate(persons):
        if key in {p.get("slug", ""), p.get("name", "")}:
            return i
    return -1


def build_entry(args: argparse.Namespace, out_root: str) -> dict:
    name = args.name.strip()
    if not name:
        raise SystemExit("--name is required")

    slug = args.slug.strip() if args.slug else slugify(name)
    if not slug:
        raise SystemExit("Unable to infer slug from name; provide --slug")

    if args.ingestor and not args.source_config:
        raise SystemExit("--source-config is required when using --ingestor")
    if not args.ingestor and not args.input_corpus:
        raise SystemExit("Provide --ingestor + --source-config or --input-corpus")

    skill_dir = args.skill_dir or str(Path(out_root) / slug)

    entry = {
        "name": name,
        "slug": slug,
        "skill_dir": skill_dir,
    }
    if args.ingestor:
        entry["ingestor"] = args.ingestor
        entry["source_config"] = args.source_config
    if args.input_corpus:
        entry["input_corpus"] = args.input_corpus
    if args.since:
        entry["since"] = args.since
    if args.incremental is not None:
        entry["incremental"] = args.incremental
    if args.overwrite_outputs:
        entry["overwrite_outputs"] = True
    if args.enabled is not None:
        entry["enabled"] = args.enabled
    return apply_compliance_fields(entry, args)


def merge_entry(existing: dict, incoming: dict, replace: bool) -> dict:
    if replace:
        return incoming
    merged = dict(existing)
    for k, v in incoming.items():
        if v is None:
            continue
        merged[k] = v
    return merged


def compliance_summary(record: dict) -> tuple[dict, str, list[str]]:
    normalized = normalize_registry_record(record)
    status, reasons = evaluate_compliance_readiness(normalized)
    return normalized, status, reasons


def bool_to_csv(value: bool | None) -> str:
    if value is None:
        return ""
    return "1" if value else "0"


def parse_csv_bool(value: str, *, field_name: str) -> bool | None:
    text = value.strip().lower()
    if not text:
        return None
    if text in TRUTHY:
        return True
    if text in FALSY:
        return False
    raise ValueError(f"invalid boolean for {field_name}: {value}")


def validate_choice(value: str, allowed: set[str], *, field_name: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if text not in allowed:
        raise ValueError(f"invalid {field_name}: {value}")
    return text


def apply_patch_args(existing: dict, args: argparse.Namespace) -> dict:
    updated = dict(existing)
    field_map = {
        "name": "name",
        "slug": "slug",
        "skill_dir": "skill_dir",
        "ingestor": "ingestor",
        "source_config": "source_config",
        "input_corpus": "input_corpus",
        "since": "since",
    }
    for arg_name, key in field_map.items():
        value = getattr(args, arg_name, "")
        if isinstance(value, str):
            value = value.strip()
        if value:
            updated[key] = value

    if getattr(args, "incremental", None) is not None:
        updated["incremental"] = args.incremental
    if getattr(args, "overwrite_outputs", None) is not None:
        updated["overwrite_outputs"] = args.overwrite_outputs
    if getattr(args, "enabled", None) is not None:
        updated["enabled"] = args.enabled

    return apply_compliance_fields(updated, args)


def maybe_sync_build_summary(record: dict, *, dry_run: bool, match_type: str) -> bool:
    skill_dir_str = str(record.get("skill_dir", "")).strip()
    if not skill_dir_str:
        return False
    skill_dir = Path(skill_dir_str)
    if not build_summary_path(skill_dir).exists():
        return False
    if dry_run:
        return True
    return sync_build_summary_from_record(skill_dir, record, match_type=match_type)


def build_review_row(record: dict, *, prefill_suggested: bool = False) -> dict[str, str]:
    normalized, compliance_status, reasons = compliance_summary(record)
    triage = triage_compliance_review(normalized)
    review_subject_type = str(normalized.get("subject_type", "")).strip()
    review_authorization_status = str(normalized.get("authorization_status", "")).strip()
    review_source_legitimacy = str(normalized.get("source_legitimacy", "")).strip()
    review_authorization_checked_at = str(normalized.get("authorization_checked_at", "")).strip()
    if prefill_suggested and bool(triage["can_review_now"]):
        suggested_auth = str(triage["suggested_authorization_status"])
        suggested_legitimacy = str(triage["suggested_source_legitimacy"])
        if suggested_auth and not suggested_auth.startswith("<"):
            review_authorization_status = suggested_auth
        if suggested_legitimacy and not suggested_legitimacy.startswith("<"):
            review_source_legitimacy = suggested_legitimacy
        if not review_authorization_checked_at:
            review_authorization_checked_at = today_str()
    return {
        "apply": "0",
        "slug": str(normalized.get("slug", "")).strip(),
        "name": str(normalized.get("name", "")).strip(),
        "compliance_status": compliance_status,
        "reasons": "; ".join(reasons) if reasons else "ok",
        "triage_bucket": str(triage["bucket"]),
        "triage_priority": str(triage["priority"]),
        "can_review_now": bool_to_csv(bool(triage["can_review_now"])),
        "triage_note": str(triage["note"]),
        "suggested_authorization_status": str(triage["suggested_authorization_status"]),
        "suggested_source_legitimacy": str(triage["suggested_source_legitimacy"]),
        "current_subject_type": str(normalized.get("subject_type", "")).strip(),
        "current_authorization_status": str(normalized.get("authorization_status", "")).strip(),
        "current_source_legitimacy": str(normalized.get("source_legitimacy", "")).strip(),
        "current_authorization_checked_at": str(normalized.get("authorization_checked_at", "")).strip(),
        "current_authorization_note": str(normalized.get("authorization_note", "")).strip(),
        "current_enabled": bool_to_csv(bool(normalized.get("enabled", True))),
        "review_subject_type": review_subject_type,
        "review_authorization_status": review_authorization_status,
        "review_source_legitimacy": review_source_legitimacy,
        "review_authorization_checked_at": review_authorization_checked_at,
        "review_authorization_note": str(normalized.get("authorization_note", "")).strip(),
        "review_enabled": bool_to_csv(bool(normalized.get("enabled", True))),
        "ingestor": str(normalized.get("ingestor", "")).strip(),
        "source_config": str(normalized.get("source_config", "")).strip(),
        "input_corpus": str(normalized.get("input_corpus", "")).strip(),
        "skill_dir": str(normalized.get("skill_dir", "")).strip(),
        "review_comment": "",
    }


def write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def cmd_review_export(
    registry: Path,
    out_path: Path,
    *,
    needs_review_only: bool = False,
    ready_only: bool = False,
    person: str = "",
    prefill_suggested: bool = False,
) -> None:
    data = load_registry(registry)
    persons = data.get("persons", [])
    rows: list[dict[str, str]] = []
    for record in persons:
        slug = str(record.get("slug", "")).strip()
        name = str(record.get("name", "")).strip()
        if person and person not in {slug, name}:
            continue
        _, compliance_status, _ = compliance_summary(record)
        if needs_review_only and compliance_status == "ready":
            continue
        if ready_only and compliance_status != "ready":
            continue
        rows.append(build_review_row(record, prefill_suggested=prefill_suggested))
    rows.sort(
        key=lambda row: (
            int(row["triage_priority"] or "999"),
            row["triage_bucket"],
            row["slug"],
        )
    )
    write_review_csv(out_path, rows)
    print(f"[done] review csv written: {out_path} rows={len(rows)}")


def apply_review_row(existing: dict, row: dict[str, str]) -> dict:
    updated = dict(existing)

    subject_type = validate_choice(row.get("review_subject_type", ""), SUBJECT_TYPES, field_name="subject_type")
    authorization_status = validate_choice(
        row.get("review_authorization_status", ""),
        AUTH_STATUSES,
        field_name="authorization_status",
    )
    source_legitimacy = validate_choice(
        row.get("review_source_legitimacy", ""),
        SOURCE_LEGITIMACY,
        field_name="source_legitimacy",
    )
    authorization_checked_at = row.get("review_authorization_checked_at", "").strip()
    authorization_note = row.get("review_authorization_note", "").strip()
    enabled = parse_csv_bool(row.get("review_enabled", ""), field_name="review_enabled")

    if subject_type:
        updated["subject_type"] = subject_type
    if authorization_status:
        updated["authorization_status"] = authorization_status
    if source_legitimacy:
        updated["source_legitimacy"] = source_legitimacy
    if authorization_checked_at:
        updated["authorization_checked_at"] = authorization_checked_at
    if authorization_note:
        updated["authorization_note"] = authorization_note
    if enabled is not None:
        updated["enabled"] = enabled

    return normalize_registry_record(updated)


def cmd_review_apply(registry: Path, csv_path: Path, *, dry_run: bool = False) -> int:
    if not csv_path.exists():
        raise SystemExit(f"csv not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    data = load_registry(registry)
    persons = [dict(p) for p in data.get("persons", [])]

    applied: list[str] = []
    skipped = 0
    errors: list[str] = []
    sync_targets: list[tuple[Path, dict]] = []
    for row in rows:
        slug = row.get("slug", "").strip()
        if not slug:
            skipped += 1
            continue
        apply_flag = row.get("apply", "")
        try:
            should_apply = parse_csv_bool(apply_flag, field_name=f"{slug}.apply")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not should_apply:
            skipped += 1
            continue

        idx = find_person_index(persons, slug)
        if idx < 0:
            errors.append(f"person not found: {slug}")
            continue

        try:
            updated = apply_review_row(persons[idx], row)
        except ValueError as exc:
            errors.append(f"{slug}: {exc}")
            continue
        persons[idx] = updated
        skill_dir = Path(str(updated.get("skill_dir", "")).strip()) if str(updated.get("skill_dir", "")).strip() else None
        if skill_dir and build_summary_path(skill_dir).exists():
            sync_targets.append((skill_dir, updated))
        _, compliance_status, reasons = compliance_summary(updated)
        reason_text = "; ".join(reasons) if reasons else "ok"
        applied.append(f"{slug}: compliance={compliance_status} reasons={reason_text}")

    if errors:
        for err in errors:
            print(f"[error] {err}")
        return 1

    if not dry_run:
        data["persons"] = persons
        save_registry(registry, data)
        synced_summaries = 0
        for skill_dir, updated in sync_targets:
            if sync_build_summary_from_record(skill_dir, updated, match_type="registry:review_apply"):
                synced_summaries += 1
        print(f"[ok] registry updated: {registry}")
    else:
        synced_summaries = len(sync_targets)
        print("[dry-run] registry not written")

    print(f"[done] review rows applied: {len(applied)} skipped: {skipped} build_summary_synced: {synced_summaries}")
    for line in applied:
        print(f"- {line}")
    return 0


def run_dispatch(
    registry: Path,
    mode: str,
    person: str,
    out_root: str,
    dry_run: bool,
    skip_compliance_gate: bool,
) -> None:
    dispatch = BASE_DIR / "scripts" / "dispatch_persons.py"
    cmd = [sys.executable, str(dispatch), "--mode", mode, "--person", person]
    if registry != DEFAULT_REGISTRY:
        cmd.extend(["--registry", str(registry)])
    if out_root:
        cmd.extend(["--out-root", out_root])
    if skip_compliance_gate:
        cmd.append("--skip-compliance-gate")
    if dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd, check=True)


def cmd_list(registry: Path, needs_review_only: bool = False, ready_only: bool = False) -> None:
    data = load_registry(registry)
    persons = data.get("persons", [])
    if not persons:
        print("[info] registry empty")
        return
    for p in persons:
        normalized, compliance_status, reasons = compliance_summary(p)
        if needs_review_only and compliance_status == "ready":
            continue
        if ready_only and compliance_status != "ready":
            continue
        name = p.get("name", "")
        slug = p.get("slug", "")
        enabled = p.get("enabled", True)
        ingestor = p.get("ingestor", "")
        input_corpus = p.get("input_corpus", "")
        src = ingestor or input_corpus or ""
        subject_type = normalized.get("subject_type", "")
        auth = normalized.get("authorization_status", "")
        legitimacy = normalized.get("source_legitimacy", "")
        reason_text = "; ".join(reasons) if reasons else "ok"
        print(
            f"- {name} ({slug}) enabled={enabled} compliance={compliance_status} "
            f"subject={subject_type} auth={auth} legitimacy={legitimacy} source={src} reasons={reason_text}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage mind-clone person registry")
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help="registry json path",
    )
    parser.add_argument(
        "--out-root",
        default=DEFAULT_OUT_ROOT,
        help="default root for new skills",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list persons")
    p_list.add_argument("--needs-review-only", action="store_true")
    p_list.add_argument("--ready-only", action="store_true")

    p_new = sub.add_parser("new", help="add or update a person entry")
    p_new.add_argument("--name", required=True)
    p_new.add_argument("--slug", default="")
    p_new.add_argument("--skill-dir", default="")
    p_new.add_argument("--ingestor", default="")
    p_new.add_argument("--source-config", default="")
    p_new.add_argument("--input-corpus", default="")
    p_new.add_argument("--since", default="")
    p_new.add_argument("--incremental", action="store_true")
    p_new.add_argument("--no-incremental", action="store_true")
    p_new.add_argument("--overwrite-outputs", action="store_true")
    p_new.add_argument("--enabled", action="store_true")
    p_new.add_argument("--disabled", action="store_true")
    p_new.add_argument("--replace", action="store_true")
    p_new.add_argument("--run", choices=["create", "update", "full"], default="")
    p_new.add_argument("--skip-compliance-gate", action="store_true")
    p_new.add_argument("--dry-run", action="store_true")
    add_compliance_fields(p_new)

    p_run = sub.add_parser("run", help="dispatch create/update/full")
    p_run.add_argument("--person", required=True)
    p_run.add_argument("--mode", choices=["create", "update", "full"], default="update")
    p_run.add_argument("--skip-compliance-gate", action="store_true")
    p_run.add_argument("--dry-run", action="store_true")

    p_show = sub.add_parser("show", help="show a person entry")
    p_show.add_argument("--person", required=True)
    p_show.add_argument("--explain-compliance", action="store_true")

    p_patch = sub.add_parser("patch", help="patch an existing person entry")
    p_patch.add_argument("--person", required=True)
    p_patch.add_argument("--name", default="")
    p_patch.add_argument("--slug", default="")
    p_patch.add_argument("--skill-dir", default="")
    p_patch.add_argument("--ingestor", default="")
    p_patch.add_argument("--source-config", default="")
    p_patch.add_argument("--input-corpus", default="")
    p_patch.add_argument("--since", default="")
    p_patch.add_argument("--incremental", action="store_true")
    p_patch.add_argument("--no-incremental", action="store_true")
    p_patch.add_argument("--overwrite-outputs", action="store_true")
    p_patch.add_argument("--no-overwrite-outputs", action="store_true")
    p_patch.add_argument("--enabled", action="store_true")
    p_patch.add_argument("--disabled", action="store_true")
    p_patch.add_argument("--run", choices=["create", "update", "full"], default="")
    p_patch.add_argument("--skip-compliance-gate", action="store_true")
    p_patch.add_argument("--dry-run", action="store_true")
    add_compliance_fields(p_patch)

    p_review_export = sub.add_parser("review-export", help="export review queue as CSV")
    p_review_export.add_argument("--out", required=True)
    p_review_export.add_argument("--person", default="")
    p_review_export.add_argument("--needs-review-only", action="store_true")
    p_review_export.add_argument("--ready-only", action="store_true")
    p_review_export.add_argument("--prefill-suggested", action="store_true")

    p_review_apply = sub.add_parser("review-apply", help="apply review CSV back to registry")
    p_review_apply.add_argument("--in", dest="input_csv", required=True)
    p_review_apply.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    registry = Path(args.registry)
    out_root = args.out_root

    if args.cmd == "list":
        if args.needs_review_only and args.ready_only:
            raise SystemExit("Use only one of --needs-review-only or --ready-only")
        cmd_list(
            registry,
            needs_review_only=args.needs_review_only,
            ready_only=args.ready_only,
        )
        return 0

    if args.cmd == "show":
        data = load_registry(registry)
        persons = data.get("persons", [])
        idx = find_person_index(persons, args.person)
        if idx < 0:
            raise SystemExit(f"person not found: {args.person}")
        print(json.dumps(persons[idx], ensure_ascii=False, indent=2))
        if args.explain_compliance:
            normalized, compliance_status, reasons = compliance_summary(persons[idx])
            reason_text = "; ".join(reasons) if reasons else "ok"
            print(
                f"compliance={compliance_status} subject={normalized.get('subject_type', '')} "
                f"auth={normalized.get('authorization_status', '')} "
                f"legitimacy={normalized.get('source_legitimacy', '')} reasons={reason_text}"
            )
        return 0

    if args.cmd == "review-export":
        if args.needs_review_only and args.ready_only:
            raise SystemExit("Use only one of --needs-review-only or --ready-only")
        cmd_review_export(
            registry,
            Path(args.out),
            needs_review_only=args.needs_review_only,
            ready_only=args.ready_only,
            person=args.person,
            prefill_suggested=args.prefill_suggested,
        )
        return 0

    if args.cmd == "review-apply":
        return cmd_review_apply(
            registry,
            Path(args.input_csv),
            dry_run=args.dry_run,
        )

    if args.cmd == "run":
        run_dispatch(
            registry,
            args.mode,
            args.person,
            out_root,
            args.dry_run,
            args.skip_compliance_gate,
        )
        return 0

    if args.cmd == "patch":
        if args.incremental and args.no_incremental:
            raise SystemExit("Use only one of --incremental or --no-incremental")
        if args.overwrite_outputs and args.no_overwrite_outputs:
            raise SystemExit("Use only one of --overwrite-outputs or --no-overwrite-outputs")
        if args.enabled and args.disabled:
            raise SystemExit("Use only one of --enabled or --disabled")

        incremental = None
        if args.incremental:
            incremental = True
        elif args.no_incremental:
            incremental = False
        args.incremental = incremental

        overwrite_outputs = None
        if args.overwrite_outputs:
            overwrite_outputs = True
        elif args.no_overwrite_outputs:
            overwrite_outputs = False
        args.overwrite_outputs = overwrite_outputs

        enabled = None
        if args.enabled:
            enabled = True
        elif args.disabled:
            enabled = False
        args.enabled = enabled

        data = load_registry(registry)
        persons = data.get("persons", [])
        idx = find_person_index(persons, args.person)
        if idx < 0:
            raise SystemExit(f"person not found: {args.person}")

        updated = apply_patch_args(persons[idx], args)
        persons[idx] = updated
        data["persons"] = persons

        if args.dry_run:
            print("[dry-run] registry not written")
            build_summary_synced = maybe_sync_build_summary(
                updated,
                dry_run=True,
                match_type="registry:patch",
            )
        else:
            save_registry(registry, data)
            build_summary_synced = maybe_sync_build_summary(
                updated,
                dry_run=False,
                match_type="registry:patch",
            )
            print(f"[ok] registry updated: {registry}")

        normalized, compliance_status, reasons = compliance_summary(updated)
        reason_text = "; ".join(reasons) if reasons else "ok"
        print(
            f"compliance={compliance_status} subject={normalized.get('subject_type', '')} "
            f"auth={normalized.get('authorization_status', '')} "
            f"legitimacy={normalized.get('source_legitimacy', '')} reasons={reason_text}"
        )
        print(f"build_summary_synced={'yes' if build_summary_synced else 'no'}")

        if args.run:
            run_dispatch(
                registry,
                args.run,
                str(updated.get("slug", "")).strip() or args.person,
                out_root,
                args.dry_run,
                args.skip_compliance_gate,
            )
        return 0

    # new
    if args.incremental and args.no_incremental:
        raise SystemExit("Use only one of --incremental or --no-incremental")
    if args.enabled and args.disabled:
        raise SystemExit("Use only one of --enabled or --disabled")

    incremental = None
    if args.incremental:
        incremental = True
    elif args.no_incremental:
        incremental = False

    enabled = None
    if args.enabled:
        enabled = True
    elif args.disabled:
        enabled = False

    args.incremental = incremental
    args.enabled = enabled

    data = load_registry(registry)
    persons = data.get("persons", [])

    entry = build_entry(args, out_root)
    idx = find_person_index(persons, entry["slug"]) if persons else -1
    if idx < 0:
        persons.append(entry)
        final_entry = persons[-1]
    else:
        persons[idx] = merge_entry(persons[idx], entry, replace=args.replace)
        final_entry = persons[idx]

    data["persons"] = persons
    if args.dry_run:
        print("[dry-run] registry not written")
        build_summary_synced = maybe_sync_build_summary(
            final_entry,
            dry_run=True,
            match_type="registry:new",
        )
    else:
        save_registry(registry, data)
        build_summary_synced = maybe_sync_build_summary(
            final_entry,
            dry_run=False,
            match_type="registry:new",
        )
        print(f"[ok] registry updated: {registry}")
    print(f"build_summary_synced={'yes' if build_summary_synced else 'no'}")

    if args.run:
        run_dispatch(
            registry,
            args.run,
            final_entry["slug"],
            out_root,
            args.dry_run,
            args.skip_compliance_gate,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
