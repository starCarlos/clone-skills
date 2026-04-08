#!/usr/bin/env python3
"""Run the executable release-readiness checks and emit one aggregated report."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from stack_discovery import (
        build_stack_summary,
        discover_latest_coherent_stack_report,
        summarize_freshness_report,
        summarize_rejection_counts,
    )
except ModuleNotFoundError:
    from scripts.stack_discovery import (
        build_stack_summary,
        discover_latest_coherent_stack_report,
        summarize_freshness_report,
        summarize_rejection_counts,
    )

LOG_PREVIEW_CHAR_LIMIT = 1200
LOG_PREVIEW_LINE_LIMIT = 24

STACK_DIR_KEYS = (
    "bundle_dir",
    "pipeline_dir",
    "runtime_dir",
    "personal_skill_dir",
    "workflow_skill_dir",
)
STACK_SIGNATURE_KEYS = ("bundle", "pipeline", "runtime", "personal_skill", "workflow_skill")
VALIDATION_CHECK_LABELS = {
    "working_clone_dispatch": "working bundle dispatch",
    "workflow_pipeline_dispatch": "workflow pipeline dispatch",
    "workflow_runtime_dispatch": "workflow runtime dispatch",
    "personal_skill_structure": "personal skill structure",
    "personal_skill_release": "personal skill release",
    "workflow_skill_structure": "workflow skill structure",
    "workflow_skill_release": "workflow skill release",
    "cross_artifact_linkage": "cross-artifact linkage",
    "source_artifact_contracts": "source artifact contracts",
}
STEP_HEADLINES = {
    "validate_repo_docs": "repo docs validation",
    "unit_tests": "unit tests",
    "rebuild_sample_stack": "sample stack rebuild",
    "validate_sample_workflow_blueprint": "workflow blueprint gate",
    "doctor_sample_stack": "sample stack doctor",
    "doctor_current_stack": "current stack doctor",
    "doctor_latest_stack": "latest stack doctor",
    "validate_latest_stack": "latest stack validation",
    "explain_latest_stack": "latest stack explanation",
}


def write_pinned_latest_stack_summary(workdir: Path, output_root: Path) -> str:
    candidate, discovery_report = discover_latest_coherent_stack_report(workdir)
    summary = build_stack_summary(*candidate, discovery_report=discovery_report)
    summary["selection_mode"] = "latest_coherent_stack"
    path = output_root / "release_pinned_latest_stack.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run release-readiness checks for the clone stack tooling.")
    parser.add_argument("--output-root", default="/tmp/mind-clone-sample-stack")
    parser.add_argument("--summary-json", default="")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-rebuild", action="store_true")
    parser.add_argument(
        "--keep-success-logs",
        action="store_true",
        help="Persist stdout/stderr logs even for successful steps. Default keeps logs only for failures.",
    )
    return parser.parse_args()


def slugify(label: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in label).strip("-") or "step"


def preview_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    lines = stripped.splitlines()
    clipped_by_lines = lines[:LOG_PREVIEW_LINE_LIMIT]
    preview = "\n".join(clipped_by_lines)
    if len(preview) > LOG_PREVIEW_CHAR_LIMIT:
        preview = preview[:LOG_PREVIEW_CHAR_LIMIT].rstrip() + "... [truncated]"
    elif len(lines) > LOG_PREVIEW_LINE_LIMIT:
        preview = preview.rstrip() + "\n... [truncated]"
    return preview


def write_log(logs_dir: Path, label: str, suffix: str, content: str) -> str:
    if not content.strip():
        return ""
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"{slugify(label)}.{suffix}.log"
    path.write_text(content, encoding="utf-8")
    return str(path)


def should_write_log(exit_code: int, content: str, keep_success_logs: bool) -> bool:
    if not content.strip():
        return False
    if exit_code != 0:
        return True
    return keep_success_logs


def try_parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def try_load_json_object(path_text: str) -> dict[str, Any] | None:
    if not path_text:
        return None
    path = Path(path_text).resolve()
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def basename_for_display(path_like: Any) -> str:
    text = str(path_like).strip()
    if not text:
        return ""
    return Path(text).name or text


def short_hash(value: Any) -> str:
    text = str(value).strip()
    return text[:12] if text else ""


def safe_positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def format_ranked_refresh_items(items: Any, limit: int = 1) -> str:
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "")).strip()
        count = safe_positive_int(item.get("count", 0))
        if not value or count <= 0:
            continue
        parts.append(f"{value}:{count}")
    return ",".join(parts)


def collect_stack_selection_details(summary: dict[str, Any] | None, *, include_freshness_notes: bool = False) -> list[str]:
    if not isinstance(summary, dict):
        return []
    details: list[str] = []

    selection_mode = str(summary.get("selection_mode", "")).strip()
    stack_ref_parts: list[str] = []
    if selection_mode:
        stack_ref_parts.append(selection_mode)

    for key, short_label in (
        ("bundle_dir", "bundle"),
        ("pipeline_dir", "pipeline"),
        ("runtime_dir", "runtime"),
    ):
        name = basename_for_display(summary.get(key, ""))
        if name:
            stack_ref_parts.append(f"{short_label}={name}")
    if not stack_ref_parts:
        for key, short_label in (
            ("personal_skill_dir", "personal"),
            ("workflow_skill_dir", "workflow"),
        ):
            name = basename_for_display(summary.get(key, ""))
            if name:
                stack_ref_parts.append(f"{short_label}={name}")
    if stack_ref_parts:
        details.append("stack_ref: " + " | ".join(stack_ref_parts))

    signatures = summary.get("signatures", {})
    if isinstance(signatures, dict):
        clone_hash = ""
        blueprint_hash = ""
        for key in STACK_SIGNATURE_KEYS:
            payload = signatures.get(key, {})
            if not isinstance(payload, dict):
                continue
            if not clone_hash:
                clone_hash = short_hash(payload.get("clone_config_hash", ""))
            if not blueprint_hash:
                blueprint_hash = short_hash(payload.get("workflow_blueprint_hash", ""))
        signature_parts: list[str] = []
        if clone_hash:
            signature_parts.append(f"clone={clone_hash}")
        if blueprint_hash:
            signature_parts.append(f"blueprint={blueprint_hash}")
        if signature_parts:
            details.append("signatures: " + ", ".join(signature_parts))

    discovery = summary.get("discovery_report", {})
    if isinstance(discovery, dict):
        rejection_counts = discovery.get("rejection_counts", {})
        if isinstance(rejection_counts, dict):
            rejection_summary = summarize_rejection_counts(
                {key: safe_positive_int(value) for key, value in rejection_counts.items()}
            )
            if rejection_summary:
                details.append("rejections: " + rejection_summary)
        freshness = discovery.get("freshness", {})
        if isinstance(freshness, dict):
            warnings = freshness.get("warnings", [])
            if isinstance(warnings, list) and warnings:
                warning_summary = summarize_freshness_report(
                    freshness,
                    include_notes=False,
                    cohort_alignment=discovery.get("cohort_alignment", {}),
                )
                details.append("freshness warnings: " + (warning_summary or str(len(warnings))))
            if include_freshness_notes:
                notes = freshness.get("notes", [])
                if isinstance(notes, list) and notes:
                    note_summary = summarize_freshness_report(
                        freshness,
                        include_notes=True,
                        cohort_alignment=discovery.get("cohort_alignment", {}),
                    )
                    details.append("freshness notes: " + (note_summary or str(len(notes))))

    return details


def collect_refresh_hotspot_details(summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(summary, dict):
        return []
    refresh_stats = summary.get("refresh_stats", {})
    if not isinstance(refresh_stats, dict):
        return []

    artifact_parts: list[str] = []
    for name in ("bundle", "pipeline", "runtime"):
        payload = refresh_stats.get(name, {})
        if not isinstance(payload, dict) or safe_positive_int(payload.get("history_count", 0)) <= 0:
            continue
        bits: list[str] = []
        groups = format_ranked_refresh_items(payload.get("top_groups", []), limit=1)
        classes = format_ranked_refresh_items(payload.get("top_classes", []), limit=1)
        files = format_ranked_refresh_items(payload.get("top_files", []), limit=2)
        if groups:
            bits.append(f"groups={groups}")
        if classes:
            bits.append(f"classes={classes}")
        if files:
            bits.append(f"files={files}")
        if bits:
            artifact_parts.append(f"{name}(" + " ".join(bits) + ")")

    if artifact_parts:
        return [("refresh_hotspots: " + " | ".join(artifact_parts))]
    return ["refresh_hotspots: none"]


def collect_validation_details(payload: dict[str, Any]) -> tuple[str, list[str]]:
    checks = payload.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    total = len(checks)
    passed = 0
    failed_labels: list[str] = []
    for key, result in checks.items():
        ok = isinstance(result, dict) and bool(result.get("ok", False))
        if ok:
            passed += 1
        else:
            failed_labels.append(VALIDATION_CHECK_LABELS.get(str(key), str(key)))

    if total:
        headline = f"{passed}/{total} checks passed" if not failed_labels else f"{passed}/{total} checks passed; {len(failed_labels)} failed"
    else:
        headline = "validation passed" if bool(payload.get("ok", False)) else "validation failed"

    details: list[str] = []
    if failed_labels:
        details.append("failed checks: " + ", ".join(failed_labels))

    release_parts: list[str] = []
    for key, short_label in (
        ("personal_skill_release", "personal"),
        ("workflow_skill_release", "workflow"),
    ):
        release_payload = checks.get(key, {})
        if not isinstance(release_payload, dict):
            continue
        current = str(release_payload.get("current_draft_status", "")).strip()
        recommended = str(release_payload.get("recommended_draft_status", "")).strip()
        release_valid = release_payload.get("release_valid")
        if not current and not recommended and release_valid is None:
            continue
        label = f"{short_label}={current or 'unknown'}"
        if recommended and recommended != current:
            label += f" (recommended {recommended})"
        if release_valid is False:
            label += " invalid"
        release_parts.append(label)
    if release_parts:
        details.append("release: " + ", ".join(release_parts))

    return headline, details


def build_unit_test_summary(exit_code: int, stdout: str, stderr: str) -> dict[str, Any]:
    combined = "\n".join(part for part in [stdout.strip(), stderr.strip()] if part).strip()
    details: list[str] = []
    match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", combined)
    if match:
        details.append(f"suite: {match.group(1)} tests in {match.group(2)}s")
    headline = "unit tests passed" if exit_code == 0 else "unit tests failed"
    return {"headline": headline, "details": details}


def build_repo_docs_summary(payload: dict[str, Any]) -> dict[str, Any]:
    headline = "repo docs validation passed" if bool(payload.get("ok", False)) else "repo docs validation failed"
    details = [
        "issues: "
        + ", ".join(
            [
                f"missing_docs={len(payload.get('missing_docs', [])) if isinstance(payload.get('missing_docs'), list) else 0}",
                f"release_checklist={len(payload.get('release_checklist_missing_patterns', [])) if isinstance(payload.get('release_checklist_missing_patterns'), list) else 0}",
                f"readme={len(payload.get('readme_missing_patterns', [])) if isinstance(payload.get('readme_missing_patterns'), list) else 0}",
                f"current_flow={len(payload.get('current_flow_missing_patterns', [])) if isinstance(payload.get('current_flow_missing_patterns'), list) else 0}",
                f"capability_index={len(payload.get('capability_index_missing_patterns', [])) if isinstance(payload.get('capability_index_missing_patterns'), list) else 0}",
                f"operator_playbook={len(payload.get('operator_playbook_missing_patterns', [])) if isinstance(payload.get('operator_playbook_missing_patterns'), list) else 0}",
                f"operator_command_contract={len(payload.get('operator_command_contract_missing_patterns', [])) if isinstance(payload.get('operator_command_contract_missing_patterns'), list) else 0}",
                f"operator_command_summary={len(payload.get('operator_command_summary_missing_patterns', [])) if isinstance(payload.get('operator_command_summary_missing_patterns'), list) else 0}",
                f"failure_guide={len(payload.get('failure_guide_missing_patterns', [])) if isinstance(payload.get('failure_guide_missing_patterns'), list) else 0}",
                f"glossary={len(payload.get('glossary_missing_terms', [])) if isinstance(payload.get('glossary_missing_terms'), list) else 0}",
                f"example_index={len(payload.get('example_index_missing_patterns', [])) if isinstance(payload.get('example_index_missing_patterns'), list) else 0}",
                f"doc_router={len(payload.get('doc_router_missing_patterns', [])) if isinstance(payload.get('doc_router_missing_patterns'), list) else 0}",
                f"new_maintainer={len(payload.get('new_maintainer_missing_patterns', [])) if isinstance(payload.get('new_maintainer_missing_patterns'), list) else 0}",
                f"release_order={len(payload.get('release_readiness_order_issues', [])) if isinstance(payload.get('release_readiness_order_issues'), list) else 0}",
                f"operator_render={int(bool(payload.get('capability_index_render_mismatch', False))) + int(bool(payload.get('release_checklist_render_mismatch', False))) + int(bool(payload.get('current_flow_render_mismatch', False))) + int(bool(payload.get('readme_operator_render_mismatch', False))) + int(bool(payload.get('operator_playbook_render_mismatch', False))) + int(bool(payload.get('new_maintainer_operator_render_mismatch', False))) + int(bool(payload.get('doc_router_render_mismatch', False))) + int(bool(payload.get('failure_guide_render_mismatch', False))) + int(bool(payload.get('operator_command_contract_render_mismatch', False))) + int(bool(payload.get('operator_command_summary_render_mismatch', False)))}",
                f"scripts={len(payload.get('missing_script_refs', [])) if isinstance(payload.get('missing_script_refs'), list) else 0}",
                f"examples={len(payload.get('missing_example_files', [])) if isinstance(payload.get('missing_example_files'), list) else 0}",
            ]
        )
    ]
    return {"headline": headline, "details": details}


def build_blueprint_gate_summary(payload: dict[str, Any]) -> dict[str, Any]:
    generic_titles = payload.get("generic_stage_titles", [])
    empty_fields = payload.get("empty_stage_fields", [])
    placeholders = payload.get("placeholder_sections", [])
    generic_checkpoints = payload.get("generic_checkpoint_titles", [])
    headline = "workflow blueprint gate passed" if bool(payload.get("ok", False)) else "workflow blueprint gate failed"
    details = [f"blueprint: {basename_for_display(payload.get('path', ''))}"] if payload.get("path") else []
    details.append(
        "issues: "
        + ", ".join(
            [
                f"generic_titles={len(generic_titles) if isinstance(generic_titles, list) else 0}",
                f"empty_fields={len(empty_fields) if isinstance(empty_fields, list) else 0}",
                f"placeholders={len(placeholders) if isinstance(placeholders, list) else 0}",
                f"generic_checkpoints={len(generic_checkpoints) if isinstance(generic_checkpoints, list) else 0}",
            ]
        )
    )
    return {"headline": headline, "details": details}


def build_rebuild_summary(payload: dict[str, Any]) -> dict[str, Any]:
    validation_payload = payload.get("validation", {})
    validation_ok = True
    validation_headline = "validation skipped"
    if isinstance(validation_payload, dict):
        validation_ok = bool(validation_payload.get("ok", True))
        if validation_payload.get("skipped"):
            validation_headline = "validation skipped"
        else:
            validation_headline, _ = collect_validation_details(validation_payload)

    latest_exports = payload.get("latest_tmp_exports", {})
    export_count = 0
    export_version = ""
    if isinstance(latest_exports, dict):
        export_version = str(latest_exports.get("version", "")).strip()
        export_count = sum(1 for key in STACK_DIR_KEYS if str(latest_exports.get(key, "")).strip())

    retention_report: dict[str, Any] = {}
    pruned_total = 0
    tmp_retention = payload.get("tmp_retention", {})
    if isinstance(tmp_retention, dict):
        report = tmp_retention.get("report", {})
        if isinstance(report, dict):
            retention_report = report
        pruned = tmp_retention.get("pruned", {})
        if isinstance(pruned, dict):
            pruned_total = sum(len(paths) for paths in pruned.values() if isinstance(paths, list))

    headline = "sample stack rebuilt and validated" if validation_ok else "sample stack rebuilt but validation failed"
    details: list[str] = []
    stack_details = collect_stack_selection_details(payload.get("stack", {}))
    if validation_ok:
        stack_details = [detail for detail in stack_details if not str(detail).startswith("signatures:")]
    details.extend(stack_details[:2])
    if export_count:
        if export_version:
            details.append(f"/tmp exports: v{export_version} across {export_count} artifact types")
        else:
            details.append(f"/tmp exports: {export_count} artifact types")
    if retention_report:
        details.append(
            f"/tmp retention: retain={retention_report.get('retain')}, "
            f"prunable={retention_report.get('prunable_total')}, pruned={pruned_total}"
        )
    if validation_payload.get("skipped"):
        details.append(validation_headline)
    elif not validation_ok:
        details.append(validation_headline)
    return {"headline": headline, "details": details}


def build_validation_step_summary(label: str, payload: dict[str, Any], selection_summary: dict[str, Any] | None) -> dict[str, Any]:
    validation_headline, validation_details = collect_validation_details(payload)
    step_label = STEP_HEADLINES.get(label, label.replace("_", " "))
    details = collect_stack_selection_details(selection_summary)
    if bool(payload.get("ok", False)) and label in {
        "doctor_sample_stack",
        "doctor_current_stack",
        "doctor_latest_stack",
        "validate_latest_stack",
    }:
        details = [detail for detail in details if not str(detail).startswith("signatures:")]
    details.extend(validation_details)
    return {"headline": f"{step_label}: {validation_headline}", "details": details}


def build_explain_step_summary(selection_summary: dict[str, Any] | None, stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    headline = "latest stack explanation generated" if exit_code == 0 else "latest stack explanation failed"
    if isinstance(selection_summary, dict):
        return {
            "headline": headline,
            "details": collect_stack_selection_details(selection_summary, include_freshness_notes=True)
            + collect_refresh_hotspot_details(selection_summary),
        }

    combined = "\n".join(part for part in [stdout.strip(), stderr.strip()] if part).strip().splitlines()
    return {"headline": headline, "details": combined[:4]}


def build_compact_summary(
    label: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    summary_json_path: str = "",
) -> dict[str, Any]:
    stdout_payload = try_parse_json_object(stdout)
    selection_summary = try_load_json_object(summary_json_path)

    if label == "unit_tests":
        return build_unit_test_summary(exit_code, stdout, stderr)
    if label == "validate_repo_docs" and stdout_payload:
        return build_repo_docs_summary(stdout_payload)
    if label == "rebuild_sample_stack" and stdout_payload:
        return build_rebuild_summary(stdout_payload)
    if label == "validate_sample_workflow_blueprint" and stdout_payload:
        return build_blueprint_gate_summary(stdout_payload)
    if label in {"doctor_sample_stack", "doctor_current_stack", "doctor_latest_stack", "validate_latest_stack"} and stdout_payload:
        return build_validation_step_summary(label, stdout_payload, selection_summary)
    if label == "explain_latest_stack":
        return build_explain_step_summary(selection_summary, stdout, stderr, exit_code)

    fallback_headline = f"{STEP_HEADLINES.get(label, label.replace('_', ' '))}: {'ok' if exit_code == 0 else 'failed'}"
    details: list[str] = []
    if stdout_payload:
        summary_headline, validation_details = collect_validation_details(stdout_payload)
        details.append(summary_headline)
        details.extend(validation_details)
    elif stdout.strip():
        details.append(preview_text(stdout))
    elif stderr.strip():
        details.append(preview_text(stderr))
    return {"headline": fallback_headline, "details": details}


def should_keep_preview(exit_code: int, preview: str, compact_summary: dict[str, Any]) -> bool:
    if not preview:
        return False
    if exit_code != 0:
        return True
    headline = str(compact_summary.get("headline", "")).strip() if isinstance(compact_summary, dict) else ""
    details = compact_summary.get("details", []) if isinstance(compact_summary, dict) else []
    if not headline:
        return True
    if not isinstance(details, list) or not details:
        return True
    return False


def run_step(
    label: str,
    command: list[str],
    workdir: Path,
    logs_dir: Path,
    summary_json_path: str = "",
    keep_success_logs: bool = False,
) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=workdir, check=False, capture_output=True, text=True)
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    compact_summary = build_compact_summary(label, proc.stdout, proc.stderr, proc.returncode, summary_json_path)
    stdout_preview = preview_text(stdout)
    stderr_preview = preview_text(stderr)
    stdout_log_path = (
        write_log(logs_dir, label, "stdout", proc.stdout)
        if should_write_log(proc.returncode, proc.stdout, keep_success_logs)
        else ""
    )
    stderr_log_path = (
        write_log(logs_dir, label, "stderr", proc.stderr)
        if should_write_log(proc.returncode, proc.stderr, keep_success_logs)
        else ""
    )
    return {
        "label": label,
        "command": command,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "compact_summary": compact_summary,
        "stdout_preview": stdout_preview if should_keep_preview(proc.returncode, stdout_preview, compact_summary) else "",
        "stderr_preview": stderr_preview if should_keep_preview(proc.returncode, stderr_preview, compact_summary) else "",
        "stdout_log_path": stdout_log_path,
        "stderr_log_path": stderr_log_path,
        "summary_json_path": summary_json_path,
    }


def select_text_details(details: list[str], ok: bool) -> list[str]:
    if not details:
        return []
    if not ok:
        return [detail for detail in details if str(detail).strip()]

    max_selected = (
        4
        if any(
            str(detail).strip().startswith(("freshness warnings:", "freshness notes:", "refresh_hotspots:"))
            for detail in details
        )
        else 3
    )
    priorities = (
        "suite:",
        "blueprint:",
        "issues:",
        "/tmp exports:",
        "/tmp retention:",
        "stack_ref:",
        "release:",
        "rejections:",
        "signatures:",
        "freshness warnings:",
        "freshness notes:",
        "refresh_hotspots:",
        "failed checks:",
    )
    selected: list[str] = []
    seen: set[str] = set()
    for prefix in priorities:
        for detail in details:
            text = str(detail).strip()
            if text and text.startswith(prefix) and text not in seen:
                selected.append(text)
                seen.add(text)
                break
        if len(selected) >= max_selected:
            break
    if not selected:
        for detail in details:
            text = str(detail).strip()
            if text:
                selected.append(text)
            if len(selected) >= 2:
                break
    return selected


def render_text(report: dict[str, Any]) -> str:
    overall_status = "ok" if report.get("ok", False) else "fail"
    lines = ["# release_readiness", f"overall: {overall_status}"]
    output_root = str(report.get("output_root", "")).strip()
    if output_root:
        lines.append(f"output_root: {output_root}")
    sample_summary = str(report.get("sample_summary", "")).strip()
    if sample_summary:
        lines.append(f"sample_summary: {sample_summary}")
    if str(report.get("logs_dir", "")).strip() and Path(str(report.get("logs_dir"))).exists():
        lines.append(f"logs_dir: {report.get('logs_dir')}")
    lines.append("steps:")
    for step in report.get("steps", []):
        if not isinstance(step, dict):
            continue
        status = "ok" if step.get("ok", False) else "fail"
        headline = ""
        compact_summary = step.get("compact_summary", {})
        if isinstance(compact_summary, dict):
            headline = str(compact_summary.get("headline", "")).strip()
            details = compact_summary.get("details", [])
        else:
            details = []
        label = step.get("label", "unknown")
        lines.append(f"- {status} {label}: {headline or 'no summary'}")

        if isinstance(details, list):
            chosen_details = select_text_details([str(detail) for detail in details], ok=bool(step.get("ok", False)))
            if chosen_details:
                lines.append(f"  details: {' ; '.join(chosen_details)}")

        if not step.get("ok", False):
            lines.append(f"  command: {' '.join(str(item) for item in step.get('command', []))}")
            if step.get("exit_code", 0):
                lines.append(f"  exit_code: {step.get('exit_code')}")
            if step.get("stdout_preview"):
                lines.append(f"  stdout: {step.get('stdout_preview')}")
            if step.get("stderr_preview"):
                lines.append(f"  stderr: {step.get('stderr_preview')}")
            if step.get("summary_json_path"):
                lines.append(f"  summary_json: {step.get('summary_json_path')}")
            if step.get("stdout_log_path"):
                lines.append(f"  stdout_log: {step.get('stdout_log_path')}")
            if step.get("stderr_log_path"):
                lines.append(f"  stderr_log: {step.get('stderr_log_path')}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    logs_dir = output_root / "release-logs"

    sample_summary = output_root / "SAMPLE_STACK_SUMMARY.json"
    current_bundle = output_root / "working-clone-bundle"
    sample_blueprint = current_bundle / "workflow-blueprint-pipeline" / "workflow_blueprint.md"
    steps: list[dict[str, Any]] = []

    steps.append(
        run_step(
            "validate_repo_docs",
            ["python3", "scripts/validate_repo_docs.py", "--format", "json"],
            workdir,
            logs_dir,
            keep_success_logs=args.keep_success_logs,
        )
    )

    if not args.skip_tests:
        steps.append(
            run_step(
                "unit_tests",
                [
                    "python3",
                    "-m",
                    "unittest",
                    "tests/test_stack_discovery.py",
                    "tests/test_stack_validators.py",
                    "tests/test_stack_operator_flow.py",
                ],
                workdir,
                logs_dir,
                keep_success_logs=args.keep_success_logs,
            )
        )

    if not args.skip_rebuild:
        steps.append(
            run_step(
                "rebuild_sample_stack",
                ["python3", "scripts/rebuild_sample_stack.py", "--output-root", str(output_root)],
                workdir,
                logs_dir,
                keep_success_logs=args.keep_success_logs,
            )
        )

    steps.append(
        run_step(
            "validate_sample_workflow_blueprint",
            [
                "python3",
                "scripts/clone_ops.py",
                "validate",
                "workflow-blueprint",
                "--input",
                str(sample_blueprint),
                "--format",
                "json",
            ],
            workdir,
            logs_dir,
            keep_success_logs=args.keep_success_logs,
        )
    )

    doctor_sample_summary = str(output_root / "release_doctor_sample_stack.json")
    steps.append(
        run_step(
            "doctor_sample_stack",
            [
                "python3",
                "scripts/clone_ops.py",
                "doctor",
                "sample-stack",
                "--sample-summary",
                str(sample_summary),
                "--summary-json",
                doctor_sample_summary,
            ],
            workdir,
            logs_dir,
            summary_json_path=doctor_sample_summary,
            keep_success_logs=args.keep_success_logs,
        )
    )

    doctor_current_summary = str(output_root / "release_doctor_current_stack.json")
    steps.append(
        run_step(
            "doctor_current_stack",
            [
                "python3",
                "scripts/clone_ops.py",
                "doctor",
                "current-stack",
                "--bundle-dir",
                str(current_bundle),
                "--summary-json",
                doctor_current_summary,
            ],
            workdir,
            logs_dir,
            summary_json_path=doctor_current_summary,
            keep_success_logs=args.keep_success_logs,
        )
    )

    pinned_latest_stack_summary = write_pinned_latest_stack_summary(workdir, output_root)

    doctor_latest_summary = str(output_root / "release_doctor_latest_stack.json")
    steps.append(
        run_step(
            "doctor_latest_stack",
            [
                "python3",
                "scripts/clone_ops.py",
                "doctor",
                "latest-stack",
                "--stack-summary",
                pinned_latest_stack_summary,
                "--explain",
                "--summary-json",
                doctor_latest_summary,
            ],
            workdir,
            logs_dir,
            summary_json_path=doctor_latest_summary,
            keep_success_logs=args.keep_success_logs,
        )
    )

    validate_latest_summary = str(output_root / "release_validate_latest_stack.json")
    steps.append(
        run_step(
            "validate_latest_stack",
            [
                "python3",
                "scripts/clone_ops.py",
                "validate",
                "latest-stack",
                "--stack-summary",
                pinned_latest_stack_summary,
                "--summary-json",
                validate_latest_summary,
            ],
            workdir,
            logs_dir,
            summary_json_path=validate_latest_summary,
            keep_success_logs=args.keep_success_logs,
        )
    )

    explain_latest_summary = str(output_root / "release_explain_latest_stack.json")
    steps.append(
        run_step(
            "explain_latest_stack",
            [
                "python3",
                "scripts/clone_ops.py",
                "explain",
                "latest-stack",
                "--stack-summary",
                pinned_latest_stack_summary,
                "--summary-json",
                explain_latest_summary,
            ],
            workdir,
            logs_dir,
            summary_json_path=explain_latest_summary,
            keep_success_logs=args.keep_success_logs,
        )
    )

    report = {
        "output_root": str(output_root),
        "logs_dir": str(logs_dir),
        "sample_summary": str(sample_summary),
        "sample_workflow_blueprint": str(sample_blueprint),
        "skip_tests": args.skip_tests,
        "skip_rebuild": args.skip_rebuild,
        "keep_success_logs": args.keep_success_logs,
        "steps": steps,
        "ok": all(step.get("ok", False) for step in steps),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_text(report)
    print(rendered)
    if args.summary_json:
        Path(args.summary_json).resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
