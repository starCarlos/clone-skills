#!/usr/bin/env python3
"""Shared helpers for coherent clone-stack discovery in /tmp."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

FRESHNESS_ARTIFACT_LABELS = {
    "bundle": "bundle",
    "pipeline": "pipeline",
    "runtime": "runtime",
    "personal_skill": "personal",
    "workflow_skill": "workflow",
}


def candidate_sort_key(path: Path) -> tuple[int, float]:
    return (path_version(path), path.stat().st_mtime)


def path_version(path: Path) -> int:
    match = re.search(r"-v(\d+)$", path.name)
    return int(match.group(1)) if match else -1


def describe_candidate_path(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "version": path_version(path),
        "mtime_ns": stat.st_mtime_ns,
    }


def run_validation(command: Sequence[str] | None, workdir: Path) -> bool:
    if not command:
        return True
    proc = subprocess.run(
        list(command),
        cwd=workdir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def load_stack_summary(path: Path) -> dict[str, Any]:
    return load_json(path.resolve())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def maybe_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def collect_tmp_dir_candidates(
    prefix: str,
    required_files: Sequence[str],
    validator_command_builder,
    workdir: Path,
) -> tuple[list[Path], list[dict[str, Any]]]:
    tmp = Path("/tmp")
    candidates = sorted(
        [path for path in tmp.iterdir() if path.is_dir() and path.name.startswith(prefix)],
        key=candidate_sort_key,
        reverse=True,
    )
    if not candidates:
        raise SystemExit(f"no directories found for prefix: {prefix}")

    reports: list[dict[str, Any]] = []
    valid: list[Path] = []
    for path in candidates:
        report = describe_candidate_path(path)
        missing = [name for name in required_files if not (path / name).exists()]
        if missing:
            report["status"] = "missing_required_files"
            report["reason"] = f"missing {', '.join(missing)}"
            report["missing_required_files"] = missing
            reports.append(report)
            continue
        validator_command = validator_command_builder(path) if validator_command_builder else None
        if validator_command and not run_validation(validator_command, workdir):
            report["status"] = "validator_failed"
            report["reason"] = "validator failed"
            reports.append(report)
            continue
        report["status"] = "valid"
        report["reason"] = "passes required file and validator checks"
        reports.append(report)
        valid.append(path)

    if valid:
        return valid, reports
    details = "; ".join(f"{item['path']}: {item['reason']}" for item in reports[:5])
    raise SystemExit(f"no valid directories found for prefix: {prefix}. {details}")


def collect_valid_tmp_dirs(
    prefix: str,
    required_files: Sequence[str],
    validator_command_builder,
    workdir: Path,
) -> list[Path]:
    valid, _ = collect_tmp_dir_candidates(prefix, required_files, validator_command_builder, workdir)
    return valid


def build_stack_validation_command(
    workdir: Path,
    bundle_dir: Path,
    pipeline_dir: Path,
    runtime_dir: Path,
    personal_skill_dir: Path,
    workflow_skill_dir: Path,
) -> list[str]:
    return [
        "python3",
        str(workdir / "scripts" / "validate_clone_stack.py"),
        "--bundle-manifest",
        str(bundle_dir / "working_clone_bundle_manifest.json"),
        "--bundle-summary",
        str(bundle_dir / "working_clone_until_final_summary.json"),
        "--bundle-readme",
        str(bundle_dir / "WORKING_CLONE_BUNDLE_README.md"),
        "--pipeline-manifest",
        str(pipeline_dir / "workflow_blueprint_pipeline_manifest.json"),
        "--pipeline-readme",
        str(pipeline_dir / "WORKFLOW_BLUEPRINT_PIPELINE_README.md"),
        "--runtime-manifest",
        str(runtime_dir / "workflow_runtime_manifest.json"),
        "--runtime-readme",
        str(runtime_dir / "WORKFLOW_RUNTIME_README.md"),
        "--personal-skill-dir",
        str(personal_skill_dir),
        "--workflow-skill-dir",
        str(workflow_skill_dir),
        "--format",
        "json",
    ]


def extract_bundle_signature(bundle_dir: Path) -> dict[str, str]:
    manifest = load_json(bundle_dir / "working_clone_bundle_manifest.json")
    clone_config_path = bundle_dir / "personal-clone-skill" / "clone_config.yaml"
    blueprint_path = Path(str(manifest.get("workflow_blueprint", "")))
    return {
        "clone_config_hash": maybe_hash(clone_config_path),
        "workflow_blueprint_hash": maybe_hash(blueprint_path),
    }


def extract_pipeline_signature(pipeline_dir: Path) -> dict[str, str]:
    manifest = load_json(pipeline_dir / "workflow_blueprint_pipeline_manifest.json")
    clone_config_path = Path(str(manifest.get("clone_config", "")))
    blueprint_path = Path(str(manifest.get("blueprint", "")))
    return {
        "clone_config_hash": maybe_hash(clone_config_path),
        "workflow_blueprint_hash": maybe_hash(blueprint_path),
    }


def extract_runtime_signature(runtime_dir: Path) -> dict[str, str]:
    manifest = load_json(runtime_dir / "workflow_runtime_manifest.json")
    clone_config_path = Path(str(manifest.get("clone_config", "")))
    blueprint_path = Path(str(manifest.get("workflow_blueprint", "")))
    return {
        "clone_config_hash": maybe_hash(clone_config_path),
        "workflow_blueprint_hash": maybe_hash(blueprint_path),
    }


def extract_personal_skill_signature(skill_dir: Path) -> dict[str, str]:
    return {
        "clone_config_hash": maybe_hash(skill_dir / "clone_config.yaml"),
        "workflow_blueprint_hash": "",
    }


def extract_workflow_skill_signature(skill_dir: Path) -> dict[str, str]:
    return {
        "clone_config_hash": maybe_hash(skill_dir / "clone_config.yaml"),
        "workflow_blueprint_hash": maybe_hash(skill_dir / "workflow_blueprint.md"),
    }


def extract_refresh_watch_from_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    manifest = load_json(manifest_path)
    groups = manifest.get("refresh_dependency_groups", [])
    if not isinstance(groups, list):
        groups = []
    refresh_cache = manifest.get("refresh_cache", {})
    tracked_files = refresh_cache.get("files", []) if isinstance(refresh_cache, dict) else []
    tracked_files_count = len(tracked_files) if isinstance(tracked_files, list) else 0
    return {
        "groups": [str(item).strip() for item in groups if str(item).strip()],
        "tracked_files_count": tracked_files_count,
    }


def extract_bundle_refresh_watch(bundle_dir: Path) -> dict[str, Any]:
    return extract_refresh_watch_from_manifest(bundle_dir / "working_clone_bundle_manifest.json")


def extract_pipeline_refresh_watch(pipeline_dir: Path) -> dict[str, Any]:
    return extract_refresh_watch_from_manifest(pipeline_dir / "workflow_blueprint_pipeline_manifest.json")


def extract_runtime_refresh_watch(runtime_dir: Path) -> dict[str, Any]:
    return extract_refresh_watch_from_manifest(runtime_dir / "workflow_runtime_manifest.json")


def extract_last_refresh_trigger_from_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {}
    manifest = load_json(manifest_path)
    trigger = manifest.get("last_refresh_trigger", {})
    return trigger if isinstance(trigger, dict) else {}


def extract_bundle_last_refresh_trigger(bundle_dir: Path) -> dict[str, Any]:
    return extract_last_refresh_trigger_from_manifest(bundle_dir / "working_clone_bundle_manifest.json")


def extract_pipeline_last_refresh_trigger(pipeline_dir: Path) -> dict[str, Any]:
    return extract_last_refresh_trigger_from_manifest(pipeline_dir / "workflow_blueprint_pipeline_manifest.json")


def extract_runtime_last_refresh_trigger(runtime_dir: Path) -> dict[str, Any]:
    return extract_last_refresh_trigger_from_manifest(runtime_dir / "workflow_runtime_manifest.json")


def extract_refresh_trigger_history_from_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.exists():
        return []
    manifest = load_json(manifest_path)
    history = manifest.get("refresh_trigger_history", [])
    return [item for item in history if isinstance(item, dict)] if isinstance(history, list) else []


def extract_bundle_refresh_trigger_history(bundle_dir: Path) -> list[dict[str, Any]]:
    return extract_refresh_trigger_history_from_manifest(bundle_dir / "working_clone_bundle_manifest.json")


def extract_pipeline_refresh_trigger_history(pipeline_dir: Path) -> list[dict[str, Any]]:
    return extract_refresh_trigger_history_from_manifest(pipeline_dir / "workflow_blueprint_pipeline_manifest.json")


def extract_runtime_refresh_trigger_history(runtime_dir: Path) -> list[dict[str, Any]]:
    return extract_refresh_trigger_history_from_manifest(runtime_dir / "workflow_runtime_manifest.json")


def render_refresh_history_entry(entry: dict[str, Any]) -> str:
    changed_files = entry.get("changed_files", [])
    if not isinstance(changed_files, list):
        changed_files = []
    file_names = [
        str(item.get("name", "")).strip()
        for item in changed_files[:2]
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]
    if len(changed_files) > 2:
        file_names.append(f"+{len(changed_files) - 2}")
    changed_classes = entry.get("changed_classes", [])
    if not isinstance(changed_classes, list):
        changed_classes = []
    classes_text = ",".join(str(item) for item in changed_classes if str(item).strip()) or str(entry.get("reason", "")).strip() or "unknown"
    files_text = ",".join(file_names) if file_names else "-"
    return f"{files_text}[{classes_text}]"


def _rank_counter(counter: Counter[str], limit: int = 3) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def summarize_refresh_trigger_history(history: Sequence[dict[str, Any]], limit: int = 3) -> dict[str, Any]:
    normalized = [item for item in history if isinstance(item, dict)]
    file_counter: Counter[str] = Counter()
    group_counter: Counter[str] = Counter()
    class_counter: Counter[str] = Counter()

    for entry in normalized:
        changed_files = entry.get("changed_files", [])
        if isinstance(changed_files, list):
            seen_files: set[str] = set()
            for item in changed_files:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                if not name or name in seen_files:
                    continue
                seen_files.add(name)
                file_counter[name] += 1

        changed_groups = entry.get("changed_groups", [])
        if isinstance(changed_groups, list):
            for group in {str(item).strip() for item in changed_groups if str(item).strip()}:
                group_counter[group] += 1

        changed_classes = entry.get("changed_classes", [])
        if isinstance(changed_classes, list):
            for change_class in {str(item).strip() for item in changed_classes if str(item).strip()}:
                class_counter[change_class] += 1

    return {
        "history_count": len(normalized),
        "top_files": _rank_counter(file_counter, limit=limit),
        "top_groups": _rank_counter(group_counter, limit=limit),
        "top_classes": _rank_counter(class_counter, limit=limit),
    }


def render_ranked_refresh_items(items: Sequence[dict[str, Any]]) -> str:
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "")).strip()
        count = int(item.get("count", 0))
        if not value or count <= 0:
            continue
        parts.append(f"{value}:{count}")
    return ",".join(parts) or "none"


def render_refresh_history_stats(stats: dict[str, Any]) -> str:
    return (
        f"history={int(stats.get('history_count', 0))} "
        f"top_files={render_ranked_refresh_items(stats.get('top_files', []))} "
        f"top_groups={render_ranked_refresh_items(stats.get('top_groups', []))} "
        f"top_classes={render_ranked_refresh_items(stats.get('top_classes', []))}"
    )


def render_refresh_artifact_summary(
    name: str,
    watch_payload: dict[str, Any],
    last_trigger_payload: dict[str, Any],
    history_payload: Sequence[dict[str, Any]],
    stats_payload: dict[str, Any],
) -> str:
    parts: list[str] = []

    groups = watch_payload.get("groups", []) if isinstance(watch_payload, dict) else []
    if not isinstance(groups, list):
        groups = []
    tracked_files_count = int(watch_payload.get("tracked_files_count", 0)) if isinstance(watch_payload, dict) else 0
    group_text = ",".join(str(item) for item in groups if str(item).strip()) or "none"
    if groups or tracked_files_count:
        parts.append(f"watch_groups={group_text}")
        parts.append(f"tracked_files={tracked_files_count}")

    if isinstance(last_trigger_payload, dict) and last_trigger_payload:
        parts.append(f"last={render_refresh_history_entry(last_trigger_payload)}")
        changed_groups = last_trigger_payload.get("changed_groups", [])
        if isinstance(changed_groups, list):
            changed_group_text = ",".join(str(item) for item in changed_groups if str(item).strip())
            if changed_group_text:
                parts.append(f"last_groups={changed_group_text}")

    history_items = [item for item in history_payload if isinstance(item, dict)] if isinstance(history_payload, Sequence) else []
    if history_items:
        recent = " -> ".join(render_refresh_history_entry(item) for item in history_items[-3:][::-1])
        parts.append(f"recent={recent}")

    if isinstance(stats_payload, dict) and int(stats_payload.get("history_count", 0)) > 0:
        parts.append(f"stats={render_refresh_history_stats(stats_payload)}")

    return f"{name}_refresh: " + " ".join(parts or ["none"])


def summarize_freshness_report(
    freshness: Any,
    *,
    include_notes: bool,
    cohort_alignment: Any = None,
) -> str:
    if not isinstance(freshness, dict):
        return ""

    categories = freshness.get("categories", {})
    if not isinstance(categories, dict):
        categories = {}

    target_version = 0
    if isinstance(cohort_alignment, dict):
        try:
            target_version = max(0, int(cohort_alignment.get("target_version", 0)))
        except (TypeError, ValueError):
            target_version = 0

    grouped: dict[str, list[str]] = {}
    for key, payload in categories.items():
        if not isinstance(payload, dict):
            continue
        status = str(payload.get("freshness_status", "")).strip()
        if not status or status == "current":
            continue
        if include_notes and status not in {"aligned_selection", "newer_other_signatures"}:
            continue
        if not include_notes and status not in {"stale_same_signature"}:
            continue
        grouped.setdefault(status, []).append(FRESHNESS_ARTIFACT_LABELS.get(str(key), str(key)))

    parts: list[str] = []
    for status in ("stale_same_signature", "newer_other_signatures", "aligned_selection"):
        labels = grouped.get(status, [])
        if not labels:
            continue
        if status == "aligned_selection":
            status_label = f"aligned_to_v{target_version}" if target_version > 0 else "aligned_selection"
        elif status == "newer_other_signatures":
            status_label = "other_signature_newer"
        else:
            status_label = "same_signature_newer"
        parts.append(f"{status_label}=" + ",".join(labels))

    return "; ".join(parts)


def summarize_rejection_counts(rejection_counts: Any) -> str:
    if not isinstance(rejection_counts, dict):
        return ""
    parts = [f"{key}={value}" for key, value in rejection_counts.items() if isinstance(value, int) and value > 0]
    return ", ".join(parts)


def summarize_rejected_candidate_reports(
    reports: Any,
    *,
    max_reasons: int = 2,
    max_names: int = 2,
) -> str:
    if not isinstance(reports, list):
        return ""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in reports:
        if not isinstance(item, dict) or item.get("status") == "valid":
            continue
        reason = str(item.get("reason", "")).strip() or str(item.get("status", "rejected")).strip() or "rejected"
        grouped.setdefault(reason, []).append(item)

    if not grouped:
        return ""

    parts: list[str] = []
    grouped_items = sorted(grouped.items(), key=lambda entry: (-len(entry[1]), entry[0]))
    for reason, items in grouped_items[:max_reasons]:
        names: list[str] = []
        for item in items[:max_names]:
            label = Path(str(item.get("path", ""))).name or str(item.get("name", "")).strip() or "candidate"
            names.append(label)
        remaining = len(items) - len(names)
        if remaining > 0:
            names.append(f"+{remaining}")
        parts.append(f"{reason} x{len(items)} (" + ",".join(names) + ")")

    remaining_reasons = len(grouped_items) - min(len(grouped_items), max_reasons)
    if remaining_reasons > 0:
        parts.append(f"+{remaining_reasons} more reasons")
    return "; ".join(parts)


def filter_matching_paths(
    paths: Sequence[Path],
    signature_getter,
    required_hashes: dict[str, str],
) -> list[Path]:
    matched: list[Path] = []
    for path in paths:
        signature = signature_getter(path)
        if all(required_hashes[key] and signature.get(key) == required_hashes[key] for key in required_hashes):
            matched.append(path)
    return matched


def build_freshness_report(
    selected: dict[str, Path],
    candidate_reports: dict[str, list[dict[str, Any]]],
    *,
    group_candidates: dict[str, Sequence[Path]] | None = None,
    cohort_alignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    categories: dict[str, Any] = {}
    warnings: list[str] = []
    notes: list[str] = []
    group_candidates = group_candidates or {}
    target_version = int(cohort_alignment.get("target_version", -1)) if isinstance(cohort_alignment, dict) else -1
    for key, selected_path in selected.items():
        reports = candidate_reports.get(key, [])
        valid_reports = [item for item in reports if item.get("status") == "valid"]
        selected_report = next((item for item in valid_reports if str(item.get("path", "")) == str(selected_path)), None)
        if selected_report is None:
            selected_report = describe_candidate_path(selected_path)
        group_candidate_paths = {str(path) for path in group_candidates.get(key, [])}
        matching_valid_reports = [
            item for item in valid_reports if str(item.get("path", "")) in group_candidate_paths
        ] or valid_reports
        selected_version = path_version(selected_path)
        newest_valid_version = max((int(item.get("version", -1)) for item in valid_reports), default=selected_version)
        newest_matching_version = max((int(item.get("version", -1)) for item in matching_valid_reports), default=selected_version)
        newer_valid_candidates = [item for item in valid_reports if int(item.get("version", -1)) > selected_version]
        newer_matching_candidates = [
            item for item in matching_valid_reports if int(item.get("version", -1)) > selected_version
        ]
        newer_external_candidates = [
            item for item in newer_valid_candidates if str(item.get("path", "")) not in group_candidate_paths
        ]
        selected_target_score = (
            _version_distance(int(selected_report.get("version", selected_version)), target_version),
            -int(selected_report.get("version", selected_version)),
            -int(selected_report.get("mtime_ns", 0)),
        )
        newer_matching_target_scores = [
            (
                _version_distance(int(item.get("version", -1)), target_version),
                -int(item.get("version", -1)),
                -int(item.get("mtime_ns", 0)),
            )
            for item in newer_matching_candidates
        ]
        alignment_preferred = bool(
            target_version >= 0
            and newer_matching_target_scores
            and selected_target_score < min(newer_matching_target_scores)
        )
        freshness_status = "current"
        if newer_matching_candidates:
            freshness_status = "aligned_selection" if alignment_preferred else "stale_same_signature"
        elif newer_external_candidates:
            freshness_status = "newer_other_signatures"
        category_report = {
            "selected_path": str(selected_path),
            "selected_version": selected_version,
            "newest_valid_version": newest_valid_version,
            "newest_matching_version": newest_matching_version,
            "selected_is_newest_valid": selected_version >= newest_valid_version,
            "selected_is_newest_matching": selected_version >= newest_matching_version,
            "newer_valid_candidate_count": len(newer_valid_candidates),
            "newer_valid_candidates": [item.get("path", "") for item in newer_valid_candidates[:5]],
            "newer_matching_candidate_count": len(newer_matching_candidates),
            "newer_matching_candidates": [item.get("path", "") for item in newer_matching_candidates[:5]],
            "newer_external_candidate_count": len(newer_external_candidates),
            "newer_external_candidates": [item.get("path", "") for item in newer_external_candidates[:5]],
            "freshness_status": freshness_status,
        }
        categories[key] = category_report
        if newer_matching_candidates and not alignment_preferred:
            warnings.append(
                f"{key}: selected {selected_path.name} while newer matching candidates exist ({', '.join(Path(str(item['path'])).name for item in newer_matching_candidates[:3])})"
            )
        elif newer_matching_candidates:
            notes.append(
                f"{key}: kept {selected_path.name} to align with cohort target v{target_version} instead of newer matching candidates ({', '.join(Path(str(item['path'])).name for item in newer_matching_candidates[:3])})"
            )
        elif newer_external_candidates:
            notes.append(
                f"{key}: newer valid candidates exist only outside the selected signature group ({', '.join(Path(str(item['path'])).name for item in newer_external_candidates[:3])})"
            )
    return {"categories": categories, "warnings": warnings, "notes": notes}


def build_stack_summary(
    bundle_dir: Path,
    pipeline_dir: Path,
    runtime_dir: Path,
    personal_skill_dir: Path,
    workflow_skill_dir: Path,
    discovery_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_signature = extract_bundle_signature(bundle_dir)
    pipeline_signature = extract_pipeline_signature(pipeline_dir)
    runtime_signature = extract_runtime_signature(runtime_dir)
    personal_skill_signature = extract_personal_skill_signature(personal_skill_dir)
    workflow_skill_signature = extract_workflow_skill_signature(workflow_skill_dir)
    bundle_history = extract_bundle_refresh_trigger_history(bundle_dir)
    pipeline_history = extract_pipeline_refresh_trigger_history(pipeline_dir)
    runtime_history = extract_runtime_refresh_trigger_history(runtime_dir)
    summary = {
        "bundle_dir": str(bundle_dir),
        "pipeline_dir": str(pipeline_dir),
        "runtime_dir": str(runtime_dir),
        "personal_skill_dir": str(personal_skill_dir),
        "workflow_skill_dir": str(workflow_skill_dir),
        "signatures": {
            "bundle": bundle_signature,
            "pipeline": pipeline_signature,
            "runtime": runtime_signature,
            "personal_skill": personal_skill_signature,
            "workflow_skill": workflow_skill_signature,
        },
        "refresh_watch": {
            "bundle": extract_bundle_refresh_watch(bundle_dir),
            "pipeline": extract_pipeline_refresh_watch(pipeline_dir),
            "runtime": extract_runtime_refresh_watch(runtime_dir),
        },
        "last_refresh_trigger": {
            "bundle": extract_bundle_last_refresh_trigger(bundle_dir),
            "pipeline": extract_pipeline_last_refresh_trigger(pipeline_dir),
            "runtime": extract_runtime_last_refresh_trigger(runtime_dir),
        },
        "refresh_trigger_history": {
            "bundle": bundle_history,
            "pipeline": pipeline_history,
            "runtime": runtime_history,
        },
        "refresh_stats": {
            "bundle": summarize_refresh_trigger_history(bundle_history),
            "pipeline": summarize_refresh_trigger_history(pipeline_history),
            "runtime": summarize_refresh_trigger_history(runtime_history),
        },
    }
    if discovery_report:
        summary["discovery_report"] = discovery_report
    return summary


def build_optional_stack_summary(
    *,
    bundle_dir: Path | None = None,
    pipeline_dir: Path | None = None,
    runtime_dir: Path | None = None,
    personal_skill_dir: Path | None = None,
    workflow_skill_dir: Path | None = None,
    selection_mode: str = "",
    discovery_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "bundle_dir": str(bundle_dir) if bundle_dir else "",
        "pipeline_dir": str(pipeline_dir) if pipeline_dir else "",
        "runtime_dir": str(runtime_dir) if runtime_dir else "",
        "personal_skill_dir": str(personal_skill_dir) if personal_skill_dir else "",
        "workflow_skill_dir": str(workflow_skill_dir) if workflow_skill_dir else "",
        "signatures": {},
    }
    if bundle_dir and bundle_dir.exists():
        bundle_history = extract_bundle_refresh_trigger_history(bundle_dir)
        summary["signatures"]["bundle"] = extract_bundle_signature(bundle_dir)
        summary.setdefault("refresh_watch", {})["bundle"] = extract_bundle_refresh_watch(bundle_dir)
        summary.setdefault("last_refresh_trigger", {})["bundle"] = extract_bundle_last_refresh_trigger(bundle_dir)
        summary.setdefault("refresh_trigger_history", {})["bundle"] = bundle_history
        summary.setdefault("refresh_stats", {})["bundle"] = summarize_refresh_trigger_history(bundle_history)
    if pipeline_dir and pipeline_dir.exists():
        pipeline_history = extract_pipeline_refresh_trigger_history(pipeline_dir)
        summary["signatures"]["pipeline"] = extract_pipeline_signature(pipeline_dir)
        summary.setdefault("refresh_watch", {})["pipeline"] = extract_pipeline_refresh_watch(pipeline_dir)
        summary.setdefault("last_refresh_trigger", {})["pipeline"] = extract_pipeline_last_refresh_trigger(pipeline_dir)
        summary.setdefault("refresh_trigger_history", {})["pipeline"] = pipeline_history
        summary.setdefault("refresh_stats", {})["pipeline"] = summarize_refresh_trigger_history(pipeline_history)
    if runtime_dir and runtime_dir.exists():
        runtime_history = extract_runtime_refresh_trigger_history(runtime_dir)
        summary["signatures"]["runtime"] = extract_runtime_signature(runtime_dir)
        summary.setdefault("refresh_watch", {})["runtime"] = extract_runtime_refresh_watch(runtime_dir)
        summary.setdefault("last_refresh_trigger", {})["runtime"] = extract_runtime_last_refresh_trigger(runtime_dir)
        summary.setdefault("refresh_trigger_history", {})["runtime"] = runtime_history
        summary.setdefault("refresh_stats", {})["runtime"] = summarize_refresh_trigger_history(runtime_history)
    if personal_skill_dir and personal_skill_dir.exists():
        summary["signatures"]["personal_skill"] = extract_personal_skill_signature(personal_skill_dir)
    if workflow_skill_dir and workflow_skill_dir.exists():
        summary["signatures"]["workflow_skill"] = extract_workflow_skill_signature(workflow_skill_dir)
    if selection_mode:
        summary["selection_mode"] = selection_mode
    if discovery_report:
        summary["discovery_report"] = discovery_report
    return summary


def render_stack_summary_text(summary: dict[str, Any]) -> str:
    lines = [
        f"selection_mode: {summary.get('selection_mode', 'unknown')}",
        f"bundle: {summary.get('bundle_dir', '')}",
        f"pipeline: {summary.get('pipeline_dir', '')}",
        f"runtime: {summary.get('runtime_dir', '')}",
        f"personal_skill: {summary.get('personal_skill_dir', '')}",
        f"workflow_skill: {summary.get('workflow_skill_dir', '')}",
    ]
    signatures = summary.get("signatures", {}) if isinstance(summary.get("signatures", {}), dict) else {}
    for name, signature in signatures.items():
        if not isinstance(signature, dict):
            continue
        clone_hash = str(signature.get("clone_config_hash", "")).strip()
        blueprint_hash = str(signature.get("workflow_blueprint_hash", "")).strip()
        parts = []
        if clone_hash:
            parts.append(f"clone={clone_hash[:12]}")
        if blueprint_hash:
            parts.append(f"blueprint={blueprint_hash[:12]}")
        lines.append(f"{name}_signature: {' '.join(parts) or 'none'}")
    refresh_watch = summary.get("refresh_watch", {}) if isinstance(summary.get("refresh_watch", {}), dict) else {}
    last_refresh_trigger = (
        summary.get("last_refresh_trigger", {}) if isinstance(summary.get("last_refresh_trigger", {}), dict) else {}
    )
    refresh_trigger_history = (
        summary.get("refresh_trigger_history", {}) if isinstance(summary.get("refresh_trigger_history", {}), dict) else {}
    )
    refresh_stats = summary.get("refresh_stats", {}) if isinstance(summary.get("refresh_stats", {}), dict) else {}
    for name in ("bundle", "pipeline", "runtime"):
        watch_payload = refresh_watch.get(name, {})
        last_trigger_payload = last_refresh_trigger.get(name, {})
        history_payload = refresh_trigger_history.get(name, {})
        stats_payload = refresh_stats.get(name, {})
        if not isinstance(watch_payload, dict):
            watch_payload = {}
        if not isinstance(last_trigger_payload, dict):
            last_trigger_payload = {}
        if not isinstance(history_payload, list):
            history_payload = []
        if not isinstance(stats_payload, dict):
            stats_payload = {}
        if not watch_payload and not last_trigger_payload and not history_payload and int(stats_payload.get("history_count", 0)) <= 0:
            continue
        lines.append(
            render_refresh_artifact_summary(
                name,
                watch_payload,
                last_trigger_payload,
                history_payload,
                stats_payload,
            )
        )
    discovery_report = summary.get("discovery_report", {}) if isinstance(summary.get("discovery_report", {}), dict) else {}
    freshness = discovery_report.get("freshness", {}) if isinstance(discovery_report.get("freshness", {}), dict) else {}
    warnings = freshness.get("warnings", []) if isinstance(freshness.get("warnings", []), list) else []
    if warnings:
        warning_summary = summarize_freshness_report(
            freshness,
            include_notes=False,
            cohort_alignment=discovery_report.get("cohort_alignment", {}),
        )
        lines.append("freshness_warnings: " + (warning_summary or str(len(warnings))))
    notes = freshness.get("notes", []) if isinstance(freshness.get("notes", []), list) else []
    if notes:
        note_summary = summarize_freshness_report(
            freshness,
            include_notes=True,
            cohort_alignment=discovery_report.get("cohort_alignment", {}),
        )
        lines.append("freshness_notes: " + (note_summary or str(len(notes))))
    rejection_counts = discovery_report.get("rejection_counts", {}) if isinstance(discovery_report.get("rejection_counts", {}), dict) else {}
    rejection_summary = summarize_rejection_counts(rejection_counts)
    if rejection_summary:
        lines.append("candidate_rejections: " + rejection_summary)
    candidate_reports = discovery_report.get("candidate_reports", {}) if isinstance(discovery_report.get("candidate_reports", {}), dict) else {}
    for key, reports in candidate_reports.items():
        rejected_summary = summarize_rejected_candidate_reports(reports)
        if not rejected_summary:
            continue
        lines.append(f"{key}_rejected_candidates: {rejected_summary}")
    return "\n".join(lines)


def diff_stack_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    differing_paths: list[dict[str, str]] = []
    for key in ["bundle_dir", "pipeline_dir", "runtime_dir", "personal_skill_dir", "workflow_skill_dir"]:
        if str(left.get(key, "")) != str(right.get(key, "")):
            differing_paths.append({"field": key, "left": str(left.get(key, "")), "right": str(right.get(key, ""))})

    differing_signatures: list[dict[str, str]] = []
    left_signatures = left.get("signatures", {}) if isinstance(left.get("signatures", {}), dict) else {}
    right_signatures = right.get("signatures", {}) if isinstance(right.get("signatures", {}), dict) else {}
    for key in sorted(set(left_signatures) | set(right_signatures)):
        left_sig = left_signatures.get(key, {}) if isinstance(left_signatures.get(key, {}), dict) else {}
        right_sig = right_signatures.get(key, {}) if isinstance(right_signatures.get(key, {}), dict) else {}
        if left_sig != right_sig:
            differing_signatures.append({"field": key, "left": json.dumps(left_sig, ensure_ascii=False), "right": json.dumps(right_sig, ensure_ascii=False)})

    return {
        "differing_paths": differing_paths,
        "differing_signatures": differing_signatures,
        "ok": not differing_paths and not differing_signatures,
    }


def _selection_attempt_report(
    bundle_dir: Path,
    signature: dict[str, str],
    matching_pipeline_dirs: Sequence[Path],
    matching_runtime_dirs: Sequence[Path],
    matching_personal_skill_dirs: Sequence[Path],
    matching_workflow_skill_dirs: Sequence[Path],
    reason: str,
) -> dict[str, Any]:
    return {
        "bundle_dir": str(bundle_dir),
        "bundle_signature": signature,
        "matching_pipeline_dirs": [str(path) for path in matching_pipeline_dirs],
        "matching_runtime_dirs": [str(path) for path in matching_runtime_dirs],
        "matching_personal_skill_dirs": [str(path) for path in matching_personal_skill_dirs],
        "matching_workflow_skill_dirs": [str(path) for path in matching_workflow_skill_dirs],
        "reason": reason,
    }


def signature_identity_key(signature: dict[str, str]) -> tuple[str, str]:
    return (
        str(signature.get("clone_config_hash", "")).strip(),
        str(signature.get("workflow_blueprint_hash", "")).strip(),
    )


def _version_distance(version: int, target_version: int) -> int:
    if version < 0 or target_version < 0:
        return 10**9
    return abs(version - target_version)


def _path_target_score(path: Path, target_version: int) -> tuple[int, int, int]:
    stat = path.stat()
    version = path_version(path)
    return (
        _version_distance(version, target_version),
        -version,
        -stat.st_mtime_ns,
    )


def _pick_best_path_for_target(paths: Sequence[Path], target_version: int) -> Path:
    if not paths:
        raise ValueError("expected at least one matching path")
    return min(paths, key=lambda path: _path_target_score(path, target_version))


def _rank_signature_group_candidates(
    bundle_dirs: Sequence[Path],
    pipeline_dirs: Sequence[Path],
    runtime_dirs: Sequence[Path],
    personal_skill_dirs: Sequence[Path],
    workflow_skill_dirs: Sequence[Path],
) -> list[dict[str, Any]]:
    options_by_key = {
        "bundle": bundle_dirs,
        "pipeline": pipeline_dirs,
        "runtime": runtime_dirs,
        "personal_skill": personal_skill_dirs,
        "workflow_skill": workflow_skill_dirs,
    }
    target_versions = sorted(
        {
            path_version(path)
            for paths in options_by_key.values()
            for path in paths
            if path_version(path) >= 0
        },
        reverse=True,
    )
    if not target_versions:
        target_versions = [-1]

    ranked_candidates: list[dict[str, Any]] = []
    seen_candidates: set[tuple[str, str, str, str, str]] = set()
    for target_version in target_versions:
        selected_map = {
            key: _pick_best_path_for_target(paths, target_version)
            for key, paths in options_by_key.items()
        }
        candidate = (
            selected_map["bundle"],
            selected_map["pipeline"],
            selected_map["runtime"],
            selected_map["personal_skill"],
            selected_map["workflow_skill"],
        )
        candidate_key = tuple(str(path) for path in candidate)
        if candidate_key in seen_candidates:
            continue
        seen_candidates.add(candidate_key)

        versions = {key: path_version(path) for key, path in selected_map.items()}
        distances = {key: _version_distance(version, target_version) for key, version in versions.items()}
        score = (
            -sum(1 for version in versions.values() if version == target_version),
            sum(distances.values()),
            max(distances.values(), default=0),
            -target_version,
        )
        ranked_candidates.append(
            {
                "candidate": candidate,
                "target_version": target_version,
                "versions": versions,
                "score": score,
            }
        )

    ranked_candidates.sort(key=lambda item: item["score"])
    return ranked_candidates


def select_latest_coherent_stack_with_report(
    workdir: Path,
    bundle_dirs: Sequence[Path],
    pipeline_dirs: Sequence[Path],
    runtime_dirs: Sequence[Path],
    personal_skill_dirs: Sequence[Path],
    workflow_skill_dirs: Sequence[Path],
    candidate_reports: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[tuple[Path, Path, Path, Path, Path], dict[str, Any]]:
    candidate_reports = candidate_reports or {}
    selection_attempts: list[dict[str, Any]] = []
    signature_groups: dict[tuple[str, str], dict[str, Any]] = {}
    signature_order: list[tuple[str, str]] = []

    for bundle_dir in bundle_dirs:
        signature = extract_bundle_signature(bundle_dir)
        if not signature["clone_config_hash"] or not signature["workflow_blueprint_hash"]:
            selection_attempts.append(
                _selection_attempt_report(bundle_dir, signature, [], [], [], [], "bundle signature incomplete")
            )
            continue

        signature_key = signature_identity_key(signature)
        if signature_key not in signature_groups:
            signature_groups[signature_key] = {
                "signature": signature,
                "bundle_dirs": [],
            }
            signature_order.append(signature_key)
        signature_groups[signature_key]["bundle_dirs"].append(bundle_dir)

    for signature_key in signature_order:
        signature_group = signature_groups[signature_key]
        signature = signature_group["signature"]
        matching_bundle_dirs = signature_group["bundle_dirs"]
        matching_pipeline_dirs = filter_matching_paths(pipeline_dirs, extract_pipeline_signature, signature)
        matching_runtime_dirs = filter_matching_paths(runtime_dirs, extract_runtime_signature, signature)
        matching_personal_skill_dirs = filter_matching_paths(
            personal_skill_dirs,
            extract_personal_skill_signature,
            {"clone_config_hash": signature["clone_config_hash"]},
        )
        matching_workflow_skill_dirs = filter_matching_paths(
            workflow_skill_dirs,
            extract_workflow_skill_signature,
            signature,
        )
        if not (matching_pipeline_dirs and matching_runtime_dirs and matching_personal_skill_dirs and matching_workflow_skill_dirs):
            selection_attempts.append(
                _selection_attempt_report(
                    matching_bundle_dirs[0],
                    signature,
                    matching_pipeline_dirs,
                    matching_runtime_dirs,
                    matching_personal_skill_dirs,
                    matching_workflow_skill_dirs,
                    "content-linked coherent stack incomplete",
                )
            )
            continue

        ranked_candidates = _rank_signature_group_candidates(
            matching_bundle_dirs,
            matching_pipeline_dirs,
            matching_runtime_dirs,
            matching_personal_skill_dirs,
            matching_workflow_skill_dirs,
        )
        for ranked_candidate in ranked_candidates:
            candidate = ranked_candidate["candidate"]
            if run_validation(build_stack_validation_command(workdir, *candidate), workdir):
                selected_map = {
                    "bundle": candidate[0],
                    "pipeline": candidate[1],
                    "runtime": candidate[2],
                    "personal_skill": candidate[3],
                    "workflow_skill": candidate[4],
                }
                report = {
                    "selection_attempts": selection_attempts,
                    "selected_bundle": str(candidate[0]),
                    "freshness": build_freshness_report(
                        selected_map,
                        candidate_reports,
                        group_candidates={
                            "bundle": matching_bundle_dirs,
                            "pipeline": matching_pipeline_dirs,
                            "runtime": matching_runtime_dirs,
                            "personal_skill": matching_personal_skill_dirs,
                            "workflow_skill": matching_workflow_skill_dirs,
                        },
                        cohort_alignment={
                            "target_version": ranked_candidate["target_version"],
                            "versions": ranked_candidate["versions"],
                        },
                    ),
                    "candidate_reports": candidate_reports,
                    "rejection_counts": {
                        key: len([item for item in reports if item.get("status") != "valid"])
                        for key, reports in candidate_reports.items()
                    },
                    "cohort_alignment": {
                        "target_version": ranked_candidate["target_version"],
                        "versions": ranked_candidate["versions"],
                    },
                }
                return candidate, report

            selection_attempts.append(
                _selection_attempt_report(
                    candidate[0],
                    signature,
                    matching_pipeline_dirs,
                    matching_runtime_dirs,
                    matching_personal_skill_dirs,
                    matching_workflow_skill_dirs,
                    "aggregate stack validation failed",
                )
            )

    raise SystemExit("no coherent latest stack found across valid /tmp artifacts")


def select_latest_coherent_stack(
    workdir: Path,
    bundle_dirs: Sequence[Path],
    pipeline_dirs: Sequence[Path],
    runtime_dirs: Sequence[Path],
    personal_skill_dirs: Sequence[Path],
    workflow_skill_dirs: Sequence[Path],
) -> tuple[Path, Path, Path, Path, Path]:
    candidate, _ = select_latest_coherent_stack_with_report(
        workdir,
        bundle_dirs,
        pipeline_dirs,
        runtime_dirs,
        personal_skill_dirs,
        workflow_skill_dirs,
    )
    return candidate


def discover_latest_coherent_stack_report(workdir: Path) -> tuple[tuple[Path, Path, Path, Path, Path], dict[str, Any]]:
    bundle_dirs, bundle_reports = collect_tmp_dir_candidates(
        "working-clone-bundle-v",
        [
            "working_clone_bundle_manifest.json",
            "working_clone_until_final_summary.json",
            "WORKING_CLONE_BUNDLE_README.md",
        ],
        lambda path: [
            "python3",
            str(workdir / "scripts" / "validate_working_clone_dispatch.py"),
            "--manifest",
            str(path / "working_clone_bundle_manifest.json"),
            "--summary",
            str(path / "working_clone_until_final_summary.json"),
            "--readme",
            str(path / "WORKING_CLONE_BUNDLE_README.md"),
            "--format",
            "json",
        ],
        workdir,
    )
    pipeline_dirs, pipeline_reports = collect_tmp_dir_candidates(
        "workflow-blueprint-pipeline-v",
        [
            "workflow_blueprint_pipeline_manifest.json",
            "WORKFLOW_BLUEPRINT_PIPELINE_README.md",
        ],
        lambda path: [
            "python3",
            str(workdir / "scripts" / "validate_workflow_pipeline_dispatch.py"),
            "--manifest",
            str(path / "workflow_blueprint_pipeline_manifest.json"),
            "--readme",
            str(path / "WORKFLOW_BLUEPRINT_PIPELINE_README.md"),
            "--format",
            "json",
        ],
        workdir,
    )
    runtime_dirs, runtime_reports = collect_tmp_dir_candidates(
        "workflow-runtime-v",
        [
            "workflow_runtime_manifest.json",
            "WORKFLOW_RUNTIME_README.md",
        ],
        lambda path: [
            "python3",
            str(workdir / "scripts" / "validate_workflow_runtime_dispatch.py"),
            "--manifest",
            str(path / "workflow_runtime_manifest.json"),
            "--readme",
            str(path / "WORKFLOW_RUNTIME_README.md"),
            "--format",
            "json",
        ],
        workdir,
    )
    personal_skill_dirs, personal_reports = collect_tmp_dir_candidates(
        "personal-clone-skill-v",
        [
            "clone_config.yaml",
            "README.md",
            "personal_clone_skill_manifest.json",
        ],
        lambda path: [
            "python3",
            str(workdir / "scripts" / "validate_personal_clone_release.py"),
            "--skill-dir",
            str(path),
            "--format",
            "json",
        ],
        workdir,
    )
    workflow_skill_dirs, workflow_reports = collect_tmp_dir_candidates(
        "workflow-clone-skill-v",
        [
            "clone_config.yaml",
            "README.md",
            "workflow_clone_skill_manifest.json",
            "workflow_blueprint.md",
        ],
        lambda path: [
            "python3",
            str(workdir / "scripts" / "validate_workflow_clone_release.py"),
            "--skill-dir",
            str(path),
            "--format",
            "json",
        ],
        workdir,
    )
    candidate_reports = {
        "bundle": bundle_reports,
        "pipeline": pipeline_reports,
        "runtime": runtime_reports,
        "personal_skill": personal_reports,
        "workflow_skill": workflow_reports,
    }
    return select_latest_coherent_stack_with_report(
        workdir,
        bundle_dirs,
        pipeline_dirs,
        runtime_dirs,
        personal_skill_dirs,
        workflow_skill_dirs,
        candidate_reports=candidate_reports,
    )


def discover_latest_coherent_stack(workdir: Path) -> tuple[Path, Path, Path, Path, Path]:
    candidate, _ = discover_latest_coherent_stack_report(workdir)
    return candidate


def discover_current_stack_from_bundle_report(workdir: Path, bundle_dir: Path) -> tuple[tuple[Path, Path, Path, Path, Path], dict[str, Any]]:
    bundle_signature = extract_bundle_signature(bundle_dir)
    if not bundle_signature["clone_config_hash"] or not bundle_signature["workflow_blueprint_hash"]:
        raise SystemExit(f"bundle does not expose a coherent signature: {bundle_dir}")

    pipeline_dir = bundle_dir / "workflow-blueprint-pipeline"
    runtime_dir = pipeline_dir / "workflow-runtime-bundle"
    personal_skill_dir = bundle_dir / "personal-clone-skill"
    workflow_skill_dir = pipeline_dir / "workflow-clone-skill"
    candidate = (bundle_dir, pipeline_dir, runtime_dir, personal_skill_dir, workflow_skill_dir)
    if run_validation(build_stack_validation_command(workdir, *candidate), workdir):
        report = {
            "selection_attempts": [
                {
                    "bundle_dir": str(bundle_dir),
                    "reason": "nested bundle artifacts already form a coherent stack",
                }
            ],
            "selected_bundle": str(bundle_dir),
            "freshness": {"categories": {}, "warnings": []},
            "candidate_reports": {},
            "rejection_counts": {},
        }
        return candidate, report

    latest, latest_report = discover_latest_coherent_stack_report(workdir)
    latest_summary = build_stack_summary(*latest)
    if latest_summary["signatures"]["bundle"] == bundle_signature:
        latest_report["selection_attempts"].append(
            {
                "bundle_dir": str(bundle_dir),
                "reason": "nested bundle artifacts failed validation, reused discovered coherent stack with matching signature",
            }
        )
        return latest, latest_report
    raise SystemExit(f"no coherent stack found for bundle: {bundle_dir}")


def discover_current_stack_from_bundle(workdir: Path, bundle_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    candidate, _ = discover_current_stack_from_bundle_report(workdir, bundle_dir)
    return candidate
