#!/usr/bin/env python3
"""Initialize interview state for persona/workflow clone creation."""

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
    parser = argparse.ArgumentParser(description="Initialize clone interview state.")
    parser.add_argument("--personal-interview", required=True)
    parser.add_argument("--workflow-interview")
    parser.add_argument("--output", required=True)
    parser.add_argument("--clone-name", default="未命名分身")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_path = Path(args.output).resolve()
    status_path = output_path.parent / (output_path.stem + ".status.json")

    command = [
        "python3",
        str(workdir / "scripts" / "plan_clone_interview_next.py"),
        "--personal-interview",
        str(Path(args.personal_interview).resolve()),
        "--output-json",
        str(status_path),
    ]
    if args.workflow_interview:
        command.extend(["--workflow-interview", str(Path(args.workflow_interview).resolve())])
    run_command(command, workdir)
    status = load_json(status_path)

    state = {
        "clone_name": args.clone_name,
        "status": status.get("overall_status", "needs_personal_interview"),
        "last_user_action": "init",
        "personal_interview": str(Path(args.personal_interview).resolve()),
        "workflow_interview": str(Path(args.workflow_interview).resolve()) if args.workflow_interview else "",
        "section_overrides": {
            "personal": {},
            "workflow": {},
        },
        "turn_count": 0,
        "current_target_file": status.get("next_target_file", ""),
        "current_section": status.get("next_item", {}).get("section", ""),
        "current_phase": status.get("next_item", {}).get("phase", ""),
        "current_prompt": status.get("next_item", {}).get("prompt", ""),
        "prompt_reference": status.get("next_item", {}).get("guide", ""),
        "current_assessment": status.get("next_item", {}).get("assessment", ""),
        "current_reasons": status.get("next_item", {}).get("reasons", []),
        "current_follow_up_strategy": status.get("next_item", {}).get("follow_up_strategy", {}),
        "current_override_status": status.get("next_item", {}).get("override_status", ""),
        "current_final_ready": status.get("next_item", {}).get("final_ready", False),
        "personal_progress": status.get("personal", {}),
        "workflow_progress": status.get("workflow", {}),
        "history": [],
        "last_updated_at": now_iso(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
