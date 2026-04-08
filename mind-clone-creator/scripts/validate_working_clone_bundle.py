#!/usr/bin/env python3
"""Validate combined working-clone bundle readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from workflow_target_utils import infer_workflow_target_defined
except ModuleNotFoundError:
    from scripts.workflow_target_utils import infer_workflow_target_defined


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def collect_pending_details(state: dict[str, Any], bucket: str) -> list[dict[str, str]]:
    progress_key = "personal_progress" if bucket == "personal" else "workflow_progress"
    progress = state.get(progress_key, {}) if isinstance(state.get(progress_key, {}), dict) else {}
    section_statuses = progress.get("section_statuses", []) if isinstance(progress.get("section_statuses", []), list) else []
    details: list[dict[str, str]] = []
    for item in section_statuses:
        if not isinstance(item, dict) or item.get("final_ready", False):
            continue
        strategy = item.get("follow_up_strategy", {}) if isinstance(item.get("follow_up_strategy", {}), dict) else {}
        details.append(
            {
                "section": str(item.get("section", "")).strip(),
                "reason": "、".join(str(x) for x in item.get("reasons", []) if str(x).strip()) or "未最终确认",
                "follow_up_question": str(strategy.get("question", "")).strip(),
                "example_hint": str(strategy.get("example_hint", "")).strip(),
            }
        )
    return details
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate working clone bundle readiness.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def validate(manifest: dict[str, Any]) -> dict[str, Any]:
    steps = manifest.get("steps", {}) if isinstance(manifest.get("steps", {}), dict) else {}
    interview_validation = (
        manifest.get("interview_validation", {}) if isinstance(manifest.get("interview_validation", {}), dict) else {}
    )
    workflow_enabled = bool(steps.get("workflow_enabled", False))
    workflow_target_defined = infer_workflow_target_defined(manifest, steps) if workflow_enabled else True
    blockers: list[dict[str, str]] = []
    detailed_interview_blockers = (
        interview_validation.get("blockers", []) if isinstance(interview_validation.get("blockers", []), list) else []
    )
    interview_state_path = str(manifest.get("interview_state", "")).strip()
    interview_state = load_json(Path(interview_state_path)) if interview_state_path and Path(interview_state_path).exists() else {}
    personal_pending_details = collect_pending_details(interview_state, "personal")
    workflow_pending_details = collect_pending_details(interview_state, "workflow")
    personal_sections = [
        item["section"]
        for item in personal_pending_details
        if item.get("section")
    ]
    workflow_sections = [
        item["section"]
        for item in workflow_pending_details
        if item.get("section")
    ]
    if not personal_sections:
        personal_sections = [
            str(item.get("section", "")).strip()
            for item in detailed_interview_blockers
            if isinstance(item, dict) and str(item.get("scope", "")).strip() == "personal" and str(item.get("section", "")).strip()
        ]
    if not workflow_sections:
        workflow_sections = [
            str(item.get("section", "")).strip()
            for item in detailed_interview_blockers
            if isinstance(item, dict) and str(item.get("scope", "")).strip() == "workflow" and str(item.get("section", "")).strip()
        ]

    if not bool(steps.get("personal_clone_skill", False)):
        blockers.append({"scope": "bundle", "item": "personal_clone_skill", "reason": "人格层 skill 尚未生成"})

    if not bool(interview_validation.get("personal_final_ready", False)):
        reason = "人格访谈尚未 final-ready"
        if personal_sections:
            reason += f"（待补 section: {', '.join(personal_sections)}）"
        blockers.append({"scope": "interview", "item": "personal", "reason": reason})

    if workflow_enabled and not workflow_target_defined:
        blockers.append(
            {
                "scope": "workflow",
                "item": "workflow_target",
                "reason": "工作流目标尚未明确；先在 workflow_interview.md 顶部确认 target_work_unit。",
            }
        )

    if workflow_enabled and workflow_target_defined:
        if not bool(interview_validation.get("workflow_final_ready", False)):
            reason = "工作流访谈尚未 final-ready"
            if workflow_sections:
                reason += f"（待补 section: {', '.join(workflow_sections)}）"
            blockers.append({"scope": "interview", "item": "workflow", "reason": reason})
        if not bool(steps.get("workflow_pipeline", False)):
            blockers.append({"scope": "bundle", "item": "workflow_pipeline", "reason": "workflow blueprint 管线尚未完成"})
        if not bool(steps.get("workflow_clone_skill", False)):
            blockers.append({"scope": "bundle", "item": "workflow_clone_skill", "reason": "workflow clone skill 尚未生成"})
        if not bool(steps.get("workflow_runtime_bundle", False)):
            blockers.append({"scope": "bundle", "item": "workflow_runtime_bundle", "reason": "workflow runtime bundle 尚未生成"})

    final_ready = not blockers
    return {
        "workflow_enabled": workflow_enabled,
        "workflow_target_defined": workflow_target_defined,
        "final_ready": final_ready,
        "recommended_release": "final" if final_ready else "draft",
        "personal_final_ready": bool(interview_validation.get("personal_final_ready", False)),
        "workflow_final_ready": bool(interview_validation.get("workflow_final_ready", False)) if workflow_enabled else True,
        "personal_clone_ready": bool(steps.get("personal_clone_skill", False)),
        "workflow_pipeline_ready": bool(steps.get("workflow_pipeline", False)) if workflow_enabled else True,
        "workflow_clone_skill_ready": bool(steps.get("workflow_clone_skill", False)) if workflow_enabled else True,
        "workflow_runtime_bundle_ready": bool(steps.get("workflow_runtime_bundle", False)) if workflow_enabled else True,
        "personal_interview_sections_pending": personal_sections,
        "workflow_interview_sections_pending": workflow_sections,
        "personal_pending_details": personal_pending_details,
        "workflow_pending_details": workflow_pending_details,
        "blockers": blockers,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "# working_clone_bundle_validation",
        "",
        f"workflow_enabled: {str(report['workflow_enabled']).lower()}",
        f"workflow_target_defined: {str(report['workflow_target_defined']).lower()}",
        f"final_ready: {str(report['final_ready']).lower()}",
        f"recommended_release: {report['recommended_release']}",
        f"personal_final_ready: {str(report['personal_final_ready']).lower()}",
        f"workflow_final_ready: {str(report['workflow_final_ready']).lower()}",
        f"personal_clone_ready: {str(report['personal_clone_ready']).lower()}",
        f"workflow_pipeline_ready: {str(report['workflow_pipeline_ready']).lower()}",
        f"workflow_clone_skill_ready: {str(report['workflow_clone_skill_ready']).lower()}",
        f"workflow_runtime_bundle_ready: {str(report['workflow_runtime_bundle_ready']).lower()}",
        f"personal_interview_sections_pending: {', '.join(report['personal_interview_sections_pending']) or 'none'}",
        f"workflow_interview_sections_pending: {', '.join(report['workflow_interview_sections_pending']) or 'none'}",
        "",
        "pending_details:",
    ]
    if not report["personal_pending_details"] and not report["workflow_pending_details"]:
        lines.append("- none")
    for scope, items in [("personal", report["personal_pending_details"]), ("workflow", report["workflow_pending_details"])]:
        for item in items:
            hint = f" | hint={item['example_hint']}" if item.get("example_hint") else ""
            question = item.get("follow_up_question", "") or "无"
            lines.append(f"- [{scope}] {item['section']}: reason={item['reason']} | question={question}{hint}")
    lines.extend(
        [
            "",
        "blockers:",
        ]
    )
    if not report["blockers"]:
        lines.append("- none")
    for item in report["blockers"]:
        lines.append(f"- [{item['scope']}] {item['item']}: {item['reason']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = validate(load_json(Path(args.manifest).resolve()))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
