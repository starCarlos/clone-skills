from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from colleague_clone_common import (
    diff_runtime_contract,
    diff_runtime_portraits,
    field_name_from_path,
    load_json,
    load_jsonl,
    normalize_runtime_release_review,
    parse_field_mapping,
    resolve_source_type,
    runtime_release_review_issues,
    summarize_runtime_portraits,
    summarize_runtime_contract,
    summarize_runtime_contract_drift,
    summarize_runtime_release_drift,
    utc_now_iso,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update an existing colleague-clone bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to update.")
    parser.add_argument("--source", action="append", default=[], help="Repeatable new local source file.")
    parser.add_argument(
        "--source-kind",
        action="append",
        default=[],
        help="Optional source kind override aligned with each --source.",
    )
    parser.add_argument(
        "--field-map",
        action="append",
        default=[],
        help='Optional JSON field mapping aligned with each --source, for example \'{"platform":"generic","text":"payload.text"}\'.',
    )
    parser.add_argument("--override-scope", choices=["persona", "work"], help="Profile scope for a manual override.")
    parser.add_argument("--override-field", default="", help="Field path for a manual override.")
    parser.add_argument("--override-value", default="", help="New value for a manual override.")
    parser.add_argument("--override-reason", default="manual override", help="Reason for the override.")
    parser.add_argument("--resolve-conflict-scope", choices=["persona", "work"], help="Scope for explicit conflict resolution.")
    parser.add_argument("--resolve-conflict-field", default="", help="Field path for explicit conflict resolution.")
    parser.add_argument("--resolve-conflict-note", default="", help="Resolution note recorded for the conflict.")
    parser.add_argument("--ack-runtime-drift", action="store_true", help="Acknowledge the currently pending runtime drift review.")
    parser.add_argument("--ack-note", default="", help="Required note recorded when acknowledging runtime drift.")
    parser.add_argument("--ack-by", default="manual-review", help="Reviewer label recorded with the runtime drift acknowledgement.")
    parser.add_argument("--rebuild", action="store_true", help="Re-run normalize/analyze/build after the update.")
    return parser.parse_args()


def next_source_id(manifest: list[dict]) -> str:
    highest = 0
    for item in manifest:
        source_id = str(item.get("source_id", ""))
        if source_id.startswith("src_"):
            try:
                highest = max(highest, int(source_id.split("_", 1)[1]))
            except ValueError:
                continue
    return f"src_{highest + 1:03d}"


def next_version_dir(bundle_dir: Path) -> Path:
    versions_dir = bundle_dir / "versions"
    existing = []
    for path in versions_dir.glob("v*"):
        if path.is_dir():
            try:
                existing.append(int(path.name[1:]))
            except ValueError:
                continue
    version = max(existing, default=0) + 1
    return versions_dir / f"v{version}"


def snapshot_bundle(bundle_dir: Path) -> Path:
    version_dir = next_version_dir(bundle_dir)
    version_dir.mkdir(parents=True, exist_ok=True)
    for relative in [
        "meta.json",
        "persona.md",
        "work.md",
        "SKILL.md",
        "evidence_index.jsonl",
        "release_manifest.json",
        "runtime_package.json",
        "runtime_smoke.json",
        "runtime_release_health.json",
        "runtime_prompt_eval.json",
        "analysis",
    ]:
        source = bundle_dir / relative
        if not source.exists():
            continue
        target = version_dir / relative
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return version_dir


def append_sources(bundle_dir: Path, raw_sources: list[str], source_kinds: list[str], field_maps: list[str]) -> list[dict]:
    manifest_path = bundle_dir / "sources" / "manifest.jsonl"
    manifest = load_jsonl(manifest_path)
    added: list[dict] = []
    timestamp = utc_now_iso()
    if source_kinds and len(source_kinds) != len(raw_sources):
        raise SystemExit("--source-kind must be omitted or provided once for each --source")
    if field_maps and len(field_maps) != len(raw_sources):
        raise SystemExit("--field-map must be omitted or provided once for each --source")
    for index, raw_path in enumerate(raw_sources):
        path = Path(raw_path).expanduser().resolve()
        explicit_kind = source_kinds[index] if source_kinds else ""
        field_mapping = parse_field_mapping(field_maps[index]) if field_maps else {}
        source_type, detection_mode = resolve_source_type(path, explicit_kind)
        entry = {
            "source_id": next_source_id(manifest + added),
            "source_type": source_type,
            "path": str(path),
            "origin": "update",
            "trust_level": "direct",
            "imported_at": timestamp,
            "parse_status": "pending",
            "detection_mode": detection_mode,
        }
        if field_mapping:
            entry["field_mapping"] = field_mapping
        added.append(entry)
    manifest.extend(added)
    write_jsonl(manifest_path, manifest)
    return added


def apply_manual_override(bundle_dir: Path, scope: str, field_path: str, new_value: str, reason: str) -> dict:
    profile_path = bundle_dir / "analysis" / f"{scope}_profile.json"
    profile = load_json(profile_path)
    override = {
        "field_path": field_path,
        "new_value": new_value,
        "reason": reason,
        "created_at": utc_now_iso(),
        "source": "manual_override",
    }
    profile.setdefault("manual_overrides", []).append(override)
    write_json(profile_path, profile)
    return override


def apply_conflict_resolution(bundle_dir: Path, scope: str, field_path: str, note: str) -> dict:
    profile_path = bundle_dir / "analysis" / f"{scope}_profile.json"
    profile = load_json(profile_path)
    field_name = field_name_from_path(field_path)
    field_snapshot = profile.get(field_name, {})
    conflict_snapshot = next((item for item in profile.get("conflicts", []) if item.get("field_path") == field_path), None)
    resolved_at = utc_now_iso()
    resolution = {
        "field_path": field_path,
        "new_value": note,
        "reason": "conflict resolution",
        "created_at": resolved_at,
        "source": "conflict_resolution",
    }
    profile.setdefault("manual_overrides", []).append(resolution)
    profile.setdefault("resolution_history", []).append(
        {
            "field_path": field_path,
            "resolution_note": note,
            "reason": "conflict resolution",
            "resolved_at": resolved_at,
            "source": "conflict_resolution",
            "conflict_snapshot": conflict_snapshot or {},
            "field_snapshot_before": {
                "summary": field_snapshot.get("summary", ""),
                "confidence": field_snapshot.get("confidence"),
                "confidence_reason": field_snapshot.get("confidence_reason", ""),
                "evidence": field_snapshot.get("evidence", []),
            },
        }
    )
    write_json(profile_path, profile)
    return {
        "field_path": field_path,
        "resolution_note": note,
        "reason": "conflict resolution",
        "resolved_at": resolved_at,
        "source": "conflict_resolution",
        "conflict_snapshot": conflict_snapshot or {},
    }


def append_version_history(bundle_dir: Path, event: dict) -> None:
    path = bundle_dir / "version_history.jsonl"
    history = load_jsonl(path)
    history.append(event)
    write_jsonl(path, history)


def run_rebuild(bundle_dir: Path) -> None:
    scripts_dir = Path(__file__).resolve().parent
    commands = [
        [sys.executable, str(scripts_dir / "normalize_colleague_sources.py"), "--bundle-dir", str(bundle_dir), "--strict"],
        [sys.executable, str(scripts_dir / "analyze_colleague_persona.py"), "--bundle-dir", str(bundle_dir)],
        [sys.executable, str(scripts_dir / "analyze_colleague_work.py"), "--bundle-dir", str(bundle_dir)],
        [sys.executable, str(scripts_dir / "build_colleague_skill.py"), "--bundle-dir", str(bundle_dir)],
    ]
    for command in commands:
        proc = subprocess.run(command, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or f"command failed: {' '.join(command)}")


def append_runtime_review_history(review: dict, event: dict) -> dict:
    history = [item for item in review.get("history", []) if isinstance(item, dict)]
    history.append(event)
    review["history"] = history
    return review


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    runtime_release_review = normalize_runtime_release_review(meta.get("runtime_release_review"))
    if args.ack_runtime_drift and not args.ack_note.strip():
        raise SystemExit("--ack-note is required with --ack-runtime-drift")

    version_dir = snapshot_bundle(bundle_dir)
    added_sources: list[dict] = []
    override_payload: dict | None = None
    conflict_resolution_payload: dict | None = None
    ack_payload: dict | None = None
    runtime_contract_before = (
        load_json(bundle_dir / "analysis" / "runtime_contract.json")
        if (bundle_dir / "analysis" / "runtime_contract.json").exists()
        else {}
    )
    runtime_contract_after: dict = runtime_contract_before
    runtime_portraits_before = (
        load_json(bundle_dir / "analysis" / "runtime_portraits.json")
        if (bundle_dir / "analysis" / "runtime_portraits.json").exists()
        else {}
    )
    runtime_portraits_after: dict = runtime_portraits_before
    runtime_contract_drift = {
        "changed": False,
        "entered_required_caveat": False,
        "entered_privacy_limited": False,
        "added_required_fields": [],
        "removed_required_fields": [],
        "before": summarize_runtime_contract(runtime_contract_before) if runtime_contract_before else {},
        "after": summarize_runtime_contract(runtime_contract_before) if runtime_contract_before else {},
    }
    runtime_portraits_drift = {
        "changed": False,
        "added_default_modules": [],
        "removed_default_modules": [],
        "added_review_focus": [],
        "removed_review_focus": [],
        "added_interaction_tendencies": [],
        "removed_interaction_tendencies": [],
        "added_redirect_topics": [],
        "removed_redirect_topics": [],
        "questioning_tendency_changed": False,
        "disagreement_style_changed": False,
        "boundary_policy_changed": False,
        "private_signal_changed": False,
        "before": summarize_runtime_portraits(runtime_portraits_before) if runtime_portraits_before else {},
        "after": summarize_runtime_portraits(runtime_portraits_before) if runtime_portraits_before else {},
    }

    if args.source:
        added_sources = append_sources(bundle_dir, args.source, args.source_kind, args.field_map)
        meta["state"] = "sources_pending"

    if args.override_scope:
        if not args.override_field or not args.override_value:
            raise SystemExit("--override-field and --override-value are required with --override-scope")
        override_payload = apply_manual_override(
            bundle_dir,
            args.override_scope,
            args.override_field,
            args.override_value,
            args.override_reason,
        )

    if args.resolve_conflict_scope:
        if not args.resolve_conflict_field or not args.resolve_conflict_note:
            raise SystemExit("--resolve-conflict-field and --resolve-conflict-note are required with --resolve-conflict-scope")
        conflict_resolution_payload = apply_conflict_resolution(
            bundle_dir,
            args.resolve_conflict_scope,
            args.resolve_conflict_field,
            args.resolve_conflict_note,
        )

    if args.rebuild and (args.source or args.override_scope or args.resolve_conflict_scope):
        run_rebuild(bundle_dir)
        meta = load_json(meta_path)
        runtime_contract_after = (
            load_json(bundle_dir / "analysis" / "runtime_contract.json")
            if (bundle_dir / "analysis" / "runtime_contract.json").exists()
            else {}
        )
        runtime_portraits_after = (
            load_json(bundle_dir / "analysis" / "runtime_portraits.json")
            if (bundle_dir / "analysis" / "runtime_portraits.json").exists()
            else {}
        )
        runtime_contract_drift = diff_runtime_contract(runtime_contract_before, runtime_contract_after)
        runtime_portraits_drift = diff_runtime_portraits(runtime_portraits_before, runtime_portraits_after)
        if runtime_contract_drift["changed"] or runtime_portraits_drift["changed"]:
            drift_detected_at = utc_now_iso()
            drift_id = f"{drift_detected_at}#{len(runtime_release_review.get('history', [])) + 1}"
            drift_trigger = "source_update" if added_sources else "manual_edit"
            drift_payload = {
                "drift_id": drift_id,
                "detected_at": drift_detected_at,
                "trigger": drift_trigger,
                **runtime_contract_drift,
                "changed": bool(runtime_contract_drift["changed"] or runtime_portraits_drift["changed"]),
                "runtime_contract_drift": runtime_contract_drift,
                "runtime_portraits_drift": runtime_portraits_drift,
            }
            if added_sources:
                runtime_release_review = {
                    "status": "pending_ack",
                    "requires_ack": True,
                    "last_drift_id": drift_id,
                    "last_drift_at": drift_detected_at,
                    "last_drift": drift_payload,
                    "drift_summary": summarize_runtime_release_drift(drift_payload),
                    "last_ack": runtime_release_review.get("last_ack", {}),
                    "history": runtime_release_review.get("history", []),
                }
                append_runtime_review_history(
                    runtime_release_review,
                    {
                        "event": "drift_detected",
                        "event_at": drift_detected_at,
                        "drift_id": drift_id,
                        "trigger": drift_trigger,
                        "summary": summarize_runtime_release_drift(drift_payload),
                    },
                )
            else:
                auto_ack = {
                    "acknowledged_at": drift_detected_at,
                    "acknowledged_by": "bundle-editor",
                    "note": "Runtime drift came from an explicit manual bundle edit.",
                    "acked_drift_id": drift_id,
                }
                runtime_release_review = {
                    "status": "acknowledged",
                    "requires_ack": False,
                    "last_drift_id": drift_id,
                    "last_drift_at": drift_detected_at,
                    "last_drift": drift_payload,
                    "drift_summary": summarize_runtime_release_drift(drift_payload),
                    "last_ack": auto_ack,
                    "history": runtime_release_review.get("history", []),
                }
                append_runtime_review_history(
                    runtime_release_review,
                    {
                        "event": "drift_detected",
                        "event_at": drift_detected_at,
                        "drift_id": drift_id,
                        "trigger": drift_trigger,
                        "summary": summarize_runtime_release_drift(drift_payload),
                    },
                )
                append_runtime_review_history(
                    runtime_release_review,
                    {
                        "event": "drift_acknowledged",
                        "event_at": drift_detected_at,
                        "drift_id": drift_id,
                        "acknowledged_by": auto_ack["acknowledged_by"],
                        "note": auto_ack["note"],
                    },
                )

    if args.ack_runtime_drift:
        review_issues = runtime_release_review_issues(runtime_release_review)
        if review_issues:
            ack_payload = {
                "acknowledged_at": utc_now_iso(),
                "acknowledged_by": args.ack_by,
                "note": args.ack_note.strip(),
                "acked_drift_id": runtime_release_review.get("last_drift_id", ""),
            }
            runtime_release_review["status"] = "acknowledged"
            runtime_release_review["requires_ack"] = False
            runtime_release_review["last_ack"] = ack_payload
            append_runtime_review_history(
                runtime_release_review,
                {
                    "event": "drift_acknowledged",
                    "event_at": ack_payload["acknowledged_at"],
                    "drift_id": ack_payload["acked_drift_id"],
                    "acknowledged_by": ack_payload["acknowledged_by"],
                    "note": ack_payload["note"],
                },
            )
        else:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "bundle_dir": str(bundle_dir),
                        "state": meta.get("state", ""),
                        "runtime_release_review": runtime_release_review,
                        "runtime_release_review_issues": ["no pending runtime drift review is available to acknowledge"],
                    },
                    ensure_ascii=False,
                )
            )
            return 1

    runtime_release_review = normalize_runtime_release_review(runtime_release_review)
    meta["runtime_release_review"] = runtime_release_review
    meta["updated_at"] = utc_now_iso()
    write_json(meta_path, meta)
    event = {
        "updated_at": utc_now_iso(),
        "snapshot_dir": str(version_dir),
        "added_sources": [item["path"] for item in added_sources],
        "manual_override": override_payload,
        "conflict_resolution": conflict_resolution_payload,
        "runtime_drift_ack": ack_payload,
    }
    append_version_history(bundle_dir, event)
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "snapshot_dir": str(version_dir),
                "added_source_count": len(added_sources),
                "added_sources": added_sources,
                "applied_override": bool(override_payload),
                "resolved_conflict": bool(conflict_resolution_payload),
                "acknowledged_runtime_drift": bool(ack_payload),
                "state": meta.get("state", ""),
                "runtime_contract_changed": runtime_contract_drift["changed"],
                "runtime_contract_drift": runtime_contract_drift,
                "runtime_portraits_changed": runtime_portraits_drift["changed"],
                "runtime_portraits_drift": runtime_portraits_drift,
                "runtime_release_review": runtime_release_review,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
