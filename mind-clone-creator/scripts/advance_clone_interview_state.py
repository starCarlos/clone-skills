#!/usr/bin/env python3
"""Advance clone interview state based on the latest interview files."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


UTC_PLUS_8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(UTC_PLUS_8).isoformat(timespec="seconds")


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advance clone interview state.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--personal-interview", required=True)
    parser.add_argument("--workflow-interview")
    parser.add_argument("--input", default="")
    parser.add_argument(
        "--user-action",
        default="answer",
        choices=["answer", "confirm", "accept_for_now", "accept_final", "revise", "skip"],
        help="Semantic action for this interview turn.",
    )
    parser.add_argument("--output-state", required=True)
    parser.add_argument("--output-summary", required=True)
    return parser.parse_args()


def classify_turn_outcome(user_action: str, previous: dict[str, Any], status: dict[str, Any]) -> str:
    if user_action == "confirm":
        user_action = "accept_for_now"
    previous_section = str(previous.get("current_section", "")).strip()
    next_section = str(status.get("next_item", {}).get("section", "")).strip()
    next_assessment = str(status.get("next_item", {}).get("assessment", "")).strip()
    if status.get("overall_status") == "ready_for_build":
        return "ready_for_build"
    if user_action == "accept_final":
        if previous_section and previous_section != next_section:
            return "accepted_final_and_advanced"
        if next_assessment == "sufficient":
            return "accepted_final_sufficient"
        return "accept_final_but_still_needs_content"
    if user_action == "accept_for_now":
        if previous_section and previous_section != next_section:
            return "accepted_for_now_and_advanced"
        if next_assessment == "sufficient":
            return "accepted_for_now_sufficient"
        return "accept_for_now_but_still_needs_content"
    if user_action == "revise":
        if previous_section and previous_section == next_section:
            return "revision_requested_same_section"
        return "revision_shifted_focus"
    if user_action == "skip":
        return "skipped_current_section"
    if previous_section and previous_section != next_section:
        return "answered_and_advanced"
    if next_assessment == "insufficient":
        return "answered_but_follow_up_needed"
    if next_assessment == "missing":
        return "no_effect_still_missing"
    return "answered_no_state_change"


def normalize_section_bucket(section: str) -> str:
    return "workflow" if section.startswith("W") else "personal"


def update_section_overrides(previous: dict[str, Any], user_action: str) -> dict[str, Any]:
    if user_action == "confirm":
        user_action = "accept_for_now"
    raw = previous.get("section_overrides", {})
    overrides = raw if isinstance(raw, dict) else {}
    personal = overrides.get("personal", {})
    workflow = overrides.get("workflow", {})
    if not isinstance(personal, dict):
        personal = {}
    if not isinstance(workflow, dict):
        workflow = {}
    current_section = str(previous.get("current_section", "")).strip()
    current_assessment = str(previous.get("current_assessment", "")).strip()
    if not current_section:
        return {"personal": personal, "workflow": workflow}
    target = workflow if normalize_section_bucket(current_section) == "workflow" else personal
    if user_action in {"accept_for_now", "accept_final"} and current_assessment in {"missing", "insufficient"}:
        target[current_section] = {
            "status": "accepted_final" if user_action == "accept_final" else "accepted_for_now",
            "reason": "人工确认最终通过" if user_action == "accept_final" else "人工确认先通过",
            "confirmed_from_assessment": current_assessment,
            "updated_at": now_iso(),
        }
    elif user_action == "revise":
        target.pop(current_section, None)
    return {"personal": personal, "workflow": workflow}


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    previous = load_json(Path(args.state).resolve())
    status_path = Path(args.output_summary).resolve().parent / "clone_interview_status.next.json"

    command = [
        "python3",
        str(workdir / "scripts" / "plan_clone_interview_next.py"),
        "--personal-interview",
        str(Path(args.personal_interview).resolve()),
        "--state",
        str(Path(args.state).resolve()),
        "--output-json",
        str(status_path),
    ]
    if args.workflow_interview:
        command.extend(["--workflow-interview", str(Path(args.workflow_interview).resolve())])
    run_command(command, workdir)
    status = load_json(status_path)

    history = previous.get("history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "turn": int(previous.get("turn_count", 0)) + 1,
            "user_action": args.user_action,
            "input": args.input,
            "status": status.get("overall_status", ""),
            "current_section": status.get("next_item", {}).get("section", ""),
            "updated_at": now_iso(),
        }
    )
    section_overrides = update_section_overrides(previous, args.user_action)

    if args.user_action in {"confirm", "accept_for_now", "accept_final", "revise"}:
        preview_state = Path(args.output_summary).resolve().parent / "clone_interview_state.override-preview.json"
        preview_status = Path(args.output_summary).resolve().parent / "clone_interview_status.override.json"
        preview_state.write_text(
            json.dumps({**previous, "section_overrides": section_overrides}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        preview_command = [
            "python3",
            str(workdir / "scripts" / "plan_clone_interview_next.py"),
            "--personal-interview",
            str(Path(args.personal_interview).resolve()),
            "--state",
            str(preview_state),
            "--output-json",
            str(preview_status),
        ]
        if args.workflow_interview:
            preview_command.extend(["--workflow-interview", str(Path(args.workflow_interview).resolve())])
        run_command(preview_command, workdir)
        status = load_json(preview_status)

    turn_outcome = classify_turn_outcome(args.user_action, previous, status)

    next_state = {
        **previous,
        "status": status.get("overall_status", "needs_personal_interview"),
        "last_user_action": args.user_action,
        "personal_interview": str(Path(args.personal_interview).resolve()),
        "workflow_interview": str(Path(args.workflow_interview).resolve()) if args.workflow_interview else "",
        "section_overrides": section_overrides,
        "turn_count": int(previous.get("turn_count", 0)) + 1,
        "current_target_file": status.get("next_target_file", ""),
        "current_section": status.get("next_item", {}).get("section", ""),
        "current_phase": status.get("next_item", {}).get("phase", ""),
        "current_prompt": status.get("next_item", {}).get("prompt", ""),
        "prompt_reference": status.get("next_item", {}).get("guide", ""),
        "current_assessment": status.get("next_item", {}).get("assessment", ""),
        "current_reasons": status.get("next_item", {}).get("reasons", []),
        "current_follow_up_strategy": status.get("next_item", {}).get("follow_up_strategy", {}),
        "current_override_applied": status.get("next_item", {}).get("override_applied", False),
        "current_override_status": status.get("next_item", {}).get("override_status", ""),
        "current_final_ready": status.get("next_item", {}).get("final_ready", False),
        "turn_outcome": turn_outcome,
        "personal_progress": status.get("personal", {}),
        "workflow_progress": status.get("workflow", {}),
        "history": history,
        "last_updated_at": now_iso(),
    }
    summary = {
        "status": next_state["status"],
        "turn_count": next_state["turn_count"],
        "last_user_action": args.user_action,
        "turn_outcome": turn_outcome,
        "current_phase": next_state["current_phase"],
        "current_section": next_state["current_section"],
        "current_target_file": next_state["current_target_file"],
        "current_prompt": next_state["current_prompt"],
        "prompt_reference": next_state["prompt_reference"],
        "current_assessment": next_state["current_assessment"],
        "current_reasons": next_state["current_reasons"],
        "current_follow_up_strategy": next_state["current_follow_up_strategy"],
        "current_override_applied": next_state["current_override_applied"],
        "current_override_status": next_state["current_override_status"],
        "current_final_ready": next_state["current_final_ready"],
        "section_overrides": next_state["section_overrides"],
        "personal_progress": next_state["personal_progress"],
        "workflow_progress": next_state["workflow_progress"],
    }

    Path(args.output_state).resolve().write_text(
        json.dumps(next_state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_summary).resolve().write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
