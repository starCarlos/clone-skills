#!/usr/bin/env python3
"""Shared helpers for manifest-driven orchestration scripts."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_REFRESH_HISTORY = 5


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def find_flag_value(command: list[str], flag: str) -> str:
    for idx, item in enumerate(command):
        if item == flag and idx + 1 < len(command):
            return str(command[idx + 1])
    return ""


def has_flag(command: list[str], flag: str) -> bool:
    return flag in command


def file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    fingerprint = {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if path.is_file():
        fingerprint["sha256"] = file_sha256(path)
    return fingerprint


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_source_artifact_entry(value: str | Path | None) -> dict[str, Any]:
    if value is None:
        return {"path": "", "exists": False, "kind": "missing"}
    path_text = str(value).strip()
    if not path_text:
        return {"path": "", "exists": False, "kind": "missing"}
    path = Path(path_text).resolve()
    exists = path.exists()
    kind = "file" if path.is_file() else ("dir" if path.is_dir() else "missing")
    entry: dict[str, Any] = {
        "path": str(path),
        "exists": exists,
        "kind": kind,
    }
    if path.is_file():
        entry["size"] = path.stat().st_size
        entry["sha256"] = file_sha256(path)
    return entry


def build_source_artifacts(items: dict[str, str | Path | None]) -> dict[str, dict[str, Any]]:
    return {key: build_source_artifact_entry(value) for key, value in items.items()}


def build_refresh_cache_from_files(files: list[dict[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {"files": files, "fingerprint": digest}


def build_refresh_cache(paths: list[str | Path | None]) -> dict[str, Any]:
    normalized: list[Path] = []
    seen: set[str] = set()
    for value in paths:
        if value is None:
            continue
        path_text = str(value).strip()
        if not path_text:
            continue
        path = Path(path_text).resolve()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return build_refresh_cache_from_files([file_fingerprint(path) for path in normalized])


def classify_refresh_change(previous: dict[str, Any], current: dict[str, Any], change_kinds: list[str]) -> str:
    previous_exists = bool(previous.get("exists", False))
    current_exists = bool(current.get("exists", False))
    if "existence" in change_kinds:
        if not previous_exists and current_exists:
            return "created"
        if previous_exists and not current_exists:
            return "deleted"
    content_like = {"content", "size"}
    if any(kind in content_like for kind in change_kinds):
        return "content_changed"
    if change_kinds == ["mtime"]:
        return "metadata_only"
    return "mixed"


def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def stamp_refresh_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    stamped = dict(trigger)
    stamped["recorded_at"] = current_timestamp()
    return stamped


def normalize_refresh_history(history: Any) -> list[dict[str, Any]]:
    return [item for item in history if isinstance(item, dict)] if isinstance(history, list) else []


def merge_refresh_history(
    previous_manifest: dict[str, Any],
    current_trigger: dict[str, Any],
    limit: int = MAX_REFRESH_HISTORY,
) -> list[dict[str, Any]]:
    history = previous_manifest.get("refresh_trigger_history", [])
    normalized = normalize_refresh_history(history)
    if not normalized:
        previous_last = previous_manifest.get("last_refresh_trigger", {})
        if isinstance(previous_last, dict) and previous_last:
            normalized = [previous_last]
    normalized.append(current_trigger)
    if limit > 0 and len(normalized) > limit:
        normalized = normalized[-limit:]
    return normalized


def diff_refresh_cache(manifest: dict[str, Any]) -> dict[str, Any]:
    refresh_cache = manifest.get("refresh_cache", {}) if isinstance(manifest.get("refresh_cache", {}), dict) else {}
    tracked_files = refresh_cache.get("files", []) if isinstance(refresh_cache.get("files", []), list) else []
    if not tracked_files:
        return {
            "changed": False,
            "reason": "no_tracked_files",
            "changed_count": 0,
            "changed_groups": [],
            "changed_files": [],
            "fingerprint_before": str(refresh_cache.get("fingerprint", "")).strip(),
            "fingerprint_after": "",
        }

    dependency_index = (
        manifest.get("refresh_dependency_index", [])
        if isinstance(manifest.get("refresh_dependency_index", []), list)
        else []
    )
    groups_by_path: dict[str, list[str]] = {}
    for item in dependency_index:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        groups = item.get("groups", [])
        if not path or not isinstance(groups, list):
            continue
        groups_by_path[path] = sorted(str(group).strip() for group in groups if str(group).strip())

    current_files = [
        file_fingerprint(Path(str(item.get("path", "")).strip()))
        for item in tracked_files
        if str(item.get("path", "")).strip()
    ]
    current_cache = build_refresh_cache_from_files(current_files)
    fingerprint_before = str(refresh_cache.get("fingerprint", "")).strip()
    fingerprint_after = str(current_cache.get("fingerprint", "")).strip()
    if fingerprint_before == fingerprint_after:
        return {
            "changed": False,
            "reason": "tracked_inputs_unchanged",
            "changed_count": 0,
            "changed_groups": [],
            "changed_files": [],
            "fingerprint_before": fingerprint_before,
            "fingerprint_after": fingerprint_after,
        }

    previous_by_path = {
        str(item.get("path", "")).strip(): item
        for item in tracked_files
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    }
    changed_files: list[dict[str, Any]] = []
    for current in current_files:
        path = str(current.get("path", "")).strip()
        previous = previous_by_path.get(path, {})
        if not isinstance(previous, dict):
            continue
        previous_exists = bool(previous.get("exists", False))
        current_exists = bool(current.get("exists", False))
        change_kinds: list[str] = []
        if previous_exists != current_exists:
            change_kinds.append("existence")
        if previous_exists and current_exists:
            if str(previous.get("sha256", "")).strip() != str(current.get("sha256", "")).strip():
                if str(previous.get("sha256", "")).strip() or str(current.get("sha256", "")).strip():
                    change_kinds.append("content")
            if previous.get("size") != current.get("size"):
                change_kinds.append("size")
            if previous.get("mtime_ns") != current.get("mtime_ns"):
                change_kinds.append("mtime")
        if not change_kinds:
            continue
        change_class = classify_refresh_change(previous, current, change_kinds)
        changed_files.append(
            {
                "path": path,
                "name": Path(path).name,
                "groups": groups_by_path.get(path, []),
                "change_kinds": change_kinds,
                "change_class": change_class,
            }
        )

    changed_groups = sorted({group for item in changed_files for group in item.get("groups", [])})
    changed_classes = sorted({str(item.get("change_class", "")).strip() for item in changed_files if str(item.get("change_class", "")).strip()})
    changed_class_counts = {
        change_class: len([item for item in changed_files if item.get("change_class") == change_class])
        for change_class in changed_classes
    }
    return {
        "changed": True,
        "reason": "tracked_inputs_changed",
        "changed_count": len(changed_files),
        "changed_groups": changed_groups,
        "changed_classes": changed_classes,
        "changed_class_counts": changed_class_counts,
        "changed_files": changed_files,
        "fingerprint_before": fingerprint_before,
        "fingerprint_after": fingerprint_after,
    }


def refresh_cache_unchanged(manifest: dict[str, Any]) -> bool:
    return not bool(diff_refresh_cache(manifest).get("changed", False))


def snapshot_refresh_metadata(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    data = load_json(manifest_path)
    last_refresh_trigger = data.get("last_refresh_trigger", {})
    return {
        "last_refresh_trigger": last_refresh_trigger if isinstance(last_refresh_trigger, dict) else {},
        "refresh_trigger_history": normalize_refresh_history(data.get("refresh_trigger_history", [])),
    }


def restore_refresh_metadata_if_missing(manifest_path: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    if not snapshot or not manifest_path.exists():
        return load_json(manifest_path) if manifest_path.exists() else {}
    data = load_json(manifest_path)
    updated = False
    previous_last = snapshot.get("last_refresh_trigger", {})
    if isinstance(previous_last, dict) and previous_last and not data.get("last_refresh_trigger"):
        data["last_refresh_trigger"] = previous_last
        updated = True

    previous_history = normalize_refresh_history(snapshot.get("refresh_trigger_history", []))
    current_history = normalize_refresh_history(data.get("refresh_trigger_history", []))
    if previous_history and not current_history:
        data["refresh_trigger_history"] = previous_history
        updated = True

    if updated:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def filter_refresh_report_to_groups(
    refresh_report: dict[str, Any],
    allowed_groups: list[str] | tuple[str, ...],
    *,
    reason: str = "",
) -> dict[str, Any]:
    if not bool(refresh_report.get("changed", False)):
        return {}

    allowed = {str(group).strip() for group in allowed_groups if str(group).strip()}
    if not allowed:
        return {}

    changed_files = refresh_report.get("changed_files", [])
    if not isinstance(changed_files, list):
        return {}

    filtered_files: list[dict[str, Any]] = []
    for item in changed_files:
        if not isinstance(item, dict):
            continue
        groups = item.get("groups", [])
        if not isinstance(groups, list):
            continue
        matched_groups = sorted({str(group).strip() for group in groups if str(group).strip() in allowed})
        if not matched_groups:
            continue
        filtered = dict(item)
        filtered["groups"] = matched_groups
        filtered_files.append(filtered)

    if not filtered_files:
        return {}

    changed_groups = sorted({group for item in filtered_files for group in item.get("groups", [])})
    changed_classes = sorted(
        {
            str(item.get("change_class", "")).strip()
            for item in filtered_files
            if str(item.get("change_class", "")).strip()
        }
    )
    changed_class_counts = {
        change_class: len([item for item in filtered_files if item.get("change_class") == change_class])
        for change_class in changed_classes
    }
    filtered_report = {
        "changed": True,
        "reason": reason or str(refresh_report.get("reason", "")).strip() or "propagated_from_parent_refresh",
        "source_reason": str(refresh_report.get("reason", "")).strip(),
        "changed_count": len(filtered_files),
        "changed_groups": changed_groups,
        "changed_classes": changed_classes,
        "changed_class_counts": changed_class_counts,
        "changed_files": filtered_files,
    }
    for key in ("fingerprint_before", "fingerprint_after"):
        value = str(refresh_report.get(key, "")).strip()
        if value:
            filtered_report[key] = value
    return filtered_report


def apply_refresh_trigger(manifest_path: Path, previous_manifest: dict[str, Any], refresh_report: dict[str, Any]) -> dict[str, Any]:
    refreshed_manifest = load_json(manifest_path)
    trigger = stamp_refresh_trigger(refresh_report)
    refreshed_manifest["last_refresh_trigger"] = trigger
    refreshed_manifest["refresh_trigger_history"] = merge_refresh_history(previous_manifest, trigger)
    manifest_path.write_text(json.dumps(refreshed_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return refreshed_manifest


def propagate_refresh_to_manifest(
    manifest_path: Path,
    parent_refresh_report: dict[str, Any],
    *,
    reason: str = "",
) -> dict[str, Any]:
    if not manifest_path.exists() or not bool(parent_refresh_report.get("changed", False)):
        return {}
    manifest = load_json(manifest_path)
    refresh_dependency_groups = manifest.get("refresh_dependency_groups", [])
    allowed_groups = (
        [str(group).strip() for group in refresh_dependency_groups if str(group).strip()]
        if isinstance(refresh_dependency_groups, list)
        else []
    )
    filtered_report = filter_refresh_report_to_groups(parent_refresh_report, allowed_groups, reason=reason)
    if not filtered_report:
        return {}
    return apply_refresh_trigger(manifest_path, manifest, filtered_report)
