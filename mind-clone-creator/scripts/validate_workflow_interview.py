#!/usr/bin/env python3
"""Validate W1-W7 workflow interview readiness for draft/final release guidance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from plan_clone_interview_next import WORKFLOW_ITEMS, evaluate_sections


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate workflow interview readiness.")
    parser.add_argument("--interview", required=True, help="Path to workflow_interview.md")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def build_report(progress: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    for item in progress.get("section_statuses", []):
        if not isinstance(item, dict) or item.get("final_ready", False):
            continue
        reasons = item.get("reasons", [])
        blockers.append(
            {
                "section": str(item.get("section", "")).strip() or "<unknown>",
                "reason": "、".join(str(x) for x in reasons if str(x).strip()) or "未最终确认",
                "override_status": str(item.get("override_status", "")).strip(),
            }
        )
    final_ready = bool(progress.get("final_ready", False))
    return {
        "interview_exists": bool(progress.get("exists", False)),
        "answered": int(progress.get("answered", 0)),
        "sufficient": int(progress.get("sufficient", 0)),
        "final_ready_count": int(progress.get("final_ready_count", 0)),
        "total": int(progress.get("total", 0)),
        "ready": bool(progress.get("ready", False)),
        "final_ready": final_ready,
        "recommended_release": "final" if final_ready else "draft",
        "next_item": progress.get("next_item"),
        "blockers": blockers,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "# workflow_interview_validation",
        "",
        f"interview_exists: {str(report['interview_exists']).lower()}",
        f"ready: {str(report['ready']).lower()}",
        f"final_ready: {str(report['final_ready']).lower()}",
        f"recommended_release: {report['recommended_release']}",
        f"answered: {report['answered']} / {report['total']}",
        f"sufficient: {report['sufficient']} / {report['total']}",
        f"final_ready_count: {report['final_ready_count']} / {report['total']}",
        "",
        "blockers:",
    ]
    if not report["blockers"]:
        lines.append("- none")
    for item in report["blockers"]:
        suffix = f" (override={item['override_status']})" if item.get("override_status") else ""
        lines.append(f"- {item['section']}: {item['reason']}{suffix}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    interview_path = Path(args.interview).resolve()
    progress = evaluate_sections(interview_path, WORKFLOW_ITEMS, kind="workflow")
    report = build_report(progress)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
