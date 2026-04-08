#!/usr/bin/env python3
"""Validate clone interview state for draft/final build readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate clone interview state.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def collect_blockers(progress: dict[str, Any], label: str) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if not isinstance(progress, dict):
        return blockers
    for item in progress.get("section_statuses", []):
        if not isinstance(item, dict):
            continue
        if item.get("final_ready", False):
            continue
        section = str(item.get("section", "")).strip() or "<unknown>"
        reasons = item.get("reasons", [])
        reason_text = "、".join(str(x) for x in reasons if str(x).strip()) or "未最终确认"
        blockers.append(
            {
                "scope": label,
                "section": section,
                "reason": reason_text,
                "override_status": str(item.get("override_status", "")).strip(),
            }
        )
    return blockers


def validate(state: dict[str, Any]) -> dict[str, Any]:
    personal = state.get("personal_progress", {}) if isinstance(state.get("personal_progress", {}), dict) else {}
    workflow = state.get("workflow_progress", {}) if isinstance(state.get("workflow_progress", {}), dict) else {}
    personal_final_ready = bool(personal.get("final_ready", False))
    workflow_exists = bool(workflow)
    workflow_final_ready = bool(workflow.get("final_ready", False)) if workflow_exists else True
    blockers = collect_blockers(personal, "personal") + collect_blockers(workflow, "workflow")
    final_ready = personal_final_ready and workflow_final_ready
    recommended_release = "final" if final_ready else "draft"
    return {
        "final_ready": final_ready,
        "recommended_release": recommended_release,
        "personal_final_ready": personal_final_ready,
        "workflow_final_ready": workflow_final_ready,
        "has_workflow": workflow_exists,
        "blockers": blockers,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "# clone_interview_state_validation",
        "",
        f"final_ready: {str(report['final_ready']).lower()}",
        f"recommended_release: {report['recommended_release']}",
        f"personal_final_ready: {str(report['personal_final_ready']).lower()}",
        f"workflow_final_ready: {str(report['workflow_final_ready']).lower()}",
        "",
        "blockers:",
    ]
    if not report["blockers"]:
        lines.append("- none")
    for item in report["blockers"]:
        suffix = f" (override={item['override_status']})" if item.get("override_status") else ""
        lines.append(f"- [{item['scope']}] {item['section']}: {item['reason']}{suffix}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = validate(load_json(Path(args.input).resolve()))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
